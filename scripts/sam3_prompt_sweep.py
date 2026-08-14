"""Which words does SAM 3 recognise these sherds by, and is the threshold hiding the rest?

The probe found the model works but the vocabulary is narrow: "rock" returned 9 instances
at scores 0.527-0.594, while "pottery sherd", "metal clamp" and "object" each returned
zero. Two explanations fit that, and they lead to different places:

  VOCABULARY   the concept is not in the model's range, and no threshold will help
  THRESHOLD    it does find them but scores below the default cut, and lowering it helps

The "rock" scores barely cleared 0.5, so the second is worth ruling in or out before
concluding anything. Sam3Processor exposes set_confidence_threshold for exactly this.

Reports counts per prompt at several thresholds, across both backdrops.
"""
import sys

import numpy as np
import torch
from PIL import Image

from sam3.model_builder import build_sam3_image_model
from sam3.model.sam3_image_processor import Sam3Processor

ROOT = "/data/gpfs/projects/punim2657/Rabati2025/16062025"
FRAMES = ["A11_0704", "A14_0837"]          # black backdrop, then the lit grey set

PROMPTS = [
    # what worked
    "rock",
    # material words
    "stone", "pottery", "ceramic", "clay", "terracotta", "earthenware",
    # object words
    "shard", "sherd", "fragment", "broken pottery", "piece of pottery",
    "pottery fragment", "clay fragment", "stone fragment",
    # the rig, for the inverse mask
    "clamp", "metal clamp", "laboratory clamp", "metal rod", "metal", "tool",
]
THRESHOLDS = [0.5, 0.3, 0.15, 0.05]


def main():
    model = build_sam3_image_model()
    proc = Sam3Processor(model)
    print(f"default confidence_threshold: {getattr(proc, 'confidence_threshold', '?')}\n")

    for frame in FRAMES:
        img = Image.open(f"{ROOT}/{frame}.JPG").convert("RGB")
        img.thumbnail((2000, 2000))
        print(f"=== {frame}  {img.size[0]}x{img.size[1]} ===")
        header = "  " + f"{'prompt':22s}" + "".join(f"  @{t:<5}" for t in THRESHOLDS) + "   best"
        print(header)
        with torch.inference_mode(), torch.autocast("cuda", dtype=torch.bfloat16):
            state = proc.set_image(img)
            for prompt in PROMPTS:
                counts, best = [], 0.0
                for t in THRESHOLDS:
                    proc.set_confidence_threshold(t)
                    out = proc.set_text_prompt(state=state, prompt=prompt)
                    sc = out.get("scores")
                    sc = sc.detach().float().cpu().numpy().ravel() if sc is not None else np.array([])
                    counts.append(int(sc.size))
                    best = max(best, float(sc.max()) if sc.size else 0.0)
                cells = "".join(f"  {c:<6d}" for c in counts)
                flag = "  <-- " if counts[-1] else ""
                print(f"  {prompt:22s}{cells}   {best:.3f}{flag}")
        print()


if __name__ == "__main__":
    sys.exit(main())
