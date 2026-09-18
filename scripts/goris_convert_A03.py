"""Convert A03_sherds to the GOR-IS dataset layout (CPU-only, login node safe).

Reads (Spartan working area, untracked):
  $MILO_ROOT/data/17062025/A03_sherds/
    images/            164 RGB JPGs, 3200x2133 (undistorted PINHOLE views)
    images_masked/     164 sherd-only RGBA (erode0, .JPG names holding PNG bytes)
    sparse/0           COLMAP model (cameras.bin, images.bin, points3D.bin)
    capture.json       held_out_views (llffhold=8 -> 21 views)
  $MILO_ROOT/data/17062025/A03/images_masked/
    164 foreground (sherd+rig) RGBA — same views, same 3200x2133

Writes $MILO_ROOT/data/goris_A03/:
  images/          symlinks to the RGB views (GOR-IS trains on plain RGB;
                   alpha-masked training stays retired per M5)
  sparse/0         copy of the COLMAP model (read-only reuse, never edited)
  object_mask/     <name>.png, 255 = rig steel to remove.
                   rig = foreground_old AND NOT sherd_erode0, both alphas >127.
                   Refuses on any size mismatch (the colmap_to_milo.py lesson:
                   resampling a misaligned mask hides the misalignment).
  specular_mask/   not written in v1 (loader tolerates absence -> zeros)
  normal/          not written in v1 (loader tolerates absence -> None)
  train_list.txt / test_list.txt / val_list.txt
                   test = capture.json held_out_views (21), train = rest (143).
                   Names carry the .JPG extension; the reader strips at ".".

Also writes mask panels beside the output for the eye check
(photo | rig mask | sherd kept) and prints steel-vs-clay cm2 per view
at 0.21 mm/px (A03 depth sampling, traps.md).

Usage:
  python scripts/goris_convert_A03.py [--dry-run]
"""

import argparse
import json
import os
import shutil
import sys

import numpy as np
from PIL import Image

MM_PER_PX = 0.21  # A03 sampling at the object (traps.md); +-20% approx


def parse_args():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--milo-root", default="/data/gpfs/projects/punim2657/MILo")
    p.add_argument("--dst-name", default="goris_A03")
    p.add_argument("--dry-run", action="store_true",
                   help="measure and report only; write nothing")
    return p.parse_args()


def main():
    args = parse_args()
    src = os.path.join(args.milo_root, "data", "17062025", "A03_sherds")
    fg_dir = os.path.join(args.milo_root, "data", "17062025", "A03", "images_masked")
    dst = os.path.join(args.milo_root, "data", args.dst_name)

    for d in (os.path.join(src, "images"),
              os.path.join(src, "images_masked"), fg_dir,
              os.path.join(src, "sparse", "0")):
        if not os.path.isdir(d):
            print(f"[ERROR] missing input dir {d}", file=sys.stderr)
            return 2
    with open(os.path.join(src, "capture.json")) as f:
        cap = json.load(f)
    held = set(cap.get("held_out_views", []))
    if len(held) != 21:
        print(f"[WARN] held_out_views has {len(held)} entries, expected 21 — "
              f"continuing with what capture.json says")

    views = sorted(f for f in os.listdir(os.path.join(src, "images"))
                   if f.lower().endswith(".jpg"))
    if len(views) != 164:
        print(f"[ERROR] {len(views)} views, expected 164", file=sys.stderr)
        return 2

    rig_px, sherd_px = [], []
    mismatched = []
    for v in views:
        fg = np.array(Image.open(os.path.join(fg_dir, v))).astype(np.int16)
        sh = np.array(Image.open(os.path.join(src, "images_masked", v))).astype(np.int16)
        ph = np.array(Image.open(os.path.join(src, "images", v)))
        if fg.shape[:2] != sh.shape[:2] or ph.shape[:2] != sh.shape[:2]:
            mismatched.append(v)
            continue
        if fg.shape[2] < 4 or sh.shape[2] < 4:
            print(f"[ERROR] {v} has no alpha band", file=sys.stderr)
            return 2
        fg_keep = fg[..., 3] > 127
        sh_keep = sh[..., 3] > 127
        rig = fg_keep & ~sh_keep
        rig_px.append(int(rig.sum()))
        sherd_px.append(int(sh_keep.sum()))

    if mismatched:
        print(f"[ERROR] size mismatch on {len(mismatched)} views "
              f"(e.g. {mismatched[:3]}) — refusing, see colmap_to_milo gate",
              file=sys.stderr)
        return 2

    rig = float(np.mean(rig_px))
    sherd = float(np.mean(sherd_px))
    total = 3200 * 2133
    cm2 = MM_PER_PX ** 2 / 100.0
    print(f"{len(views)} views")
    print(f"sherd kept     {sherd:>12,.0f} px = {100.0 * sherd / total:5.2f}% of frame "
          f"= {sherd * cm2:,.0f} cm2/view")
    print(f"rig to remove  {rig:>12,.0f} px = {100.0 * rig / total:5.2f}% of frame "
          f"= {rig * cm2:,.0f} cm2/view")
    print(f"held-out views: {len(held)} test / {len(views) - len(held & set(views))} train")

    if args.dry_run:
        return 0

    os.makedirs(os.path.join(dst, "images"), exist_ok=True)
    os.makedirs(os.path.join(dst, "object_mask"), exist_ok=True)
    for v in views:
        link = os.path.join(dst, "images", v)
        if not os.path.exists(link):
            os.symlink(os.path.join(src, "images", v), link)
    sparse_dst = os.path.join(dst, "sparse", "0")
    if not os.path.isdir(sparse_dst):
        os.makedirs(os.path.join(dst, "sparse"), exist_ok=True)
        shutil.copytree(os.path.join(src, "sparse", "0"), sparse_dst)
    for v in views:
        fg = np.array(Image.open(os.path.join(fg_dir, v)))
        sh = np.array(Image.open(os.path.join(src, "images_masked", v)))
        rig = ((fg[..., 3] > 127) & ~(sh[..., 3] > 127)).astype(np.uint8) * 255
        Image.fromarray(rig).save(os.path.join(dst, "object_mask",
                                               os.path.splitext(v)[0] + ".png"))
    train = [v for v in views if v not in held]
    test = [v for v in views if v in held]
    for name, seq in (("train_list.txt", train), ("test_list.txt", test),
                      ("val_list.txt", test)):
        with open(os.path.join(dst, name), "w") as f:
            f.write("\n".join(seq) + "\n")

    panels = os.path.join(dst, "mask_panels")
    os.makedirs(panels, exist_ok=True)
    for v in views[::41][:4]:
        ph = np.array(Image.open(os.path.join(src, "images", v)).convert("RGB"))
        rig = np.array(Image.open(
            os.path.join(dst, "object_mask", os.path.splitext(v)[0] + ".png"))) > 127
        sh = np.array(Image.open(os.path.join(src, "images_masked", v)))[..., 3] > 127
        panel = np.concatenate(
            [ph,
             np.where(rig[..., None], ph, 0).astype(np.uint8),
             np.where(sh[..., None], ph, 0).astype(np.uint8)], axis=1)
        out = Image.fromarray(panel)
        out = out.resize((out.width // 4, out.height // 4), Image.LANCZOS)
        out.save(os.path.join(panels, os.path.splitext(v)[0] + "_rig.jpg"), quality=88)
    print(f"wrote {dst} (photo | rig mask | sherd kept panels in mask_panels/)")
    print("LOOK AT THE PANELS before training: a warm-lit rig misreads, "
          "and these masks decide what the label field learns.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
