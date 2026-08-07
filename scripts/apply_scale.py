#!/usr/bin/env python3
"""
Put a MILo mesh into millimetres.

MILo reconstructs in whatever units its COLMAP model uses. Two cases, and confusing them
would silently corrupt every measurement taken from the mesh afterwards:

  1. The capture was scaled with `pipeline/bin/scale_apply.py`. That rewrites the COLMAP
     sparse model itself, so the model MILo trained on was ALREADY metric and so is its
     mesh. Nothing to do here — applying the factor again would shrink the sherd by that
     factor a second time. This script refuses to do it.

  2. The scale was measured but never applied (`<work>/scale/SCALE.txt` exists, no
     `scale_log.txt`). Then the mesh is in arbitrary units and needs multiplying.

Case 1 vs 2 is read from `capture.json`, written by scripts/colmap_to_milo.py.

Usage:
    python scripts/apply_scale.py \\
        --capture /data/gpfs/projects/punim2657/MILo/data/16062025/capture.json \\
        --mesh    /data/gpfs/projects/punim2657/MILo/output/16062025/mesh.ply \\
        --out     /data/gpfs/projects/punim2657/MILo/output/16062025/mesh_mm.ply
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import trimesh


def main() -> int:
    ap = argparse.ArgumentParser(description="Scale a MILo mesh to millimetres")
    ap.add_argument("--capture", required=True, type=Path,
                    help="capture.json written by colmap_to_milo.py")
    ap.add_argument("--mesh", required=True, type=Path, help="mesh in COLMAP units")
    ap.add_argument("--out", required=True, type=Path, help="output mesh in millimetres")
    ap.add_argument("--force-factor", type=float, default=None,
                    help="override the recorded factor (COLMAP units -> metres)")
    args = ap.parse_args()

    capture = json.loads(args.capture.read_text())
    scale = capture.get("scale", {})
    factor = args.force_factor if args.force_factor is not None else scale.get("scale_factor")
    already = bool(scale.get("already_applied"))

    if factor is None:
        print(
            "No scale factor for this capture. The mesh is in arbitrary units and no\n"
            "measurement taken from it can be stated in millimetres. Measure the scale\n"
            "first (pipeline/bin/scale_aruco.py or scale_export.py + scale_apply.py).",
            file=sys.stderr,
        )
        return 1

    if already and args.force_factor is None:
        print(
            f"Capture {capture.get('work_dir')} was scaled at the COLMAP stage:\n"
            f"  {scale.get('scale_source')} (factor {factor:.9f}) is already baked into\n"
            "  the sparse model, so this mesh is metric already.\n"
            "Refusing to apply it twice. Convert metres to millimetres only:\n"
            "  --force-factor 1.0",
            file=sys.stderr,
        )
        return 1

    mesh = trimesh.load(args.mesh, process=False)
    if isinstance(mesh, trimesh.Scene):
        mesh = trimesh.util.concatenate(tuple(mesh.geometry.values()))

    before = mesh.extents.copy()
    # factor converts COLMAP units -> metres; x1000 -> millimetres.
    mesh.apply_scale(float(factor) * 1000.0)
    after = mesh.extents

    args.out.parent.mkdir(parents=True, exist_ok=True)
    mesh.export(args.out)

    print(f"Wrote {args.out}")
    print(f"  vertices        : {len(mesh.vertices):,}")
    print(f"  factor          : {factor:.9f} (COLMAP units -> m), then x1000 -> mm")
    print(f"  bounding box    : {np.array2string(before, precision=4)} units")
    print(f"                  → {np.array2string(after, precision=1)} mm")

    # A sherd that comes out the size of a room, or of a grain of sand, means the factor
    # or the mesh is wrong. Say so rather than letting it flow into a comparison.
    longest = float(after.max())
    if not (5.0 <= longest <= 1000.0):
        print(
            f"\nWARNING: longest dimension is {longest:.1f} mm. A pottery sherd is "
            "normally 20-300 mm. Check the scale measurement before using this mesh.",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
