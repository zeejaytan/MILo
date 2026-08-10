#!/usr/bin/env python3
"""
Pull the sherds out of a reconstructed scene by SHAPE, not by size.

Why this exists. The photogrammetry pipeline selected connected components by vertex
count (min_vertices: 100000). On capture 16062025 that kept exactly two pieces — the
laboratory clamp rig and the backdrop — and discarded every actual sherd, because a
sherd came out at 18k-82k vertices while the rig, seen from every photograph in the
capture, came out at 232k. The validation reported PASS. Counting vertices measures how
well something was photographed, not whether it is pottery.

Shape is the right thing to judge on, because unlike vertex count it does not depend on
how many views a component happened to be seen from. But be clear about how far this
gets: it currently rejects the obvious furniture and no more. Two measures were tried.

  THINNESS — smallest principal extent over largest. USED, provisionally. It separated
    the rig (0.49) and backdrop (0.68) from the sherds (0.12-0.17) on capture 16062025.
    Its known bias is CURVATURE: it measures a bounding box, so a strongly curved piece
    of pot wall fills a chunky box and can be rejected as blocky, while a stray sliver of
    noise scores like a perfect sherd.

  WALL THICKNESS — distance through the material from the surface along the inward
    normal. It would be curvature-independent, which is why it was tried. It DOES NOT
    WORK on photogrammetric output: these meshes are hollow shells, so the clamp bar
    measured 0.023 of its length, thinner than any sherd. It is a skin around a tube.
    Still computed and reported, since it is the right measure for a closed scan.

So: treat the selection as a first pass, and look at the contact sheet. Thresholds have
NOT been tuned, deliberately — the only mesh available to tune them on is a
reconstruction already known to be faulty, and a threshold fitted to that is fitted to
the fault.

Usage:
    python scripts/extract_sherds.py --mesh scene_refined_mesh.ply --out sherds/
    python scripts/extract_sherds.py --mesh mesh.ply --out sherds/ --max-thinness 0.2

Writes: sherd_XXX.ply per accepted component, components.csv for every component
(accepted or not, with the reason), and contact_sheet.png so the decision can be checked
by eye rather than trusted.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import trimesh
from PIL import Image

# Deliberately generous. The cost of admitting a doubtful component is one extra file to
# look at; the cost of rejecting a real sherd is losing material that cannot be
# re-excavated. Err towards keeping, and look at the contact sheet.
DEFAULT_MAX_THINNESS = 0.20        # smallest/largest principal extent (provisional)
DEFAULT_MIN_VERTICES = 2000
DEFAULT_THICKNESS_RAYS = 400


def principal_extents(v: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """Extents along the component's own principal axes, largest first."""
    c = v - v.mean(0)
    sample = c if len(c) <= 50_000 else c[rng.choice(len(c), 50_000, replace=False)]
    _, _, vt = np.linalg.svd(sample, full_matrices=False)
    p = c @ vt.T
    return np.sort(p.max(0) - p.min(0))[::-1]


def wall_thickness(m: trimesh.Trimesh, rng: np.random.Generator, n_rays: int) -> float:
    """
    Median distance through the material, measured from the surface along -normal.

    Curvature-independent, which is the whole point: a curved sherd and a flat one both
    report their wall, whereas a bounding-box measure calls the curved one solid. Rays
    that escape without hitting anything are dropped — those start on a break face or a
    rim, where "thickness" is not defined.
    """
    n = min(n_rays, len(m.vertices))
    idx = rng.choice(len(m.vertices), n, replace=False)
    origins = np.asarray(m.vertices)[idx]
    normals = np.asarray(m.vertex_normals)[idx]
    eps = float(np.linalg.norm(m.extents)) * 1e-5
    # Deliberately NOT wrapped in a bare except. An earlier version caught everything and
    # returned nan, so a missing `rtree` (the ray engine's spatial index) was reported as
    # "no measurable wall" for every single component — and the script then accepted the
    # clamp rig as a sherd. A broken instrument must be distinguishable from a real
    # measurement of nothing, so import errors are left to propagate loudly.
    loc, ray_idx, _ = m.ray.intersects_location(
        ray_origins=origins - normals * eps,
        ray_directions=-normals,
        multiple_hits=False,
    )
    if len(ray_idx) < max(8, n * 0.02):
        # Almost nothing hit the far side: an open sheet, not a closed shell.
        return float("nan")
    return float(np.median(np.linalg.norm(loc - origins[ray_idx], axis=1)))


def describe_component(m: trimesh.Trimesh, rng: np.random.Generator, n_rays: int) -> dict:
    ext = principal_extents(np.asarray(m.vertices), rng)
    longest = float(ext[0]) if ext[0] > 0 else 1e-9
    t = wall_thickness(m, rng, n_rays)
    return {
        "vertices": int(len(m.vertices)),
        "faces": int(len(m.faces)),
        "area": float(m.area),
        "extent_max": float(ext[0]),
        "extent_min": float(ext[2]),
        "thinness": float(ext[2] / longest),
        "wall_thickness": t,
        "rel_thickness": float(t / longest) if np.isfinite(t) else float("nan"),
    }


def judge(d: dict, args) -> str:
    """
    Return "" if the component looks like a sherd, else why it does not.

    THRESHOLDS HERE ARE PROVISIONAL, and the honest state of this test is:

      * Bounding-box thinness separates the rig (0.49) and backdrop (0.68) from the
        sherds (0.12-0.17) on capture 16062025 — but it penalises CURVATURE, so a
        strongly curved piece of pot wall fills a chunky box and can be rejected.
      * Wall thickness, which would be curvature-independent, does NOT work here:
        photogrammetry reconstructs everything as a hollow shell, so the clamp bar
        measured 0.023 of its length — thinner than any sherd. It is a skin around a
        tube. It is still reported below, because it is the right measure for a closed
        scan and it costs nothing to compute.

    So this rejects the obvious furniture and nothing more. The contact sheet is not
    decoration: it is how you find out whether the threshold suited YOUR capture. Any
    threshold tuned on a reconstruction known to be faulty is fitted to the fault.
    """
    if d["vertices"] < args.min_vertices:
        return f"too few vertices ({d['vertices']})"
    if d["thinness"] > args.max_thinness:
        return f"too blocky for a sherd (thinness {d['thinness']:.2f})"
    return ""


# --------------------------------------------------------------------------------------
# A small software renderer, so the decision can be looked at on a headless node.
# --------------------------------------------------------------------------------------

def render_tile(m: trimesh.Trimesh, size: int = 220) -> np.ndarray:
    v = np.asarray(m.vertices, np.float64)
    f = np.asarray(m.faces, np.int64)
    c = (v.min(0) + v.max(0)) / 2
    s = (v.max(0) - v.min(0)).max() or 1.0
    v = (v - c) / s
    xy = v[:, :2] * (size * 0.40) + size / 2
    z = v[:, 2]

    light = np.array([-0.94, 0.33, 0.08])
    light /= np.linalg.norm(light)
    # Two-sided: scanned meshes have inconsistently wound normals, and one-sided shading
    # renders those faces black — holes that are not in the geometry.
    shade = 0.12 + 0.88 * np.abs(m.face_normals @ light) ** 0.75

    img = np.zeros((size, size), np.float32)
    zbuf = np.full((size, size), -np.inf, np.float32)
    tri = xy[f]
    for i in np.argsort(z[f].mean(1)):
        t = tri[i]
        x0, y0 = np.maximum(np.floor(t.min(0)).astype(int), 0)
        x1, y1 = np.minimum(np.ceil(t.max(0)).astype(int), size - 1)
        if x1 <= x0 or y1 <= y0:
            xi, yi = int(t[:, 0].mean()), int(t[:, 1].mean())
            if 0 <= xi < size and 0 <= yi < size:
                img[yi, xi] = max(img[yi, xi], shade[i])
            continue
        ys, xs = np.mgrid[y0:y1 + 1, x0:x1 + 1]
        e0, e1 = t[1] - t[0], t[2] - t[0]
        den = e0[0] * e1[1] - e1[0] * e0[1]
        if abs(den) < 1e-12:
            continue
        px, py = xs - t[0, 0], ys - t[0, 1]
        u = (px * e1[1] - e1[0] * py) / den
        w = (e0[0] * py - px * e0[1]) / den
        zc = z[f[i]].mean()
        m_in = (u >= 0) & (w >= 0) & (u + w <= 1) & (zc > zbuf[y0:y1 + 1, x0:x1 + 1])
        zbuf[y0:y1 + 1, x0:x1 + 1][m_in] = zc
        img[y0:y1 + 1, x0:x1 + 1][m_in] = shade[i]
    return np.flipud((img * 255).clip(0, 255).astype(np.uint8))


def contact_sheet(items, path: Path, cols: int = 8, size: int = 220):
    """One tile per component, accepted ones marked with a bright border."""
    if not items:
        return
    rows = (len(items) + cols - 1) // cols
    sheet = np.zeros((rows * size, cols * size, 3), np.uint8)
    for i, (mesh, accepted) in enumerate(items):
        tile = render_tile(mesh, size)
        rgb = np.stack([tile] * 3, -1)
        colour = (60, 200, 90) if accepted else (170, 60, 60)
        rgb[:3, :] = colour
        rgb[-3:, :] = colour
        rgb[:, :3] = colour
        rgb[:, -3:] = colour
        r, c = divmod(i, cols)
        sheet[r * size:(r + 1) * size, c * size:(c + 1) * size] = rgb
    Image.fromarray(sheet).save(path)


def main() -> int:
    ap = argparse.ArgumentParser(description="Extract sherd-shaped components from a scene mesh")
    ap.add_argument("--mesh", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--max-thinness", type=float, default=DEFAULT_MAX_THINNESS,
                    help="smallest/largest principal extent; provisional, see judge()")
    ap.add_argument("--min-vertices", type=int, default=DEFAULT_MIN_VERTICES)
    ap.add_argument("--rays", type=int, default=DEFAULT_THICKNESS_RAYS)
    ap.add_argument("--max-tiles", type=int, default=64,
                    help="components drawn on the contact sheet, largest first")
    args = ap.parse_args()

    # Check the ray engine before doing any work. Without it every thickness comes back
    # unmeasurable, which silently degrades the whole test to "accept everything".
    try:
        probe = trimesh.creation.box((1, 1, 1))
        probe.ray.intersects_location(ray_origins=np.array([[0, 0, 2.0]]),
                                      ray_directions=np.array([[0, 0, -1.0]]))
    except Exception as exc:
        print(f"Ray casting is unavailable ({exc}).\n"
              "Wall thickness cannot be measured, and without it this script cannot tell "
              "a sherd from a clamp. Install the ray engine:\n"
              "  pip install rtree            (or: pip install embreex, which is faster)",
              file=sys.stderr)
        return 2

    rng = np.random.default_rng(0)
    scene = trimesh.load(args.mesh, process=False)
    if isinstance(scene, trimesh.Scene):
        scene = trimesh.util.concatenate(tuple(scene.geometry.values()))
    print(f"{args.mesh.name}: {len(scene.vertices):,} vertices, {len(scene.faces):,} faces")

    parts = scene.split(only_watertight=False)
    print(f"connected components: {len(parts)}")
    parts = sorted(parts, key=lambda p: -len(p.vertices))

    args.out.mkdir(parents=True, exist_ok=True)
    rows, accepted, tiles = [], [], []

    for i, p in enumerate(parts):
        d = describe_component(p, rng, args.rays)
        reason = judge(d, args)
        d["component"] = i
        d["accepted"] = not reason
        d["reason"] = reason or "sherd-shaped"
        rows.append(d)
        if not reason:
            name = f"sherd_{len(accepted) + 1:03d}.ply"
            p.export(args.out / name)
            d["file"] = name
            accepted.append(d)
        else:
            d["file"] = ""
        if len(tiles) < args.max_tiles:
            tiles.append((p, not reason))

    import csv
    with (args.out / "components.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    contact_sheet(tiles, args.out / "contact_sheet.png")

    print(f"\naccepted {len(accepted)} of {len(parts)} components as sherd-shaped")
    print(f"{'#':>4} {'verts':>9} {'wall/len':>9} {'thinness':>9}  file")
    for d in accepted[:25]:
        print(f"{d['component']:>4} {d['vertices']:>9,} {d['rel_thickness']:>9.3f} "
              f"{d['thinness']:>9.3f}  {d['file']}")

    rejected_big = [d for d in rows if not d["accepted"] and d["vertices"] >= args.min_vertices]
    if rejected_big:
        print(f"\nlargest rejected (these are the ones worth checking by eye):")
        for d in rejected_big[:8]:
            print(f"{d['component']:>4} {d['vertices']:>9,} {d['rel_thickness']:>9.3f} "
                  f"{d['thinness']:>9.3f}  {d['reason']}")

    print(f"\nreport: {args.out / 'components.csv'}")
    print(f"LOOK AT THIS before trusting the selection: {args.out / 'contact_sheet.png'}")
    print("Green border = kept, red = rejected. A rejected sherd or a kept clamp means "
          "the thresholds are wrong for this capture, not that the mesh is bad.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
