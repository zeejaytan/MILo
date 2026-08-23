"""Build background masks for a turntable capture, and render them to be looked at.

The rig is lit against a black backdrop, so separating them is a brightness problem
rather than a hand-tracing one. 177 photographs take a couple of minutes.

Two things about this that are easy to get wrong and silent when you do:

  LIGHTING. Two backdrops were used in this capture: black for most frames and a lit grey
  one for the 44 A14_* frames, shot from a lower angle. A brightness threshold cannot
  serve both -- on the grey frames 94% of the image is above any workable level, so the
  whole frame is kept and the mask silently does nothing. Local texture serves both,
  because the backdrop is smooth either way and the rig never is.

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


def build_mask(bgr, threshold, min_area_frac, dilate_px, keep_largest=True, win=9):
    """Textured rig against a smooth backdrop -> uint8 mask, 255 = keep, 0 = ignore.

    Keyed on local texture, not brightness. Brightness worked for the frames shot against
    the black backdrop and failed completely for the 44 A14_* frames, which were taken
    against a LIT GREY backdrop from a lower angle: 94% of that frame is brighter than any
    workable threshold, so the whole image was kept and the mask did nothing.

    Texture separates both setups with one rule. The backdrop is smooth whether it is flat
    black or a soft grey gradient, while sherds, clamps and rod all carry detail.
    """
    grey = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY).astype(np.float32)
    # Local standard deviation: sqrt(E[x^2] - E[x]^2) over a small window.
    mean = cv2.boxFilter(grey, -1, (win, win))
    sq = cv2.boxFilter(grey * grey, -1, (win, win))
    std = np.sqrt(np.maximum(sq - mean * mean, 0))
    mask = (std >= threshold).astype(np.uint8) * 255

    # Close first: the rig is thin metal with dark gaps, and without this the clamps
    # fragment into dozens of pieces and "keep the largest" throws most of them away.
    # Deliberately generous. The job of this mask is to drop the bulk of the STATIC
    # backdrop, not to trace a sherd outline. Including some backdrop costs a few useless
    # features; clipping a sherd removes the evidence we actually depend on, and the
    # conservator found exactly that in the previous version. So: close hard enough to
    # bridge the dark gaps between a sherd and its clamp, open only enough to drop
    # single-pixel speckle, and grow the result well past the silhouette.
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (61, 61))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, k)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN,
                            cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5)))

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


def coverage_report(mask, bgr):
    """How much of the frame survives -- printed per frame so a failure is visible."""
    return float((mask > 0).mean())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--images", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--overlays", type=Path, help="write contact sheets to look at")
    ap.add_argument("--threshold", type=float, default=2.5,
                    help="minimum local standard deviation counted as detail. Not a "
                         "brightness: the backdrop is smooth in both lighting setups "
                         "used in this capture, while the rig and sherds are not.")
    ap.add_argument("--window", type=int, default=9,
                    help="window size for the local texture measure, in pixels")
    ap.add_argument("--min-area-frac", type=float, default=0.00008,
                    help="size floor for a kept region, as a fraction of the frame: low "
                         "enough to keep a small sherd, high enough to drop a reflection")
    ap.add_argument("--dilate", type=int, default=45,
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
        # The mask must match the pixels COLMAP reads, which are the STORED pixels --
        # COLMAP reads the EXIF orientation tag into a gravity prior and does not rotate
        # (doc/faq.rst). This line used to say cv2.imread ignores EXIF orientation. It
        # does not, and the comment saying so was written from memory rather than
        # measured: on the OpenCV in envs/milo (5.0.0), plain IMREAD_COLOR on an N01
        # frame returns 3712x5568 where the stored frame is 5568x3712 -- a mask rotated
        # a quarter turn, which would still load and would simply mask the wrong region.
        # IMREAD_IGNORE_ORIENTATION is what makes the promise above true.
        bgr = cv2.imread(str(p), cv2.IMREAD_COLOR | cv2.IMREAD_IGNORE_ORIENTATION)
        if bgr is None:
            sys.exit(f"Could not read {p}")
        mask = build_mask(bgr, args.threshold, args.min_area_frac, args.dilate,
                          keep_largest=args.largest_only, win=args.window)
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
