"""Score N meshes of one capture against photographs none of them was built to fit.

WHY THIS EXISTS. Every other measurement available on these meshes is either absolute
(how much loose debris, how many holes) or relative (how far mesh A sits from mesh B).
None of them can say which mesh is RIGHT, because no ground-truth scan of a Rabati
sherd exists. This one can, without a reference mesh: render each mesh from the
cameras of the HELD-OUT photographs and compare its outline with the sherd mask in
that photograph. A shape that explains pictures it was never fitted to is a better
shape, and the question is answerable with what we already have.

WHAT IT DOES NOT SAY. A silhouette is an outline. It is blind to relief inside the
outline, so a mesh can score well here and still have smoothed a fracture edge away
(OpenMVS does exactly that on one A02 sherd). Read this beside the surface
measurements, never instead of them.

TWO TRAPS, BOTH ALREADY PAID FOR IN THIS PROJECT.

  SCALE. The *_mm.ply meshes have been multiplied by mm-per-unit and are no longer in
  the cameras' frame. Rendering those would produce a confident, meaningless number.
  Pass the UNSCALED meshes, and this script checks the extents agree before scoring.

  MASK RESOLUTION. The SAM 3 masks are made at the camera's full 5568 px; the meshes
  come from undistorted 3200 px images. A mask that has not been through
  undistort_masks.sh does not line up with these cameras, and the mismatch looks like
  a bad reconstruction rather than a bad mask. This script refuses if mask and image
  dimensions disagree.

Usage:
    python scripts/silhouette_compare.py \\
        --dense   <work>/dense_masked \\
        --masks   <undistorted mask dir, COLMAP naming: NAME.JPG.png> \\
        --capture <MILo>/data/17062025/A02/capture.json \\
        --out     <MILo>/output/17062025/A02/silhouette \\
        --mesh openmvs=<...>/scene_refined_mesh.ply \\
        --mesh delaunay=<...>/colmap_delaunay_mesh.ply \\
        --mesh poisson=<...>/colmap_poisson_mesh.ply \\
        --mesh milo=<...>/mesh_learnable_sdf.ply
"""
from __future__ import annotations

import argparse
import json
import struct
import sys
from pathlib import Path

import numpy as np
import trimesh
from PIL import Image

# Below this, the most likely explanation is a broken camera convention in this
# script, not four independently bad reconstructions. Say so rather than rank them.
SUSPECT_IOU = 0.5


# ------------------------------------------------------------------ COLMAP (undistorted)
def read_cameras(path: Path) -> dict:
    out = {}
    with open(path, "rb") as f:
        (n,) = struct.unpack("<Q", f.read(8))
        for _ in range(n):
            cid, model, w, h = struct.unpack("<iiQQ", f.read(24))
            npar = {0: 3, 1: 4, 2: 4, 3: 5, 4: 8}.get(model, 4)
            par = struct.unpack("<" + "d" * npar, f.read(8 * npar))
            out[cid] = dict(model=model, w=int(w), h=int(h), params=par)
    return out


def read_images(path: Path) -> dict:
    out = {}
    with open(path, "rb") as f:
        (n,) = struct.unpack("<Q", f.read(8))
        for _ in range(n):
            (_, qw, qx, qy, qz, tx, ty, tz, cid) = struct.unpack("<idddddddi", f.read(64))
            nm = b""
            while (c := f.read(1)) != b"\x00":
                nm += c
            (p,) = struct.unpack("<Q", f.read(8))
            f.seek(24 * p, 1)
            R = np.array([
                [1 - 2 * (qy * qy + qz * qz), 2 * (qx * qy - qz * qw), 2 * (qx * qz + qy * qw)],
                [2 * (qx * qy + qz * qw), 1 - 2 * (qx * qx + qz * qz), 2 * (qy * qz - qx * qw)],
                [2 * (qx * qz - qy * qw), 2 * (qy * qz + qx * qw), 1 - 2 * (qx * qx + qy * qy)]])
            out[nm.decode()] = dict(R=R, t=np.array([tx, ty, tz]), cam=cid)
    return out


def pinhole(cam) -> tuple:
    if cam["model"] == 1:                      # PINHOLE
        fx, fy, cx, cy = cam["params"][:4]
    elif cam["model"] == 0:                    # SIMPLE_PINHOLE
        f_, cx, cy = cam["params"][:3]
        fx = fy = f_
    else:
        raise SystemExit(
            f"camera model {cam['model']} is not pinhole, so these views were never "
            "undistorted. Point --dense at the undistorted workspace.")
    return float(fx), float(fy), float(cx), float(cy)


def view_matrix(im) -> np.ndarray:
    """World -> OpenGL camera (x right, y up, -z forward)."""
    m = np.eye(4)
    m[:3, :3] = im["R"]
    m[:3, 3] = im["t"]
    return np.diag([1.0, -1.0, -1.0, 1.0]) @ m


def projection(fx, fy, cx, cy, w, h, znear, zfar) -> np.ndarray:
    p = np.zeros((4, 4))
    p[0, 0] = 2.0 * fx / w
    p[1, 1] = 2.0 * fy / h
    p[0, 2] = 1.0 - 2.0 * cx / w
    p[1, 2] = 2.0 * cy / h - 1.0
    p[2, 2] = -(zfar + znear) / (zfar - znear)
    p[2, 3] = -2.0 * zfar * znear / (zfar - znear)
    p[3, 2] = -1.0
    return p


# ------------------------------------------------------------------------------ raster
class Renderer:
    def __init__(self):
        try:
            import torch
            import nvdiffrast.torch as dr
        except ImportError as exc:
            raise SystemExit(
                f"nvdiffrast/torch unavailable ({exc}). Run inside the MILo conda "
                "environment on a GPU node.")
        self.torch, self.dr = torch, dr
        # CUDA context, not GL: the compute nodes are headless.
        self.ctx = dr.RasterizeCudaContext()

    def mask(self, verts, faces, mvp, w, h) -> np.ndarray:
        torch, dr = self.torch, self.dr
        v = torch.as_tensor(verts, device="cuda")
        f = torch.as_tensor(faces, device="cuda")
        mvp_t = torch.as_tensor(mvp.astype(np.float32), device="cuda")
        vh = torch.cat([v, torch.ones_like(v[:, :1])], dim=1)
        clip = (vh @ mvp_t.T)[None]
        rh, rw = (h + 7) // 8 * 8, (w + 7) // 8 * 8       # nvdiffrast wants multiples of 8
        rast, _ = dr.rasterize(self.ctx, clip, f, resolution=[rh, rw])
        out = (rast[0, :h, :w, 3] > 0).detach().cpu().numpy()
        return np.flipud(out)                             # row 0 is the bottom


def overlay(pred, gt, path: Path):
    """Green agreed, red the mesh invents material, blue the mesh misses it."""
    h, w = gt.shape
    img = np.zeros((h, w, 3), np.uint8)
    img[pred & gt] = (40, 180, 60)
    img[pred & ~gt] = (200, 40, 40)
    img[~pred & gt] = (40, 80, 200)
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(img).save(path)


def load_mesh(p: Path):
    m = trimesh.load(p, process=False, force="mesh")
    if isinstance(m, trimesh.Scene):
        m = trimesh.util.concatenate(tuple(m.geometry.values()))
    m.metadata = {}
    return (np.ascontiguousarray(m.vertices, np.float32),
            np.ascontiguousarray(m.faces, np.int32),
            np.ptp(np.asarray(m.vertices), axis=0))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dense", required=True, type=Path)
    ap.add_argument("--masks", required=True, type=Path)
    ap.add_argument("--capture", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--mesh", action="append", required=True,
                    metavar="tag=path", help="repeat once per mesh")
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    meshes = {}
    for spec in args.mesh:
        tag, _, p = spec.partition("=")
        if not p:
            raise SystemExit(f"--mesh wants tag=path, got {spec!r}")
        meshes[tag] = Path(p)

    cams = read_cameras(args.dense / "sparse" / "cameras.bin")
    imgs = read_images(args.dense / "sparse" / "images.bin")
    held = json.loads(args.capture.read_text())["held_out_views"]
    print(f"model: {len(imgs)} views, {len(cams)} camera(s); {len(held)} held out")

    # TRAP 2: refuse rather than score against masks that do not match these cameras.
    cam0 = cams[next(iter(cams))]
    probe = None
    for nm in held:
        cand = args.masks / f"{nm}.png"
        if cand.exists():
            probe = cand
            break
    if probe is None:
        raise SystemExit(
            f"No mask found for any held-out view in {args.masks}. Expected COLMAP "
            "naming, e.g. A21_0891.JPG.png. Run scripts/undistort_masks.sh first.")
    mw, mh = Image.open(probe).size
    if (mw, mh) != (cam0["w"], cam0["h"]):
        raise SystemExit(
            f"Mask is {mw}x{mh} but the cameras are {cam0['w']}x{cam0['h']}.\n"
            "These masks have not been through undistort_masks.sh, so they do not line "
            "up with the meshes' cameras. Scoring them would blame the reconstruction "
            "for a mask that was never aligned.")
    print(f"masks match cameras at {mw}x{mh}")

    report = {"capture": str(args.capture), "n_held_out": len(held), "meshes": {}}
    extents = {}

    for tag, path in meshes.items():
        verts, faces, ext = load_mesh(path)
        extents[tag] = ext
        print(f"\n=== {tag} === {len(verts):,} verts, {len(faces):,} faces, "
              f"extent {np.round(ext, 4)}")
        renderer = getattr(main, "_r", None) or Renderer()
        main._r = renderer

        rows = []
        for k, nm in enumerate(held):
            im = imgs.get(nm)
            mp = args.masks / f"{nm}.png"
            if im is None or not mp.exists():
                continue
            gt = np.asarray(Image.open(mp).convert("L")) > 127
            h, w = gt.shape
            fx, fy, cx, cy = pinhole(cams[im["cam"]])
            diag = float(np.linalg.norm(ext))
            mvp = projection(fx, fy, cx, cy, w, h,
                             diag * 1e-3, diag * 1e3) @ view_matrix(im)
            pred = renderer.mask(verts, faces, mvp, w, h)
            inter = int(np.logical_and(pred, gt).sum())
            union = int(np.logical_or(pred, gt).sum())
            rows.append({
                "view": nm,
                "iou": inter / union if union else 0.0,
                # Split the error: invented material and missing material mean
                # opposite things for a reconstruction.
                "excess_frac": float(np.logical_and(pred, ~gt).sum() / max(gt.sum(), 1)),
                "missing_frac": float(np.logical_and(~pred, gt).sum() / max(gt.sum(), 1)),
            })
            if k < 3:
                overlay(pred, gt, args.out / f"overlay_{tag}_{Path(nm).stem}.png")

        if not rows:
            print("  no scorable views")
            continue
        iou = np.array([r["iou"] for r in rows])
        report["meshes"][tag] = {
            "n_views": len(rows),
            "iou_mean": float(iou.mean()),
            "iou_min": float(iou.min()),
            "excess_mean": float(np.mean([r["excess_frac"] for r in rows])),
            "missing_mean": float(np.mean([r["missing_frac"] for r in rows])),
            "per_view": rows,
        }
        m = report["meshes"][tag]
        print(f"  outline matches held-out photographs {m['iou_mean']:.1%} on average "
              f"(worst {m['iou_min']:.1%}, {m['n_views']} views)")
        print(f"  invents {m['excess_mean']:.1%} of the masked area, "
              f"misses {m['missing_mean']:.1%}")

    # TRAP 1: unequal extents mean at least one mesh is not in the cameras' frame.
    if len(extents) > 1:
        diags = {t: float(np.linalg.norm(e)) for t, e in extents.items()}
        lo, hi = min(diags.values()), max(diags.values())
        report["extent_diagonals"] = diags
        if hi / max(lo, 1e-9) > 1.5:
            print(f"\nWARNING: mesh sizes differ by {hi/lo:.2f}x {diags}.\n"
                  "At least one is not in the cameras' frame - most likely a scaled "
                  "*_mm.ply was passed. Its score below is meaningless.")

    (args.out / "silhouette.json").write_text(json.dumps(report, indent=2))
    scored = report["meshes"]
    if scored:
        best = max(scored, key=lambda t: scored[t]["iou_mean"])
        worst_iou = min(scored[t]["iou_mean"] for t in scored)
        print("\n" + "=" * 72)
        for t in sorted(scored, key=lambda t: -scored[t]["iou_mean"]):
            s = scored[t]
            print(f"  {t:10s} outline agreement {s['iou_mean']:.1%}   "
                  f"invents {s['excess_mean']:.1%}   misses {s['missing_mean']:.1%}")
        if worst_iou < SUSPECT_IOU:
            print(f"\nAll four score below {SUSPECT_IOU:.0%} at worst. Before concluding "
                  "anything, check the overlays: a renderer pointing the wrong way, or a "
                  "mask covering different objects from the mesh, produces exactly this.")
        else:
            print(f"\n{best} explains the held-out photographs best on this capture.")
        print("A silhouette is an outline: it cannot see a fracture edge that has been "
              "smoothed away inside it. Read this with the surface measurements.")
    print(f"\nWritten to {args.out / 'silhouette.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
