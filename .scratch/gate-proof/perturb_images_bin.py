"""Put N photographs at the wrong rotation in a COPY of a real COLMAP model.

Why by swapping NAMES rather than by moving cameras: the board reference is keyed by
filename, so swapping two widely separated frames' names says "this photograph was taken
at the other side of the turn" without touching a single coordinate. That is exactly the
A03 failure -- every frame registered, geometry self-consistent, frames in the wrong place
-- and it needs no assumption about where the axis is in this model's coordinates.

Usage: perturb_images_bin.py <model_dir> <npairs>
"""
import shutil, struct, sys
from pathlib import Path

def read(p):
    b = p.read_bytes()
    o = 0
    n, = struct.unpack_from("<Q", b, o); o += 8
    recs = []
    for _ in range(n):
        head = b[o:o + 64]; o += 64
        e = b.index(b"\x00", o)
        name = b[o:e]; o = e + 1
        np2, = struct.unpack_from("<Q", b, o); o += 8
        pts = b[o:o + 24 * np2]; o += 24 * np2
        recs.append([head, name, np2, pts])
    assert o == len(b), (o, len(b))
    return recs

def write(p, recs):
    out = [struct.pack("<Q", len(recs))]
    for head, name, np2, pts in recs:
        out += [head, name, b"\x00", struct.pack("<Q", np2), pts]
    p.write_bytes(b"".join(out))

src, npairs = Path(sys.argv[1]), int(sys.argv[2])
dst = Path(sys.argv[3])
if dst.exists():
    shutil.rmtree(dst)
shutil.copytree(src, dst)

recs = read(dst / "images.bin")
recs.sort(key=lambda r: r[1])
n = len(recs)
swapped = []
for k in range(npairs):
    i = 5 + k * 7
    j = (i + n // 3) % n                      # a third of a turn away
    recs[i][1], recs[j][1] = recs[j][1], recs[i][1]
    swapped += [recs[i][1].decode(), recs[j][1].decode()]
write(dst / "images.bin", recs)
print(f"copied {src} -> {dst}")
print(f"swapped {npairs} pair(s), i.e. {2*npairs} photographs now claim to be a third of a")
print(f"turn from where they were: {', '.join(sorted(swapped))}")
