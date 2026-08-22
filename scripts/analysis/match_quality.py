"""How well did the photographs of each capture actually match each other?

The one number that lines up with the ranking so far is how many photographs each sparse
point was recognised in: A03 7.6, A02 9.7, A01 10.2. That is a claim about the pictures,
not about the sherds, so it should be checkable directly from the feature matching --
before it gets believed.

Reads images.bin, which records every 2D feature in every photograph and whether it was
matched into a 3D point. Reports per capture:
  features per photograph      -- how much detail the detector found at all
  matched features per photo   -- how much of that survived into the 3D model
  match rate                   -- the fraction that did

A capture whose photographs are slightly dimmer, softer or lower in contrast produces
fewer stable features and matches a smaller share of them, and every later stage inherits
that. If A03 is not lower here, the lead is dead and the cause is still unknown.
"""
import struct
import sys
from pathlib import Path

import numpy as np


def read_images(path):
    per_img = []
    with open(path, "rb") as f:
        n = struct.unpack("<Q", f.read(8))[0]
        for _ in range(n):
            struct.unpack("<idddddddi", f.read(64))       # id, quat, trans, cam id
            while f.read(1) != b"\x00":                   # null-terminated name
                pass
            m = struct.unpack("<Q", f.read(8))[0]
            buf = np.frombuffer(f.read(24 * m), dtype=np.dtype([("x", "<f8"),
                                                                ("y", "<f8"),
                                                                ("p", "<i8")]))
            per_img.append((m, int((buf["p"] >= 0).sum())))
    return np.array(per_img, float)


if __name__ == "__main__":
    res = {}
    for arg in sys.argv[1:]:
        tag, path = arg.split("=", 1)
        a = read_images(Path(path))
        res[tag] = a
        print(f"\n{tag}   {len(a)} photographs")
        print(f"  features found per photograph   {a[:,0].mean():8.0f}")
        print(f"  of those, matched into 3D       {a[:,1].mean():8.0f}"
              f"   ({100*a[:,1].sum()/a[:,0].sum():.1f}%)")

    if len(res) >= 2:
        base = list(res)[0]
        print(f"\nrelative to {base}:")
        for k, a in res.items():
            b = res[base]
            print(f"  {k:<6} features {a[:,0].mean()/b[:,0].mean():5.2f}x   "
                  f"matched {a[:,1].mean()/b[:,1].mean():5.2f}x")
