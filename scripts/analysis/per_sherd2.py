"""Every sherd-sized piece in all three captures, so size can be tested rather than guessed.

The previous pass kept only pieces above 3000 vertices and 3 cm2, which left three per
capture -- few enough that a correlation is meaningless, and the two captures duly gave
opposite signs. This lowers the thresholds and pools all three captures, so the question
"does a bigger fragment get sampled more finely" has enough pieces behind it to answer.

Reports each piece with the things that could plausibly explain its sampling density, so
whatever does explain it can be seen rather than assumed.
"""
import sys
from pathlib import Path

import numpy as np
import trimesh

MIN_VERTS = 400
MIN_AREA_CM2 = 0.8


def load_sherds(path, mm):
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
    s.visual.vertex_colors = col[used]
    del m, F, Fs

    rows = []
    for c in s.split(only_watertight=False):
        a = c.area * mm ** 2 / 100.0
        if len(c.vertices) < MIN_VERTS or a < MIN_AREA_CM2:
            continue
        e = np.sort(np.ptp(c.vertices, 0)) * mm
        rows.append(dict(area=a,
                         dens=len(c.vertices) / a,
                         verts=len(c.vertices),
                         longest=e[2],
                         thinness=e[2] / max(e[0], 1e-6),
                         bright=float(np.asarray(c.visual.vertex_colors)[:, :3].mean())))
    return rows


if __name__ == "__main__":
    allr = []
    for arg in sys.argv[1:]:
        tag, rest = arg.split("=", 1)
        path, mm = rest.split(":")
        rows = load_sherds(Path(path), float(mm))
        for r in rows:
            r["cap"] = tag
        allr += rows
        print(f"\n{tag}: {len(rows)} pieces")
        print(f"  {'area cm2':>9} {'longest mm':>11} {'thin':>6} {'bright':>7} {'verts/cm2':>10}")
        for r in sorted(rows, key=lambda r: r["area"]):
            print(f"  {r['area']:9.1f} {r['longest']:11.0f} {r['thinness']:6.1f} "
                  f"{r['bright']:7.0f} {r['dens']:10.0f}")
        if len(rows) >= 4:
            A = np.array([r["area"] for r in rows]); D = np.array([r["dens"] for r in rows])
            print(f"  within this capture, density vs area: r = {np.corrcoef(A, D)[0,1]:+.2f} "
                  f"(n={len(rows)})")

    print("\n" + "=" * 64)
    print(f"pooled, {len(allr)} pieces across {len(set(r['cap'] for r in allr))} captures")
    D = np.array([r["dens"] for r in allr])
    for k in ("area", "longest", "thinness", "bright"):
        X = np.array([r[k] for r in allr])
        print(f"  density vs {k:<9} r = {np.corrcoef(X, D)[0,1]:+.2f}")
    print("\n  density by capture:")
    for cap in dict.fromkeys(r["cap"] for r in allr):
        d = np.array([r["dens"] for r in allr if r["cap"] == cap])
        a = np.array([r["area"] for r in allr if r["cap"] == cap])
        print(f"    {cap:<6} n={len(d):2d}  density {d.min():.0f}-{d.max():.0f} "
              f"(median {np.median(d):.0f})   area {a.min():.1f}-{a.max():.1f} cm2")
