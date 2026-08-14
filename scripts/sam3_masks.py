"""Generate COLMAP masks for a whole tree with SAM 3, via the transformers API.

Replaces the standalone-repo version. The Hugging Face model card documents this path and
it avoids every problem the GitHub README route produced: no cloned repo, no editable
install, no `pkg_resources` against a setuptools that removed it, no undeclared
einops/pycocotools/psutil, and no bfloat16 autocast context to discover from example
notebooks. One dependency instead of a source tree.

WHAT PROMPT. This matters more than any parameter. On tree A01 the model returned ZERO
detections at every threshold down to 0.05 for "pottery", "ceramic", "sherd" and "pottery
fragment" -- it has no concept of pottery at all. It scores "clay fragment" at 0.88-0.91
and finds every sherd on the tree. Testing only the obvious words would have condemned SAM
3 as unusable for this material.

ORIENTATION. These files carry EXIF 8. COLMAP reads stored pixels and ignores the tag, so
masks must be written in stored orientation. Segmenting upright scored marginally better
(0.91 vs 0.88) but returned IDENTICAL counts, so this segments in stored orientation and
skips the invertible-rotation step -- one less thing to get silently wrong.

NAMING. COLMAP wants "<image filename>.png", keeping the original extension:
A11_0704.JPG -> A11_0704.JPG.png. The existing maskbuild tool writes "<stem>.png", which
COLMAP will not match, and a mask it cannot find is a mask it silently ignores.

TWO MASK SETS, because the two downstream uses want different things:
  masks_sherds/  just the sherds -- for a sherds-only dense reconstruction
  masks_object/  sherds AND rig, i.e. everything but the backdrop -- for SfM and for MILo,
                 which otherwise spends its capacity modelling the room

Usage:
    python sam3_masks.py --images <dir> --out <dir> [--overlay-every 20]
"""
import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import torch
from PIL import Image

SHERD_PROMPTS = ["clay fragment"]
RIG_PROMPTS = ["metal rod", "metal"]


def union_mask(processor, model, image, prompts, device, threshold, target_hw):
    """Union of all instances matched by any prompt, at the original image size."""
    total = np.zeros(target_hw, bool)
    detail = {}
    for prompt in prompts:
        inputs = processor(images=image, text=prompt, return_tensors="pt").to(device)
        with torch.inference_mode():
            outputs = model(**inputs)
        res = processor.post_process_instance_segmentation(
            outputs, threshold=threshold, mask_threshold=0.5,
            target_sizes=[target_hw])[0]
        masks = res.get("masks")
        scores = res.get("scores")
        n = 0
        if masks is not None and len(masks):
            m = masks.detach().cpu().numpy()
            if m.ndim == 4:
                m = m[:, 0]
            total |= np.any(m > 0.5, axis=0)
            n = int(len(m))
        best = float(scores.max()) if scores is not None and len(scores) else 0.0
        detail[prompt] = dict(instances=n, best=round(best, 3))
    return total, detail


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--images", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--model", default="facebook/sam3")
    ap.add_argument("--threshold", type=float, default=0.3)
    ap.add_argument("--seg-side", type=int, default=2000,
                    help="segment at this longest side, then upscale the mask to full "
                         "resolution. Masks gate feature extraction, so a few pixels of "
                         "slop is harmless and the dilation below covers it.")
    ap.add_argument("--dilate", type=int, default=8,
                    help="grow each mask, so features ON the silhouette survive")
    ap.add_argument("--overlay-every", type=int, default=20)
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    import cv2
    from transformers import Sam3Model, Sam3Processor

    paths = sorted(p for p in args.images.iterdir()
                   if p.suffix.lower() in (".jpg", ".jpeg"))
    if args.limit:
        paths = paths[:args.limit]
    if not paths:
        sys.exit(f"no photographs in {args.images}")

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"device: {device}")
    if device == "cuda":
        print(f"  {torch.cuda.get_device_name(0)}")
    model = Sam3Model.from_pretrained(args.model).to(device)
    processor = Sam3Processor.from_pretrained(args.model)
    model.eval()
    print(f"  {args.model} loaded")

    dirs = {k: args.out / k for k in ("masks_sherds", "masks_object", "overlays")}
    for d in dirs.values():
        d.mkdir(parents=True, exist_ok=True)

    kern = cv2.getStructuringElement(
        cv2.MORPH_ELLIPSE, (2 * args.dilate + 1, 2 * args.dilate + 1))
    rows, t0 = [], time.time()

    for i, path in enumerate(paths):
        # No exif_transpose: COLMAP reads the stored pixels, so the mask must match them.
        full = Image.open(path).convert("RGB")
        W, H = full.size
        small = full.copy()
        small.thumbnail((args.seg_side, args.seg_side))

        sherds, sd = union_mask(processor, model, small, SHERD_PROMPTS,
                                device, args.threshold, (H, W))
        rig, rd = union_mask(processor, model, small, RIG_PROMPTS,
                             device, args.threshold, (H, W))
        obj = sherds | rig

        for name, m in (("masks_sherds", sherds), ("masks_object", obj)):
            out = (m.astype(np.uint8) * 255)
            if args.dilate:
                out = cv2.dilate(out, kern)
            cv2.imwrite(str(dirs[name] / (path.name + ".png")), out)

        n_sherd = sum(v["instances"] for v in sd.values())
        rows.append(dict(frame=path.name, sherd_instances=n_sherd,
                         sherd_best=max(v["best"] for v in sd.values()),
                         sherd_coverage=round(float(sherds.mean()), 4),
                         object_coverage=round(float(obj.mean()), 4)))

        if i % args.overlay_every == 0:
            vis = np.asarray(small).copy()
            sm = cv2.resize(sherds.astype(np.uint8), small.size,
                            interpolation=cv2.INTER_NEAREST)
            rm = cv2.resize(rig.astype(np.uint8), small.size,
                            interpolation=cv2.INTER_NEAREST)
            vis[rm > 0] = (0.7 * vis[rm > 0] + 0.3 * np.array([80, 80, 255])).astype(np.uint8)
            vis[sm > 0] = (0.55 * vis[sm > 0] + 0.45 * np.array([255, 80, 80])).astype(np.uint8)
            Image.fromarray(vis).save(dirs["overlays"] / f"{path.stem}.jpg", quality=85)

        if (i + 1) % 20 == 0 or i == len(paths) - 1:
            print(f"  {i+1}/{len(paths)}  {path.name}  "
                  f"{n_sherd} sherds, covers {100*rows[-1]['sherd_coverage']:.1f}%  "
                  f"({(time.time()-t0)/(i+1):.2f}s/frame)", flush=True)

    (args.out / "masks.json").write_text(json.dumps(rows, indent=2))

    ns = np.array([r["sherd_instances"] for r in rows])
    cov = np.array([r["sherd_coverage"] for r in rows])
    print(f"\n=== {len(rows)} frames in {time.time()-t0:.0f}s ===")
    print(f"  sherd instances per frame: min {ns.min()} median {int(np.median(ns))} max {ns.max()}")
    print(f"  sherd coverage: min {100*cov.min():.1f}% median {100*np.median(cov):.1f}% "
          f"max {100*cov.max():.1f}%")

    # A frame with nothing found is the failure that matters, and it is invisible in an
    # average. Name them so they can be looked at.
    bad = [r["frame"] for r in rows if r["sherd_instances"] == 0]
    if bad:
        print(f"\n  {len(bad)} FRAME(S) WITH NO SHERDS FOUND -- look at these:")
        for b in bad[:12]:
            print(f"    {b}")
    else:
        print("\n  every frame found at least one sherd")

    print(f"\nLOOK AT {dirs['overlays']} before using these.")
    print("Red = sherds, blue = rig. The question is whether the outline stops at the clamp.")


if __name__ == "__main__":
    main()
