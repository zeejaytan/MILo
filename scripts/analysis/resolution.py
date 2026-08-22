"""How fine is the surface, in millimetres, on the sherds themselves?

Total vertex counts across whole scene meshes are not comparable: most of a MILo scene
mesh is rig and room. This measures the thing that matters -- the spacing between
neighbouring vertices ON A SHERD -- and reports it in mm, so it can be set against the
size of a fracture ridge.
"""
import sys
import numpy as np
import trimesh

MM_PER_UNIT = 373.73          # A03, from the base plate (measure_base.py)


def report(path, label, mm_per_unit=MM_PER_UNIT, max_pieces=6):
    m = trimesh.load(path, process=False)
    if isinstance(m, trimesh.Scene):
        m = trimesh.util.concatenate(list(m.geometry.values()))
    ext = np.ptp(m.vertices, 0)
    print(f"\n{label}")
    print(f"  {len(m.vertices):,} vertices, extent "
          f"{ext[0]:.2f} x {ext[1]:.2f} x {ext[2]:.2f} units "
          f"= {ext[0]*mm_per_unit:.0f} x {ext[1]*mm_per_unit:.0f} x {ext[2]*mm_per_unit:.0f} mm")

    comps = m.split(only_watertight=False)
    comps = sorted(comps, key=lambda c: len(c.vertices), reverse=True)
    # The base plate is flat and much wider than a sherd; skip anything whose smallest
    # extent is under a tenth of its largest AND which is large -- that is the board.
    rows = []
    for c in comps:
        if len(c.vertices) < 2000:
            continue
        e = np.sort(np.ptp(c.vertices, 0))
        flat = e[0] / max(e[2], 1e-9)
        kind = "PLATE" if (flat < 0.06 and e[2] * mm_per_unit > 150) else "sherd"
        # median triangle edge length -> vertex spacing
        el = np.linalg.norm(c.vertices[c.edges_unique[:, 0]] - c.vertices[c.edges_unique[:, 1]], axis=1)
        rows.append((kind, len(c.vertices), e[2] * mm_per_unit,
                     np.median(el) * mm_per_unit, c.area * mm_per_unit ** 2))
    sherds = [r for r in rows if r[0] == "sherd"][:max_pieces]
    print(f"  {'':4} {'verts':>9} {'longest mm':>11} {'spacing mm':>11} {'area mm2':>10} {'v/mm2':>8}")
    for k, n, lo, sp, ar in sherds:
        print(f"  {k:4} {n:9,} {lo:11.1f} {sp:11.3f} {ar:10.0f} {n/max(ar,1e-9):8.2f}")
    if sherds:
        sp = np.array([r[3] for r in sherds])
        print(f"  -> median vertex spacing on sherds: {np.median(sp):.3f} mm")
    plate = [r for r in rows if r[0] == "PLATE"]
    for k, n, lo, sp, ar in plate[:1]:
        print(f"  {k:4} {n:9,} {lo:11.1f} {sp:11.3f} {ar:10.0f} {n/max(ar,1e-9):8.2f}")


if __name__ == "__main__":
    for arg in sys.argv[1:]:
        label, path = arg.split("=", 1)
        report(path, label)
