"""Are the masks actually being applied? Ask the question two different ways.

COLMAP does not report an unmatched mask. A mask under the wrong filename, a mask of the
wrong size, a mask that is entirely white -- each produces an ordinary, successful,
completely unmasked run. That is how a "masked" reconstruction of tree A02 came back after
1h37m with no masks applied at all, reporting COMPLETED throughout.

So this asks twice, and the two questions are not the same question:

  BEFORE extraction -- the precondition.  One mask per photograph, under the name COLMAP
      matches, at the same pixel dimensions. Cheap, and it fails in seconds rather than
      after an hour. But it only catches the ways of failing that we thought of.

  AFTER extraction -- the effect.  Take the keypoints COLMAP actually stored and count how
      many of them sit in the region the mask paints black. If the masks were applied that
      figure is essentially zero; if they were ignored for ANY reason -- a reason nobody
      anticipated included -- the keypoints are spread over the backdrop and it is large.
      This needs no baseline, no comparison run and no knowledge of the cause.

The second is the one that earns its keep. Prefer it wherever a database exists.

Usage:
    python check_masks.py --images <dir> --masks <dir>                 # precondition only
    python check_masks.py --images <dir> --masks <dir> --database <db> # and the effect

Exit status is 0 when everything checked passed and 1 when it did not, so a caller can
gate on it directly:  python check_masks.py ... || exit 1
"""
import argparse
import sqlite3
import struct
import sys
from pathlib import Path

import numpy as np

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".tif", ".tiff"}

# Keypoints landing in the black region. Set from the pair of A02 databases, which are the
# same 162 photographs extracted with and without the same masks: masked read 0.00%,
# unmasked 5.81% (worst frame 9.13%). 1% therefore sits ~200x above a correct run and well
# under an incorrect one. Boundary slop from extracting on a downscaled copy was the worry
# and measured as nothing at all.
MASKED_KEYPOINT_FRACTION_MAX = 0.01
# A mask keeping less than this much of the frame is not isolating an object, it is
# deleting one. The first hand-built attempt here kept 10% and cut 90% of the features.
KEPT_AREA_MIN = 0.02


def png_size(path):
    """Width and height from the IHDR chunk, without decoding the image."""
    with open(path, "rb") as fh:
        head = fh.read(24)
    if head[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    return struct.unpack(">II", head[16:24])


def jpeg_size(path):
    """Width and height from the SOF marker -- the STORED dimensions.

    Deliberately not the EXIF-rotated ones. COLMAP reads stored pixels and ignores the
    orientation tag, so stored-versus-stored is the comparison that matches what COLMAP
    will do. A mask built from an EXIF-upright copy is 90 degrees out and this is what
    catches it: on a portrait-tagged landscape frame the two sizes come out transposed.
    """
    with open(path, "rb") as fh:
        if fh.read(2) != b"\xff\xd8":
            return None
        while True:
            b = fh.read(1)
            if not b:
                return None
            if b != b"\xff":
                continue
            while b == b"\xff":
                b = fh.read(1)
                if not b:
                    return None
            m = b[0]
            if m == 0x01 or 0xD0 <= m <= 0xD9:
                continue
            raw = fh.read(2)
            if len(raw) < 2:
                return None
            (length,) = struct.unpack(">H", raw)
            if 0xC0 <= m <= 0xCF and m not in (0xC4, 0xC8, 0xCC):
                data = fh.read(5)
                h, w = struct.unpack(">HH", data[1:5])
                return w, h
            fh.seek(length - 2, 1)


def image_size(path):
    """Stored pixel dimensions, whatever the file actually turns out to be.

    Sniff the header first, both ways, because the extension cannot be trusted here:
    COLMAP's image_undistorter writes its output in the format the FILENAME implies, so an
    undistorted mask can arrive as JPEG content under a .png name. Falling through to
    Pillow rather than giving up keeps the size check from quietly doing nothing on
    exactly the files it was added to check.
    """
    for probe in (png_size, jpeg_size):
        try:
            size = probe(path)
        except (OSError, struct.error):
            size = None
        if size:
            return size
    try:
        from PIL import Image
        with Image.open(path) as im:
            return im.size
    except Exception:
        return None


def load_mask(path):
    """Boolean array, True where features are KEPT. None if no image library is present."""
    try:
        from PIL import Image
    except ImportError:
        return None
    with Image.open(path) as im:
        return np.array(im.convert("L")) > 127


def list_images(images_dir):
    return sorted(p for p in Path(images_dir).iterdir()
                  if p.is_file() and p.suffix.lower() in IMAGE_SUFFIXES)


def check_naming(images, masks_dir, sample):
    """Every photograph has a mask, correctly named, at the same size."""
    masks_dir = Path(masks_dir)
    problems = []

    present = sorted(masks_dir.glob("*.png"))
    print(f"  {len(present)} masks in {masks_dir} for {len(images)} photographs")
    if not present:
        problems.append("There are no masks in that directory at all.")
        return problems

    # COLMAP matches "<image filename>.png" -- the ORIGINAL EXTENSION KEPT, so
    # A21_0891.JPG becomes A21_0891.JPG.png. The stem-only form A21_0891.png is the one
    # this project used to write, and COLMAP finds none of it while saying nothing.
    missing, legacy = [], []
    for img in images:
        if (masks_dir / (img.name + ".png")).exists():
            continue
        if (masks_dir / (img.stem + ".png")).exists():
            legacy.append(img.name)
        else:
            missing.append(img.name)

    if legacy:
        problems.append(
            f"{len(legacy)} masks use the old '<stem>.png' name (e.g. {Path(legacy[0]).stem}.png). "
            f"COLMAP matches '<image filename>.png' with the extension kept "
            f"({legacy[0]}.png) and silently ignores anything else -- these masks would "
            f"do nothing while the run reported success.")
    if missing:
        problems.append(
            f"{len(missing)} photographs have no mask under either name, first "
            f"{missing[0]}. A partly masked run is not a comparison of anything.")
    if not legacy and not missing:
        print(f"  naming OK: every photograph has <name>.png, COLMAP's convention")

    # Dimensions, on a sample -- header reads only, so this costs nothing, but one wrong
    # size almost always means all of them are wrong the same way.
    bad, checked, unreadable = [], 0, []
    for img in sample:
        mask = masks_dir / (img.name + ".png")
        if not mask.exists():
            continue
        si, sm = image_size(img), image_size(mask)
        if not (si and sm):
            unreadable.append(img.name if not si else mask.name)
            continue
        checked += 1
        if si != sm:
            bad.append(f"{img.name} is {si[0]}x{si[1]} but its mask is {sm[0]}x{sm[1]}")
    if unreadable:
        problems.append(f"{len(unreadable)} files could not be read as images at all "
                        f"(first {unreadable[0]}) -- their size could not be compared.")
    if bad:
        detail = "; ".join(bad[:3])
        hint = ""
        if any("x" in b for b in bad) and len(sample):
            si, sm = image_size(sample[0]), image_size(masks_dir / (sample[0].name + ".png"))
            if si and sm and si == sm[::-1]:
                hint = (" The two are transposed, which means the masks were built from "
                        "EXIF-upright copies. COLMAP reads the stored pixels, so the mask "
                        "would be rotated 90 degrees against the photograph.")
        problems.append(f"Mask and photograph differ in size: {detail}.{hint}")
    elif checked:
        print(f"  dimensions OK on {checked} sampled frames")

    return problems


def check_content(images, masks_dir, sample):
    """A mask that keeps everything, or almost nothing, is not doing the job asked of it."""
    masks_dir = Path(masks_dir)
    kept = []
    for img in sample:
        path = masks_dir / (img.name + ".png")
        if not path.exists():
            continue        # already reported by the naming check; do not crash on top of it
        m = load_mask(path)
        if m is None:
            print("  (no PIL in this environment -- skipping the mask-content check)")
            return []
        kept.append(float(m.mean()))
    if not kept:
        return []

    kept = np.array(kept)
    print(f"  masks keep {100*kept.mean():.1f}% of the frame on average "
          f"({100*kept.min():.1f}-{100*kept.max():.1f}%)")
    problems = []
    if kept.max() > 0.999:
        problems.append("At least one mask is entirely white -- it removes nothing, which "
                        "is indistinguishable from not masking at all.")
    if kept.min() < KEPT_AREA_MIN:
        problems.append(f"At least one mask keeps only {100*kept.min():.1f}% of the frame. "
                        "That is not isolating the object, it is deleting it -- look at "
                        "the mask before running a reconstruction on it.")
    return problems


def check_effect(database, images, masks_dir, sample):
    """The question that does not depend on guessing the failure mode.

    Where did COLMAP actually put its keypoints? If any meaningful number of them sit in
    the region the mask paints black, the mask was not applied -- and it does not matter
    whether the cause was the name, the size, the orientation or something nobody has
    thought of yet.
    """
    masks_dir = Path(masks_dir)
    db = sqlite3.connect(str(database))
    ids = {name: (iid,) for iid, name in db.execute("SELECT image_id, name FROM images")}

    rows, fracs = [], []
    for img in sample:
        rec = ids.get(img.name)
        mask = masks_dir / (img.name + ".png")
        if rec is None or not mask.exists():
            continue
        r = db.execute("SELECT rows, cols, data FROM keypoints WHERE image_id=?", rec).fetchone()
        if not r or not r[0]:
            continue
        n, cols, blob = r
        kp = np.frombuffer(blob, dtype=np.float32).reshape(n, cols)[:, :2]
        keep = load_mask(mask)
        if keep is None:
            db.close()
            # Do NOT quietly skip the one check that catches unanticipated causes. Silently
            # disabling itself is the behaviour this whole script exists to prevent.
            return ["Pillow is not installed in this environment, so where the keypoints "
                    "landed could not be checked -- and that is the only check that "
                    "catches a mask failing for a reason nobody predicted. Install "
                    "Pillow, or run without --database and accept a weaker guarantee."]
        h, w = keep.shape
        x = np.clip(kp[:, 0].astype(int), 0, w - 1)
        y = np.clip(kp[:, 1].astype(int), 0, h - 1)
        inside_black = float((~keep[y, x]).mean())
        fracs.append(inside_black)
        rows.append((img.name, n, inside_black))
    db.close()

    if not rows:
        print("  (no keypoints to check yet)")
        return []

    fr = np.array(fracs)
    med = float(np.median([r[1] for r in rows]))
    print(f"  {len(rows)} frames checked, median {med:,.0f} keypoints each")
    print(f"  keypoints landing in the masked-out region: "
          f"{100*fr.mean():.2f}% average, {100*fr.max():.2f}% worst")

    if fr.max() > MASKED_KEYPOINT_FRACTION_MAX:
        worst = max(rows, key=lambda r: r[2])
        return [f"{100*fr.mean():.1f}% of keypoints sit where the mask says no features "
                f"should be extracted (worst {worst[0]}, {100*worst[2]:.1f}%). The masks "
                f"were NOT applied to this database. Every downstream stage would be "
                f"working from the backdrop as well as the object."]

    print("  -> the masks were applied: COLMAP put essentially no features on the backdrop")
    return []


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--images", required=True, type=Path)
    ap.add_argument("--masks", required=True, type=Path)
    ap.add_argument("--database", type=Path,
                    help="COLMAP database. Given, the effect check runs too -- prefer it.")
    ap.add_argument("--sample", type=int, default=12,
                    help="frames to open for the size/content/keypoint checks (0 = all)")
    args = ap.parse_args()

    if not args.images.is_dir():
        sys.exit(f"No photographs at {args.images}")
    if not args.masks.is_dir():
        sys.exit(f"No masks at {args.masks}")

    images = list_images(args.images)
    if not images:
        sys.exit(f"No photographs in {args.images}")

    # Spread the sample across the capture rather than taking the first N: on a turntable
    # the first dozen frames are one side of the object and can all be fine while the rest
    # are not.
    k = len(images) if args.sample <= 0 else min(args.sample, len(images))
    sample = [images[i] for i in np.linspace(0, len(images) - 1, k).astype(int)]

    print(f"\nmasks for {args.images.name}")
    problems = check_naming(images, args.masks, sample)
    problems += check_content(images, args.masks, sample)
    if args.database and args.database.exists():
        problems += check_effect(args.database, images, args.masks, sample)

    print()
    if problems:
        print("-> PROBLEM")
        for p in problems:
            print(f"   {p}")
        print("\n   Stopping here. COLMAP would not have said anything about any of this:")
        print("   an unmatched or ineffective mask produces an ordinary successful run.")
        return 1
    print("-> OK  the masks are present, correctly named and sized"
          + (", and demonstrably applied" if args.database else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
