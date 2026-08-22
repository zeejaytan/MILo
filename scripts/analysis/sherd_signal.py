"""How strong is the photographic signal ON the sherds in each capture?

Gaussian splatting adds detail where the picture disagrees with the render, and it measures
that disagreement as image gradient. So the thing that decides how finely a surface gets
modelled is not how many pixels cover it -- both captures record 5 pixels per millimetre --
but how much those pixels VARY: how bright the sherd is, how much local contrast its
surface carries, and how sharply it is focused.

A dim, low-contrast, slightly soft sherd asks the optimiser for very little, and gets it.
"""
import sys
from pathlib import Path

import numpy as np
import cv2


def sherd_mask(bgr):
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    h, s, v = hsv[..., 0], hsv[..., 1], hsv[..., 2]
    m = (((h <= 22) | (h >= 170)) & (s >= 60) & (v >= 55)).astype(np.uint8)
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
    return cv2.erode(m, np.ones((9, 9), np.uint8)).astype(bool)   # interior only, no rim


def analyse(tag, folder, every=16):
    fs = [f for f in sorted(Path(folder).iterdir())
          if f.suffix.lower() in (".jpg", ".png")][::every]
    bright, contrast, sharp = [], [], []
    for f in fs:
        bgr = cv2.imread(str(f), cv2.IMREAD_COLOR)
        if bgr is None:
            continue
        M = sherd_mask(bgr)
        if M.sum() < 2000:
            continue
        g = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY).astype(np.float32)
        bright.append(g[M].mean())

        # local contrast: standard deviation in a 9 px window, i.e. over ~2 mm of sherd
        mu = cv2.blur(g, (9, 9))
        sd = np.sqrt(np.maximum(cv2.blur(g * g, (9, 9)) - mu * mu, 0))
        contrast.append(sd[M].mean())

        lap = cv2.Laplacian(g, cv2.CV_32F, ksize=3)
        sharp.append(lap[M].var())

    if not bright:
        print(f"{tag}: nothing to measure"); return None
    print(f"\n{tag}  ({len(bright)} views)")
    print(f"  sherd brightness      {np.mean(bright):6.1f} / 255")
    print(f"  local contrast        {np.mean(contrast):6.2f} grey levels over a 2 mm window")
    print(f"  focus (edge energy)   {np.mean(sharp):6.1f}")
    return np.mean(bright), np.mean(contrast), np.mean(sharp)


if __name__ == "__main__":
    res = {}
    for arg in sys.argv[1:]:
        tag, folder = arg.split("=", 1)
        res[tag] = analyse(tag, folder)
    res = {k: v for k, v in res.items() if v}
    if len(res) >= 2:
        ks = list(res)
        b = res[ks[0]]
        print(f"\nrelative to {ks[0]}:")
        for k in ks:
            v = res[k]
            print(f"  {k:<8} brightness {v[0]/b[0]:5.2f}x   "
                  f"contrast {v[1]/b[1]:5.2f}x   focus {v[2]/b[2]:5.2f}x")
