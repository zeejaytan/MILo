"""How finely is the SHERD surface sampled, in each mesh, per square centimetre?

Median edge length over a whole scene mesh is not this number. Most of a MILo scene mesh
is backdrop and clamp, and those are large smooth surfaces that drag the median wherever
they happen to sit -- which is how a mesh can look "finer" scene-wide while being coarser
on the only surface anyone cares about.

So: keep only the terracotta-coloured faces, and report vertices per square centimetre of
actual sherd surface, plus the spacing that implies. Colour is the one thing that reliably
separates sherd from grey clamp and black backdrop in every one of these meshes.
"""
import sys
from pathlib import Path

import numpy as np
import trimesh


def terracotta(m):
    col = getattr(m.visual, "vertex_colors", None)
    if col is None or len(col) != len(m.vertices):
        return None
    rgb = np.asarray(col)[:, :3].astype(int)
    red = (rgb[:, 0] - (rgb[:, 1] + rgb[:, 2]) / 2) > 25
    bright = rgb.mean(1) > 45
    return red & bright


def report(tag, path, mm_per_unit):
    m = trimesh.load(path, process=False)
    if isinstance(m, trimesh.Scene):
        m = trimesh.util.concatenate(list(m.geometry.values()))
    sel = terracotta(m)
    if sel is None:
        print(f"{tag}: no vertex colour in {path} -- cannot separate sherd from clamp")
        return
    F = np.asarray(m.faces)
    fsel = sel[F].all(axis=1)
    if fsel.sum() < 100:
        print(f"{tag}: almost no terracotta faces ({fsel.sum()})")
        return
    sub = m.submesh([np.where(fsel)[0]], append=True, repair=False)

    area_cm2 = sub.area * mm_per_unit ** 2 / 100.0
    nv = len(sub.vertices)
    dens = nv / area_cm2
    spacing = 10.0 / np.sqrt(dens)          # mm between neighbours at that density

    e = sub.edges_unique
    el = np.linalg.norm(sub.vertices[e[:, 0]] - sub.vertices[e[:, 1]], axis=1) * mm_per_unit

    print(f"\n{tag}")
    print(f"  {nv:,} vertices over {area_cm2:.0f} cm2 of sherd surface")
    print(f"  --> {dens:.0f} vertices per cm2, about {spacing:.2f} mm apart")
    print(f"      (median triangle edge {np.median(el):.3f} mm, "
          f"90th percentile {np.percentile(el, 90):.3f} mm)")
    return dens


if __name__ == "__main__":
    d = {}
    for arg in sys.argv[1:]:
        tag, path, mm = arg.split("=", 1)[0], *arg.split("=", 1)[1].split(":")
        d[tag] = report(tag, Path(path), float(mm))
    vals = {k: v for k, v in d.items() if v}
    if len(vals) >= 2:
        ks = list(vals)
        base = vals[ks[0]]
        print("\nsherd surface sampling, relative to " + ks[0] + ":")
        for k in ks:
            print(f"  {k:<28} {vals[k]/base:5.2f}x the vertices per cm2 "
                  f"({np.sqrt(base/vals[k]):.2f}x coarser spacing)")
