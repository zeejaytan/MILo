"""Cut a mesh down to the volume other meshes already agree on.

WHY A REFERENCE MESH AND NOT A TYPED-IN BOX. The MILo surface for 03072025/N01 came out
2.76 m across -- the studio, not the tray -- while the three photogrammetric surfaces of
the same capture agreed on a box 59 cm across. The question that box answers is whether
the sherds are in there underneath the junk (a cull that under-removed, which is fixable)
or absent (the method failed on this capture, which is not). Typing the numbers in by hand
would make the answer depend on my arithmetic; taking them from a mesh built by a
different method makes it depend on the data.

THE FAILURE THIS GUARDS AGAINST is a frame mismatch. If the two meshes are not in the same
coordinate system the crop returns nothing, and an empty mesh renders as a black picture
that reads exactly like "the method produced nothing". So the overlap is measured first and
a crop that keeps almost nothing is refused rather than written. Say no loudly, or the
tool's silence gets mistaken for a finding.

Faces are kept by CENTROID, not by all-three-vertices: a face straddling the boundary is
kept whole rather than punching a hole along every wall of the box.

Usage:
    python crop_mesh.py --mesh <in.ply> --box-from <ref.ply> [--box-from <ref2.ply> ...]
        --out <out.ply> [--margin 0.02] [--min-keep 0.001]
"""
import argparse
import sys
from pathlib import Path

import numpy as np
import trimesh


def box_of(paths, margin):
    """Union of the reference bounding boxes, grown by margin of the largest span.

    Union rather than intersection: each reference is one method's opinion of where the
    object is, and a method that missed part of the object should not be able to shrink
    the box below what another one saw.
    """
    los, his = [], []
    for p in paths:
        V = np.asarray(trimesh.load(p, process=False).vertices, np.float64)
        los.append(V.min(0))
        his.append(V.max(0))
        print(f"  box from {Path(p).name}: "
              f"{np.round(V.min(0), 3)} .. {np.round(V.max(0), 3)}")
    lo, hi = np.min(los, 0), np.max(his, 0)
    pad = (hi - lo).max() * margin
    return lo - pad, hi + pad


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mesh", required=True, type=Path)
    ap.add_argument("--box-from", required=True, action="append", type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--margin", type=float, default=0.02,
                    help="grow the box by this fraction of its largest span (default 2%%)")
    ap.add_argument("--min-keep", type=float, default=0.001,
                    help="refuse to write if less than this fraction of faces survives")
    args = ap.parse_args()

    lo, hi = box_of(args.box_from, args.margin)
    print(f"  crop box: {np.round(lo, 3)} .. {np.round(hi, 3)}  "
          f"span {np.round(hi - lo, 3)}")

    m = trimesh.load(args.mesh, process=False)
    V = np.asarray(m.vertices, np.float64)
    F = np.asarray(m.faces)
    print(f"  {args.mesh.name}: {len(V):,} vertices, {len(F):,} faces, "
          f"extent {np.round(V.max(0) - V.min(0), 3)}")

    cen = V[F].mean(axis=1)
    keep = np.all((cen >= lo) & (cen <= hi), axis=1)
    frac = keep.sum() / max(len(F), 1)
    print(f"  inside the box: {keep.sum():,} of {len(F):,} faces ({100 * frac:.1f}%)")

    if frac < args.min_keep:
        sys.exit(f"REFUSED: only {100 * frac:.3f}% of faces fall inside the box. Either the "
                 "two meshes are in different coordinate frames, or this mesh genuinely has "
                 "nothing where the reference has the object. Do not read the empty result "
                 "as a rendering of the method's output -- find out which of the two it is.")

    out = m.submesh([keep], append=True)
    Vo = np.asarray(out.vertices, np.float64)
    print(f"  kept: {len(Vo):,} vertices, {len(out.faces):,} faces, "
          f"extent {np.round(Vo.max(0) - Vo.min(0), 3)}")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    out.export(args.out)
    print(f"  wrote {args.out}")
    print("  The crop is a VIEWING aid, not a result: it says what the method put in the "
          "box, and nothing about what it put outside.")


if __name__ == "__main__":
    main()
