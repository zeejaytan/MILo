"""Delete geometry that is not inside the object's outline in the photographs.

This is visual-hull carving (Laurentini 1994) used as a cleanup rather than a
reconstruction: a point that belongs to the object must project INSIDE the object's
silhouette in every view that sees it, because the silhouette is the object's outline. A
point that falls outside the outline in view after view cannot be part of the object,
whatever produced it.

WHAT IT IS FOR HERE, two problems with one instrument:

  SPIKES on the photogrammetry meshes. Masking the clamps creates a hard depth
      discontinuity right at the sherd's edge, which is the least constrained place for
      stereo matching. A pixel INSIDE the sherd mask given a wrong depth lands in 3D beside
      the sherd -- the classic flying-pixel artefact. Those points have real dense support,
      so no "remove unsupported geometry" filter finds them, but they sit outside the
      silhouette and this does.

  RIG AND ROOM on a MILo mesh trained WITHOUT masks. Masked training starves the model:
      the loss replaces everything outside the mask with flat background, 96% of the frame
      becomes trivially easy, and gradient-driven densification barely fires. A03 came out
      with 4.2 MB of Gaussians against A02's 95.6 MB, 23x fewer. Training on the scene and
      carving afterwards keeps the density and still ends with only the object.

WHY NOT SIMPLY "OUTSIDE IN ANY ONE VIEW". Strict carving is the textbook rule and it is too
brittle here: one bad mask frame would eat real sherd. A vertex is dropped only when it
falls outside the mask in more than --tol of the views that see it at all.

SELF-CHECK, because the failure is silent. Projecting with the undistorted cameras while
indexing masks at the ORIGINAL photograph resolution scales every coordinate by ~1.74 and
quietly puts most of the object "outside" -- it would carve the mesh away and report a
tidy-looking number. So the mask size is compared against the camera size up front, and the
median support across all vertices is checked: on a real mesh it is near 1.0, and anything
low means the projection is wrong rather than the mesh being bad.

Usage:
    python silhouette_filter.py --mesh in.ply --out out.ply \\
        --dense <dense workspace> --masks <undistorted mask dir> [--tol 0.10]
"""
import argparse
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from measure_base import read_cameras, read_images, project          # noqa: E402

# Below this median support the projection is wrong, not the mesh. A correct setup puts
# essentially every vertex of a real object inside the outline in essentially every view.
SANITY_MEDIAN_SUPPORT = 0.60


def read_ply_mesh(path):
    """Vertices, faces and the raw header, keeping the header so it can be re-emitted."""
    raw = b""
    with open(path, "rb") as f:
        while b"end_header" not in raw:
            line = f.readline()
            if not line:
                sys.exit(f"{path}: no end_header")
            raw += line
        body = f.read()
    hdr = raw.decode("ascii", "replace")
    if "format binary_little_endian" not in hdr:
        sys.exit(f"{path}: only binary_little_endian PLY is handled")

    SZ = {"float": 4, "float32": 4, "double": 8, "uchar": 1, "uint8": 1, "char": 1,
          "int": 4, "int32": 4, "uint": 4, "uint32": 4, "short": 2, "ushort": 2}
    nv = nf = 0
    vprops, cur, fprop = [], None, None
    for l in hdr.splitlines():
        w = l.split()
        if not w:
            continue
        if w[0] == "element":
            cur = w[1]
            if cur == "vertex":
                nv = int(w[2])
            elif cur == "face":
                nf = int(w[2])
        elif w[0] == "property" and cur == "vertex" and w[1] != "list":
            vprops.append((w[1], w[2]))
        elif w[0] == "property" and cur == "face" and w[1] == "list":
            fprop = (w[2], w[3])          # count type, index type
    stride = sum(SZ[t] for t, _ in vprops)
    varr = np.frombuffer(body[:nv * stride], np.uint8).reshape(nv, stride)
    off = 0
    cols = {}
    for t, n in vprops:
        cols[n] = varr[:, off:off + SZ[t]].copy().view("<f4" if SZ[t] == 4 and
                                                       t.startswith("float") else np.uint8)
        off += SZ[t]
    V = np.stack([cols[c].ravel() for c in ("x", "y", "z")], 1).astype(np.float64)

    faces = None
    if nf:
        ctype, itype = fprop
        cs, isz = SZ[ctype], SZ[itype]
        fb = body[nv * stride:]
        # Assume a constant vertex count per face (3 for every mesh this pipeline makes).
        k = fb[0]
        rec = cs + k * isz
        fa = np.frombuffer(fb[:nf * rec], np.uint8).reshape(nf, rec)
        if not (fa[:, 0] == k).all():
            sys.exit("mixed face sizes; expected triangles throughout")
        faces = fa[:, cs:].copy().view("<u4" if isz == 4 else "<i4").reshape(nf, k).astype(np.int64)
    return V, faces, varr, stride, hdr, vprops


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mesh", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--dense", required=True, type=Path,
                    help="dense workspace: sparse/ and images/ inside")
    ap.add_argument("--masks", required=True, type=Path,
                    help="UNDISTORTED masks matching the dense images (dense/masks/colmap)")
    ap.add_argument("--tol", type=float, default=0.40,
                    help="drop a vertex when it falls outside the outline in more than this "
                         "fraction of the views that see it. 0.40 is deliberately not a "
                         "tight visual hull: masking the clamps means a real sherd point is "
                         "occluded by a MASKED occluder in some views and reads as outside, "
                         "so honest surface never scores 1.0. On A03 it sits at 0.80-1.00 "
                         "with a flat tail below 0.65. Check the histogram this prints "
                         "before trusting the default on a new tree.")
    ap.add_argument("--every", type=int, default=2, help="use every Nth view")
    ap.add_argument("--min-piece", type=int, default=200,
                    help="delete leftover fragments smaller than this many vertices")
    ap.add_argument("--scale-mm-per-unit", type=float, default=None,
                    help="if the mesh is already in mm, give the factor so vertices can be "
                         "put back into the reconstruction units the cameras use")
    args = ap.parse_args()

    V, F, varr, stride, hdr, vprops = read_ply_mesh(args.mesh)
    print(f"{args.mesh.name}: {len(V):,} vertices, {0 if F is None else len(F):,} faces")

    P = V / args.scale_mm_per_unit if args.scale_mm_per_unit else V
    cams = read_cameras(args.dense / "sparse" / "cameras.bin")
    imgs = read_images(args.dense / "sparse" / "images.bin")

    # SIZE CHECK FIRST. Masks at the original photograph resolution with undistorted
    # cameras scales every coordinate by ~1.74 and silently carves the object away.
    cam0 = cams[imgs[0]["cam"]]
    m0 = args.masks / (imgs[0]["name"] + ".png")
    if not m0.exists():
        sys.exit(f"no mask for the first view at {m0}")
    mw, mh = Image.open(m0).size
    print(f"  camera {cam0['w']}x{cam0['h']}   mask {mw}x{mh}")
    if (mw, mh) != (cam0["w"], cam0["h"]):
        sys.exit(f"Mask size {mw}x{mh} does not match the camera {cam0['w']}x{cam0['h']}.\n"
                 "These must be the UNDISTORTED masks that go with this dense workspace "
                 "(usually <dense>/masks/colmap), not the masks made on the original "
                 "photographs. Projecting into the wrong size carves the object away and "
                 "reports a tidy number while doing it.")

    inside = np.zeros(len(P)); seen = np.zeros(len(P))
    views = imgs[::max(1, args.every)]
    for k, im in enumerate(views):
        mp = args.masks / (im["name"] + ".png")
        if not mp.exists():
            continue
        M = np.asarray(Image.open(mp).convert("L")) > 127
        px, ok = project(P, im, cams[im["cam"]])
        H, W = M.shape
        u = np.round(px[:, 0]).astype(int); v = np.round(px[:, 1]).astype(int)
        vis = ok & (u >= 0) & (u < W) & (v >= 0) & (v < H)
        seen += vis
        inside[vis] += M[v[vis], u[vis]]
        if (k + 1) % 20 == 0:
            print(f"  {k+1}/{len(views)} views", flush=True)

    support = inside / np.maximum(seen, 1)
    med = float(np.median(support))
    print(f"\n  support (fraction of views placing a vertex inside the outline): "
          f"median {med:.3f}, mean {support.mean():.3f}")
    # PRINT THE DISTRIBUTION, because the threshold is a judgement about this tree and
    # should be made while looking at it. Real surface forms the bulk near 1.0; what is
    # worth carving is the flat tail. A tree with no tail has nothing to carve.
    h, e = np.histogram(support, bins=20, range=(0, 1))
    print("  distribution (the left tail is what gets carved):")
    for c, lo in zip(h, e[:-1]):
        bar = "#" * int(46 * c / max(h.max(), 1))
        mark = "  <- cut here" if lo <= 1.0 - args.tol < lo + 0.05 else ""
        print(f"    {lo:.2f}-{lo+0.05:.2f} {bar:<46} {c:>8,}{mark}")
    if med < SANITY_MEDIAN_SUPPORT:
        sys.exit(f"Median support {med:.3f} is below {SANITY_MEDIAN_SUPPORT}. On a real mesh "
                 "nearly every vertex sits inside the outline in nearly every view, so this "
                 "says the projection is wrong -- wrong masks, wrong model, or a mesh in "
                 "different units (see --scale-mm-per-unit). Refusing to carve.")

    keep = (seen >= 3) & (support >= 1.0 - args.tol)
    print(f"  keeping {keep.sum():,} of {len(V):,} vertices "
          f"({100*keep.mean():.1f}%), dropping {(~keep).sum():,}")

    if F is not None:
        fkeep = keep[F].all(1)
        remap = -np.ones(len(V), np.int64)
        remap[keep] = np.arange(keep.sum())
        F2 = remap[F[fkeep]]
        print(f"  keeping {fkeep.sum():,} of {len(F):,} faces ({100*fkeep.mean():.1f}%)")
    else:
        F2 = None

    # Prune the fragments the carving leaves behind.
    if F2 is not None and len(F2) and args.min_piece > 0:
        import trimesh
        mesh = trimesh.Trimesh(vertices=V[keep], faces=F2, process=False)
        comps = mesh.split(only_watertight=False)
        big = [c for c in comps if len(c.vertices) >= args.min_piece]
        if big and len(big) < len(comps):
            mesh = trimesh.util.concatenate(big)
            print(f"  dropped {len(comps)-len(big)} fragment(s) under {args.min_piece} "
                  f"vertices; {len(big)} pieces remain")
        Vk, F2 = np.asarray(mesh.vertices), np.asarray(mesh.faces)
    else:
        Vk = V[keep]

    ext_before = np.ptp(V, 0); ext_after = np.ptp(Vk, 0)
    print(f"\n  extent before {ext_before[0]:.1f} x {ext_before[1]:.1f} x {ext_before[2]:.1f}")
    print(f"  extent after  {ext_after[0]:.1f} x {ext_after[1]:.1f} x {ext_after[2]:.1f}")
    shrink = 1 - ext_after / np.maximum(ext_before, 1e-9)
    print(f"  shrank by {100*shrink[0]:.1f}%, {100*shrink[1]:.1f}%, {100*shrink[2]:.1f}% "
          "-- a large drop here means real surface was carved, not just spikes")

    import trimesh
    out = trimesh.Trimesh(vertices=Vk, faces=F2, process=False)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    out.export(args.out)
    print(f"  wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
