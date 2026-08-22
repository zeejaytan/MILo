"""How much sherd did each capture actually photograph, and what is touching its edges?

A02 has no sherd masks, so both captures are segmented the same way instead: terracotta is
the only strongly reddish thing in the frame. The rig is grey metal, blue knobs and black
rubber; the backdrop is black. One rule, applied identically, so the two are comparable.

Two numbers per capture:

  1. Sherd area per view, and the size of a typical single sherd. This is how much evidence
     the reconstruction had to work with, and no amount of training invents more of it.

  2. What sits immediately outside each sherd's outline: clean backdrop, or rig. A sherd
     edge against black backdrop is the easiest thing in the scene to reconstruct. A sherd
     edge against a clamp jaw touching it is the hardest -- the two surfaces meet with no
     gap, so nothing in any view separates them.
"""
import sys
from pathlib import Path

import numpy as np
import cv2

PX_PER_MM = 5.0


def sherd_mask(bgr):
    """Terracotta: reddish hue, real saturation, not in shadow."""
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    h, s, v = hsv[..., 0], hsv[..., 1], hsv[..., 2]
    m = (((h <= 22) | (h >= 170)) & (s >= 60) & (v >= 55))
    m = cv2.morphologyEx(m.astype(np.uint8), cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((15, 15), np.uint8))
    return m.astype(bool)


def analyse(tag, folder, every=16):
    fs = sorted(Path(folder).iterdir())
    fs = [f for f in fs if f.suffix.lower() in (".jpg", ".png")][::every]
    areas, sizes, touch, npieces = [], [], [], []
    for f in fs:
        bgr = cv2.imread(str(f), cv2.IMREAD_COLOR)
        if bgr is None:
            continue
        M = sherd_mask(bgr)
        if M.sum() < 500:
            continue
        areas.append(M.mean())

        n, lab, stats, _ = cv2.connectedComponentsWithStats(M.astype(np.uint8), 8)
        big = [stats[i, cv2.CC_STAT_AREA] for i in range(1, n)
               if stats[i, cv2.CC_STAT_AREA] >= 1500]
        sizes += big
        npieces.append(len(big))

        # A ring just outside every sherd. Is it black backdrop, or is it rig?
        ring = cv2.dilate(M.astype(np.uint8), np.ones((9, 9), np.uint8)).astype(bool) & ~M
        if ring.sum():
            v = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)[..., 2][ring]
            touch.append((v > 70).mean())      # brighter than backdrop => rig, not black cloth

    if not areas:
        print(f"{tag}: nothing segmented"); return
    med_px = np.median(sizes) if sizes else 0
    print(f"\n{tag}  ({len(areas)} views sampled)")
    print(f"  sherd covers {100*np.mean(areas):.2f}% of the frame")
    print(f"  {np.median(npieces):.0f} sherds visible per view")
    print(f"  a typical single sherd is {med_px/1e3:.0f}k pixels "
          f"= {med_px/PX_PER_MM**2/100:.1f} cm2 of surface facing the camera")
    print(f"  equivalent square: {np.sqrt(med_px)/PX_PER_MM:.0f} mm across, "
          f"{np.sqrt(med_px):.0f} px across")
    print(f"  {100*np.mean(touch):.0f}% of the sherd outline is up against the rig "
          "rather than clean backdrop")
    return med_px, np.mean(touch)


if __name__ == "__main__":
    out = {}
    for arg in sys.argv[1:]:
        tag, folder = arg.split("=", 1)
        out[tag] = analyse(tag, folder)
    if len(out) >= 2 and all(out.values()):
        ks = list(out)
        a, b = out[ks[0]], out[ks[1]]
        print(f"\n{ks[0]} sherds are {a[0]/b[0]:.1f}x the pixel area of {ks[1]} sherds")
