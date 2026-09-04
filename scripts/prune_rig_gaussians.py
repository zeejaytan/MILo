"""Drop rig Gaussians after training by voting centres against sherd outlines.

The native tet path (`mesh_extract_sdf.py`) builds from *all* Gaussians, and its
mask inputs are hard-coded `None` -- so the rig survives into the mesh. This
filters the Gaussian set *before* pivots are built: a Gaussian survives only if
its centre lands inside the sherd-only outline (erode0, on the clay edge) in at
least `--keep-ratio` of the training views where it is in front of the camera.
Training data and the source point cloud are never modified; the keep set is
written as an index array the tet flow already accepts as its downsample index.

Deliberately CPU-only -- numpy, no torch, no Gaussians library, no CUDA -- so it
runs on the login node like `cull_diag.py` instead of costing a GPU job to ask
which Gaussians are clay.

Two deliberate differences from `cull_diag.py`, both load-bearing:

* No dilation. The cull dilates by disk(6) to be generous; here the outline
  decides inclusion, and dilating would vote the clamp rim back in.
* No off-frame excuse. A Gaussian no training view sees in front of a camera
  cannot be photographed clay, so it is dropped, not kept.

usage:
    python scripts/prune_rig_gaussians.py --point-cloud point_cloud.ply \
        --data <dataset dir> --masked-images <dataset dir>/images_masked \
        --out kept_idx.npy [--plot votes.png]
    python scripts/prune_rig_gaussians.py --self-test
"""

import argparse
import os
import sys
from pathlib import Path

import numpy as np
import trimesh
from PIL import Image

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# colmap_loader is numpy-only, but importing it as scene.colmap_loader executes
# scene/__init__.py, which pulls in torch. Load the file directly so this stays
# runnable without the conda env -- the whole point of a CPU login-node script.
import importlib.util as _ilu
_spec = _ilu.spec_from_file_location(
    "colmap_loader", os.path.join(REPO, "milo", "scene", "colmap_loader.py"))
_colmap_loader = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(_colmap_loader)
qvec2rotmat = _colmap_loader.qvec2rotmat
read_extrinsics_binary = _colmap_loader.read_extrinsics_binary
read_intrinsics_binary = _colmap_loader.read_intrinsics_binary


def vote_keep(X, views, keep_ratio=0.8):
    """Vote each point against per-view sherd outlines.

    X: (N, 3) float64 centres in COLMAP world frame.
    views: list of dicts with R (3,3), t (3,), fx, fy, cx, cy, W, H,
        alpha (H, W) bool sherd outline. No dilation is applied here.
    Returns (keep (N,) bool, inside_counts (N,) int32, seen_counts (N,) int32).
    A point seen in front of no camera is dropped (0/0 keeps nothing).
    """
    n = len(X)
    inside = np.zeros(n, np.int32)
    seen = np.zeros(n, np.int32)
    for v in views:
        Xc = X @ v["R"].T + v["t"]
        z = Xc[:, 2]
        front = z > 1e-6
        u = v["fx"] * Xc[:, 0] / np.where(front, z, 1.0) + v["cx"]
        vv = v["fy"] * Xc[:, 1] / np.where(front, z, 1.0) + v["cy"]
        inframe = front & (u >= 0) & (u < v["W"]) & (vv >= 0) & (vv < v["H"])
        seen += inframe
        ui = np.clip(u.astype(np.int32), 0, v["W"] - 1)
        vi = np.clip(vv.astype(np.int32), 0, v["H"] - 1)
        inside += (v["alpha"][vi, ui] & inframe).astype(np.int32)
    with np.errstate(invalid="ignore", divide="ignore"):
        frac = np.where(seen > 0, inside / np.maximum(seen, 1), -1.0)
    keep = frac >= keep_ratio
    return keep, inside, seen


def load_views(data_dir, masked_images, llffhold):
    """Read COLMAP sparse model plus RGBA alphas into view dicts.

    Mirrors the training-view selection (sorted by name, every llffhold-th
    held out), the same way `cull_diag.py` does -- getting this wrong changes
    which views vote.
    """
    cams = read_intrinsics_binary(str(data_dir / "sparse/0/cameras.bin"))
    exts = read_extrinsics_binary(str(data_dir / "sparse/0/images.bin"))
    order = sorted(exts.values(), key=lambda e: Path(e.name).name)
    train = ([e for i, e in enumerate(order) if i % llffhold != 0]
             if llffhold else order)
    views = []
    for e in train:
        cam = cams[e.camera_id]
        if cam.model != "PINHOLE":
            sys.exit(f"[ERROR] camera model {cam.model} is not PINHOLE; this expects "
                     f"COLMAP's undistorted output, and a distorted model read as "
                     f"undistorted would misplace every Gaussian silently.")
        fx, fy, cx, cy = cam.params
        W, H = cam.width, cam.height
        img = Image.open(masked_images / Path(e.name).name)
        if img.mode != "RGBA":
            sys.exit(f"[ERROR] {Path(e.name).name} has no alpha channel, so it carries "
                     f"no mask. Point --masked-images at the RGBA images.")
        views.append({"R": qvec2rotmat(e.qvec), "t": np.asarray(e.tvec, np.float64),
                      "fx": fx, "fy": fy, "cx": cx, "cy": cy, "W": W, "H": H,
                      "alpha": np.asarray(img.getchannel("A")) > 0,
                      "name": Path(e.name).name})
    return views


def _synth_view(W=40, H=30, box=(10, 10, 30, 20)):
    alpha = np.zeros((H, W), bool)
    x0, y0, x1, y1 = box
    alpha[y0:y1, x0:x1] = True
    return {"R": np.eye(3), "t": np.zeros(3), "fx": 10.0, "fy": 10.0,
            "cx": 20.0, "cy": 15.0, "W": W, "H": H, "alpha": alpha, "name": "synth"}


def self_test():
    """Prove the vote can both keep and drop, so a passing run means something.

    A check that only ever keeps would pass on real data while proving nothing;
    the all-outside blob below is the control that fails such a check.
    """
    v = _synth_view()
    # Point at world (0,0,10) projects to principal point (20,15): inside box.
    clay = np.array([[0.0, 0.0, 10.0]])
    # World (100,0,10) projects to u=120: off-frame, seen by no view.
    rig = np.array([[100.0, 0.0, 10.0]])
    # World (12,0,10) projects to u=32: in frame (W=40) but outside the box.
    rim = np.array([[12.0, 0.0, 10.0]])
    X = np.vstack([clay, rig, rim])

    keep, inside, seen = vote_keep(X, [v, v], keep_ratio=0.8)
    assert seen.tolist() == [2, 0, 2], f"seen counts wrong: {seen}"
    assert inside.tolist() == [2, 0, 0], f"inside counts wrong: {inside}"
    assert keep.tolist() == [True, False, False], f"keep wrong: {keep}"

    # Boundary: inside in 1 of 2 views with ratio 0.8 must drop.
    v2 = _synth_view(box=(0, 0, 5, 5))  # principal point outside this box
    keep_b, _, _ = vote_keep(clay, [v, v2], keep_ratio=0.8)
    assert keep_b.tolist() == [False], "1-of-2 with ratio 0.8 must drop"
    keep_b, _, _ = vote_keep(clay, [v, v2], keep_ratio=0.5)
    assert keep_b.tolist() == [True], "1-of-2 with ratio 0.5 must keep"

    # Edge survival: world x so u lands 1 px inside the box's right edge
    # (u=29 -> x=9 with fx=10, cx=20, z=10). Erosion must not eat the rim.
    edge = np.array([[9.0, 0.0, 10.0]])
    keep_e, inside_e, seen_e = vote_keep(edge, [v, v], keep_ratio=0.8)
    assert seen_e.tolist() == [2] and inside_e.tolist() == [2], \
        f"edge counts wrong: seen {seen_e}, inside {inside_e}"
    assert keep_e.tolist() == [True], "1 px inside the outline must survive"

    # Determinism: two runs agree exactly.
    k1, _, _ = vote_keep(X, [v, v])
    k2, _, _ = vote_keep(X, [v, v])
    assert (k1 == k2).all(), "vote is not deterministic"

    print("self-test: 7 assertions passed "
          "(clay kept, rig blob dropped, rim dropped, edge survives, boundary "
          "drops at 0.8 and keeps at 0.5, deterministic).")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--point-cloud", type=Path, default=None)
    ap.add_argument("--data", type=Path, default=None,
                    help="MILo dataset dir (has sparse/0)")
    ap.add_argument("--masked-images", type=Path, default=None,
                    help="RGBA images whose alpha is the mask, i.e. images_masked")
    ap.add_argument("--llffhold", type=int, default=8,
                    help="--eval holds out every Nth view; 0 to use all views")
    ap.add_argument("--keep-ratio", type=float, default=0.8)
    ap.add_argument("--out", type=Path, default=None,
                    help="where to write the kept indices (.npy)")
    ap.add_argument("--plot", type=Path, default=None)
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        self_test()
        return
    for req in ("point_cloud", "data", "masked_images", "out"):
        if getattr(args, req) is None:
            ap.error(f"--{req.replace('_', '-')} is required (or pass --self-test)")

    pc = trimesh.load(args.point_cloud, process=False)
    X = np.asarray(pc.vertices, np.float64)
    print(f"{len(X):,} Gaussians in {args.point_cloud.name}")

    views = load_views(args.data, args.masked_images, args.llffhold)
    print(f"{len(views)} training views vote at keep-ratio {args.keep_ratio}")

    keep, inside, seen = vote_keep(X, views, args.keep_ratio)
    nk = int(keep.sum())
    print(f"kept {nk:,} of {len(X):,} ({100.0 * nk / max(len(X), 1):.2f}%)")
    print(f"never seen in front of any view (dropped): {int((seen == 0).sum()):,}")
    print(f"median views seen: {int(np.median(seen))}, "
          f"median inside: {int(np.median(inside))}")

    np.save(args.out, np.nonzero(keep)[0].astype(np.int64))
    print(f"wrote {args.out}")

    if args.plot:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        frac = np.where(seen > 0, inside / np.maximum(seen, 1), -1.0)
        fig, ax = plt.subplots(1, 2, figsize=(12, 4.2))
        ax[0].hist(frac[seen > 0], bins=60, color="#2a6f9e")
        ax[0].axvline(args.keep_ratio, color="crimson", ls="--")
        ax[0].set_xlabel("share of seen views inside the outline; red = keep rule")
        ax[0].set_ylabel("Gaussians")
        ax[0].set_title("How close each Gaussian came to surviving")
        ax[1].hist(seen, bins=60, color="#7a9e2a")
        ax[1].set_xlabel("views seeing the Gaussian in front of camera")
        ax[1].set_ylabel("Gaussians")
        ax[1].set_title("How often each Gaussian is seen")
        fig.tight_layout()
        fig.savefig(args.plot, dpi=110)
        print(f"wrote {args.plot}")


if __name__ == "__main__":
    main()
