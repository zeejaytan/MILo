"""Look at a mesh. Two views, with the measurements printed on the picture.

CLAUDE.md requires that geometry is rendered before anything is claimed about it, so this
is the tool for doing that rather than something rewritten per question. It needs no GPU,
no display and no scene setup: a z-buffered splat of the vertices, shaded by normal.

Splatting rather than triangle rasterisation because these meshes carry 0.5-4 million
vertices against a 900x900 frame -- several samples per pixel, so the surface resolves as
well as it would from triangles, in seconds instead of hours.

Reports connected components too, which is the number that matters after surface masking:
with the clamps removed the sherds should be separate objects, where a clamp jaw resting on
a sherd fuses them into one.

Usage:
    python render_mesh.py --mesh a.ply [--mesh b.ply ...] --out <dir> [--label "..."]
"""
import argparse
from pathlib import Path

import numpy as np
import trimesh
from PIL import Image, ImageDraw

W = H = 900
LIGHT = np.array([0.35, 0.40, -0.85])
LIGHT /= np.linalg.norm(LIGHT)


def view(V, N, azim, bounds):
    """Orthographic z-buffer splat, camera orbiting the vertical axis by `azim` degrees.

    `bounds` is (world-space centre, span) and is shared between the views of one mesh so
    both are framed identically. The centre is rotated into camera space HERE -- subtracting
    a world-space centre from camera-space coordinates silently pushes any mesh whose
    centroid is away from the origin off the edge of the frame, which renders as a
    completely black image and reads as "the mesh is empty".
    """
    a = np.radians(azim)
    fwd = np.array([np.cos(a), np.sin(a), 0.0])
    up = np.array([0.0, 0.0, 1.0])
    right = np.cross(up, fwd)
    Rm = np.stack([right, up, fwd])

    P, Nv = V @ Rm.T, N @ Rm.T
    ctr_world, span = bounds
    ctr = ctr_world @ Rm.T
    s = (W - 60) / span
    px = ((P[:, 0] - ctr[0]) * s + W / 2).astype(np.int32)
    py = (H / 2 - (P[:, 1] - ctr[1]) * s).astype(np.int32)
    z = P[:, 2]

    inb = (px >= 0) & (px < W) & (py >= 0) & (py < H)
    if not inb.any():
        return np.full((H, W), 23, np.uint8)
    px, py, z, Nv = px[inb], py[inb], z[inb], Nv[inb]
    flat = py * W + px

    zbuf = np.full(W * H, np.inf, np.float64)
    np.minimum.at(zbuf, flat, z)
    win = z <= zbuf[flat] + 1e-9

    nb = np.zeros((W * H, 3), np.float32)
    nb[flat[win]] = Nv[win]
    lit = np.abs(nb @ LIGHT)
    img = (0.15 + 0.85 * lit) ** (1 / 2.2)
    img[~np.isfinite(zbuf)] = 0.09
    img = img.reshape(H, W)

    stack = np.stack([np.roll(np.roll(img, dy, 0), dx, 1)
                      for dy in (-1, 0, 1) for dx in (-1, 0, 1)])
    filled = np.where(img <= 0.091, stack.max(0), img)
    return (np.clip(filled, 0, 1) * 255).astype(np.uint8)


def render(path, out_dir, label=None, components=True):
    m = trimesh.load(path, process=False)
    V = np.asarray(m.vertices, np.float64)
    N = np.asarray(m.vertex_normals, np.float64)
    lo, hi = V.min(0), V.max(0)
    ext = hi - lo

    # Component sizes are in FACES, and are counted by labelling the face-adjacency graph
    # rather than by trimesh's split(). Same definition of a component -- split() walks the
    # same graph -- but split() then materialises a full Trimesh object per component, and
    # that cost is what matters here: these meshes are mostly speckle. The MILo surface for
    # 03072025/N01 has 8,860 components, so split() built 8,860 meshes and had not finished
    # after thirty minutes (job 29619651, TIMEOUT). Labelling the same graph takes 21 s.
    #
    # A mesh too broken to count is exactly the mesh worth looking at, so a failure here
    # must not stop the picture being drawn.
    ncomp, sizes = None, []
    if components:
        try:
            lab = trimesh.graph.connected_component_labels(
                m.face_adjacency, node_count=len(m.faces))
            counts = np.bincount(lab)
            ncomp = len(counts)
            sizes = sorted(counts.tolist(), reverse=True)[:6]
        except Exception:
            ncomp = None

    units = "mm" if b"units: millimetres" in open(path, "rb").read(4096) else "arbitrary units"
    bounds = ((lo + hi) / 2, ext.max() * 1.05)
    canvas = Image.new("L", (W * 2, H), 23)
    for i, az in enumerate((0, 90)):
        canvas.paste(Image.fromarray(view(V, N, az, bounds)), (i * W, 0))
    canvas = canvas.convert("RGB")
    d = ImageDraw.Draw(canvas)
    d.text((14, 12), label or Path(path).name, fill=(255, 255, 255))
    d.text((14, 30), f"{len(V):,} vertices, {len(m.faces):,} faces    "
                     f"extent {ext[0]:.1f} x {ext[1]:.1f} x {ext[2]:.1f} {units}",
           fill=(205, 205, 205))
    if ncomp is not None:
        d.text((14, 48), f"{ncomp:,} separate pieces; largest, in faces: {sizes}", fill=(205, 205, 205))
    d.text((14, 66), "left: front        right: turned 90 degrees", fill=(145, 145, 145))

    out = Path(out_dir) / (Path(path).stem + "_render.png")
    out.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out)
    print(f"  {Path(path).name}: {len(V):,} vertices, {ncomp} pieces, "
          f"extent {ext[0]:.1f} x {ext[1]:.1f} x {ext[2]:.1f} {units} -> {out.name}")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mesh", action="append", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--label", default=None)
    ap.add_argument("--no-components", dest="components", action="store_false")
    args = ap.parse_args()
    for p in args.mesh:
        render(p, args.out, args.label if len(args.mesh) == 1 else None, args.components)


if __name__ == "__main__":
    main()
