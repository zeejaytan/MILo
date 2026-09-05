"""Paired rim close-ups: control vs masked-training renders, same windows.

Ticket masked-training/02 stops on "band alpha below 0.2 AND receding rims" --
this cuts the picture half. For spread held-out views it loads both models'
test renders plus the sherd outline, finds the densest outline-boundary windows
(where fracture rims live), and writes control/masked pairs plus composites at
NATIVE photo scale (0.21 mm/px on A03). Deliberately no upsampling: a 0.10 mm/px
view of a 0.21 mm/px render invents pixels rather than resolving ridges.

usage:
    python scripts/rim_crops.py --ctrl <test/ours_18000/renders> \
        --masked <test/ours_18000/renders> --masks <images_masked dir> \
        --data <dataset dir> --out <dir> [--views 0 10 20] [--size 500]
    python scripts/rim_crops.py --self-test
"""
import argparse
import os
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "milo"))

import importlib.util as _ilu
_spec = _ilu.spec_from_file_location(
    "colmap_loader", os.path.join(REPO, "milo", "scene", "colmap_loader.py"))
_cl = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(_cl)


def boundary_windows(alpha, size=500, top=2):
    """Return up to `top` non-overlapping (x0, y0) windows rich in outline edge.

    Edge = dilated XOR eroded alpha via PIL min/max filters (no scipy needed).
    Greedy: take the densest window, blank it, repeat.
    """
    a = (np.asarray(alpha) > 0).astype(np.uint8) * 255
    edge = np.asarray(Image.fromarray(a).filter(ImageFilter.MaxFilter(3))).astype(int) \
        - np.asarray(Image.fromarray(a).filter(ImageFilter.MinFilter(3))).astype(int)
    edge = (edge > 0).astype(np.int32)
    H, W = edge.shape
    # integral image for O(1) window sums
    ii = np.zeros((H + 1, W + 1), np.int64)
    ii[1:, 1:] = edge.cumsum(0).cumsum(1)
    taken = []
    taken_mask = np.zeros_like(edge, bool)

    def window_sum(x0, y0):
        x1, y1 = min(x0 + size, W), min(y0 + size, H)
        return ii[y1, x1] - ii[y0, x1] - ii[y1, x0] + ii[y0, x0]

    step = max(size // 4, 1)
    for _ in range(top):
        best, best_xy = -1, None
        for y0 in range(0, max(H - size + 1, 1), step):
            for x0 in range(0, max(W - size + 1, 1), step):
                if taken_mask[y0:y0 + size, x0:x0 + size].any():
                    continue
                s = window_sum(x0, y0)
                if s > best:
                    best, best_xy = s, (x0, y0)
        if best_xy is None or best <= 0:
            break
        taken.append(best_xy)
        x0, y0 = best_xy
        taken_mask[y0:y0 + size, x0:x0 + size] = True
    return taken


def test_names(data_dir, llffhold=8):
    exts = _cl.read_extrinsics_binary(str(Path(data_dir) / "sparse/0/images.bin"))
    order = sorted(exts.values(), key=lambda e: Path(e.name).name)
    test = [e for i, e in enumerate(order) if i % llffhold == 0] if llffhold else order
    return [Path(e.name).name for e in test]


def self_test():
    # 16x16 toy: mask = left half; boundary runs down column 7/8.
    alpha = Image.fromarray((np.tile(np.arange(16) < 8, (16, 1)) * 255).astype(np.uint8))
    wins = boundary_windows(alpha, size=8, top=2)
    assert len(wins) == 2, f"expected 2 windows, got {wins}"
    # both windows must actually contain boundary pixels
    a = (np.asarray(alpha) > 0).astype(np.uint8) * 255
    edge = (np.asarray(Image.fromarray(a).filter(ImageFilter.MaxFilter(3))).astype(int)
            - np.asarray(Image.fromarray(a).filter(ImageFilter.MinFilter(3))).astype(int)) > 0
    for x0, y0 in wins:
        assert edge[y0:y0 + 8, x0:x0 + 8].any(), f"window {x0},{y0} holds no edge"
    # windows must not overlap
    (x0, y0), (x1, y1) = wins
    assert x0 + 8 <= x1 or x1 + 8 <= x0 or y0 + 8 <= y1 or y1 + 8 <= y0, "windows overlap"
    # empty mask yields nothing rather than garbage
    assert boundary_windows(Image.fromarray(np.zeros((16, 16), np.uint8)), size=8) == []
    print("self-test: 4 assertions passed (2 edge windows, non-overlap, empty-safe).")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ctrl", type=Path, default=None)
    ap.add_argument("--masked", type=Path, default=None)
    ap.add_argument("--masks", type=Path, default=None,
                    help="RGBA images whose alpha is the outline")
    ap.add_argument("--data", type=Path, default=None,
                    help="dataset dir (sparse/0/images.bin for view order)")
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--views", type=int, nargs="+", default=None,
                    help="test-set indices (default: first, middle, last)")
    ap.add_argument("--size", type=int, default=500)
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        self_test()
        return
    for req in ("ctrl", "masked", "masks", "data", "out"):
        if getattr(args, req) is None:
            ap.error(f"--{req} is required (or pass --self-test)")
    args.out.mkdir(parents=True, exist_ok=True)

    names = test_names(args.data)
    idxs = args.views if args.views is not None else [0, len(names) // 2, len(names) - 1]
    for i in idxs:
        name = names[i]
        stem = f"{i:02d}_{Path(name).stem}"
        rc = Image.open(args.ctrl / f"{i:05d}.png").convert("RGB")
        rm = Image.open(args.masked / f"{i:05d}.png").convert("RGB")
        alpha = Image.open(args.masks / name).convert("RGBA").getchannel("A")
        if rc.size != alpha.size:
            alpha = alpha.resize(rc.size, Image.NEAREST)
        wins = boundary_windows(alpha, size=args.size, top=2)
        print(f"view {i} {name}: {len(wins)} rim windows")
        for k, (x0, y0) in enumerate(wins):
            box = (x0, y0, min(x0 + args.size, rc.width), min(y0 + args.size, rc.height))
            rc.crop(box).save(args.out / f"{stem}_rim{k}_ctrl.png")
            rm.crop(box).save(args.out / f"{stem}_rim{k}_masked.png")
            comp = Image.new("RGB", (box[2] - box[0], (box[3] - box[1]) * 2 + 8), "white")
            comp.paste(rc.crop(box), (0, 0))
            comp.paste(rm.crop(box), (0, box[3] - box[1] + 8))
            comp.save(args.out / f"{stem}_rim{k}_pair.png")
    print(f"wrote pairs to {args.out}")


if __name__ == "__main__":
    main()
