"""Close-up of one sherd from each mesh, at the SAME millimetres per pixel.

Whole-mesh renders cannot answer "is this one rougher than that one" -- they frame two
objects of different size to the same box, so the coarser one is drawn larger and looks
finer. This fixes the scale instead: every output is rendered at a stated number of pixels
per millimetre, so a bump of a given real size is the same number of pixels in every
picture and the two can be set against each other honestly.

Lit from a grazing angle, because relief is what is in question and flat frontal light
hides it.
"""
import argparse
import sys
from pathlib import Path

import numpy as np
import trimesh
from PIL import Image, ImageDraw

PX_PER_MM = 6.0
RAKE = np.array([0.94, 0.10, -0.32])       # low, from the left: shows relief, not albedo
RAKE /= np.linalg.norm(RAKE)


def pick_sherd(m, mm_per_unit, box_mm=None):
    """The largest terracotta piece, or whatever sits in a given millimetre box."""
    if box_mm is not None:
        lo, hi = np.array(box_mm[0]) / mm_per_unit, np.array(box_mm[1]) / mm_per_unit
        V = np.asarray(m.vertices)
        keep = np.all((V >= lo) & (V <= hi), axis=1)
        # submesh() indexes FACES, not vertices. Handing it vertex indices silently
        # returns a different, much larger piece of the scene -- which renders as a
        # plausible-looking picture of the wrong thing.
        F = np.asarray(m.faces)
        fidx = np.where(keep[F].all(axis=1))[0]
        return m.submesh([fidx], append=True, repair=False) if len(fidx) > 50 else None

    comps = m.split(only_watertight=False)
    best, best_score = None, -1
    for c in comps:
        if len(c.vertices) < 5000:
            continue
        col = getattr(c.visual, "vertex_colors", None)
        if col is None or len(col) != len(c.vertices):
            score = len(c.vertices)
        else:
            rgb = np.asarray(col)[:, :3].astype(int)
            red = ((rgb[:, 0] - (rgb[:, 1] + rgb[:, 2]) / 2) > 25).mean()
            e = np.sort(np.ptp(c.vertices, 0))
            if e[0] / max(e[2], 1e-9) < 0.06:        # flat and wide: that is the base plate
                continue
            score = red * len(c.vertices)
        if score > best_score:
            best, best_score = c, score
    return best


def render(c, mm_per_unit, azim, px_per_mm=PX_PER_MM, size=900):
    V = np.asarray(c.vertices) * mm_per_unit
    N = np.asarray(c.vertex_normals)
    a = np.radians(azim)
    fwd = np.array([np.cos(a), np.sin(a), 0.0])
    up = np.array([0.0, 0.0, 1.0])
    Rm = np.stack([np.cross(up, fwd), up, fwd])
    P, Nv = V @ Rm.T, N @ Rm.T
    ctr = P.mean(0)

    px = ((P[:, 0] - ctr[0]) * px_per_mm + size / 2).astype(np.int32)
    py = (size / 2 - (P[:, 1] - ctr[1]) * px_per_mm).astype(np.int32)
    inb = (px >= 0) & (px < size) & (py >= 0) & (py < size)
    px, py, z, Nv = px[inb], py[inb], P[inb, 2], Nv[inb]
    flat = py * size + px

    zb = np.full(size * size, np.inf)
    np.minimum.at(zb, flat, z)
    front = z <= zb[flat] + 1e-9
    shade = np.clip(Nv @ RAKE, 0, 1) ** 0.8 * 235 + 20

    img = np.full(size * size, 18, np.uint8)
    img[flat[front]] = shade[front].astype(np.uint8)
    return img.reshape(size, size), inb.sum(), len(V)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mesh", required=True, type=Path)
    ap.add_argument("--mm-per-unit", required=True, type=float)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--label", default="")
    ap.add_argument("--box-mm", default=None, help="x0,y0,z0,x1,y1,z1 in mm")
    a = ap.parse_args()

    m = trimesh.load(a.mesh, process=False)
    if isinstance(m, trimesh.Scene):
        m = trimesh.util.concatenate(list(m.geometry.values()))

    box = None
    if a.box_mm:
        v = [float(x) for x in a.box_mm.split(",")]
        box = (v[:3], v[3:])
    c = pick_sherd(m, a.mm_per_unit, box)
    if c is None:
        sys.exit(f"no sherd found in {a.mesh}")

    ext = np.ptp(c.vertices, 0) * a.mm_per_unit
    print(f"{a.label}: {len(c.vertices):,} verts, "
          f"{ext[0]:.0f} x {ext[1]:.0f} x {ext[2]:.0f} mm")

    tiles = [render(c, a.mm_per_unit, az)[0] for az in (0, 90, 180)]
    sheet = Image.new("L", (900 * 3 + 20, 940), 18)
    for i, t in enumerate(tiles):
        sheet.paste(Image.fromarray(t), (i * 910, 0))
    d = ImageDraw.Draw(sheet)
    bar = int(20 * PX_PER_MM)
    d.line([(20, 915), (20 + bar, 915)], fill=255, width=4)
    d.text((20, 920), f"20 mm   |   {PX_PER_MM:.0f} px per mm   |   {a.label}   "
                      f"|   {len(c.vertices):,} vertices over "
                      f"{c.area * a.mm_per_unit**2 / 100:.0f} cm2", fill=255)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(a.out)
    print(f"  wrote {a.out}")


if __name__ == "__main__":
    sys.exit(main())
