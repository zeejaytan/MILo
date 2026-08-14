"""Can SAM 3 tell a pottery sherd from the clamp holding it?

This is a test of the ONE thing that decides whether SAM 3 is usable here. Separating the
rig from the backdrop is easy and any method manages it; separating a sherd from the metal
clamp gripping it is fine-grained, physically touching and partly occluding -- and it is
the boundary that a sherds-only mesh depends on. Ultralytics' documentation warns that
"performance may degrade on extremely rare or fine-grained concepts", and archaeological
potsherds in laboratory clamps are exactly that. None of the sources found addressed
overlapping objects at all, so it has to be tried.

Two variables are crossed deliberately:

  BACKDROP.    133 frames were shot against black, 44 (the A14_* set) against a lit grey
               backdrop from a lower angle. A brightness rule cannot serve both -- that is
               what defeated the earlier thresholding attempt. A semantic model should not
               care, and this checks whether that is true.

  ORIENTATION. These files carry EXIF orientation 8. COLMAP reads the stored pixels and
               ignores the tag, so masks must be generated in stored (sideways)
               orientation to line up. But a model trained on upright photographs may
               recognise a sherd better upright. Both are run: if upright wins, the fix is
               to segment upright and rotate the mask back, not to feed COLMAP a rotated
               mask.

Nothing here is believed without the contact sheet. Counts and scores are reported, but
the output to look at is the overlay.

Usage:
    python sam3_test.py --images <dir> --out <dir> [--frames A11_0704 ...]
"""
import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import torch
from PIL import Image, ImageOps

# Prompts worth trying, from most to least domain-specific. The specific ones are what we
# want; the generic ones tell us whether a failure is about vocabulary or about the image.
PROMPTS = [
    "pottery sherd",
    "pottery fragment",
    "ceramic fragment",
    "broken piece of pottery",
    "metal clamp",          # the inverse: if this is clean, masking the RIG out is viable
]


def load_model():
    from sam3.model_builder import build_sam3_image_model
    from sam3.model.sam3_image_processor import Sam3Processor
    t = time.time()
    model = build_sam3_image_model()
    print(f"  model loaded in {time.time() - t:.1f}s", flush=True)
    return Sam3Processor(model)


def to_np(x):
    """SAM 3 returns CUDA tensors; numpy cannot touch them directly."""
    if hasattr(x, "detach"):
        return x.detach().float().cpu().numpy()
    return np.asarray(x)


def overlay(img_rgb, masks, scores, min_score):
    """Tint each accepted instance and outline it, so boundaries are judgeable."""
    import cv2
    out = np.asarray(img_rgb).copy()
    colours = [(255, 70, 70), (70, 200, 255), (120, 255, 120), (255, 220, 60),
               (255, 120, 255), (255, 160, 60)]
    kept = 0
    for i, (m, s) in enumerate(zip(masks, scores)):
        if s < min_score:
            continue
        m = to_np(m).astype(np.uint8)
        if m.ndim == 3:
            m = m[0]
        if m.shape != out.shape[:2]:
            m = cv2.resize(m, (out.shape[1], out.shape[0]), interpolation=cv2.INTER_NEAREST)
        c = colours[kept % len(colours)]
        out[m > 0] = (0.55 * out[m > 0] + 0.45 * np.array(c)).astype(np.uint8)
        edge = cv2.dilate(cv2.Canny(m * 255, 50, 150), np.ones((3, 3), np.uint8))
        out[edge > 0] = c
        kept += 1
    return out, kept


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--images", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--frames", nargs="*", default=None)
    ap.add_argument("--max-side", type=int, default=2000,
                    help="downscale longest side before segmenting. The full 5568px frame "
                         "is slow and SAM 3 resizes internally anyway; 2000 keeps the "
                         "sherd/clamp boundary resolvable while the test stays cheap.")
    ap.add_argument("--min-score", type=float, default=0.5)
    args = ap.parse_args()

    import cv2  # noqa: F401  (checked early, used in overlay)
    args.out.mkdir(parents=True, exist_ok=True)

    if args.frames:
        paths = [args.images / f"{f}.JPG" for f in args.frames]
    else:
        paths = sorted(p for p in args.images.iterdir()
                       if p.suffix.lower() in (".jpg", ".jpeg"))[:6]
    missing = [p for p in paths if not p.exists()]
    if missing:
        sys.exit(f"missing: {[str(m) for m in missing]}")

    print(f"device: {'cuda' if torch.cuda.is_available() else 'CPU (will be very slow)'}")
    if torch.cuda.is_available():
        print(f"  {torch.cuda.get_device_name(0)}")
    processor = load_model()

    # SAM 3 must run under bfloat16 autocast. Its weights are bf16 and the processor does
    # NOT set this itself, so calling it exactly as the README's minimal example shows
    # fails with "mat1 and mat2 must have the same dtype, but got BFloat16 and Float".
    # All six example notebooks in the repo open this context first; the README does not
    # mention it. The examples are the real reference here, not the README.
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    autocast = torch.autocast(dev, dtype=torch.bfloat16, enabled=(dev == "cuda"))

    rows = []
    with torch.inference_mode(), autocast:
      for path in paths:
          raw = Image.open(path).convert("RGB")
          for orient in ("stored", "upright"):
              # ImageOps.exif_transpose applies the tag; cv2/COLMAP do not. See the docstring.
              img = ImageOps.exif_transpose(raw) if orient == "upright" else raw
              img = img.copy()
              img.thumbnail((args.max_side, args.max_side))
              state = processor.set_image(img)
              for prompt in PROMPTS:
                  t = time.time()
                  out = processor.set_text_prompt(state=state, prompt=prompt)
                  dt = time.time() - t
                  masks = out.get("masks", [])
                  scores = to_np(out.get("scores", [])).ravel()
                  vis, kept = overlay(img, masks, scores, args.min_score)
                  cov = 0.0
                  if kept:
                      acc = [to_np(m)[0] if to_np(m).ndim == 3 else to_np(m)
                             for m, s in zip(masks, scores) if s >= args.min_score]
                      cov = float(np.any(np.stack(acc) > 0, axis=0).mean())
                  tag = f"{path.stem}__{orient}__{prompt.replace(' ', '_')}"
                  Image.fromarray(vis).save(args.out / f"{tag}.jpg", quality=88)
                  rows.append(dict(frame=path.stem, orientation=orient, prompt=prompt,
                                   instances=int(len(scores)), kept=kept,
                                   best=float(scores.max()) if len(scores) else 0.0,
                                   coverage=round(cov, 4), seconds=round(dt, 2)))
                  print(f"  {path.stem:12s} {orient:8s} {prompt:24s} "
                        f"{len(scores):3d} found, {kept:3d} kept, "
                        f"best {rows[-1]['best']:.2f}, covers {100*cov:5.1f}%, {dt:5.2f}s",
                        flush=True)

    (args.out / "results.json").write_text(json.dumps(rows, indent=2))

    print("\n=== which prompt found the most, per orientation ===")
    for orient in ("stored", "upright"):
        sub = [r for r in rows if r["orientation"] == orient]
        for prompt in PROMPTS:
            rs = [r for r in sub if r["prompt"] == prompt]
            if rs:
                print(f"  {orient:8s} {prompt:24s} kept {np.mean([r['kept'] for r in rs]):5.1f} "
                      f"avg, covers {100*np.mean([r['coverage'] for r in rs]):5.1f}% avg")

    print(f"\nLOOK AT {args.out}. The question is not how many instances it found -- it is")
    print("whether the outline follows the sherd or wanders onto the clamp gripping it.")


if __name__ == "__main__":
    main()
