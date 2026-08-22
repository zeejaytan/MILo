"""Does what the reconstruction STARTED with predict how finely each sherd ended up modelled?

Size has just failed this test: across 25 fragments in three captures the correlation
between how big a fragment is and how finely it is modelled is -0.07, i.e. nothing.

This asks the next candidate, and asks it the same way -- against all 25 fragments, not
against a hand-picked few. Gaussian splatting does not start from nothing: it starts from
the sparse points COLMAP recovered when it worked out where the camera was. Those points
are the seeds that later split and multiply into the surface. A fragment that COLMAP
matched few features on starts with few seeds.

Two numbers per fragment:
  seeds per cm2       -- how many sparse points landed on that fragment's surface
  views per seed      -- how many photographs each of those points was matched in
                         (a point seen in 30 photographs is pinned down; one seen in 3
                         is a guess, and the optimiser has little reason to refine it)

If neither predicts the outcome, the cause is not in the starting point either, and that
is worth knowing before any more GPU time is spent.
"""
import struct
import sys
from pathlib import Path

import numpy as np
import trimesh
from scipy.spatial import cKDTree

MIN_VERTS = 400
MIN_AREA_CM2 = 0.8
NEAR_MM = 4.0        # a seed counts as "on" a fragment within this distance of its surface


def read_points3D(path):
    """xyz plus track length. The repo's reader drops the track, which is the half of the
    record that says how well observed a point is."""
    xyz, ntracks = [], []
    with open(path, "rb") as f:
        n = struct.unpack("<Q", f.read(8))[0]
        for _ in range(n):
            d = struct.unpack("<QdddBBBd", f.read(43))
            t = struct.unpack("<Q", f.read(8))[0]
            f.read(8 * t)
            xyz.append(d[1:4])
            ntracks.append(t)
    return np.array(xyz), np.array(ntracks, float)


def pieces(path, mm):
    m = trimesh.load(path, process=False)
    if isinstance(m, trimesh.Scene):
        m = trimesh.util.concatenate(list(m.geometry.values()))
    col = np.asarray(m.visual.vertex_colors)[:, :3].astype(int)
    sel = ((col[:, 0] - (col[:, 1] + col[:, 2]) / 2) > 25) & (col.mean(1) > 45)
    F = np.asarray(m.faces)
    Fs = F[sel[F].all(axis=1)]
    used = np.unique(Fs)
    remap = np.full(len(m.vertices), -1, np.int64)
    remap[used] = np.arange(len(used))
    s = trimesh.Trimesh(vertices=np.asarray(m.vertices)[used], faces=remap[Fs],
                        process=False)
    del m, F, Fs
    out = []
    for c in s.split(only_watertight=False):
        a = c.area * mm ** 2 / 100.0
        if len(c.vertices) >= MIN_VERTS and a >= MIN_AREA_CM2:
            out.append((a, np.asarray(c.vertices)))
    return out


def run(tag, mesh, sparse, mm):
    P, trk = read_points3D(sparse)
    rows = []
    for area, V in pieces(mesh, mm):
        tree = cKDTree(V)
        d, _ = tree.query(P, workers=-1)
        on = d * mm <= NEAR_MM
        rows.append(dict(cap=tag, area=area, dens=len(V) / area,
                         seeds=on.sum() / area,
                         views=float(trk[on].mean()) if on.sum() else 0.0,
                         nseed=int(on.sum())))
    print(f"\n{tag}   ({len(P)} sparse points in the whole scene)")
    print(f"  {'area cm2':>9} {'verts/cm2':>10} {'seeds/cm2':>10} {'views/seed':>11}")
    for r in sorted(rows, key=lambda r: r["area"]):
        print(f"  {r['area']:9.1f} {r['dens']:10.0f} {r['seeds']:10.1f} {r['views']:11.1f}")
    return rows


if __name__ == "__main__":
    allr = []
    for arg in sys.argv[1:]:
        tag, rest = arg.split("=", 1)
        mesh, sparse, mm = rest.split(",")
        allr += run(tag, mesh, sparse, float(mm))

    D = np.array([r["dens"] for r in allr])
    print("\n" + "=" * 64)
    print(f"across all {len(allr)} fragments in {len(set(r['cap'] for r in allr))} captures:")
    for k, lab in (("seeds", "seeds per cm2"), ("views", "views per seed"),
                   ("area", "fragment area")):
        X = np.array([r[k] for r in allr])
        print(f"  final sampling density vs {lab:<16} r = {np.corrcoef(X, D)[0,1]:+.2f}")

    print("\n  per capture (median over its fragments):")
    for cap in dict.fromkeys(r["cap"] for r in allr):
        rs = [r for r in allr if r["cap"] == cap]
        print(f"    {cap:<6} n={len(rs):2d}  verts/cm2 {np.median([r['dens'] for r in rs]):6.0f}"
              f"   seeds/cm2 {np.median([r['seeds'] for r in rs]):6.1f}"
              f"   views/seed {np.median([r['views'] for r in rs]):5.1f}")

    big = [r for r in allr if r["area"] >= 20]
    print(f"\n  like for like -- fragments over 20 cm2 only ({len(big)}):")
    for cap in dict.fromkeys(r["cap"] for r in big):
        v = [r["dens"] for r in big if r["cap"] == cap]
        print(f"    {cap:<6} n={len(v)}  verts/cm2 {' '.join(f'{x:.0f}' for x in sorted(v))}")
