"""What does SAM 3 actually return? A probe, not a test.

The six-frame test reported 0 detections for every frame, every orientation and every
prompt -- including "metal clamp", which is an ordinary object -- at 0.04 s per call, which
is far too fast for an 848M-parameter model. A number that is constant across all inputs is
a bug until proven otherwise, so this inspects the output structure rather than trusting
the keys the README example implies.
"""
import numpy as np
import torch
from PIL import Image

from sam3.model_builder import build_sam3_image_model
from sam3.model.sam3_image_processor import Sam3Processor

IMG = "/data/gpfs/projects/punim2657/Rabati2025/16062025/A11_0704.JPG"

model = build_sam3_image_model()
proc = Sam3Processor(model)

img = Image.open(IMG).convert("RGB")
img.thumbnail((2000, 2000))
print("image size:", img.size)

with torch.inference_mode(), torch.autocast("cuda", dtype=torch.bfloat16):
    state = proc.set_image(img)
    # Something obviously present, to separate "model is broken" from "sherd is too rare".
    for prompt in ("pottery sherd", "metal clamp", "object", "rock"):
        out = proc.set_text_prompt(state=state, prompt=prompt)
        print(f"\n=== prompt: {prompt!r} -> {type(out).__name__}")
        if isinstance(out, dict):
            for k, v in out.items():
                shape = getattr(v, "shape", None)
                n = len(v) if hasattr(v, "__len__") else "-"
                print(f"    {k:16s} {type(v).__name__:14s} shape={shape} len={n}")
            sc = out.get("scores")
            if sc is not None and hasattr(sc, "numel"):
                sc = sc.detach().float().cpu().numpy().ravel()
                if sc.size:
                    print(f"    scores: n={sc.size} min={sc.min():.3f} "
                          f"max={sc.max():.3f} >0.5={(sc > 0.5).sum()} >0.1={(sc > 0.1).sum()}")
                else:
                    print("    scores: EMPTY")
        else:
            print("    attributes:", [a for a in dir(out) if not a.startswith("_")][:30])

print("\n=== what else can the processor do? ===")
print("  Sam3Processor methods:",
      [m for m in dir(proc) if not m.startswith("_")])
print("\n=== state keys ===")
if isinstance(state, dict):
    for k, v in state.items():
        print(f"    {k:20s} {type(v).__name__} shape={getattr(v, 'shape', None)}")
else:
    print("   ", [a for a in dir(state) if not a.startswith("_")][:30])
