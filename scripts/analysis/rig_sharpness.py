"""Are A03's photographs softer than A02's, or are only its sherds?

A03's photographs yield 5,600 detectable features each where A02's yield 19,300 -- and that
deficit is spread over the whole frame, not confined to the sherds. Something about the
pictures themselves carries less fine detail. This separates the two possible reasons.

The rig is the control. The grey clamp and the stand are the SAME physical objects,
photographed by the same camera on consecutive days. They cannot have got less detailed.
So if they come out softer in A03, the camera or the light changed and the whole capture
is affected. If the rig is equally sharp in both and only the sherds are soft, the
difference belongs to the sherds and how they were lit and mounted.

Sharpness is measured as high-frequency energy: the variance of the Laplacian, in grey
levels, over regions of matched type. Reported separately for rig and sherd so the two
readings can disagree.
"""
import sys
from pathlib import Path

import cv2
import numpy as np


def regions(bgr):
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    h, s, v = hsv[..., 0], hsv[..., 1], hsv[..., 2]
    sherd = (((h <= 22) | (h >= 170)) & (s >= 60) & (v >= 55))
    rig = (s < 45) & (v > 70) & (v < 235)          # grey clamp / stand, not black, not blown
    k5, k9 = np.ones((5, 5), np.uint8), np.ones((9, 9), np.uint8)
    sherd = cv2.erode(cv2.morphologyEx(sherd.astype(np.uint8), cv2.MORPH_OPEN, k5), k9)
    rig = cv2.erode(cv2.morphologyEx(rig.astype(np.uint8), cv2.MORPH_OPEN, k5), k9)
    return sherd.astype(bool), rig.astype(bool)


def analyse(tag, folder, every=20):
    fs = [f for f in sorted(Path(folder).iterdir())
          if f.suffix.lower() in (".jpg", ".png")][::every]
    out = {"sherd": [], "rig": [], "frame": [], "rigbright": [], "rigarea": []}
    for f in fs:
        bgr = cv2.imread(str(f), cv2.IMREAD_COLOR)
        if bgr is None:
            continue
        S, R = regions(bgr)
        g = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY).astype(np.float32)
        lap = cv2.Laplacian(g, cv2.CV_32F, ksize=3)
        out["frame"].append(lap.var())
        if S.sum() > 3000:
            out["sherd"].append(lap[S].var())
        if R.sum() > 3000:
            out["rig"].append(lap[R].var())
            out["rigbright"].append(g[R].mean())
            out["rigarea"].append(100 * R.mean())
    if not out["rig"]:
        print(f"{tag}: no rig region found"); return None
    m = {k: float(np.mean(v)) if v else 0.0 for k, v in out.items()}
    print(f"\n{tag}  ({len(fs)} photographs sampled)")
    print(f"  whole frame sharpness            {m['frame']:8.1f}")
    print(f"  RIG  (same hardware both days)   {m['rig']:8.1f}"
          f"   brightness {m['rigbright']:5.1f}/255, {m['rigarea']:.1f}% of frame")
    print(f"  SHERD                            {m['sherd']:8.1f}")
    return m


if __name__ == "__main__":
    res = {}
    for arg in sys.argv[1:]:
        tag, folder = arg.split("=", 1)
        r = analyse(tag, folder)
        if r:
            res[tag] = r
    if len(res) >= 2:
        base = list(res)[0]
        b = res[base]
        print(f"\nrelative to {base}:")
        for k, m in res.items():
            print(f"  {k:<6} whole frame {m['frame']/b['frame']:5.2f}x   "
                  f"RIG {m['rig']/b['rig']:5.2f}x   sherd {m['sherd']/b['sherd']:5.2f}x")
        print("\n  the rig column is the control: it is the same physical object every day.")
