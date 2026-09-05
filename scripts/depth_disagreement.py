"""Cross-view depth disagreement in millimetres (ticket 02).

Renders median depth from the trained Gaussians for a handful of spread views,
unprojects the sherd pixels to world points, and reports nearest-neighbour
distances between view pairs: the honest resolution floor M1's first box needs.

Deliberately no Open3D, no mesh, no fusion: the number must describe the rendered
depth, not any grid built from it. Median depth, not expected depth (outlier
sensitive); sherd pixels only (gt_mask), background never enters the comparison.

Memory: the established trap is cameraList_from_camInfos putting every training
image on the GPU (~15.6 GiB for A03). Views are filtered BEFORE that call, and
each view's pixels are released after its depth is rendered.

Usage (inside milo/ on the node, -m points at the trained run):
    python -u ../scripts/depth_disagreement.py -s <dataset> -m <trained run> \
        -i images_masked -r 1 --eval --mm_per_unit 373.7 \
        --views 0 24 48 72 96 120 --subsample 20000
"""

import gc
import json
import math
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE_DIR, "milo"))

import numpy as np
import torch
from argparse import ArgumentParser

from scene import GaussianModel
from arguments import ModelParams, PipelineParams
from scene.dataset_readers import sceneLoadTypeCallbacks
from utils.camera_utils import cameraList_from_camInfos


def load_camera_subset(dataset, indices):
    if os.path.exists(os.path.join(dataset.source_path, "sparse")):
        scene_info = sceneLoadTypeCallbacks["Colmap"](
            dataset.source_path, dataset.images, dataset.eval)
    else:
        print("[ERROR] no COLMAP sparse model under the dataset dir.", file=sys.stderr)
        sys.exit(2)
    train_cams = scene_info.train_cameras
    n = len(train_cams)
    bad = [i for i in indices if i < 0 or i >= n]
    if bad:
        print(f"[ERROR] view indices {bad} out of range for {n} training views.",
              file=sys.stderr)
        sys.exit(2)
    scene_info = scene_info._replace(
        train_cameras=[train_cams[i] for i in indices])
    return cameraList_from_camInfos(scene_info.train_cameras, 1.0, dataset)


def unproject(depth, mask, cam):
    """Sherd-pixel depths -> world points (N,3) tensor on CPU."""
    # Principal point assumed centred: measured exactly centred on A03, and the
    # 6-px mask erosion dwarfs any residual offset. Revisit per capture if reused.
    W, H = cam.image_width, cam.image_height
    fx = W / (2 * math.tan(cam.FoVx / 2.))
    fy = H / (2 * math.tan(cam.FoVy / 2.))
    vs, us = np.nonzero(mask & (depth > 0))
    d = depth[vs, us].astype(np.float64)
    x = (us.astype(np.float64) - W / 2.) * d / fx
    y = (vs.astype(np.float64) - H / 2.) * d / fy
    ones = np.ones_like(d)
    p_cam = np.stack([x, y, d, ones], axis=1)
    w2v = np.asarray(cam.world_view_transform.cpu().numpy(), dtype=np.float64)
    c2w = np.linalg.inv(w2v)
    p_world = (c2w @ p_cam.T).T[:, :3]
    ok = np.isfinite(p_world).all(axis=1)
    return torch.from_numpy(p_world[ok]).float()


@torch.no_grad()
def pairwise_nn(a, b, chunk=5000):
    """Median / p90 / max of nearest-neighbour distances a->b (scene units)."""
    dists = []
    for i in range(0, len(a), chunk):
        d = torch.cdist(a[i:i + chunk].cuda(), b.cuda()).min(dim=1).values
        dists.append(d.cpu())
    dists = torch.cat(dists).numpy()
    return float(np.median(dists)), float(np.percentile(dists, 90)), float(dists.max())


def main(dataset, pipe, args):
    ply = os.path.join(dataset.model_path, "point_cloud",
                       f"iteration_{args.iteration}", "point_cloud.ply")
    if not os.path.isfile(ply):
        print(f"[ERROR] no trained Gaussians at {ply}.", file=sys.stderr)
        sys.exit(2)

    gaussians = GaussianModel(dataset.sh_degree)
    gaussians.load_ply(ply)
    print(f"[INFO] loaded {ply}")

    cams = load_camera_subset(dataset, args.views)
    n_masked = sum(1 for c in cams if c.gt_mask is not None)
    print(f"[INFO] {n_masked} of {len(cams)} probed views carried a mask.")
    if n_masked == 0:
        print("[ERROR] no view carried a mask: the comparison would score the "
              "rig and the backdrop, not the sherds.", file=sys.stderr)
        sys.exit(2)

    from gaussian_renderer.radegs import render_radegs as render
    background = torch.tensor([1, 1, 1], dtype=torch.float32, device="cuda")
    clouds, kept_views = [], []
    for k, cam in enumerate(cams):
        pkg = render(cam, gaussians, pipe, background, dataset.kernel_size)
        depth = pkg["median_depth"][0].cpu().numpy()
        rmask = (pkg["mask"][0].cpu().numpy() > 0.5)
        gmask = (cam.gt_mask.cpu().numpy() > 0.5) if cam.gt_mask is not None else np.ones_like(rmask, bool)
        pts = unproject(depth, rmask & gmask, cam)
        # Release this view's pixels now: the established 15.6 GiB trap is per
        # retained camera, and only intrinsics/extrinsics/size are needed later.
        for attr in ("original_image", "gt_mask", "gt_alpha_mask", "depth_image", "mask"):
            if torch.is_tensor(getattr(cam, attr, None)):
                setattr(cam, attr, None)
        gc.collect()
        torch.cuda.empty_cache()
        rng = np.random.default_rng(7)
        if len(pts) > args.subsample:
            pts = pts[torch.from_numpy(rng.choice(len(pts), args.subsample, replace=False))]
        print(f"[INFO] view {args.views[k]}: {len(pts):,} sherd points "
              f"({100.0 * len(pts) / max(depth.size, 1):.2f}% of frame).")
        if len(pts) == 0:
            print(f"[ERROR] view {args.views[k]} contributed no sherd points.",
                  file=sys.stderr)
            sys.exit(2)
        clouds.append(pts)
        kept_views.append(args.views[k])
    del gaussians
    gc.collect()
    torch.cuda.empty_cache()

    u = args.mm_per_unit
    pooled = []
    print(f"[INFO] scale: {u:.4f} mm per scene unit.")
    for i in range(len(clouds)):
        for j in range(i + 1, len(clouds)):
            med, p90, mx = pairwise_nn(clouds[i], clouds[j])
            pooled.append((med, kept_views[i], kept_views[j]))
            print(f"[PAIR] views {kept_views[i]}->{kept_views[j]}: "
                  f"median {med * u:.3f} mm, p90 {p90 * u:.3f} mm, max {mx * u:.3f} mm.")
    meds = sorted(m for m, _, _ in pooled)
    print(f"[RESULT] pooled over {len(pooled)} pairs: median-of-medians "
          f"{meds[len(meds) // 2] * u:.3f} mm "
          f"(worst pair {meds[-1] * u:.3f} mm).")
    out = os.path.join(dataset.model_path, "depth_disagreement.json")
    json.dump({"mm_per_unit": u, "views": kept_views,
               "pairs_mm": [{"a": a, "b": b, "median_mm": m * u} for m, a, b in pooled]},
              open(out, "w"), indent=1)
    print(f"[INFO] wrote {out}")
    print("done!")


if __name__ == "__main__":
    parser = ArgumentParser(description="Cross-view depth disagreement probe")
    lp = ModelParams(parser)
    pp = PipelineParams(parser)
    parser.add_argument("--iteration", type=int, default=18000)
    parser.add_argument("--views", nargs="+", type=int, default=[0, 24, 48, 72, 96, 120],
                        help="training-view indices, spread across the ring")
    parser.add_argument("--subsample", type=int, default=20000,
                        help="points per view for the pairwise comparison (seeded)")
    parser.add_argument("--mm_per_unit", type=float, required=True,
                        help="REQUIRED: scene units to millimetres. Guessing a scale "
                             "is how the last false finding happened.")
    a = parser.parse_args(sys.argv[1:])
    with torch.no_grad():
        main(lp.extract(a), pp.extract(a), a)
