"""Three sherds at the same millimetres per pixel: A02 big, A02 small, A03 biggest.

The comparison that matters is not A02 against A03 -- those differ in more than one way at
once. It is A02's own small sherd against A02's own big one: same camera, same lights, same
training run, same mask, one object. Whatever separates those two cannot be the training
configuration, and if A03's sherds look like A02's small one, the question is answered.

Everything is drawn at a fixed 7 pixels per millimetre so a bump of a given real size is
the same number of pixels in all three panels.
"""
import sys
from pathlib import Path

import numpy as np
import trimesh
from PIL import Image, ImageDraw

PX_PER_MM = 7.0
SIZE = 900
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
    out = []
    for c in s.split(only_watertight=False):
        a = c.area * mm ** 2 / 100.0
        if len(c.vertices) >= 3000 and a >= 3:
            out.append((a, c))
    out.sort(key=lambda t: t[0])
    return out


def render(c, mm, azim):
    V = np.asarray(c.vertices) * mm
    N = np.asarray(c.vertex_normals)
    # Broadside, by the sherd's OWN axes. Spinning about the world vertical cannot face a
    # sherd that was clamped edge-on: every azimuth renders it as the same sliver, and the
    # panel looks like a rendering failure rather than an answer. The two widest principal
    # axes go in the image plane, so the flat of the sherd faces the camera by construction.
    ctr0 = V.mean(0)
    _, _, W = np.linalg.svd(V - ctr0, full_matrices=False)
    Rm = np.stack([W[0], W[1], W[2]])
    P, Nv = V @ Rm.T, N @ Rm.T
    ctr = P.mean(0)
    px = ((P[:, 0] - ctr[0]) * PX_PER_MM + SIZE / 2).astype(np.int32)
    py = (SIZE / 2 - (P[:, 1] - ctr[1]) * PX_PER_MM).astype(np.int32)
    ok = (px >= 0) & (px < SIZE) & (py >= 0) & (py < SIZE)
    px, py, z, Nv = px[ok], py[ok], P[ok, 2], Nv[ok]
    flat = py * SIZE + px
    zb = np.full(SIZE * SIZE, np.inf); np.minimum.at(zb, flat, z)
    front = z <= zb[flat] + 1e-9
    img = np.full(SIZE * SIZE, 18, np.uint8)
    img[flat[front]] = (np.clip(Nv @ RAKE, 0, 1) ** 0.8 * 235 + 20)[front].astype(np.uint8)
    return img.reshape(SIZE, SIZE)


if __name__ == "__main__":
    O = "/data/gpfs/projects/punim2657/MILo/output/17062025"
    a02 = sherds(f"{O}/A02/mesh_learnable_sdf.ply", 377.53)
    a03 = sherds(f"{O}/A03/mesh_learnable_sdf.ply", 373.73)
    picks = [("A02 largest sherd", a02[-1], 377.53),
             ("A02 SMALLEST sherd", a02[0], 377.53),
             ("A03 largest sherd", a03[-1], 373.73)]

    sheet = Image.new("L", (SIZE * 3 + 20, SIZE + 46), 18)
    d = ImageDraw.Draw(sheet)
    for i, (lab, (area, c), mm) in enumerate(picks):
        # Face each sherd broadside. A fixed azimuth renders whichever ones happen to sit
        # edge-on as a sliver, which shows nothing at all while looking like a real panel.
        best = max((render(c, mm, az) for az in range(0, 180, 20)),
                   key=lambda im: int((im > 25).sum()))
        sheet.paste(Image.fromarray(best), (i * (SIZE + 10), 0))
        dens = len(c.vertices) / area
        d.text((i * (SIZE + 10) + 12, SIZE + 8),
               f"{lab}   {area:.0f} cm2   {dens:.0f} vertices per cm2   "
               f"({10/np.sqrt(dens):.2f} mm apart)", fill=255)
        print(f"{lab}: {area:.0f} cm2, {dens:.0f} v/cm2")
    bar = int(10 * PX_PER_MM)
    d.line([(12, SIZE + 30), (12 + bar, SIZE + 30)], fill=255, width=4)
    d.text((12 + bar + 8, SIZE + 24), f"10 mm  ({PX_PER_MM:.0f} px per mm, all panels)",
           fill=255)
    out = Path("look/three_sherds.png")
    out.parent.mkdir(exist_ok=True)
    sheet.save(out)
    print("wrote", out)
