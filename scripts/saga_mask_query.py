"""Headless mask-prompt query for the SAGA track (ticket alt-09).

Replicates prompt_segmenting.ipynb cells 4/11/12/14/15/24/25/29 without the
notebook or GUI: render contrastive features for spread views, average the
rendered features over OUR sherd-mask pixels as the query (no hand-picked
pixel), cosine similarity against per-Gaussian features, keep-index at three
prespecified thresholds plus similarity overlays for the eye.

Primary threshold prespecified: 0.6 (notebook uses 0.75 for display, 0.5 as
viz floor; training showed 2D pos 0.86 / neg -0.55). All three counts plus the
raw similarities are saved, so re-thresholding needs no GPU.

Usage (saga env, GPU):
    python saga_mask_query.py --saga_root /data/.../saga \\
        --src /data/.../saga_data/A03 --model /data/.../output/saga_A03 \\
        --out /data/.../output/saga_A03/query
"""

import argparse
import json
import os
import sys

import numpy as np
import torch
from PIL import Image


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--saga_root", required=True)
    ap.add_argument("--src", required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--feature_iter", type=int, default=10000)
    ap.add_argument("--thresholds", default="0.0,0.1,0.2,0.5,0.6,0.75")
    ap.add_argument("--overlay_thrs", default="0.0,0.1,0.2,0.6")
    args = ap.parse_args()

    # SAGA's loader reads sys.argv behind our back (get_combined_args parses
    # it inside). Rebuild argv with only SAGA-known flags carrying our paths —
    # a bare argv leaves model_path empty and the config lookup fails.
    # The saved feature cfg already carries every other SAGA-side value.
    sys.argv = [sys.argv[0], "-s", args.src, "-m", args.model,
                "--target", "contrastive_feature", "--image_root", args.src]

    sys.path.insert(0, args.saga_root)
    from argparse import ArgumentParser, Namespace  # noqa
    from arguments import ModelParams, PipelineParams, OptimizationParams, get_combined_args  # noqa
    from scene import Scene, GaussianModel  # noqa
    from scene.gaussian_model_ff import FeatureGaussianModel  # noqa
    from gaussian_renderer import render_contrastive_feature  # noqa

    FEATURE_DIM = 32
    os.makedirs(args.out, exist_ok=True)

    # Args the way train built them: full registration + saved feature cfg.
    parser = ArgumentParser()
    model = ModelParams(parser)
    pipe = PipelineParams(parser)
    opt = OptimizationParams(parser)
    parser.add_argument("--target", default="contrastive_feature")
    parser.add_argument("--iteration", default=-1, type=int)
    parser.add_argument("--image_root", default=args.src)
    ns = get_combined_args(parser)
    ns.source_path, ns.model_path = args.src, args.model
    dataset = model.extract(ns)
    dataset.need_features = False
    dataset.need_masks = False

    scale_gate = torch.nn.Sequential(torch.nn.Linear(1, 32, bias=True),
                                     torch.nn.Sigmoid())
    gate_path = os.path.join(args.model, "point_cloud",
                             f"iteration_{args.feature_iter}", "scale_gate.pt")
    scale_gate.load_state_dict(torch.load(gate_path))
    scale_gate = scale_gate.cuda().eval()

    scene_gaussians = GaussianModel(dataset.sh_degree)
    feature_gaussians = FeatureGaussianModel(FEATURE_DIM)
    scene = Scene(dataset, scene_gaussians, feature_gaussians,
                  load_iteration=-1, feature_load_iteration=args.feature_iter,
                  shuffle=False, mode="eval", target="contrastive_feature")
    cameras = scene.getTrainCameras()
    print(f"{len(cameras)} train cameras; "
          f"{feature_gaussians.get_point_features.shape[0]} feature Gaussians",
          flush=True)

    spread = cameras[::16]  # 11 views around the ring
    queries = []
    with torch.no_grad():
        gates = scale_gate(torch.tensor([1.0]).cuda())
        for idx, view in enumerate(spread):
            view.feature_height, view.feature_width = (view.image_height,
                                                       view.image_width)
            bg = torch.zeros(FEATURE_DIM, dtype=torch.float32, device="cuda")
            rendered = render_contrastive_feature(
                view, feature_gaussians, pipe.extract(ns), bg,
                norm_point_features=True, smooth_type=None)["render"]
            C, H, W = rendered.shape
            stem = view.image_name.split(".")[0]
            mask = torch.load(os.path.join(args.src, "sam_masks", stem + ".pt"),
                              weights_only=True)[0].to("cuda")  # sherd row
            if mask.shape != (H, W):
                mask = torch.nn.functional.interpolate(
                    mask[None, None].float(), size=(H, W),
                    mode="nearest")[0, 0].bool()
            feat = (rendered * gates.unsqueeze(-1).unsqueeze(-1)).permute(1, 2, 0)
            feat = torch.nn.functional.normalize(feat, dim=-1, p=2)
            q = feat[mask].mean(dim=0)
            queries.append(q)
            print(f"view {idx} ({view.image_name}): "
                  f"{int(mask.sum())} masked px, query norm {float(q.norm()):.3f}",
                  flush=True)
    query_feature = torch.stack(queries).mean(dim=0)
    query_feature = query_feature / query_feature.norm()
    torch.save(query_feature.cpu(), os.path.join(args.out, "query_feature.pt"))

    with torch.no_grad():
        pf = feature_gaussians.get_point_features
        pf = pf * gates.unsqueeze(0)
        pf = torch.nn.functional.normalize(pf, dim=-1, p=2)
        sims = torch.einsum("C,NC->N", query_feature.cuda(), pf).cpu()
    torch.save(sims, os.path.join(args.out, "similarities.pt"))
    sims_np = sims.numpy()

    report = {"n_gaussians": int(sims.numel()),
              "sim_median": float(np.median(sims_np)),
              "sim_p10": float(np.percentile(sims_np, 10)),
              "sim_p90": float(np.percentile(sims_np, 90)),
              "thresholds": {}}
    for thr in (float(t) for t in args.thresholds.split(",")):
        keep = np.nonzero(sims_np > thr)[0]
        np.save(os.path.join(args.out, f"keep_idx_{thr:g}.npy"), keep)
        report["thresholds"][str(thr)] = {
            "kept": int(len(keep)),
            "frac": float(len(keep) / len(sims_np)),
            "kept_frac_of_full_scene": float(len(keep) / 222678)}
        print(f"thr {thr:g}: kept {len(keep)} "
              f"({100 * len(keep) / len(sims_np):.1f}%)", flush=True)

    # Overlays for the eye at each overlay threshold (rendered sim > thr).
    # Which thresholds separate sherd from rig is read off these pictures,
    # not off the training numbers: the 3D point sims live far lower.
    import glob as _glob
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    def _photo(stem):
        hits = _glob.glob(os.path.join(args.src, "images", stem + ".*"))
        assert hits, stem  # SAGA's image_name is the stem; resolve extension
        return np.asarray(Image.open(hits[0]).convert("RGB"))

    overlay_thrs = [float(t) for t in args.overlay_thrs.split(",")]
    for idx in (0, len(spread) // 2, -1):
        view = spread[idx]
        view.feature_height, view.feature_width = (view.image_height,
                                                   view.image_width)
        with torch.no_grad():
            bg = torch.zeros(FEATURE_DIM, dtype=torch.float32, device="cuda")
            rendered = render_contrastive_feature(
                view, feature_gaussians, pipe.extract(ns), bg,
                norm_point_features=True, smooth_type=None)["render"]
            feat = (rendered * gates.unsqueeze(-1).unsqueeze(-1)).permute(1, 2, 0)
            feat = torch.nn.functional.normalize(feat, dim=-1, p=2)
            sm = torch.einsum(
                "C,HWC->HW", query_feature.cuda(), feat).cpu().numpy()
        stem = view.image_name.split(".")[0]
        photo = _photo(stem)
        if photo.shape[:2] != sm.shape:
            from PIL import Image as _I
            photo = np.asarray(_I.open(
                _glob.glob(os.path.join(args.src, "images", stem + ".*"))[0]
                ).convert("RGB").resize((sm.shape[1], sm.shape[0])))
        n = len(overlay_thrs)
        fig, ax = plt.subplots(1, 2 + n, figsize=(5 * (2 + n), 5))
        ax[0].imshow(photo)
        ax[0].set_title(view.image_name)
        ax[1].imshow(sm, vmin=-1, vmax=1, cmap="coolwarm")
        ax[1].set_title("similarity")
        for j, thr in enumerate(overlay_thrs):
            ax[2 + j].imshow(photo)
            ax[2 + j].imshow(sm > thr, alpha=0.45, cmap="Greens")
            ax[2 + j].set_title(f"keep>{thr:g}")
        for a in ax:
            a.axis("off")
        fig.savefig(os.path.join(args.out, f"overlay_{idx}.png"), dpi=70)
        plt.close(fig)
    json.dump(report, open(os.path.join(args.out, "query_report.json"),
                           "w"), indent=2)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
