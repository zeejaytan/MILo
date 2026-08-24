#!/usr/bin/env python
"""Turn COLMAP's undistorted mask output into genuine binary PNGs, under both names.

WHY THIS STEP EXISTS. `colmap image_undistorter` writes each output image under the name
the model holds for it, and every name in these captures ends `.JPG` -- so the undistorted
masks come out JPEG-compressed, three channels, even though the pipeline then copies them
to a `.png` filename. A binary silhouette put through JPEG picks up ringing along every
edge, and a sherd mask is nearly all edge: it keeps about 2.7% of the frame across ten
small pieces. `--jpeg_quality` is the only image-format lever the pinned build (COLMAP
4.1.1) offers here; there is no PNG output option, so the fix belongs after the fact.

The carve threshold at >127 already tolerates the ringing, but OpenMVS's mask reader and
anything else downstream should not have to, and nothing should have to guess what a grey
pixel in a binary mask means. This writes single-channel 0/255 PNGs that are what the file
extension has been claiming all along.

It also REPORTS how much of the frame the compression left ambiguous. That number is the
size of the problem being cleaned up; if it is ever large, the mask boundary itself is in
question and the run should stop rather than quietly threshold its way past it.

Usage:
    binarize_masks.py --src <undistorter output dir> --colmap <dir> --openmvs <dir>
"""
import argparse
import sys
from pathlib import Path

import numpy as np
from PIL import Image

# A pixel this far from black or white was invented by the compressor, not drawn by the
# segmenter. The band is deliberately wide: near-edge ringing overshoots well past mid-grey.
AMBIG_LO, AMBIG_HI = 32, 223
# Above this fraction of the frame the boundary is no longer a boundary, it is a gradient.
AMBIG_LIMIT = 0.02


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--src", required=True, type=Path,
                    help="image_undistorter's output images/ directory")
    ap.add_argument("--colmap", required=True, type=Path,
                    help="write <image>.JPG.png here (COLMAP naming, extension KEPT)")
    ap.add_argument("--openmvs", required=True, type=Path,
                    help="write <image>.mask.png here (OpenMVS naming, extension STRIPPED)")
    args = ap.parse_args()

    files = sorted(p for p in args.src.iterdir() if p.is_file())
    if not files:
        print(f"Nothing to binarize in {args.src}", file=sys.stderr)
        return 1

    args.colmap.mkdir(parents=True, exist_ok=True)
    args.openmvs.mkdir(parents=True, exist_ok=True)

    ambig, kept = [], []
    for p in files:
        a = np.asarray(Image.open(p).convert("L"))
        ambig.append(float(((a >= AMBIG_LO) & (a <= AMBIG_HI)).mean()))
        b = (a > 127).astype(np.uint8) * 255
        kept.append(float((b > 0).mean()))
        im = Image.fromarray(b, mode="L")
        im.save(args.colmap / f"{p.name}.png")
        im.save(args.openmvs / f"{p.stem}.mask.png")

    amean, amax = float(np.mean(ambig)), float(np.max(ambig))
    print(f"  binarized {len(files)} masks to 0/255 single-channel PNG")
    print(f"  masks keep {100*np.mean(kept):.1f}% of the frame "
          f"({100*np.min(kept):.1f}-{100*np.max(kept):.1f}%)")
    print(f"  compression left {100*amean:.2f}% of the frame between {AMBIG_LO} and "
          f"{AMBIG_HI} on average, {100*amax:.2f}% at worst -- that is the edge ringing "
          f"this step removed")
    if amax > AMBIG_LIMIT:
        print(f"\n-> PROBLEM\n   {100*amax:.1f}% of a frame is neither in nor out. A "
              f"binary mask should have only a thin ring of that.\n   Either the source "
              f"masks are not binary, or the undistorter is resampling them\n   far more "
              f"heavily than expected. Thresholding past this would invent a boundary.",
              file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
