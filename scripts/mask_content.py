"""What is actually inside the masks -- sherd, or mounting rig?

A mask that keeps the clamp stand looks like a working mask: the backdrop is gone, the
outlines are tight, the overlays look right. It is still wrong for our purpose, and the
cost is not cosmetic. On A03 the masks keep 24% of every frame, of which only ~9% is
fired clay; the rest is a stand made of thin chromed rods. Thin specular metal has a huge
surface area for its volume and its rendered depth moves with the viewpoint, so TSDF
fusion stores a separate shell per view instead of one reinforced surface. That is what
took the A03 voxel grid from the author's 50,000 blocks to 290,640, and what puts a finer
voxel out of reach (job 29694649).

So: measure the composition of a mask before spending a GPU on it.

The separator is the redness already validated on these captures --
    redness = R - (G + B) / 2
with carved A03 sherds running +7..+27 and the steel-and-blue rig around -5. It is a
coarse instrument and it is only used here to answer a coarse question ("is most of this
pot, or most of this stand?"). It will misread a strongly warm-lit rig, which is why this
also writes a picture: look at that before believing the percentage.

Usage:
    python scripts/mask_content.py --images DIR [--every 20] [--redness 7]
                                   [--out DIR] [--min-sherd-frac 0.5]
"""
import argparse
import glob
import os
import sys

import numpy as np
from PIL import Image


def parse_args():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--images", required=True,
                   help="directory of RGBA images whose alpha is the mask")
    p.add_argument("--every", type=int, default=20,
                   help="sample every Nth image (default 20)")
    p.add_argument("--redness", type=float, default=7.0,
                   help="R-(G+B)/2 above which a kept pixel counts as sherd (default 7)")
    p.add_argument("--mm-per-px", type=float, default=None,
                   help="object-plane sampling, to report areas in cm^2 as well as pixels")
    p.add_argument("--out", default=None,
                   help="directory to write look-at-it images into")
    p.add_argument("--min-sherd-frac", type=float, default=None,
                   help="exit non-zero if sherd is below this fraction of the kept pixels")
    return p.parse_args()


def main():
    args = parse_args()
    files = sorted(glob.glob(os.path.join(args.images, "*.*")))
    files = [f for f in files if not f.endswith(".txt")]
    if not files:
        print(f"[ERROR] no images in {args.images}", file=sys.stderr)
        return 2
    sample = files[:: max(args.every, 1)]
    print(f"{len(files)} images, sampling {len(sample)}")

    if args.out:
        os.makedirs(args.out, exist_ok=True)

    kept_px, sherd_px, total_px = [], [], []
    for i, f in enumerate(sample):
        im = Image.open(f)
        a = np.array(im).astype(np.int16)
        if a.ndim != 3 or a.shape[2] < 4:
            print(f"[ERROR] {os.path.basename(f)} has no alpha channel (mode {im.mode}). "
                  f"These are supposed to be RGBA; nothing here is masked.",
                  file=sys.stderr)
            return 2
        rgb, alpha = a[..., :3], a[..., 3]
        keep = alpha > 127
        red = rgb[..., 0] - (rgb[..., 1] + rgb[..., 2]) / 2.0
        sherd = keep & (red > args.redness)
        kept_px.append(int(keep.sum()))
        sherd_px.append(int(sherd.sum()))
        total_px.append(int(keep.size))
        print(f"  {os.path.basename(f):<24} kept {keep.sum():>9,} "
              f"({100.0 * keep.mean():5.1f}% of frame)  sherd {sherd.sum():>9,} "
              f"({100.0 * sherd.sum() / max(keep.sum(), 1):5.1f}% of kept)")

        # Look at it: photograph | what the mask keeps | what reads as sherd.
        if args.out and i < 3:
            u8 = rgb.astype(np.uint8)
            panel = np.concatenate(
                [u8,
                 np.where(keep[..., None], u8, 0).astype(np.uint8),
                 np.where(sherd[..., None], u8, 0).astype(np.uint8)], axis=1)
            out = Image.fromarray(panel)
            out = out.resize((out.width // 4, out.height // 4), Image.LANCZOS)
            path = os.path.join(args.out,
                                os.path.splitext(os.path.basename(f))[0] + "_content.jpg")
            out.save(path, quality=88)
            print(f"    wrote {path}  (photo | kept by mask | reads as sherd)")

    kept = float(np.mean(kept_px))
    sherd = float(np.mean(sherd_px))
    frac = sherd / max(kept, 1.0)
    print()
    print(f"mask keeps      {kept:>12,.0f} px = {100.0 * kept / np.mean(total_px):.1f}% of frame")
    print(f"reads as sherd  {sherd:>12,.0f} px = {100.0 * frac:.1f}% of what the mask keeps")
    print(f"everything else {kept - sherd:>12,.0f} px = {100.0 * (1 - frac):.1f}% -- "
          f"rig, stand, board, backdrop")
    if args.mm_per_px:
        cm2 = args.mm_per_px ** 2 / 100.0
        print()
        print(f"per view: {kept * cm2:,.0f} cm^2 kept, of which "
              f"{sherd * cm2:,.0f} cm^2 sherd and {(kept - sherd) * cm2:,.0f} cm^2 not")

    print()
    print("LOOK AT THE PANELS before believing the split. A warm-lit rig reads as clay to")
    print("this test, and a shadowed sherd reads as rig.")

    if args.min_sherd_frac is not None and frac < args.min_sherd_frac:
        print(f"\n[ERROR] sherd is {100.0 * frac:.1f}% of the mask, below the "
              f"{100.0 * args.min_sherd_frac:.0f}% asked for. Fusing this spends the voxel "
              f"grid on the mounting hardware.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
