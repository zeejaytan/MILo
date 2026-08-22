"""Where in the photograph did COLMAP look for features?

A03 found 5,600 features per photograph where A02 found 19,300 and A01 23,800. A dimmer,
softer picture loses some features, but not three quarters of them. The other explanation
is that A03's camera solve was run with the background masked out, so the detector was
only ever allowed to look at the sherds -- in which case the mask affected the stage that
decides where the cameras are, not just the stage I already tested.

That is checkable without rerunning anything: the 2D position of every detected feature is
recorded in images.bin. Lay them on a coarse grid and see how much of the frame they touch.

  unmasked  -- features everywhere: backdrop, clamps, rig, sherds. Most cells occupied.
  masked    -- features confined to a small, sherd-shaped part of the frame.
"""
import struct
import sys
from pathlib import Path

import numpy as np

G = 48   # grid cells across the frame


def occupancy(path, every=8):
    occ = np.zeros((G, G), np.int64)
    nimg = 0
    W = H = 0
    with open(path, "rb") as f:
        n = struct.unpack("<Q", f.read(8))[0]
        for i in range(n):
            struct.unpack("<idddddddi", f.read(64))
            while f.read(1) != b"\x00":
                pass
            m = struct.unpack("<Q", f.read(8))[0]
            raw = f.read(24 * m)
            if i % every:
                continue
            b = np.frombuffer(raw, dtype=np.dtype([("x", "<f8"), ("y", "<f8"),
                                                   ("p", "<i8")]))
            if not len(b):
                continue
            W = max(W, b["x"].max()); H = max(H, b["y"].max())
            gx = np.clip((b["x"] / (W + 1) * G).astype(int), 0, G - 1)
            gy = np.clip((b["y"] / (H + 1) * G).astype(int), 0, G - 1)
            np.add.at(occ, (gy, gx), 1)
            nimg += 1
    return occ, nimg, W, H


if __name__ == "__main__":
    for arg in sys.argv[1:]:
        tag, path = arg.split("=", 1)
        occ, nimg, W, H = occupancy(Path(path))
        tot = occ.sum()
        frac_cells = (occ > 0).mean()
        # how concentrated: what share of the frame holds 90% of the features
        s = np.sort(occ.ravel())[::-1]
        c = np.cumsum(s) / max(tot, 1)
        k = int(np.searchsorted(c, 0.90) + 1)
        print(f"\n{tag}  ({nimg} photographs sampled, frame about {W:.0f}x{H:.0f} px)")
        print(f"  cells of the frame with any feature at all : {100*frac_cells:5.1f}%")
        print(f"  smallest part of the frame holding 90% of them: {100*k/(G*G):5.1f}%")
        rows = (occ.reshape(G, G) > 0).astype(int)
        blk = rows.reshape(G // 3, 3, G // 3, 3).max(axis=(1, 3))
        print("  where features are (each character = 1/16 of the frame width):")
        for r in blk:
            print("    " + "".join("#" if v else "." for v in r))
