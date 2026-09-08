"""Filter a MILo point_cloud.ply to a SAGA keep set (ticket alt-09).

Rows in, same columns out: every attribute (including MILo's occupancy
fields) is preserved, only rows drop. Refuses an empty keep set and reports
kept count + kept-Gaussian footprint median (the M4 number: 1.76 mm there).

Usage (milo env, CPU seconds):
    python saga_filter_ply.py --ply <in> --keep <keep_idx.npy> --out <out>
"""

import argparse

import numpy as np
from plyfile import PlyData


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ply", required=True)
    ap.add_argument("--keep", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    ply = PlyData.read(args.ply)
    el = ply["vertex"]
    keep = np.load(args.keep)
    if keep.size == 0:
        raise SystemExit("refusing: empty keep set")
    if keep.max() >= el.count or keep.min() < 0:
        raise SystemExit("refusing: keep index out of range")
    names = [p.name for p in el.properties]
    cols = [np.asarray(el[n])[keep] for n in names]
    arr = np.empty(len(keep), dtype=el.data.dtype)
    for n, c in zip(names, cols):
        arr[n] = c
    from plyfile import PlyElement
    PlyData([PlyElement.describe(arr, "vertex")], text=False).write(args.out)

    print(f"kept {len(keep)} of {el.count} "
          f"({100 * len(keep) / el.count:.2f}%)")
    if all(f"scale_{i}" in names for i in range(3)):
        sc = np.stack([np.asarray(el[f"scale_{i}"])[keep] for i in range(3)],
                      axis=1)
        print(f"kept-scale median {np.median(np.exp(sc)):.4f} units")


if __name__ == "__main__":
    main()
