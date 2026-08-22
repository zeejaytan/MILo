"""Look at A04's largest fragments beside A02's, at the same millimetres per pixel.

A04 measures worse than anything so far -- its 56 cm2 fragment holds 161 vertices per cm2
against A02's 884. That is a number, and the standing rule here is that no number about
geometry gets reported before the geometry has been drawn. A figure that low can mean a
genuinely coarse surface or it can mean the piece is not a sherd at all: a slab of clamp,
a fused pair, a sheet of background that survived the colour filter.

Everything is drawn at a fixed 7 pixels per millimetre, and each fragment is turned to face
the camera by its own principal axes -- spinning about the world vertical renders an
edge-mounted sherd as the same sliver from every angle, which looks like a broken renderer
rather than an answer.
"""
import sys
from pathlib import Path

import numpy as np
import trimesh
from PIL import Image, ImageDraw

PX_PER_MM = 7.0
SIZE = 820
RAKE = np.array([0.94, 0.10, -0.32]); RAKE /= np.linalg.norm(RAKE)


def sherds(path, mm):
    m = trimesh.load(path, process=False)
    if isinstance(m, trimesh.Scene):
        m = trimesh.util.concatenate(list(m.geometry.values()))
    col = np.asarray(m.visual.vertex_colors)[:, :3].astype(int)
    sel = ((col[:, 0] - (col[:, 1] + col[:, 2]) / 2) > 25) & (col.mean(1) > 45)
    F = np.asarray(m.faces)
    Fs = F[sel[F].all(axis=1)]
    used = np.unique(Fs)
    remap = np.full(len(m.vertices), -1, np.int64); remap[used] = np.arange(len(used))
    s = trimesh.Trimesh(vertices=np.asarray(m.vertices)[used], faces=remap[Fs],
                        process=False)
    del m, F, Fs
    out = [(c.area * mm ** 2 / 100.0, c) for c in s.split(only_watertight=False)]
    out = [(a, c) for a, c in out if len(c.vertices) >= 400 and a >= 0.8]
    out.sort(key=lambda t: t[0])
    return out


def render(c, mm):
    V = np.asarray(c.vertices) * mm
    N = np.asarray(c.vertex_normals)
    # Broadside, by the fragment's OWN axes: the two directions it is widest in become
    # the image plane, so a piece clamped edge-on still presents its face.
    ctr = V.mean(0)
    _, _, W = np.linalg.svd(V - ctr, full_matrices=False)
    Rm = np.stack([W[0], W[1], W[2]])
    P, Nv = (V - ctr) @ Rm.T, N @ Rm.T
    px = (P[:, 0] * PX_PER_MM + SIZE / 2).astype(np.int32)
    py = (SIZE / 2 - P[:, 1] * PX_PER_MM).astype(np.int32)
    ok = (px >= 0) & (px < SIZE) & (py >= 0) & (py < SIZE)
    px, py, z, Nv = px[ok], py[ok], P[ok, 2], Nv[ok]
    flat = py * SIZE + px
    zb = np.full(SIZE * SIZE, np.inf); np.minimum.at(zb, flat, z)
    front = z <= zb[flat] + 1e-9
    img = np.full(SIZE * SIZE, 18, np.uint8)
    img[flat[front]] = (np.clip(Nv @ RAKE, 0, 1) ** 0.8 * 235 + 20)[front].astype(np.uint8)
    return img.reshape(SIZE, SIZE), 100.0 * ok.mean()


if __name__ == "__main__":
    O = "/data/gpfs/projects/punim2657/MILo/output/17062025"
    a02 = sherds(f"{O}/A02/mesh_learnable_sdf.ply", 377.53)
    a04 = sherds(f"{O}/A04/mesh_learnable_sdf.ply", 383.714)
    picks = [("A02 largest", a02[-1], 377.53),
             ("A04 largest", a04[-1], 383.714),
             ("A04 2nd largest", a04[-2], 383.714)]

    sheet = Image.new("L", (SIZE * 3 + 20, SIZE + 46), 18)
    d = ImageDraw.Draw(sheet)
    for i, (lab, (area, c), mm) in enumerate(picks):
        im, shown = render(c, mm)
        sheet.paste(Image.fromarray(im), (i * (SIZE + 10), 0))
        dens = len(c.vertices) / area
        d.text((i * (SIZE + 10) + 12, SIZE + 8),
               f"{lab}   {area:.0f} cm2   {dens:.0f} vertices per cm2   "
               f"({10/np.sqrt(dens):.2f} mm apart)", fill=255)
        print(f"{lab}: {area:.1f} cm2, {dens:.0f} v/cm2, {shown:.0f}% of it fits the frame")
    bar = int(10 * PX_PER_MM)
    d.line([(12, SIZE + 30), (12 + bar, SIZE + 30)], fill=255, width=4)
    d.text((12 + bar + 8, SIZE + 24), f"10 mm  ({PX_PER_MM:.0f} px per mm, all panels)",
           fill=255)
    out = Path("look/a04_vs_a02.png"); out.parent.mkdir(exist_ok=True)
    sheet.save(out)
    print("wrote", out)
