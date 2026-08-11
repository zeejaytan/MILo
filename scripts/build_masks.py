"""Build background masks for a turntable capture, and render them to be looked at.

The rig is lit against a black backdrop, so separating them is a brightness problem
rather than a hand-tracing one. 177 photographs take a couple of minutes.

Two things about this that are easy to get wrong and silent when you do:

  ORIENTATION. COLMAP does not rotate images by their EXIF tag -- it reads the tag into a
  gravity prior and leaves the pixels as stored (doc/faq.rst, "Image orientation and
  EXIF"). These photographs carry orientation 8, so a mask built from an upright copy
  would be 90 degrees out. It would still load, still be the wrong shape, and simply mask
  the wrong region. Masks here are built from the STORED pixels, never exif_transposed.

  REFLECTIONS. The backdrop is glossy black and reflects the rig. Those reflections are
  bright, move when the rig turns, and would defeat the purpose if kept. They are dropped
  by a size floor, NOT by keeping only the largest region -- the sherds hang out on arms
  with dark background between them, so each sherd is its own region and "largest only"
  discards every one of them. That was the first version's behaviour: it masked out the
  pottery, kept the rig, removed 90% of the features, and reported nothing wrong.

Nothing here is trusted without a picture: --overlays writes a contact sheet with the mask
edge drawn on the photograph, at a resolution that shows whether sherd edges are cut. The
error above was invisible in every statistic and obvious in the first frame of the sheet.

Usage:
    python build_masks.py --images <dir> --out <mask-dir> --overlays <dir>
"""
import argparse
import sys
from pathlib import Path

import cv2
import numpy as np


def build_mask(bgr, threshold, min_area_frac, dilate_px, keep_largest=True):
    """Bright rig on a dark backdrop -> uint8 mask, 255 = keep, 0 = ignore."""
    grey = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    # Otsu picks the split from the image itself; a floor stops it inventing a split on a
    # frame that happens to be almost entirely backdrop.
    otsu, _ = cv2.threshold(grey, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    level = max(otsu, threshold)
    mask = (grey >= level).astype(np.uint8) * 255

    # Close first: the rig is thin metal with dark gaps, and without this the clamps
    # fragment into dozens of pieces and "keep the largest" throws most of them away.
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (31, 31))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, k)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN,
                            cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9)))

    # Keep EVERY region above a size floor, not just the largest.
    #
    # The first version kept only the largest, to drop the rig's reflections in the glossy
    # backdrop. Looking at the contact sheet showed what that actually did: the sherds hang
    # out on arms and are separated from the central rod by dark background, so each one is
    # its own region and all of them were discarded. It masked out the pottery and kept the
    # rig -- the exact opposite of the intent -- and removed 90% of the features while
    # reporting nothing wrong. A size floor drops reflections, which are small and dim,
    # without dropping sherds, which are neither.
    n, labels, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
    if n > 1:
        areas = stats[1:, cv2.CC_STAT_AREA]
        if keep_largest:
            keep = {1 + int(np.argmax(areas))}
        else:
            keep = {1 + i for i, a in enumerate(areas)
                    if a >= min_area_frac * mask.size}
            if not keep:                      # never return an empty mask
                keep = {1 + int(np.argmax(areas))}
        mask = np.isin(labels, list(keep)).astype(np.uint8) * 255

    # Fill interior holes so dark patches inside a sherd are not excluded.
    ff = mask.copy()
    cv2.floodFill(ff, np.zeros((mask.shape[0] + 2, mask.shape[1] + 2), np.uint8), (0, 0), 255)
    mask = mask | cv2.bitwise_not(ff)

    # Grow slightly: a feature ON the silhouette is real and useful, and a mask cut exactly
    # at the edge would discard it.
    if dilate_px > 0:
        mask = cv2.dilate(mask, cv2.getStructuringElement(
            cv2.MORPH_ELLIPSE, (2 * dilate_px + 1, 2 * dilate_px + 1)))
    return mask


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--images", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--overlays", type=Path, help="write contact sheets to look at")
    ap.add_argument("--threshold", type=int, default=28,
                    help="minimum grey level counted as foreground")
    ap.add_argument("--min-area-frac", type=float, default=0.0004,
                    help="size floor for a kept region, as a fraction of the frame: low "
                         "enough to keep a small sherd, high enough to drop a reflection")
    ap.add_argument("--dilate", type=int, default=12,
                    help="pixels to grow the mask, to keep silhouette features")
    ap.add_argument("--largest-only", action="store_true",
                    help="keep ONLY the largest region. Wrong for this rig -- the sherds "
                         "hang on arms separated from the rod by dark background, so each "
                         "is its own region and this discards all of them.")
    ap.add_argument("--overlay-every", type=int, default=22)
    args = ap.parse_args()

    images = sorted([p for p in args.images.iterdir()
                     if p.suffix.lower() in (".jpg", ".jpeg", ".png")])
    if not images:
        sys.exit(f"No photographs in {args.images}")
    args.out.mkdir(parents=True, exist_ok=True)
    if args.overlays:
        args.overlays.mkdir(parents=True, exist_ok=True)

    print(f"{len(images)} photographs from {args.images}")
    fracs, tiles = [], []
    for i, p in enumerate(images):
        # cv2.imread ignores EXIF orientation, which is what COLMAP does too. Do not
        # "fix" this: the mask must match the pixels COLMAP reads.
        bgr = cv2.imread(str(p), cv2.IMREAD_COLOR)
        if bgr is None:
            sys.exit(f"Could not read {p}")
        mask = build_mask(bgr, args.threshold, args.min_area_frac, args.dilate,
                          keep_largest=args.largest_only)
        # COLMAP wants <image filename>.png, keeping the original extension.
        cv2.imwrite(str(args.out / (p.name + ".png")), mask)
        frac = float((mask > 0).mean())
        fracs.append(frac)

        if args.overlays and i % args.overlay_every == 0:
            small = cv2.resize(bgr, (0, 0), fx=0.22, fy=0.22)
            m = cv2.resize(mask, (small.shape[1], small.shape[0]),
                           interpolation=cv2.INTER_NEAREST)
            edges = cv2.dilate(cv2.Canny(m, 50, 150), np.ones((3, 3), np.uint8))
            small[edges > 0] = (0, 0, 255)
            dark = small.copy(); dark[m == 0] = (dark[m == 0] * 0.25).astype(np.uint8)
            tiles.append(np.hstack([small, dark]))
        if (i + 1) % 25 == 0:
            print(f"  {i + 1}/{len(images)}", flush=True)

    fr = np.array(fracs)
    print(f"\nfraction of each photograph kept: "
          f"min {fr.min():.3f}  median {np.median(fr):.3f}  max {fr.max():.3f}")
    print(f"  so roughly {100 * (1 - np.median(fr)):.0f}% of each frame is excluded")
    odd = [(images[i].name, f) for i, f in enumerate(fracs)
           if f < 0.02 or f > 0.85]
    if odd:
        print(f"\n  {len(odd)} frame(s) look wrong -- LOOK AT THESE:")
        for n, f in odd[:10]:
            print(f"    {n}: {f:.3f} kept")

    if args.overlays and tiles:
        w = max(t.shape[1] for t in tiles)
        tiles = [cv2.copyMakeBorder(t, 0, 0, 0, w - t.shape[1], cv2.BORDER_CONSTANT)
                 for t in tiles]
        sheet = np.vstack(tiles)
        cv2.imwrite(str(args.overlays / "contact_sheet.png"), sheet)
        print(f"\nwrote {args.overlays / 'contact_sheet.png'} "
              f"({len(tiles)} frames, mask edge in red, excluded area darkened)")
        print("LOOK AT IT before running structure-from-motion on these masks.")


if __name__ == "__main__":
    main()
