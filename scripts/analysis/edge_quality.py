"""How ragged are the sherd edges, and how much of that did the carving step cause?

The A03 mesh that was handed over had been silhouette-carved; the A02 mesh it was compared
against had not. Carving cuts triangles wherever a vertex falls outside the photographed
outline, which leaves torn boundaries and orphan crumbs along every edge it touches. That
is a cleanup artefact, not a reconstruction one, and it needs separating from the question
of whether MILo did worse on A03.

Measured per mesh:
  - open boundary edge length per cm2 of surface: a closed surface has none; a torn one has
    a lot, and it is concentrated exactly where the user is reporting artefacts
  - loose crumbs: separate pieces too small to be a sherd
"""
import sys
from pathlib import Path

import numpy as np
import trimesh


def terracotta_faces(m):
    col = getattr(m.visual, "vertex_colors", None)
    if col is None or len(col) != len(m.vertices):
        return None
    rgb = np.asarray(col)[:, :3].astype(int)
    sel = ((rgb[:, 0] - (rgb[:, 1] + rgb[:, 2]) / 2) > 25) & (rgb.mean(1) > 45)
    F = np.asarray(m.faces)
    return np.where(sel[F].all(axis=1))[0]


def report(tag, path, mm_per_unit):
    m = trimesh.load(path, process=False)
    if isinstance(m, trimesh.Scene):
        m = trimesh.util.concatenate(list(m.geometry.values()))
    fi = terracotta_faces(m)
    if fi is None or len(fi) < 100:
        print(f"{tag}: no usable colour"); return
    # Build the subset by hand. trimesh.submesh() on a multi-million-vertex scene mesh
    # allocates enough to be killed outright on a login node, and this is a few lines.
    F = np.asarray(m.faces)[fi]
    used = np.unique(F)
    remap = np.full(len(m.vertices), -1, np.int64)
    remap[used] = np.arange(len(used))
    s = trimesh.Trimesh(vertices=np.asarray(m.vertices)[used], faces=remap[F],
                        process=False)
    del m, F

    area_cm2 = s.area * mm_per_unit ** 2 / 100.0
    # An edge used by exactly one face is an open boundary: a tear, or a genuine rim.
    e = s.edges_sorted
    uniq, cnt = np.unique(e, axis=0, return_counts=True)
    b = uniq[cnt == 1]
    blen = np.linalg.norm(s.vertices[b[:, 0]] - s.vertices[b[:, 1]], axis=1).sum() * mm_per_unit

    comps = s.split(only_watertight=False)
    crumbs = [c for c in comps if len(c.vertices) < 500]

    print(f"\n{tag}")
    print(f"  {area_cm2:.0f} cm2 of sherd, in {len(comps)} separate pieces "
          f"({len(crumbs)} of them crumbs under 500 vertices)")
    print(f"  torn boundary: {blen/10:.0f} cm of open edge "
          f"= {blen/10/area_cm2:.2f} cm of tear per cm2 of surface")
    return blen / 10 / area_cm2


if __name__ == "__main__":
    out = {}
    for arg in sys.argv[1:]:
        tag, rest = arg.split("=", 1)
        path, mm = rest.split(":")
        out[tag] = report(tag, Path(path), float(mm))
    out = {k: v for k, v in out.items() if v is not None}
    if len(out) >= 2:
        ks = list(out)
        print(f"\ntorn edge relative to {ks[0]}:")
        for k in ks:
            print(f"  {k:<26} {out[k]/out[ks[0]]:5.2f}x")
