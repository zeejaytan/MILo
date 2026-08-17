"""Which prompt is claiming which object? One panel per prompt, on real frames.

Written because masks_measure lost 97% of the blue base on tree A03: the hardware prompts
claimed the plate, so subtracting them from the base mask erased the scale reference. The
grouped overlay cannot show why -- it draws the result, not who claimed what -- and the
plate is a blue METAL plate, so more than one prompt is a plausible culprit.

Guessing which one is how the pipeline got here. This renders each prompt separately, at
the SAME threshold the real run uses, and prints how much of the frame each claims and how
much each overlaps the plate.

Usage:
    python sam3_prompt_diag.py --images <dir> --out <dir> [--frames 6]
"""
import argparse
import sys
from pathlib import Path

import numpy as np
import torch
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).parent))
from sam3_masks import (SHERD_PROMPTS, HARDWARE_PROMPTS, BASE_PROMPTS,
                        TURNTABLE_PROMPTS, encode_image, union_mask)

GROUPS = [("sherd", SHERD_PROMPTS), ("hardware", HARDWARE_PROMPTS),
          ("base", BASE_PROMPTS), ("turntable", TURNTABLE_PROMPTS)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--images", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--model", default="facebook/sam3")
    ap.add_argument("--threshold", type=float, default=0.3)
    ap.add_argument("--seg-side", type=int, default=2000)
    ap.add_argument("--frames", type=int, default=6)
    args = ap.parse_args()

    from transformers import Sam3Model, Sam3Processor

    paths = sorted(p for p in args.images.iterdir()
                   if p.suffix.lower() in (".jpg", ".jpeg"))
    # Spread across the capture: the plate is edge-on or out of frame for part of a turn,
    # and a run of consecutive frames would show only one of those situations.
    pick = [paths[i] for i in np.linspace(0, len(paths) - 1, args.frames).astype(int)]

    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = Sam3Model.from_pretrained(args.model).to(device).eval()
    processor = Sam3Processor.from_pretrained(args.model)
    args.out.mkdir(parents=True, exist_ok=True)
    print(f"device {device}, {len(pick)} frames, threshold {args.threshold}\n")

    flat = [(g, p) for g, ps in GROUPS for p in ps]
    totals = {p: [] for _, p in flat}
    overlap = {p: [] for _, p in flat}

    for path in pick:
        full = Image.open(path).convert("RGB")
        small = full.copy(); small.thumbnail((args.seg_side, args.seg_side))
        sw, sh = small.size
        emb = encode_image(processor, model, small, device)

        masks = {}
        for _, prompt in flat:
            m, _ = union_mask(processor, model, emb, [prompt], device,
                              args.threshold, (sh, sw))
            masks[prompt] = m
            totals[prompt].append(float(m.mean()))

        # "The plate" for this comparison is what the base prompts agree on between them.
        plate = np.zeros((sh, sw), bool)
        for p in BASE_PROMPTS:
            plate |= masks[p]
        for _, prompt in flat:
            overlap[prompt].append(
                float((masks[prompt] & plate).sum() / max(plate.sum(), 1)))

        cols = 1 + len(flat)
        W = sw // 2; H = sh // 2
        sheet = Image.new("RGB", (W * cols, H), (18, 18, 18))
        sheet.paste(small.resize((W, H)), (0, 0))
        d = ImageDraw.Draw(sheet)
        d.text((8, 8), path.name, fill=(255, 255, 255))
        for k, (grp, prompt) in enumerate(flat, start=1):
            vis = np.asarray(small).copy()
            sel = masks[prompt]
            vis[sel] = (0.35 * vis[sel] + 0.65 * np.array([255, 90, 90])).astype(np.uint8)
            panel = Image.fromarray(vis).resize((W, H))
            sheet.paste(panel, (k * W, 0))
            d2 = ImageDraw.Draw(sheet)
            d2.text((k * W + 8, 8), f'"{prompt}"  [{grp}]', fill=(255, 255, 255))
            d2.text((k * W + 8, 26),
                    f"{100*masks[prompt].mean():.1f}% of frame, "
                    f"{100*overlap[prompt][-1]:.0f}% of plate", fill=(200, 200, 200))
        out = args.out / f"prompts_{path.stem}.jpg"
        sheet.save(out, quality=88)
        print(f"  {path.name} -> {out.name}")

    print(f"\n{'prompt':<22} {'group':<10} {'% of frame':>11} {'% OF THE PLATE it claims':>26}")
    for grp, prompt in flat:
        print(f'{prompt:<22} {grp:<10} {100*np.mean(totals[prompt]):10.1f}% '
              f'{100*np.mean(overlap[prompt]):25.0f}%')
    print("\nA hardware prompt claiming most of the plate is the bug: masks_measure")
    print("subtracts hardware from base, so that prompt is what erases the scale reference.")


if __name__ == "__main__":
    main()
