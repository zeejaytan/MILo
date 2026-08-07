#!/usr/bin/env python3
"""
Compare a MILo mesh against an OpenMVS mesh of the same sherd — without a ground truth.

There is no correct mesh for a Rabati sherd. Nothing here scores against one, and no
number this script prints should be described as accuracy. What it can do honestly:

  1. SILHOUETTE AGREEMENT ON HELD-OUT VIEWS (the primary number). Every 8th photograph is
     withheld from training. Each mesh is rendered from those camera positions and its
     outline compared with the sherd's mask in that photograph. This asks "does this shape
     explain pictures it has never seen", which is answerable without a reference mesh and
     is unaffected by what units the mesh is in.

  2. WHERE THE TWO DISAGREE, in millimetres, mapped onto the surface. This says nothing
     about which one is right. It says where to look.

  3. WALL THICKNESS distribution. A sherd's wall is a physical quantity a conservator can
     check with callipers, and it is a sanity test that neither method has inflated or
     thinned the body.

  4. PICTURES. Raking-light renders of both meshes from matched viewpoints with a
     millimetre scale bar burnt in. Required, not optional: a wear bug in this workspace
     once survived three rounds of numeric validation and was obvious within seconds of
     drawing the geometry. Renders are written whatever the numbers say.

Usage:
    python scripts/compare_meshes.py \\
        --capture  /data/.../MILo/data/16062025/capture.json \\
        --milo     /data/.../MILo/output/16062025/mesh_mm.ply \\
        --openmvs  /data/.../Rabati2025/16062025/work_colmap_openmvs/scene_dense_mesh_refine.ply \\
        --out      /data/.../MILo/output/16062025/compare
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import trimesh
from PIL import Image as PILImage

_REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_colmap_loader():
    """MILo's COLMAP reader, loaded from its file so the import does not drag in the
    whole scene package (and torch) before we know a GPU is even needed."""
    import importlib.util

    path = _REPO_ROOT / "milo" / "scene" / "colmap_loader.py"
    spec = importlib.util.spec_from_file_location("milo_colmap_loader", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_colmap = _load_colmap_loader()
qvec2rotmat = _colmap.qvec2rotmat
read_extrinsics_binary = _colmap.read_extrinsics_binary
read_extrinsics_text = _colmap.read_extrinsics_text
read_intrinsics_binary = _colmap.read_intrinsics_binary
read_intrinsics_text = _colmap.read_intrinsics_text

# Below this, a silhouette score means the renderer disagrees with the photographs so
# badly that the most likely explanation is a broken camera convention in this script,
# not two independently bad reconstructions.
SUSPECT_IOU = 0.5


# --------------------------------------------------------------------------------------
# COLMAP model
# --------------------------------------------------------------------------------------

def read_model(sparse_dir: Path):
    if (sparse_dir / "images.bin").exists():
        return (read_extrinsics_binary(str(sparse_dir / "images.bin")),
                read_intrinsics_binary(str(sparse_dir / "cameras.bin")))
    return (read_extrinsics_text(str(sparse_dir / "images.txt")),
            read_intrinsics_text(str(sparse_dir / "cameras.txt")))


def pinhole_params(cam):
    """(fx, fy, cx, cy) for the pinhole models COLMAP's undistorter emits."""
    if cam.model == "PINHOLE":
        fx, fy, cx, cy = cam.params[:4]
    elif cam.model == "SIMPLE_PINHOLE":
        f, cx, cy = cam.params[:3]
        fx = fy = f
    else:
        raise ValueError(
            f"camera model {cam.model} is not pinhole; these views were not undistorted"
        )
    return float(fx), float(fy), float(cx), float(cy)


def view_matrix(image) -> np.ndarray:
    """World -> OpenGL camera (x right, y up, -z forward), 4x4."""
    R = qvec2rotmat(image.qvec)          # world -> COLMAP camera (x right, y down, +z fwd)
    t = np.asarray(image.tvec, dtype=np.float64)
    m = np.eye(4)
    m[:3, :3] = R
    m[:3, 3] = t
    # COLMAP -> OpenGL: flip y and z.
    return np.diag([1.0, -1.0, -1.0, 1.0]) @ m


def projection_matrix(fx, fy, cx, cy, w, h, znear, zfar) -> np.ndarray:
    """Pinhole intrinsics as an OpenGL projection matrix."""
    p = np.zeros((4, 4))
    p[0, 0] = 2.0 * fx / w
    p[1, 1] = 2.0 * fy / h
    p[0, 2] = 1.0 - 2.0 * cx / w
    p[1, 2] = 2.0 * cy / h - 1.0
    p[2, 2] = -(zfar + znear) / (zfar - znear)
    p[2, 3] = -2.0 * zfar * znear / (zfar - znear)
    p[3, 2] = -1.0
    return p


# --------------------------------------------------------------------------------------
# Rasterisation (nvdiffrast, CUDA context — the compute nodes are headless)
# --------------------------------------------------------------------------------------

class Renderer:
    def __init__(self):
        try:
            import torch
            import nvdiffrast.torch as dr
        except ImportError as exc:
            raise SystemExit(
                f"nvdiffrast/torch unavailable ({exc}).\n"
                "Run this inside the MILo conda environment on a GPU node — it is "
                "installed there as part of MILo itself."
            )
        self.torch = torch
        self.dr = dr
        # RasterizeCudaContext, not GL: the compute nodes have no display and an OpenGL
        # context would fail to initialise.
        self.ctx = dr.RasterizeCudaContext()

    def render(self, mesh: trimesh.Trimesh, mvp: np.ndarray, w: int, h: int):
        """Return (mask HxW bool, depth HxW float, normal HxWx3 float) in camera space."""
        torch, dr = self.torch, self.dr
        v = torch.tensor(np.asarray(mesh.vertices, np.float32), device="cuda")
        f = torch.tensor(np.asarray(mesh.faces, np.int32), device="cuda")
        n = torch.tensor(np.asarray(mesh.vertex_normals, np.float32), device="cuda")

        mvp_t = torch.tensor(mvp.astype(np.float32), device="cuda")
        v_h = torch.cat([v, torch.ones_like(v[:, :1])], dim=1)
        v_clip = (v_h @ mvp_t.T)[None]

        # nvdiffrast wants both raster dimensions to be multiples of 8.
        rh, rw = (h + 7) // 8 * 8, (w + 7) // 8 * 8
        rast, _ = dr.rasterize(self.ctx, v_clip, f, resolution=[rh, rw])

        mask = (rast[..., 3:4] > 0).float()
        depth = v_clip[..., 2:3] / v_clip[..., 3:4]
        depth_img, _ = dr.interpolate(depth, rast, f)
        normal_img, _ = dr.interpolate(n[None], rast, f)

        def to_np(x, c):
            a = x[0, :h, :w, :c].detach().cpu().numpy()
            return np.flipud(a)          # nvdiffrast row 0 is the bottom of the image

        return (to_np(mask, 1)[..., 0] > 0.5,
                to_np(depth_img, 1)[..., 0],
                to_np(normal_img, 3))


# --------------------------------------------------------------------------------------
# The four things this script reports
# --------------------------------------------------------------------------------------

def silhouette_agreement(renderer, mesh, model, masks_dir, held_out, out_dir, tag):
    """Intersection-over-union between each rendered outline and the view's mask."""
    extrinsics, intrinsics = model
    by_name = {im.name: im for im in extrinsics.values()}
    rows = []
    for name in held_out:
        image = by_name.get(name)
        if image is None:
            continue
        mask_path = masks_dir / (Path(name).stem + ".png")
        if not mask_path.exists():
            continue
        gt = np.asarray(PILImage.open(mask_path).convert("L")) > 127
        h, w = gt.shape

        cam = intrinsics[image.camera_id]
        fx, fy, cx, cy = pinhole_params(cam)
        extent = float(np.linalg.norm(mesh.extents))
        mvp = projection_matrix(fx, fy, cx, cy, w, h,
                                znear=extent * 1e-3, zfar=extent * 1e3) @ view_matrix(image)

        pred, _, _ = renderer.render(mesh, mvp, w, h)
        inter = np.logical_and(pred, gt).sum()
        union = np.logical_or(pred, gt).sum()
        rows.append({
            "view": name,
            "iou": float(inter / union) if union else 0.0,
            # Split the error so the direction is visible: material the mesh invents vs
            # material it is missing. They mean different things for a break face.
            "excess_px": int(np.logical_and(pred, ~gt).sum()),
            "missing_px": int(np.logical_and(~pred, gt).sum()),
            "gt_px": int(gt.sum()),
        })

        if len(rows) <= 3:
            _save_silhouette_overlay(pred, gt, out_dir / f"silhouette_{tag}_{Path(name).stem}.png")
    return rows


def _save_silhouette_overlay(pred, gt, path: Path):
    """Green = agreed, red = mesh invents material, blue = mesh misses material."""
    h, w = gt.shape
    img = np.zeros((h, w, 3), np.uint8)
    img[np.logical_and(pred, gt)] = (40, 180, 60)
    img[np.logical_and(pred, ~gt)] = (200, 40, 40)
    img[np.logical_and(~pred, gt)] = (40, 80, 200)
    path.parent.mkdir(parents=True, exist_ok=True)
    PILImage.fromarray(img).save(path)


def surface_disagreement(a: trimesh.Trimesh, b: trimesh.Trimesh, n_samples=200_000):
    """Symmetric point-to-surface distance between the two meshes, in mesh units."""
    from scipy.spatial import cKDTree

    pa = a.sample(n_samples)
    pb = b.sample(n_samples)
    d_ab = cKDTree(pb).query(pa)[0]
    d_ba = cKDTree(pa).query(pb)[0]
    d = np.concatenate([d_ab, d_ba])
    return {
        "median": float(np.median(d)),
        "p90": float(np.percentile(d, 90)),
        "p99": float(np.percentile(d, 99)),
        "max": float(d.max()),
        "frac_within_0.5mm": float((d < 0.5).mean()),
        "frac_within_1mm": float((d < 1.0).mean()),
    }


def wall_thickness(mesh: trimesh.Trimesh, n_samples=20_000, seed=0):
    """
    Distance from a point on the surface to the opposite face, along the inward normal.

    Sampled rather than exhaustive: a refined OpenMVS mesh has ~1M vertices and this is a
    distribution, not a per-vertex map. Rays that exit without hitting anything are
    dropped — those are break faces and rim edges, where "wall thickness" has no meaning.
    """
    rng = np.random.default_rng(seed)
    idx = rng.choice(len(mesh.vertices), size=min(n_samples, len(mesh.vertices)),
                     replace=False)
    origins = mesh.vertices[idx]
    normals = mesh.vertex_normals[idx]
    eps = float(np.linalg.norm(mesh.extents)) * 1e-5
    hits = mesh.ray.intersects_location(
        ray_origins=origins - normals * eps,
        ray_directions=-normals,
        multiple_hits=False,
    )
    locations, index_ray = hits[0], hits[1]
    if len(index_ray) == 0:
        return None
    d = np.linalg.norm(locations - origins[index_ray], axis=1)
    return {
        "n_rays_hit": int(len(d)),
        "n_rays_cast": int(len(origins)),
        "median": float(np.median(d)),
        "p10": float(np.percentile(d, 10)),
        "p90": float(np.percentile(d, 90)),
    }


def raking_render(renderer, mesh, model, view_name, out_path: Path, mm_per_unit=1.0):
    """
    Shade the mesh with a grazing light, the way raking light reveals a worn surface.

    Flat, head-on lighting hides exactly the sub-millimetre relief this comparison is
    about. A millimetre scale bar is burnt into the corner so the picture cannot be read
    at the wrong scale.
    """
    extrinsics, intrinsics = model
    by_name = {im.name: im for im in extrinsics.values()}
    image = by_name.get(view_name) or list(extrinsics.values())[0]
    cam = intrinsics[image.camera_id]
    fx, fy, cx, cy = pinhole_params(cam)
    w, h = int(cam.width), int(cam.height)

    extent = float(np.linalg.norm(mesh.extents))
    view = view_matrix(image)
    mvp = projection_matrix(fx, fy, cx, cy, w, h,
                            znear=extent * 1e-3, zfar=extent * 1e3) @ view

    mask, _, normal = renderer.render(mesh, mvp, w, h)

    # Light ~15 degrees above the image plane, from the left, in camera space.
    light = np.array([-0.966, 0.259, -0.05])
    light /= np.linalg.norm(light)
    n_cam = normal @ view[:3, :3].T
    n_cam /= (np.linalg.norm(n_cam, axis=-1, keepdims=True) + 1e-9)
    shade = np.clip((n_cam * light).sum(-1), 0.0, 1.0) ** 0.8

    img = np.zeros((h, w, 3), np.float32)
    img[mask] = (0.08 + 0.92 * shade[mask])[:, None]
    img = (img * 255).astype(np.uint8)

    _draw_scale_bar(img, fx, view, mesh, mm_per_unit)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    PILImage.fromarray(img).save(out_path)


def _draw_scale_bar(img, fx, view, mesh, mm_per_unit):
    """Burn a 10 mm bar into the bottom-left corner, sized at the sherd's own depth."""
    centre_cam = (view @ np.append(mesh.centroid, 1.0))[:3]
    depth = abs(centre_cam[2])
    if depth <= 0 or mm_per_unit <= 0:
        return
    px_per_mm = fx / depth / mm_per_unit
    bar_px = int(round(10.0 * px_per_mm))
    h, w = img.shape[:2]
    if not (5 < bar_px < w * 0.8):
        return
    y0, x0, t = h - 60, 40, 8
    img[y0:y0 + t, x0:x0 + bar_px] = 255
    img[y0 - 4:y0 + t + 4, x0 - 3:x0] = 255
    img[y0 - 4:y0 + t + 4, x0 + bar_px:x0 + bar_px + 3] = 255


# --------------------------------------------------------------------------------------

def load_mesh(path: Path) -> trimesh.Trimesh:
    m = trimesh.load(path, process=False)
    if isinstance(m, trimesh.Scene):
        m = trimesh.util.concatenate(tuple(m.geometry.values()))
    return m


def describe(mesh: trimesh.Trimesh) -> dict:
    return {
        "vertices": int(len(mesh.vertices)),
        "faces": int(len(mesh.faces)),
        "watertight": bool(mesh.is_watertight),
        "components": int(len(mesh.split(only_watertight=False))),
        "extents_mm": [round(float(x), 2) for x in mesh.extents],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Compare a MILo mesh with an OpenMVS mesh")
    ap.add_argument("--capture", required=True, type=Path)
    ap.add_argument("--milo", required=True, type=Path)
    ap.add_argument("--openmvs", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--mm-per-unit", type=float, default=1.0,
                    help="millimetres per mesh unit; 1.0 if both meshes are already in mm")
    ap.add_argument("--skip-thickness", action="store_true",
                    help="skip wall thickness (ray casting is slow without embree)")
    args = ap.parse_args()

    capture = json.loads(args.capture.read_text())
    dataset = Path(capture["dataset_dir"])
    masks_dir = Path(capture["masks"]["masks_dir"]) if capture["masks"].get("masks_dir") else None
    held_out = capture["held_out_views"]
    args.out.mkdir(parents=True, exist_ok=True)

    if masks_dir is None:
        print("This capture has no masks, so there is no outline to compare a render "
              "against. Silhouette agreement — the only measure here that does not need "
              "a ground truth — cannot be computed.", file=sys.stderr)
        return 1

    model = read_model(dataset / "sparse" / "0")
    meshes = {"milo": load_mesh(args.milo), "openmvs": load_mesh(args.openmvs)}

    report = {"capture": str(args.capture), "mm_per_unit": args.mm_per_unit,
              "meshes": {}, "silhouette": {}, "thickness": {}}
    for tag, mesh in meshes.items():
        report["meshes"][tag] = describe(mesh)

    # Both meshes come from the same COLMAP model, so they share a coordinate frame and
    # need no alignment. If their sizes disagree they are not in the same units, and
    # every millimetre below would be meaningless.
    ext = np.array([meshes["milo"].extents, meshes["openmvs"].extents])
    ratio = float(np.max(ext[0] / np.maximum(ext[1], 1e-9)))
    if not (0.9 < ratio < 1.1):
        print(f"\nSTOP: the two meshes differ in size by a factor of about {ratio:.2f}.\n"
              "They are not in the same units, so no distance below would mean anything.\n"
              "Check whether scale_apply.py was run for one and not the other "
              "(see scripts/apply_scale.py).", file=sys.stderr)
        return 1

    renderer = Renderer()

    for tag, mesh in meshes.items():
        rows = silhouette_agreement(renderer, mesh, model, masks_dir, held_out,
                                    args.out, tag)
        ious = [r["iou"] for r in rows]
        report["silhouette"][tag] = {
            "n_views": len(rows),
            "iou_mean": float(np.mean(ious)) if ious else None,
            "iou_min": float(np.min(ious)) if ious else None,
            "per_view": rows,
        }
        raking_render(renderer, mesh, model, held_out[0] if held_out else None,
                      args.out / f"raking_{tag}.png", mm_per_unit=args.mm_per_unit)

    report["disagreement_mm"] = surface_disagreement(meshes["milo"], meshes["openmvs"])

    if not args.skip_thickness:
        for tag, mesh in meshes.items():
            report["thickness"][tag] = wall_thickness(mesh)

    (args.out / "comparison.json").write_text(json.dumps(report, indent=2))

    # ---- read-out -------------------------------------------------------------------
    print(f"\nComparison written to {args.out}\n")
    for tag in ("milo", "openmvs"):
        d, s = report["meshes"][tag], report["silhouette"][tag]
        print(f"{tag:8s} {d['vertices']:>10,} vertices  {d['components']:>3} piece(s)  "
              f"watertight={d['watertight']}")
        if s["iou_mean"] is not None:
            print(f"         outline matches held-out photographs "
                  f"{s['iou_mean']:.1%} on average (worst view {s['iou_min']:.1%}, "
                  f"{s['n_views']} views)")
        t = report["thickness"].get(tag)
        if t:
            print(f"         wall thickness median {t['median'] * args.mm_per_unit:.2f} mm "
                  f"(10-90%: {t['p10'] * args.mm_per_unit:.2f}-"
                  f"{t['p90'] * args.mm_per_unit:.2f} mm)")

    dis = report["disagreement_mm"]
    print(f"\nThe two disagree by {dis['median'] * args.mm_per_unit:.2f} mm at the median, "
          f"{dis['p90'] * args.mm_per_unit:.2f} mm at the 90th percentile.")
    print("That says where they differ, not which one is right.")

    best = max(("milo", "openmvs"), key=lambda t: report["silhouette"][t]["iou_mean"] or 0)
    worst_iou = min(report["silhouette"][t]["iou_mean"] or 0 for t in meshes)
    if worst_iou < SUSPECT_IOU:
        print(f"\nWARNING: the best outline agreement is only "
              f"{report['silhouette'][best]['iou_mean']:.1%}. Before concluding that a "
              "method failed, check that this script's camera convention is right — a "
              "renderer pointing the wrong way produces exactly this. Look at "
              f"{args.out}/silhouette_*.png.")
    else:
        print(f"\nOn this capture, {best} explains the held-out photographs better.")

    print("\nOne sherd is a lead, not a result. Look at the renders "
          f"({args.out}/raking_*.png) before taking any of these numbers further.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
