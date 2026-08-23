"""Put a mesh into millimetres, and record in the file where the scale came from.

PLY, OBJ and STL have no units field -- a coordinate is a bare number and nothing in the
format says what it means. So "metric" can only be two things, and this does both:

  the coordinates are multiplied into millimetres, and
  the provenance is written into the PLY header's comment lines, which is the one place
  the format lets you say anything at all.

A mesh silently in arbitrary units looks identical to a metric one, which is why the
comments matter as much as the numbers. A sidecar JSON is written too, because some tools
strip comments on load and save.

DOUBLE SCALING is the failure this guards hardest against. Applying the factor twice is
invisible -- the mesh simply becomes 377x too large and every measurement from it is wrong
by that factor with nothing to reveal it. Any mesh already carrying a units comment is
refused.

Usage:
    python scale_mesh.py --mesh <in.ply> --out <out.ply> \\
        --measurement <base_measurement.json> [--capture 17062025/A02]
"""
import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

MARKER = "comment units:"


def read_header(path):
    with open(path, "rb") as f:
        raw = b""
        while b"end_header" not in raw:
            line = f.readline()
            if not line:
                sys.exit(f"{path}: no end_header -- not a PLY?")
            raw += line
        return raw, f.tell()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mesh", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--measurement", required=True, type=Path,
                    help="base_measurement.json from measure_base.py")
    ap.add_argument("--capture", default="")
    ap.add_argument("--method", default="")
    args = ap.parse_args()

    m = json.loads(args.measurement.read_text())
    if not m.get("accepted"):
        sys.exit("That measurement was REJECTED. Refusing to scale by a factor its own "
                 "checks did not accept.")
    factor = 0.5 * (m["mm_per_unit_long"] + m["mm_per_unit_short"])

    raw, offset = read_header(args.mesh)
    header = raw.decode("ascii", errors="replace")
    if MARKER in header:
        sys.exit(f"{args.mesh.name} already carries a units comment -- it has been scaled "
                 "before. Scaling twice is invisible and would make every measurement "
                 "wrong by the square of the factor. Refusing.")

    # Vertex layout: x,y,z are the first three properties of the vertex element in every
    # file this pipeline produces, but check rather than assume.
    lines = header.splitlines()
    in_vertex, props, nvert = False, [], 0
    for l in lines:
        w = l.split()
        if not w:
            continue
        if w[0] == "element":
            in_vertex = (w[1] == "vertex")
            if in_vertex:
                nvert = int(w[2])
        elif w[0] == "property" and in_vertex and w[1] != "list":
            props.append((w[1], w[2]))
    if [p[1] for p in props[:3]] != ["x", "y", "z"]:
        sys.exit(f"Unexpected vertex layout {[p[1] for p in props[:3]]}; refusing to guess.")
    if props[0][0] not in ("float", "float32"):
        sys.exit(f"x is {props[0][0]}, expected float32; refusing to guess.")

    size = {"float": 4, "float32": 4, "double": 8, "uchar": 1, "uint8": 1, "char": 1,
            "int": 4, "int32": 4, "uint": 4, "short": 2, "ushort": 2}
    stride = sum(size.get(t, 4) for t, _ in props)

    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
    note = [
        f"{MARKER} millimetres",
        f"comment scale_applied: {factor:.6f} mm per reconstruction unit",
        "comment scale_source: top face of the blue metal base, 190 x 130 mm",
        f"comment scale_long_edge: {m['mm_per_unit_long']:.4f} mm/unit",
        f"comment scale_short_edge: {m['mm_per_unit_short']:.4f} mm/unit",
        f"comment scale_edge_disagreement: {100*m['disagreement']:.2f} percent",
        f"comment scale_aspect_measured: {m['aspect']:.4f} (true 1.4615)",
        "comment scale_caveat: this is PRECISION not ACCURACY -- every check derives from",
        "comment scale_caveat: the top face really being 190 x 130 mm, which is a nominal",
        "comment scale_caveat: figure until the physical plate is measured with calipers",
        f"comment scaled_at: {stamp}",
    ]
    if args.capture:
        note.append(f"comment capture: {args.capture}")
    if args.method:
        note.append(f"comment method: {args.method}")

    new_header = header.replace("end_header", "\n".join(note) + "\nend_header")

    print(f"  {args.mesh.name}: {nvert:,} vertices, stride {stride} B, x{factor:.3f} mm/unit")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.mesh, "rb") as fi, open(args.out, "wb") as fo:
        fi.seek(offset)
        fo.write(new_header.encode("ascii"))
        # Stream it: these meshes reach 200 MB and there is no reason to hold one in memory.
        CH = 200_000
        left = nvert
        while left > 0:
            n = min(CH, left)
            buf = bytearray(fi.read(stride * n))
            arr = np.frombuffer(buf, dtype=np.uint8).reshape(n, stride)
            xyz = arr[:, :12].copy().view("<f4").reshape(n, 3) * np.float32(factor)
            arr = arr.copy()
            arr[:, :12] = xyz.view(np.uint8).reshape(n, 12)
            fo.write(arr.tobytes())
            left -= n
        shutil.copyfileobj(fi, fo)          # faces and anything after, untouched

    side = args.out.with_suffix(".scale.json")
    side.write_text(json.dumps(dict(
        units="millimetres", mm_per_unit=factor, source="blue base top face 190x130 mm",
        capture=args.capture, method=args.method, measured=m, scaled_at=stamp,
        # The reference used to be unchecked -- 190x130 mm was the conservator's
        # record and nothing had ever tested it. The turntable marker board now has:
        # 16 machine-detected targets on a printed 40 mm lattice reach the plate's
        # LONG edge to 0.42% (docs/notes/2026-08-22-turntable-markers.md, section 10).
        # The short edge is still unchecked, because the Metashape point that would
        # have checked it is the one found to be misplaced. This factor is the mean of
        # both edges, so half its reference is now verified and half is not.
        caveat="precision ~1%; long edge of the 190x130 mm reference verified to "
               "0.42% against the turntable marker board, short edge unverified",
        reference_check="turntable board, docs/reference/turntable-board-03072025-N01.json"),
        indent=2))
    print(f"  wrote {args.out.name} and {side.name}")


if __name__ == "__main__":
    main()
