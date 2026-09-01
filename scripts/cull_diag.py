"""Why did MILo's all-views silhouette cull keep (or delete) what it did?

`cull_dtu_mesh.py` runs the authors' cull and reports how much survived. When the answer
is "nothing", that number cannot say which of two very different things happened, and they
lead to opposite actions:

  * a few views are broken -- bad pose, bad or empty mask -- and the cull is behaving
    correctly by deleting what those views reject; or
  * every view rejects a slice, no single view is at fault, and the all-views rule is
    simply too strict for this material.

This separates them. It reimplements the arithmetic of
`eval/dtu/evaluate_dtu_mesh.py:cull_mesh` -- same projection, same 6-px dilation, same
"a vertex off-frame is excused for that view" rule -- but instead of returning a mesh it
reports, per view, the share of in-frame vertices that land inside the outline, and per
vertex, how many views accepted it.

On A03 the answer was the second one: each view accepted 68-90% of the mesh but a
different ~18% each time, and the best vertex passed 139 of 143. See
`docs/notes/A03_DTU_EXTRACTION_RESULT.md`.

Deliberately CPU-only -- numpy, no torch, no Gaussians, no CUDA -- so it runs on the login
node in about two minutes instead of costing a GPU job to ask a question about geometry.

usage:
    python scripts/cull_diag.py --mesh recon_tsdf.ply --data <dataset dir> \
        --masked-images <dataset dir>/images_masked [--plot out.png]
"""
import argparse
import os
import sys
from pathlib import Path

import numpy as np
import trimesh
from PIL import Image
from scipy.ndimage import binary_dilation

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "milo"))

from scene.colmap_loader import (  # noqa: E402
    qvec2rotmat, read_extrinsics_binary, read_intrinsics_binary)

# cull_mesh dilates the mask with skimage's disk(6) before sampling it. At A03's 0.206 mm
# per pixel that is 1.24 mm of tolerance -- deliberately generous, because a tight mask
# eats fracture edges before it eats background.
_yy, _xx = np.mgrid[-6:7, -6:7]
DISK6 = (_xx ** 2 + _yy ** 2) <= 36


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mesh", required=True, type=Path)
    ap.add_argument("--data", required=True, type=Path, help="MILo dataset dir (has sparse/0)")
    ap.add_argument("--masked-images", required=True, type=Path,
                    help="RGBA images whose alpha is the mask, i.e. images_masked")
    ap.add_argument("--llffhold", type=int, default=8,
                    help="--eval holds out every Nth view; 0 to use all views")
    ap.add_argument("--plot", type=Path, default=None)
    args = ap.parse_args()

    cams = read_intrinsics_binary(str(args.data / "sparse/0/cameras.bin"))
    exts = read_extrinsics_binary(str(args.data / "sparse/0/images.bin"))

    # MILo sorts camera infos by image name, then drops every llffhold-th as the test set.
    # Getting this wrong changes which views vote, so it is mirrored rather than guessed.
    order = sorted(exts.values(), key=lambda e: Path(e.name).name)
    train = ([e for i, e in enumerate(order) if i % args.llffhold != 0]
             if args.llffhold else order)
    print(f"{len(order)} cameras, {len(train)} training views")

    m = trimesh.load(args.mesh, process=False)
    V = np.asarray(m.vertices, np.float64)
    print(f"{len(V):,} vertices in {args.mesh.name}")

    passed = np.zeros(len(V), np.int32)
    rows = []
    for n, e in enumerate(train):
        cam = cams[e.camera_id]
        if cam.model != "PINHOLE":
            sys.exit(f"[ERROR] camera model {cam.model} is not PINHOLE; this expects "
                     f"COLMAP's undistorted output, and reading a distorted model as if "
                     f"it were undistorted would misplace every vertex silently.")
        fx, fy, cx, cy = cam.params
        W, H = cam.width, cam.height

        R = qvec2rotmat(e.qvec)
        Xc = V @ R.T + e.tvec
        z = Xc[:, 2]
        front = z > 1e-6
        u = fx * Xc[:, 0] / np.where(front, z, 1.0) + cx
        v = fy * Xc[:, 1] / np.where(front, z, 1.0) + cy
        inframe = front & (u >= 0) & (u < W) & (v >= 0) & (v < H)

        img = Image.open(args.masked_images / Path(e.name).name)
        if img.mode != "RGBA":
            sys.exit(f"[ERROR] {Path(e.name).name} has no alpha channel, so it carries no "
                     f"mask. Point --masked-images at the RGBA images.")
        alpha = binary_dilation(np.asarray(img.getchannel("A")) > 0, DISK6)

        ui = np.clip(u.astype(np.int32), 0, W - 1)
        vi = np.clip(v.astype(np.int32), 0, H - 1)
        inside = alpha[vi, ui] & inframe
        passed += inside | ~inframe          # off-frame is excused, as cull_mesh does

        nf = int(inframe.sum())
        rows.append((100.0 * int(inside.sum()) / max(nf, 1), nf, Path(e.name).name))
        if n % 30 == 0:
            print(f"  view {n + 1}/{len(train)}", flush=True)

    N = len(train)
    rows.sort()
    print("\nper view: share of IN-FRAME vertices landing inside the dilated outline")
    for label, sel in (("worst 10", rows[:10]), ("best 5", rows[-5:])):
        print(f"  {label}:")
        for pct, nf, name in sel:
            print(f"    {pct:6.2f}%  ({nf:,} of {len(V):,} in frame)  {name}")
    per_view = np.array([r[0] for r in rows])
    print(f"  median {np.median(per_view):.2f}%")

    print(f"\nper vertex: views accepting it, out of {N}")
    print(f"  accepted by ALL {N} views (what the cull keeps): {int((passed == N).sum()):,}")
    for frac in (0.95, 0.90, 0.75):
        thr = int(np.ceil(frac * N))
        print(f"  accepted by >= {thr:3d} views ({frac:.0%}): {int((passed >= thr).sum()):,}")
    print(f"  best vertex {int(passed.max())} views; median vertex {int(np.median(passed))}")

    if (passed == N).sum() == 0:
        worst = per_view.min()
        print(f"\n  Nothing survives. If the worst view ({worst:.1f}%) is far below the rest, "
              f"that view is the problem.\n  If every view is in the same band, no view is "
              f"broken and the all-views rule itself is what empties the mesh.")

    if args.plot:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(1, 2, figsize=(12, 4.2))
        ax[0].hist(passed, bins=60, color="#2a6f9e")
        ax[0].axvline(N, color="crimson", ls="--")
        ax[0].set_xlabel(f"views accepting the vertex (of {N}); red = the cull's threshold")
        ax[0].set_ylabel("vertices")
        ax[0].set_title("How close each vertex came to surviving")
        ax[1].hist(per_view, bins=40, color="#7a9e2a")
        ax[1].set_xlabel("% of in-frame vertices inside the outline")
        ax[1].set_ylabel("views")
        ax[1].set_title("How strict each view is")
        fig.tight_layout()
        fig.savefig(args.plot, dpi=110)
        print(f"\nwrote {args.plot}")


if __name__ == "__main__":
    main()
