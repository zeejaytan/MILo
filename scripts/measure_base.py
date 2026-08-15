"""Measure the blue base plate in a reconstruction, and refuse if it cannot be trusted.

The base is the only physical scale in these captures: its TOP FACE is a known 13 x 19 cm
(the conservator's record says "Top of the tree base (blue metal base) = 13x19cm" -- top,
because the base is a trapezoid and tapers). Measuring it in reconstruction units gives the
factor that turns every downstream mesh metric.

WHY NOT COLOUR. Three attempts at isolating the plate by colour failed, all the same way:
the clamp knobs are blue too, there are dozens of them along the whole rod, and they
dominate any fit. The rendered selection made it obvious and the numbers never did --
aspect ratios of 1.66, 1.95, 2.50 against a true 1.462, and scale factors disagreeing by
13-29%. SAM 3 prompted with "blue board" finds exactly ONE region at 0.94 confidence and no
knobs, so the isolation is done semantically and the geometry is only asked to measure.

WHAT MAKES THE ANSWER CHECKABLE. A rectangle of known proportions is self-validating: the
long and short edges give two independent scale factors, and they can only agree if the
thing measured really is the plate. The aspect ratio is the same check stated as a shape,
and it is scale-free, so it catches a wrong region before any factor is computed. This
script refuses rather than reports when the checks fail -- a wrong scale is worse than no
scale, because nothing downstream would ever reveal it.

Usage:
    python measure_base.py --dense <dense_workspace> --cloud <fused .ply> \\
        --out <dir> [--views 24] [--write-measurement-env]
"""
import argparse
import json
import struct
import sys
from pathlib import Path

import numpy as np
from PIL import Image

LONG_MM, SHORT_MM = 190.0, 130.0          # top face of the base, from the record
TRUE_ASPECT = LONG_MM / SHORT_MM          # 1.4615
ASPECT_TOL = 0.05                         # ~3.4%; looser than this and the region is wrong


# ----------------------------------------------------------------- COLMAP model (undistorted)
def read_cameras(path):
    cams = {}
    with open(path, "rb") as f:
        (n,) = struct.unpack("<Q", f.read(8))
        for _ in range(n):
            cid, model, w, h = struct.unpack("<iiQQ", f.read(24))
            npar = {0: 3, 1: 4, 2: 4, 3: 5, 4: 8}.get(model, 4)
            par = struct.unpack("<" + "d" * npar, f.read(8 * npar))
            cams[cid] = dict(model=model, w=w, h=h, params=par)
    return cams


def read_images(path):
    out = []
    with open(path, "rb") as f:
        (n,) = struct.unpack("<Q", f.read(8))
        for _ in range(n):
            _, qw, qx, qy, qz, tx, ty, tz, cid = struct.unpack("<idddddddi", f.read(64))
            nm = b""
            while (c := f.read(1)) != b"\x00":
                nm += c
            (p,) = struct.unpack("<Q", f.read(8))
            f.seek(24 * p, 1)
            R = np.array([
                [1-2*(qy*qy+qz*qz), 2*(qx*qy-qz*qw), 2*(qx*qz+qy*qw)],
                [2*(qx*qy+qz*qw), 1-2*(qx*qx+qz*qz), 2*(qy*qz-qx*qw)],
                [2*(qx*qz-qy*qw), 2*(qy*qz+qx*qw), 1-2*(qx*qx+qy*qy)]])
            out.append(dict(name=nm.decode(), R=R, t=np.array([tx, ty, tz]), cam=cid))
    return out


def project(P, im, cam):
    """World points -> pixels, for an UNDISTORTED (pinhole) camera."""
    X = (im["R"] @ P.T).T + im["t"]
    z = X[:, 2]
    ok = z > 1e-6
    p = np.full((len(P), 2), -1.0)
    pr = X[ok, :2] / z[ok, None]
    m, par = cam["model"], cam["params"]
    if m == 1:                                    # PINHOLE fx fy cx cy
        fx, fy, cx, cy = par[:4]
    else:                                         # SIMPLE_PINHOLE / fallback
        fx = fy = par[0]; cx, cy = par[1], par[2]
    p[ok, 0] = fx * pr[:, 0] + cx
    p[ok, 1] = fy * pr[:, 1] + cy
    return p, ok


# ----------------------------------------------------------------- PLY (binary, list-tolerant)
def read_ply_xyzrgb(path):
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from look_at_cloud import read_ply
    return read_ply(path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dense", required=True, type=Path,
                    help="undistorted workspace: images/ and sparse/ inside")
    ap.add_argument("--cloud", required=True, type=Path, help="dense point cloud (.ply)")
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--views", type=int, default=24,
                    help="how many photographs to segment; the plate is large and visible "
                         "in most, so a couple of dozen is plenty and keeps this quick")
    ap.add_argument("--vote", type=float, default=0.6,
                    help="fraction of views in which a point must land inside the base mask")
    ap.add_argument("--seg-side", type=int, default=1600)
    ap.add_argument("--write-measurement-env", action="store_true",
                    help="write measurement.env for scale_apply.py, ONLY if the checks pass")
    args = ap.parse_args()

    import cv2
    import torch
    from transformers import Sam3Model, Sam3Processor

    args.out.mkdir(parents=True, exist_ok=True)
    cams = read_cameras(args.dense / "sparse" / "cameras.bin")
    imgs = read_images(args.dense / "sparse" / "images.bin")
    print(f"model: {len(imgs)} views, {len(cams)} camera(s)")

    xyz, rgb = read_ply_xyzrgb(args.cloud)
    print(f"cloud: {len(xyz):,} points")

    # Cheap pre-filter purely to keep the projection work small. It is NOT the isolation --
    # it is deliberately loose, and SAM 3 does the discriminating.
    r, g, b = rgb[:, 0].astype(int), rgb[:, 1].astype(int), rgb[:, 2].astype(int)
    cand = np.where((b > r + 8) & (b > 30))[0]
    print(f"  loose blue candidates: {len(cand):,} (SAM 3 decides which are the plate)")
    if len(cand) < 5000:
        sys.exit("Too few blue candidates -- is this the right cloud?")

    dev = "cuda" if torch.cuda.is_available() else "cpu"
    model = Sam3Model.from_pretrained("facebook/sam3").to(dev).eval()
    proc = Sam3Processor.from_pretrained("facebook/sam3")

    step = max(1, len(imgs) // args.views)
    chosen = imgs[::step][:args.views]
    inside = np.zeros(len(cand), np.int32)
    seen = np.zeros(len(cand), np.int32)
    P = xyz[cand]

    for k, im in enumerate(chosen):
        fp = args.dense / "images" / im["name"]
        if not fp.exists():
            continue
        pil = Image.open(fp).convert("RGB")
        W, H = pil.size
        small = pil.copy(); small.thumbnail((args.seg_side, args.seg_side))
        inputs = proc(images=small, text="blue board", return_tensors="pt").to(dev)
        with torch.inference_mode():
            out = model(**inputs)
        res = proc.post_process_instance_segmentation(
            out, threshold=0.3, mask_threshold=0.5,
            target_sizes=[(small.size[1], small.size[0])])[0]
        m = res.get("masks")
        if m is None or not len(m):
            continue
        mm = m.detach().cpu().numpy()
        if mm.ndim == 4:
            mm = mm[:, 0]
        mask = np.any(mm > 0.5, axis=0)
        mask = cv2.resize(mask.astype(np.uint8), (W, H), interpolation=cv2.INTER_NEAREST)

        px, ok = project(P, im, cams[im["cam"]])
        u = np.round(px[:, 0]).astype(int); v = np.round(px[:, 1]).astype(int)
        vis = ok & (u >= 0) & (u < W) & (v >= 0) & (v < H)
        seen += vis
        inside[vis] += mask[v[vis], u[vis]] > 0
        if (k + 1) % 8 == 0:
            print(f"  {k+1}/{len(chosen)} views", flush=True)

    ratio = np.divide(inside, np.maximum(seen, 1))
    keep = (seen >= 4) & (ratio >= args.vote)
    B = P[keep]
    print(f"\nbase points after voting: {len(B):,} "
          f"({100*len(B)/max(len(cand),1):.1f}% of candidates)")
    if len(B) < 2000:
        sys.exit("Too few points survived the vote -- SAM 3 did not find a stable plate.")

    # The plate is a tapered solid and the record's 13 x 19 is the TOP face, so the face
    # has to be chosen, not averaged over. The base sits on the turntable with the rod
    # rising from it, so the top face is the extreme along the plate normal in the
    # direction of the rest of the rig.
    ctr = B.mean(0)
    _, _, Vt = np.linalg.svd(B - ctr, full_matrices=False)
    n = Vt[2]
    rig_dir = xyz.mean(0) - ctr                       # from the plate toward the tree
    if n @ rig_dir < 0:
        n = -n
    d = (B - ctr) @ n
    top = np.percentile(d, 97)
    face = B[d > top - 0.12 * (d.max() - d.min())]
    if len(face) < 1000:
        face = B[d > np.percentile(d, 80)]

    # Measure a real bounding rectangle, not percentile extents along PCA axes. The plate
    # has corners; percentiles of a principal axis trim them unevenly and that is what
    # turned a correctly isolated plate into an aspect of 1.316 instead of ~1.46.
    e1 = Vt[0] - (Vt[0] @ n) * n; e1 /= np.linalg.norm(e1)
    e2 = np.cross(n, e1)
    uv = np.stack([(face - face.mean(0)) @ e1, (face - face.mean(0)) @ e2], 1).astype(np.float32)
    # Trim a thin outer shell first: single stray points would otherwise set the rectangle.
    c2 = np.median(uv, axis=0)
    keep2 = np.linalg.norm(uv - c2, axis=1) < np.percentile(np.linalg.norm(uv - c2, axis=1), 99.5)
    rect = cv2.minAreaRect(uv[keep2])
    (w_r, h_r) = rect[1]
    L, Sh = (max(w_r, h_r), min(w_r, h_r))
    aspect = L / Sh
    s_long, s_short = LONG_MM / L, SHORT_MM / Sh
    disagree = abs(s_long - s_short) / ((s_long + s_short) / 2)

    print(f"\n  fitted top face: {L:.5f} x {Sh:.5f} units from {len(face):,} points")
    print(f"  aspect ratio   : {aspect:.3f}      (true {TRUE_ASPECT:.3f})")
    print(f"  scale from long edge : {s_long:9.3f} mm/unit")
    print(f"  scale from short edge: {s_short:9.3f} mm/unit")
    print(f"  the two disagree by  : {100*disagree:.1f}%")

    # Always render the selection. Every failure here came from fitting geometry to a
    # selection nobody had looked at.
    from look_at_cloud import render, basis
    vis_rgb = rgb.copy(); vis_rgb[cand[keep]] = [255, 40, 40]
    for tag, dirn in (("base_selection_side", (0, 1, 0)), ("base_selection_face", tuple(n))):
        Bb = basis(dirn); q = xyz @ Bb.T
        c = np.median(q[cand[keep]][:, :2], axis=0)
        e = float(np.ptp(q[cand[keep]][:, :2], axis=0).max()) * 2.0
        img, _, _ = render(xyz, vis_rgb, dirn, 1200, centre=c, extent=e, point_px=1)
        Image.fromarray(img).save(args.out / f"{tag}.png")
    print(f"  wrote selection renders to {args.out} -- LOOK AT THEM")

    ok_aspect = abs(aspect - TRUE_ASPECT) <= ASPECT_TOL
    result = dict(long_units=float(L), short_units=float(Sh), aspect=float(aspect),
                  mm_per_unit_long=float(s_long), mm_per_unit_short=float(s_short),
                  disagreement=float(disagree), points=int(len(face)),
                  accepted=bool(ok_aspect and disagree < 0.02))
    (args.out / "base_measurement.json").write_text(json.dumps(result, indent=2))

    if not result["accepted"]:
        print("\n  REJECTED. A wrong scale is worse than no scale: nothing downstream would")
        print("  ever reveal it, and every measurement taken from these meshes would be off")
        print("  by that factor. Measure the base by hand instead, and look at the renders")
        print("  above to see what was picked up.")
        return 1

    scale = 0.5 * (s_long + s_short)
    print(f"\n  ACCEPTED: {scale:.3f} mm per reconstruction unit")
    if args.write_measurement_env:
        env = args.dense.parent / "measurement.env"
        env.write_text(f"d1_real_m={LONG_MM/1000:.4f}\nd1_rec_units={L:.9f}\n"
                       f"d2_real_m={SHORT_MM/1000:.4f}\nd2_rec_units={Sh:.9f}\n")
        print(f"  wrote {env} for scale_apply.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
