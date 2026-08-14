"""Which words find the blue base plate and the turntable?

Both must be in the object mask, for reasons that are not about tidiness:

  THE BLUE BASE is the scale reference. It is a known 13 x 19 cm, and sherd measurements
  are derived from it. Masking it out would remove the only physical scale in the frame.

  THE TURNTABLE carries the graduated tick marks, rotates with the tree, and is strongly
  textured -- good, rigid, plentiful features. Excluding it throws away evidence that helps
  the reconstruction.

Guessing the words is what this exists to avoid. On the sherds, "pottery", "ceramic" and
"sherd" each returned ZERO detections at every threshold while "clay fragment" scored 0.88.
The obvious word is not reliably the working word.
"""
import numpy as np
import torch
from PIL import Image
from transformers import Sam3Model, Sam3Processor

ROOT = "/data/gpfs/projects/punim2657/Rabati2025/16062025"
FRAMES = ["A11_0704", "A14_0837"]

PROMPTS = [
    # the blue base plate
    "blue plate", "blue metal plate", "metal plate", "blue base", "blue square",
    "blue board", "plate",
    # the turntable / graduated dial
    "turntable", "black disc", "dial", "circular platform", "round base",
    "record player", "disc",
    # already known to work, as controls
    "clay fragment", "metal rod",
]
THRESHOLDS = [0.5, 0.3, 0.15]


def main():
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    model = Sam3Model.from_pretrained("facebook/sam3").to(dev).eval()
    proc = Sam3Processor.from_pretrained("facebook/sam3")

    for frame in FRAMES:
        img = Image.open(f"{ROOT}/{frame}.JPG").convert("RGB")
        img.thumbnail((2000, 2000))
        print(f"\n=== {frame} ===")
        print("  " + f"{'prompt':20s}" + "".join(f"  @{t:<5}" for t in THRESHOLDS)
              + "   best   covers")
        for prompt in PROMPTS:
            counts, best, cov = [], 0.0, 0.0
            for t in THRESHOLDS:
                inputs = proc(images=img, text=prompt, return_tensors="pt").to(dev)
                with torch.inference_mode():
                    out = model(**inputs)
                res = proc.post_process_instance_segmentation(
                    out, threshold=t, mask_threshold=0.5,
                    target_sizes=[(img.size[1], img.size[0])])[0]
                m, s = res.get("masks"), res.get("scores")
                counts.append(0 if m is None else int(len(m)))
                if s is not None and len(s):
                    best = max(best, float(s.max()))
                if t == THRESHOLDS[1] and m is not None and len(m):
                    arr = m.detach().cpu().numpy()
                    if arr.ndim == 4:
                        arr = arr[:, 0]
                    cov = float(np.any(arr > 0.5, axis=0).mean())
            cells = "".join(f"  {c:<6d}" for c in counts)
            flag = "  <--" if counts[-1] else ""
            print(f"  {prompt:20s}{cells}   {best:.3f}  {100*cov:5.1f}%{flag}")


if __name__ == "__main__":
    main()
