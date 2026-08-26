"""Summarise a mesh: size, connected pieces, and the colour of each piece.

Why not trimesh.split(): it materialises a full copy of every connected component
and has been OOM-killed twice on meshes of this size, once taking a job's whole
report with it after the reconstruction had already succeeded. scipy's
connected_components runs on the edge list alone and gives the same answer for a
fraction of the memory.

Colour is reported because on this material it separates the two things a piece
count cannot: a terracotta piece is a sherd, a grey or blue one is the mounting
rig or its clamp pads. Redness is R minus the mean of G and B -- the carved A03
sherds run +7 to +27, the rig runs about -5.

None of this says whether the break surfaces are any good. That needs a render at
a scale which resolves a fracture ridge. This only catches the obvious failures.
"""
import argparse

import numpy as np
import trimesh
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components


def load(path):
    m = trimesh.load(path, process=False)
    if isinstance(m, trimesh.Scene):
        m = trimesh.util.concatenate(list(m.geometry.values()))
    return m


def report(m, name, min_vertices=200, top=15, expect_pieces=None):
    V, F = np.asarray(m.vertices), np.asarray(m.faces)
    ext = V.max(0) - V.min(0)
    print(f"\n=== {name} ===")
    print(f"  {len(V):,} vertices, {len(F):,} faces")
    print(f"  extent {ext[0]:.1f} x {ext[1]:.1f} x {ext[2]:.1f}")

    e = np.vstack([F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]])
    g = coo_matrix((np.ones(len(e), np.int8), (e[:, 0], e[:, 1])), shape=(len(V), len(V)))
    n, lab = connected_components(g, directed=False)
    cnt = np.bincount(lab, minlength=n)
    big = np.nonzero(cnt >= min_vertices)[0]
    order = big[np.argsort(-cnt[big])]
    print(f"  {n:,} connected pieces, {len(big)} of them over {min_vertices} vertices")

    try:
        C = np.asarray(m.visual.vertex_colors)[:, :3].astype(float)
    except Exception:
        C = None

    print("   #     span   vertices   mean colour (R G B)   redness")
    for i, k in enumerate(order[:top]):
        sel = lab == k
        Vk = V[sel]
        span = (Vk.max(0) - Vk.min(0)).max()
        if C is not None:
            c = C[sel].mean(0)
            col = f"({c[0]:5.0f} {c[1]:5.0f} {c[2]:5.0f})   {c[0] - (c[1] + c[2]) / 2:+5.0f}"
        else:
            col = "(no vertex colour)"
        print(f"  {i + 1:>2}  {span:7.1f}   {cnt[k]:>8,}   {col}")

    # The two failures worth shouting about, both of which have happened here.
    if len(order):
        biggest = (V[lab == order[0]].max(0) - V[lab == order[0]].min(0)).max()
        if biggest > 0.8 * ext.max():
            print(f"  NOTE: the largest piece spans {biggest:.1f}, nearly the whole mesh. "
                  f"Separate objects are fused into one.")
    if expect_pieces is not None and len(big) != expect_pieces:
        print(f"  NOTE: {len(big)} pieces over {min_vertices} vertices, expected "
              f"{expect_pieces}.")
    return len(big)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("meshes", nargs="+")
    p.add_argument("--min-vertices", type=int, default=200)
    p.add_argument("--top", type=int, default=15)
    p.add_argument("--expect-pieces", type=int, default=None)
    a = p.parse_args()
    for path in a.meshes:
        report(load(path), path, a.min_vertices, a.top, a.expect_pieces)
    print("\nLOOK AT IT before believing any number above.")
