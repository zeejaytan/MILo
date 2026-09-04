#!/usr/bin/env python3
"""
Compare a MILo mesh against an OpenMVS mesh of the same sherd — without a ground truth.

There is no correct mesh for a Rabati sherd. Nothing here scores against one, and no
number this script prints should be described as accuracy. What it can do honestly:

  1. SILHOUETTE AGREEMENT ON HELD-OUT VIEWS (the primary number). Every 8th photograph is
     withheld from training. Each mesh is rendered from those camera positions and its
     outline compared with the sherd's mask in that photograph. This asks "does this shape
     explain pictures it has never seen", which is answerable without a reference mesh and
     is unaffected by what units the mesh is in.

  2. WHERE THE TWO DISAGREE, in millimetres, mapped onto the surface. This says nothing
     about which one is right. It says where to look.

  3. WALL THICKNESS distribution. A sherd's wall is a physical quantity a conservator can
     check with callipers, and it is a sanity test that neither method has inflated or
     thinned the body.

  4. PICTURES. Raking-light renders of both meshes from matched viewpoints with a
     millimetre scale bar burnt in. Required, not optional: a wear bug in this workspace
     once survived three rounds of numeric validation and was obvious within seconds of
     drawing the geometry. Once the comparison runs at all, renders are written whatever
     the numbers say — but a scale refusal (below) stops before any mesh is loaded, so it
     produces no picture either.

BEFORE ANY OF THAT, this script finds out what units each mesh is in, by reading the
`<mesh>.scale.json` sidecar that `scale_mesh.py` writes beside a scaled mesh. If either
mesh cannot say, or the two say different things, the comparison STOPS and prints no
millimetre figure at all. Where only shape matters, `--shape-only` runs item 1 -- the one
measure here that does not depend on units -- and suppresses items 2, 3 and the scale
bar. It has to be asked for by name, so a shape answer cannot be mistaken for a metric
one. `--self-test` proves the refusal can actually fire.

Usage:
    python scripts/compare_meshes.py \\
        --capture  /data/.../MILo/data/16062025/capture.json \\
        --milo     /data/.../MILo/output/16062025/mesh_mm.ply \\
        --openmvs  /data/.../Rabati2025/16062025/work_colmap_openmvs/scene_dense_mesh_refine.ply \\
        --out      /data/.../MILo/output/16062025/compare

    python scripts/compare_meshes.py --self-test     # no data needed; proves the gate
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import trimesh
from PIL import Image as PILImage

_REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_colmap_loader():
    """MILo's COLMAP reader, loaded from its file so the import does not drag in the
    whole scene package (and torch) before we know a GPU is even needed."""
    import importlib.util

    path = _REPO_ROOT / "milo" / "scene" / "colmap_loader.py"
    spec = importlib.util.spec_from_file_location("milo_colmap_loader", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_colmap = _load_colmap_loader()
qvec2rotmat = _colmap.qvec2rotmat
read_extrinsics_binary = _colmap.read_extrinsics_binary
read_extrinsics_text = _colmap.read_extrinsics_text
read_intrinsics_binary = _colmap.read_intrinsics_binary
read_intrinsics_text = _colmap.read_intrinsics_text

# Below this, a silhouette score means the renderer disagrees with the photographs so
# badly that the most likely explanation is a broken camera convention in this script,
# not two independently bad reconstructions.
SUSPECT_IOU = 0.5

# --------------------------------------------------------------------------------------
# Scale provenance: what units is this mesh in, and what said so
# --------------------------------------------------------------------------------------

# A mesh file carries no units. The millimetres come from something physical in the
# scene -- the turntable marker board, or the blue base plate -- and scale_mesh.py
# records which, in a <mesh>.scale.json sidecar written beside the scaled mesh. Without
# reading it, a distance "in mesh units" gets printed as millimetres and nothing here can
# notice. That was true of this script until 2026-09-03: its --mm-per-unit flag reached
# only the render's scale bar, and frac_within_0.5mm was computed against a raw 0.5.

SIDECAR_SUFFIX = ".scale.json"

# Unit names a sidecar may declare, and what one mesh unit is worth in millimetres.
# Anything not on this list is refused rather than guessed at.
MM_PER_UNIT_BY_NAME = {
    "millimetres": 1.0, "millimeters": 1.0, "mm": 1.0,
    "centimetres": 10.0, "centimeters": 10.0, "cm": 10.0,
    "metres": 1000.0, "meters": 1000.0, "m": 1000.0,
}

# Exit statuses. 1 stays with the failures this script already had (no masks; two meshes
# whose sizes disagree). These two are about the scale record itself.
RC_OK = 0
RC_NO_SCALE = 2        # a mesh cannot say what units it is in
RC_SCALE_CONFLICT = 3  # the two meshes say different things


def sidecar_path(mesh_path: Path) -> Path:
    """<mesh>.ply -> <mesh>.scale.json, the name scale_mesh.py writes."""
    return Path(mesh_path).with_suffix(SIDECAR_SUFFIX)


def read_scale(mesh_path: Path):
    """The scale sidecar beside a mesh, or None if there is not one we can read."""
    p = sidecar_path(mesh_path)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text())
    except (OSError, ValueError):
        return None


def internal_disagreements(sidecar: dict) -> list:
    """What the scale measurement recorded about disagreeing with itself.

    A02/A03 were scaled off a 190 x 130 mm plate measured on two edges and on two point
    clouds. Those figures live in the sidecar and have never been printed anywhere: a
    5.4 % gap between the sparse and dense clouds was reachable only by opening the JSON.
    """
    out = []
    m = sidecar.get("measured") or {}
    d = m.get("disagreement")
    if isinstance(d, (int, float)):
        out.append("the two reference edges disagree by %.1f%%" % (d * 100))
    x = m.get("cross_cloud_disagreement")
    if isinstance(x, (int, float)):
        out.append("the sparse and dense clouds disagree by %.1f%%" % (x * 100))
    for sub in m.get("measurements") or []:
        if sub.get("accepted") is False:
            out.append("the %s cloud's measurement was rejected"
                       % (sub.get("cloud") or "unnamed"))
    return out


def scale_decision(paths: dict, shape_only: bool = False) -> dict:
    """Can this comparison honestly report millimetres, and on whose authority.

    `paths` maps a tag ("milo", "openmvs") to a mesh path. Nothing is loaded and nothing
    is written; this only reads the sidecars, so it can run before the capture, the
    COLMAP model or the CUDA renderer exist. That is deliberate -- the refusal must not
    depend on a GPU being present.
    """
    sidecars, units, reasons = {}, {}, []
    for tag, path in paths.items():
        sc = read_scale(Path(path))
        sidecars[tag] = sc
        if sc is None:
            reasons.append(
                "%s: no scale sidecar beside %s. Nothing records what units it is in, or "
                "what physical object supplied them." % (tag, Path(path).name))
            continue
        name = str(sc.get("units", "")).strip().lower()
        if name not in MM_PER_UNIT_BY_NAME:
            reasons.append(
                "%s: its sidecar declares units %r, which is not a unit this script will "
                "guess at." % (tag, sc.get("units")))
            continue
        units[tag] = name

    # Compare the SIZE the unit names denote, not the names. MM_PER_UNIT_BY_NAME exists
    # precisely so that "mm" and "millimetres" are the same unit; comparing the strings
    # made the table decorative and refused correctly-scaled pairs -- telling the
    # conservator one of the meshes was never scaled, which was false.
    factors = {t: MM_PER_UNIT_BY_NAME[u] for t, u in units.items()}

    scale_code = RC_OK
    if len(units) < len(paths):
        scale_code = RC_NO_SCALE
    elif len(set(factors.values())) > 1:
        scale_code = RC_SCALE_CONFLICT
        reasons.append(
            "the two meshes do not agree on units -- " +
            ", ".join("%s says %s" % (t, u) for t, u in sorted(units.items())) +
            ". They come from the same camera solve, so one of them was never scaled.")

    scale_ok = scale_code == RC_OK
    return {
        "scale_ok": scale_ok,
        "scale_code": scale_code,
        "shape_only": bool(shape_only),
        # Metric means: millimetres may be printed. Asking for --shape-only suppresses
        # them even when the sidecars would have allowed them.
        "metric": scale_ok and not shape_only,
        "reasons": reasons,
        "sidecars": sidecars,
        "mm_per_unit": factors if scale_ok else {},
    }


# Every key in a sidecar whose value is a scale FACTOR -- a number a reader could
# multiply a mesh coordinate by to get millimetres. Under --shape-only none of them may
# reach the written report: a suppressed read-out with the factor still in the JSON is
# not a suppressed millimetre, it is a millimetre one multiplication away.
SCALE_FACTOR_KEYS = ("mm_per_unit", "mm_per_unit_long", "mm_per_unit_short",
                     "long_units", "short_units", "measured")


def without_scale_factors(sidecar):
    """The sidecar's provenance -- who supplied the millimetres -- with no factor left.

    Keeps units, source, capture, method, scaled_at and caveat, because under
    --shape-only it is still worth recording which meshes could have been measured and
    on whose authority. Drops everything a downstream reader could compute with.
    """
    if not isinstance(sidecar, dict):
        return sidecar
    return {k: v for k, v in sidecar.items() if k not in SCALE_FACTOR_KEYS}


def exit_code_for_scale(decision: dict) -> int:
    """The status the caller branches on.

    Separate from the printing on purpose. check_turntable.py printed a perfectly correct
    page of disagreeing frames while returning 0, so the gate was dead and the pipeline
    ran on regardless. The status is the thing that has to be proven, so it is the thing
    the self-test asserts.
    """
    if decision["scale_ok"] or decision["shape_only"]:
        return RC_OK
    return decision["scale_code"]


def provenance_lines(decision: dict) -> list:
    """Where each mesh's millimetres came from, printed above the results, not beneath."""
    lines = ["Scale provenance"]
    for tag, sc in sorted(decision["sidecars"].items()):
        if sc is None:
            lines.append("  %-9s no sidecar -- units unknown" % tag)
            continue
        lines.append("  %-9s %s, from %s" % (tag, sc.get("units"),
                                             sc.get("source") or "an unrecorded source"))
        lines.append("  %-9s capture %s, %s, scaled %s"
                     % ("", sc.get("capture") or "?", sc.get("method") or "?",
                        sc.get("scaled_at") or "?"))
        # How precisely the millimetres are known, and how much the scale measurement
        # disagreed with itself, only mean something when millimetres are being
        # reported. Under --shape-only they would be precision figures for a number
        # that never appears.
        if decision["shape_only"]:
            continue
        if sc.get("caveat"):
            lines.append("  %-9s stated precision: %s" % ("", sc["caveat"]))
        checks = internal_disagreements(sc)
        if checks:
            lines.append("  %-9s the scale measurement's own checks:" % "")
            for d in checks:
                lines.append("  %-9s   - %s" % ("", d))
    if decision["shape_only"]:
        lines.append("  --shape-only: outline agreement only. No distance, thickness or "
                     "size figure is reported below,")
        lines.append("  because none of them would be in millimetres. The sidecars are "
                     "named above so it is on record")
        lines.append("  which meshes could have been measured, but no scale factor is "
                     "printed or written.")
    return lines



# --------------------------------------------------------------------------------------
# COLMAP model
# --------------------------------------------------------------------------------------

def read_model(sparse_dir: Path):
    if (sparse_dir / "images.bin").exists():
        return (read_extrinsics_binary(str(sparse_dir / "images.bin")),
                read_intrinsics_binary(str(sparse_dir / "cameras.bin")))
    return (read_extrinsics_text(str(sparse_dir / "images.txt")),
            read_intrinsics_text(str(sparse_dir / "cameras.txt")))


def pinhole_params(cam):
    """(fx, fy, cx, cy) for the pinhole models COLMAP's undistorter emits."""
    if cam.model == "PINHOLE":
        fx, fy, cx, cy = cam.params[:4]
    elif cam.model == "SIMPLE_PINHOLE":
        f, cx, cy = cam.params[:3]
        fx = fy = f
    else:
        raise ValueError(
            f"camera model {cam.model} is not pinhole; these views were not undistorted"
        )
    return float(fx), float(fy), float(cx), float(cy)


def view_matrix(image) -> np.ndarray:
    """World -> OpenGL camera (x right, y up, -z forward), 4x4."""
    R = qvec2rotmat(image.qvec)          # world -> COLMAP camera (x right, y down, +z fwd)
    t = np.asarray(image.tvec, dtype=np.float64)
    m = np.eye(4)
    m[:3, :3] = R
    m[:3, 3] = t
    # COLMAP -> OpenGL: flip y and z.
    return np.diag([1.0, -1.0, -1.0, 1.0]) @ m


def projection_matrix(fx, fy, cx, cy, w, h, znear, zfar) -> np.ndarray:
    """Pinhole intrinsics as an OpenGL projection matrix."""
    p = np.zeros((4, 4))
    p[0, 0] = 2.0 * fx / w
    p[1, 1] = 2.0 * fy / h
    p[0, 2] = 1.0 - 2.0 * cx / w
    p[1, 2] = 2.0 * cy / h - 1.0
    p[2, 2] = -(zfar + znear) / (zfar - znear)
    p[2, 3] = -2.0 * zfar * znear / (zfar - znear)
    p[3, 2] = -1.0
    return p


# --------------------------------------------------------------------------------------
# Rasterisation (nvdiffrast, CUDA context — the compute nodes are headless)
# --------------------------------------------------------------------------------------

class Renderer:
    def __init__(self):
        try:
            import torch
            import nvdiffrast.torch as dr
        except ImportError as exc:
            raise SystemExit(
                f"nvdiffrast/torch unavailable ({exc}).\n"
                "Run this inside the MILo conda environment on a GPU node — it is "
                "installed there as part of MILo itself."
            )
        self.torch = torch
        self.dr = dr
        # RasterizeCudaContext, not GL: the compute nodes have no display and an OpenGL
        # context would fail to initialise.
        self.ctx = dr.RasterizeCudaContext()

    def render(self, mesh: trimesh.Trimesh, mvp: np.ndarray, w: int, h: int):
        """Return (mask HxW bool, depth HxW float, normal HxWx3 float) in camera space."""
        torch, dr = self.torch, self.dr
        v = torch.tensor(np.asarray(mesh.vertices, np.float32), device="cuda")
        f = torch.tensor(np.asarray(mesh.faces, np.int32), device="cuda")
        n = torch.tensor(np.asarray(mesh.vertex_normals, np.float32), device="cuda")

        mvp_t = torch.tensor(mvp.astype(np.float32), device="cuda")
        v_h = torch.cat([v, torch.ones_like(v[:, :1])], dim=1)
        v_clip = (v_h @ mvp_t.T)[None]

        # nvdiffrast wants both raster dimensions to be multiples of 8.
        rh, rw = (h + 7) // 8 * 8, (w + 7) // 8 * 8
        rast, _ = dr.rasterize(self.ctx, v_clip, f, resolution=[rh, rw])

        mask = (rast[..., 3:4] > 0).float()
        depth = v_clip[..., 2:3] / v_clip[..., 3:4]
        depth_img, _ = dr.interpolate(depth, rast, f)
        normal_img, _ = dr.interpolate(n[None], rast, f)

        def to_np(x, c):
            a = x[0, :h, :w, :c].detach().cpu().numpy()
            return np.flipud(a)          # nvdiffrast row 0 is the bottom of the image

        return (to_np(mask, 1)[..., 0] > 0.5,
                to_np(depth_img, 1)[..., 0],
                to_np(normal_img, 3))


# --------------------------------------------------------------------------------------
# The four things this script reports
# --------------------------------------------------------------------------------------

def silhouette_agreement(renderer, mesh, model, masks_dir, held_out, out_dir, tag):
    """Intersection-over-union between each rendered outline and the view's mask."""
    extrinsics, intrinsics = model
    by_name = {im.name: im for im in extrinsics.values()}
    rows = []
    for name in held_out:
        image = by_name.get(name)
        if image is None:
            continue
        mask_path = masks_dir / (Path(name).stem + ".png")
        if not mask_path.exists():
            continue
        gt = np.asarray(PILImage.open(mask_path).convert("L")) > 127
        h, w = gt.shape

        cam = intrinsics[image.camera_id]
        fx, fy, cx, cy = pinhole_params(cam)
        extent = float(np.linalg.norm(mesh.extents))
        mvp = projection_matrix(fx, fy, cx, cy, w, h,
                                znear=extent * 1e-3, zfar=extent * 1e3) @ view_matrix(image)

        pred, _, _ = renderer.render(mesh, mvp, w, h)
        inter = np.logical_and(pred, gt).sum()
        union = np.logical_or(pred, gt).sum()
        rows.append({
            "view": name,
            "iou": float(inter / union) if union else 0.0,
            # Split the error so the direction is visible: material the mesh invents vs
            # material it is missing. They mean different things for a break face.
            "excess_px": int(np.logical_and(pred, ~gt).sum()),
            "missing_px": int(np.logical_and(~pred, gt).sum()),
            "gt_px": int(gt.sum()),
        })

        if len(rows) <= 3:
            _save_silhouette_overlay(pred, gt, out_dir / f"silhouette_{tag}_{Path(name).stem}.png")
    return rows


def _save_silhouette_overlay(pred, gt, path: Path):
    """Green = agreed, red = mesh invents material, blue = mesh misses material."""
    h, w = gt.shape
    img = np.zeros((h, w, 3), np.uint8)
    img[np.logical_and(pred, gt)] = (40, 180, 60)
    img[np.logical_and(pred, ~gt)] = (200, 40, 40)
    img[np.logical_and(~pred, gt)] = (40, 80, 200)
    path.parent.mkdir(parents=True, exist_ok=True)
    PILImage.fromarray(img).save(path)


def surface_disagreement(a: trimesh.Trimesh, b: trimesh.Trimesh, mm_per_unit: float,
                         n_samples=200_000):
    """Symmetric point-to-surface distance between the two meshes, in MILLIMETRES.

    `mm_per_unit` comes from the meshes' own scale sidecars, and the conversion happens
    here, before the 0.5 mm and 1 mm fractions below are computed. Until 2026-09-03 those
    two fractions were computed against a raw 0.5 and 1.0 in whatever units the mesh
    happened to be in: a mesh in metres reported "99.9 % of the surface within 0.5 mm"
    when the real figure was in metres and meant nothing at all.
    """
    from scipy.spatial import cKDTree

    pa = a.sample(n_samples)
    pb = b.sample(n_samples)
    d_ab = cKDTree(pb).query(pa)[0]
    d_ba = cKDTree(pa).query(pb)[0]
    d = np.concatenate([d_ab, d_ba]) * float(mm_per_unit)
    return {
        "median": float(np.median(d)),
        "p90": float(np.percentile(d, 90)),
        "p99": float(np.percentile(d, 99)),
        "max": float(d.max()),
        "frac_within_0.5mm": float((d < 0.5).mean()),
        "frac_within_1mm": float((d < 1.0).mean()),
    }


def wall_thickness(mesh: trimesh.Trimesh, mm_per_unit: float, n_samples=20_000, seed=0):
    """
    Distance from a point on the surface to the opposite face, along the inward normal,
    in millimetres -- a conservator can check this one against the sherd with callipers.

    Sampled rather than exhaustive: a refined OpenMVS mesh has ~1M vertices and this is a
    distribution, not a per-vertex map. Rays that exit without hitting anything are
    dropped — those are break faces and rim edges, where "wall thickness" has no meaning.
    """
    rng = np.random.default_rng(seed)
    idx = rng.choice(len(mesh.vertices), size=min(n_samples, len(mesh.vertices)),
                     replace=False)
    origins = mesh.vertices[idx]
    normals = mesh.vertex_normals[idx]
    eps = float(np.linalg.norm(mesh.extents)) * 1e-5
    hits = mesh.ray.intersects_location(
        ray_origins=origins - normals * eps,
        ray_directions=-normals,
        multiple_hits=False,
    )
    locations, index_ray = hits[0], hits[1]
    if len(index_ray) == 0:
        return None
    d = np.linalg.norm(locations - origins[index_ray], axis=1) * float(mm_per_unit)
    return {
        "n_rays_hit": int(len(d)),
        "n_rays_cast": int(len(origins)),
        "median": float(np.median(d)),
        "p10": float(np.percentile(d, 10)),
        "p90": float(np.percentile(d, 90)),
    }


def raking_render(renderer, mesh, model, view_name, out_path: Path, mm_per_unit=None):
    """
    Shade the mesh with a grazing light, the way raking light reveals a worn surface.

    Flat, head-on lighting hides exactly the sub-millimetre relief this comparison is
    about. A millimetre scale bar is burnt into the corner so the picture cannot be read
    at the wrong scale.
    """
    extrinsics, intrinsics = model
    by_name = {im.name: im for im in extrinsics.values()}
    image = by_name.get(view_name) or list(extrinsics.values())[0]
    cam = intrinsics[image.camera_id]
    fx, fy, cx, cy = pinhole_params(cam)
    w, h = int(cam.width), int(cam.height)

    extent = float(np.linalg.norm(mesh.extents))
    view = view_matrix(image)
    mvp = projection_matrix(fx, fy, cx, cy, w, h,
                            znear=extent * 1e-3, zfar=extent * 1e3) @ view

    mask, _, normal = renderer.render(mesh, mvp, w, h)

    # Light ~15 degrees above the image plane, from the left, in camera space.
    light = np.array([-0.966, 0.259, -0.05])
    light /= np.linalg.norm(light)
    n_cam = normal @ view[:3, :3].T
    n_cam /= (np.linalg.norm(n_cam, axis=-1, keepdims=True) + 1e-9)
    shade = np.clip((n_cam * light).sum(-1), 0.0, 1.0) ** 0.8

    img = np.zeros((h, w, 3), np.float32)
    img[mask] = (0.08 + 0.92 * shade[mask])[:, None]
    img = (img * 255).astype(np.uint8)

    if mm_per_unit is not None:
        _draw_scale_bar(img, fx, view, mesh, mm_per_unit)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    PILImage.fromarray(img).save(out_path)


def _draw_scale_bar(img, fx, view, mesh, mm_per_unit):
    """Burn a 10 mm bar into the bottom-left corner, sized at the sherd's own depth."""
    centre_cam = (view @ np.append(mesh.centroid, 1.0))[:3]
    depth = abs(centre_cam[2])
    if depth <= 0 or mm_per_unit <= 0:
        return
    px_per_mm = fx / depth / mm_per_unit
    bar_px = int(round(10.0 * px_per_mm))
    h, w = img.shape[:2]
    if not (5 < bar_px < w * 0.8):
        return
    y0, x0, t = h - 60, 40, 8
    img[y0:y0 + t, x0:x0 + bar_px] = 255
    img[y0 - 4:y0 + t + 4, x0 - 3:x0] = 255
    img[y0 - 4:y0 + t + 4, x0 + bar_px:x0 + bar_px + 3] = 255


# --------------------------------------------------------------------------------------

def load_mesh(path: Path) -> trimesh.Trimesh:
    m = trimesh.load(path, process=False)
    if isinstance(m, trimesh.Scene):
        m = trimesh.util.concatenate(tuple(m.geometry.values()))
    return m


def describe(mesh: trimesh.Trimesh, mm_per_unit=None) -> dict:
    """`mm_per_unit=None` means the units are unknown, so the extents are not called mm."""
    d = {
        "vertices": int(len(mesh.vertices)),
        "faces": int(len(mesh.faces)),
        "watertight": bool(mesh.is_watertight),
        "components": int(len(mesh.split(only_watertight=False))),
    }
    if mm_per_unit is None:
        d["extents_units"] = [round(float(x), 6) for x in mesh.extents]
    else:
        d["extents_mm"] = [round(float(x) * mm_per_unit, 2) for x in mesh.extents]
    return d


# --------------------------------------------------------------------------------------
# Proving the gate can refuse
# --------------------------------------------------------------------------------------

def _fixture(dirpath: Path, tag: str, radius: float, sidecar=None) -> Path:
    """A small sphere written as a mesh, with the sidecar it is meant to have (or none)."""
    path = dirpath / (tag + ".ply")
    trimesh.creation.icosphere(subdivisions=4, radius=radius).export(path)
    if sidecar is not None:
        sidecar_path(path).write_text(json.dumps(sidecar, indent=2))
    return path


def _mm_sidecar(**extra) -> dict:
    d = {"units": "millimetres", "mm_per_unit": 373.73, "capture": "17062025/A03",
         "method": "self-test fixture", "source": "blue base top face 190x130 mm",
         "scaled_at": "2026-09-03T00:00Z", "caveat": "precision ~1%"}
    d.update(extra)
    return d


def self_test() -> int:
    """Prove the scale gate can refuse as well as pass, and that the millimetre
    thresholds are actually in millimetres.

    A gate that has only ever been seen to pass is indistinguishable from a gate that
    always passes. check_turntable.py in this repo printed a perfectly correct page of
    disagreeing frames while returning 0, so the dense stage ran anyway; the fix was to
    assert the exit STATUS, which is what the caller branches on. Same reasoning here.

    Runs on a laptop: nothing below needs the capture, the COLMAP model or CUDA, because
    the scale gate is decided before any of those are touched.
    """
    import re
    import tempfile

    state = {"ok": True}

    def case(got, want):
        good = got == want
        state["ok"] &= good
        print(f"   exit status {got}, expected {want}  -> {'OK' if good else 'WRONG'}")

    def check(condition, detail):
        state["ok"] &= bool(condition)
        print(f"   {detail}  -> {'OK' if condition else 'WRONG'}")

    with tempfile.TemporaryDirectory() as td:
        d = Path(td)

        print("\n-- both meshes declare millimetres and agree")
        a = _fixture(d, "milo_ok", 50.0, _mm_sidecar())
        b = _fixture(d, "mvs_ok", 50.8, _mm_sidecar(method="self-test fixture B"))
        dec = scale_decision({"milo": a, "openmvs": b})
        case(exit_code_for_scale(dec), RC_OK)
        check(dec["metric"] and dec["mm_per_unit"]["milo"] == 1.0,
              "millimetres may be printed, 1 unit = 1 mm")
        check("blue base top face" in "\n".join(provenance_lines(dec)),
              "the scale source is printed with the results")

        print("\n-- one mesh has no sidecar at all")
        c = _fixture(d, "mvs_bare", 50.8, None)
        dec = scale_decision({"milo": a, "openmvs": c})
        case(exit_code_for_scale(dec), RC_NO_SCALE)
        check(not dec["metric"], "no millimetre figure may be printed")

        print("\n-- the two sidecars disagree on units")
        e = _fixture(d, "mvs_metres", 0.0508, _mm_sidecar(units="metres"))
        dec = scale_decision({"milo": a, "openmvs": e})
        case(exit_code_for_scale(dec), RC_SCALE_CONFLICT)

        print("\n-- two spellings of the same unit are the same unit")
        # "mm" and "millimetres" are both millimetres. Comparing the unit STRINGS
        # refused this pair as a conflict and told the conservator one of the meshes
        # had never been scaled, which was false. A gate that rejects correct work with
        # a wrong explanation is a gate that gets commented out.
        alias = _fixture(d, "mvs_mm_alias", 50.8, _mm_sidecar(units="mm"))
        dec = scale_decision({"milo": a, "openmvs": alias})
        case(exit_code_for_scale(dec), RC_OK)
        check(dec["metric"] and dec["mm_per_unit"]["openmvs"] == 1.0,
              "'mm' resolves to the same millimetre as 'millimetres'")

        print("\n-- a sidecar declaring units nobody here recognises")
        f = _fixture(d, "mvs_cubits", 50.8, _mm_sidecar(units="cubits"))
        dec = scale_decision({"milo": a, "openmvs": f})
        case(exit_code_for_scale(dec), RC_NO_SCALE)

        print("\n-- no sidecars anywhere, but --shape-only was asked for")
        g = _fixture(d, "milo_bare", 50.0, None)
        dec = scale_decision({"milo": g, "openmvs": c}, shape_only=True)
        case(exit_code_for_scale(dec), RC_OK)
        check(not dec["metric"], "millimetres stay suppressed")
        check(re.search(r"\d\s*mm", "\n".join(provenance_lines(dec))) is None,
              "no millimetre figure appears in the read-out")

        print("\n-- --shape-only with sidecars that WOULD have allowed millimetres")
        # The case above cannot fail: with no sidecars there is nothing to leak. This is
        # the one that could. Both meshes are fully scaled and --shape-only is still
        # asked for, so the read-out and the written report must carry no scale factor
        # -- a suppressed figure with mm_per_unit still in the JSON is one
        # multiplication away from being reported.
        dec = scale_decision({"milo": a, "openmvs": alias}, shape_only=True)
        case(exit_code_for_scale(dec), RC_OK)
        check(not dec["metric"], "millimetres stay suppressed even though both are scaled")
        written = json.dumps({t: without_scale_factors(sc)
                              for t, sc in dec["sidecars"].items()})
        leaked = [k for k in SCALE_FACTOR_KEYS if k in written]
        check(not leaked, "no scale factor reaches the written report (%s)"
              % (", ".join(leaked) or "none"))
        check("373.73" not in written and "373.73" not in "\n".join(provenance_lines(dec)),
              "the factor itself appears nowhere")
        check("blue base top face" in written,
              "which mesh could have been measured, and on whose authority, is still recorded")

        print("\n-- a sidecar whose own measurement disagreed with itself")
        noisy = _mm_sidecar(measured={
            "cross_cloud_disagreement": 0.0537, "disagreement": 0.0138, "chosen": "dense",
            "accepted": True,
            "measurements": [{"cloud": "dense", "accepted": True},
                             {"cloud": "sparse", "accepted": False}]})
        h = _fixture(d, "mvs_noisy", 50.8, noisy)
        dec = scale_decision({"milo": a, "openmvs": h})
        case(exit_code_for_scale(dec), RC_OK)
        text = "\n".join(provenance_lines(dec))
        check("5.4%" in text and "sparse cloud's measurement was rejected" in text,
              "the 5.4% cross-cloud gap and the rejected cloud are printed, not buried")

        # ---- the defect that started this ------------------------------------------
        # Two spheres 0.8 mm apart, expressed in millimetres and again in metres. The
        # same pair must give the same answer, and did not: the 0.5 mm and 1 mm
        # fractions were computed against a raw 0.5 and 1.0 in whatever the mesh units
        # happened to be.
        print("\n-- the millimetre thresholds are in millimetres")
        a_mm = trimesh.creation.icosphere(subdivisions=4, radius=50.0)
        b_mm = trimesh.creation.icosphere(subdivisions=4, radius=50.8)
        a_m = trimesh.creation.icosphere(subdivisions=4, radius=0.050)
        b_m = trimesh.creation.icosphere(subdivisions=4, radius=0.0508)
        in_mm = surface_disagreement(a_mm, b_mm, 1.0, n_samples=50_000)
        in_m = surface_disagreement(a_m, b_m, 1000.0, n_samples=50_000)
        # frac_within_1mm, not 0.5mm: at 0.8 mm apart the 0.5 mm figure is 0 for both
        # and two zeros would agree whatever the conversion did.
        check(abs(in_mm["frac_within_1mm"] - in_m["frac_within_1mm"]) < 0.02,
              f"the same pair in mm ({in_mm['frac_within_1mm']:.3f}) and in metres "
              f"({in_m['frac_within_1mm']:.3f}) agree within 2 points")
        check(in_mm["frac_within_0.5mm"] < 0.5 < in_mm["frac_within_1mm"],
              f"0.8 mm apart reads as {in_mm['frac_within_0.5mm']:.0%} within 0.5 mm "
              f"and {in_mm['frac_within_1mm']:.0%} within 1 mm")
        old = surface_disagreement(a_m, b_m, 1.0, n_samples=20_000)
        check(old["frac_within_0.5mm"] > 0.99,
              f"unconverted, the metres pair would have claimed "
              f"{old['frac_within_0.5mm']:.1%} of its surface within 0.5 mm")

    print("\nself-test:", "PASS" if state["ok"] else "FAIL")
    return 0 if state["ok"] else 1


def main() -> int:
    ap = argparse.ArgumentParser(description="Compare a MILo mesh with an OpenMVS mesh")
    # Not argparse-`required`, because --self-test needs none of them and a `required`
    # flag would make the self-test unreachable through the parser that advertises it.
    # They are required for a comparison, and checked as such below.
    ap.add_argument("--capture", type=Path)
    ap.add_argument("--milo", type=Path)
    ap.add_argument("--openmvs", type=Path)
    ap.add_argument("--out", type=Path)
    ap.add_argument("--shape-only", action="store_true",
                    help="run only the measure that does not depend on units (outline "
                         "agreement on held-out views) and print no millimetre figure")
    ap.add_argument("--self-test", action="store_true",
                    help="prove the scale gate can refuse as well as pass; needs no data")
    ap.add_argument("--skip-thickness", action="store_true",
                    help="skip wall thickness (ray casting is slow without embree)")
    args = ap.parse_args()

    if args.self_test:
        return self_test()

    missing = [n for n in ("capture", "milo", "openmvs", "out")
               if getattr(args, n) is None]
    if missing:
        ap.error("a comparison needs " + ", ".join("--" + n for n in missing))

    # The scale gate runs FIRST, before the capture, the COLMAP model or the CUDA
    # renderer are touched. A refusal that needed a GPU node to happen would not be a
    # gate; and there is no point loading a million vertices to then decline to measure
    # them.
    decision = scale_decision({"milo": args.milo, "openmvs": args.openmvs},
                              shape_only=args.shape_only)
    rc = exit_code_for_scale(decision)
    if rc != RC_OK:
        print("\nSTOP: this comparison cannot say what units it would be reporting in.\n",
              file=sys.stderr)
        for reason in decision["reasons"]:
            print("  - " + reason, file=sys.stderr)
        print("\nA mesh scaled by scripts/scale_mesh.py has a <mesh>.scale.json beside it,\n"
              "naming the physical object that supplied the millimetres. If only the\n"
              "shape matters -- outline agreement against held-out photographs, which\n"
              "does not depend on units -- rerun with --shape-only.\n\n"
              "Nothing was written. No figure above would have been in millimetres.",
              file=sys.stderr)
        return rc

    mm_per_unit = (decision["mm_per_unit"]["milo"] if decision["metric"] else None)
    for line in provenance_lines(decision):
        print(line)

    capture = json.loads(args.capture.read_text())
    dataset = Path(capture["dataset_dir"])
    masks_dir = Path(capture["masks"]["masks_dir"]) if capture["masks"].get("masks_dir") else None
    held_out = capture["held_out_views"]
    args.out.mkdir(parents=True, exist_ok=True)

    if masks_dir is None:
        print("This capture has no masks, so there is no outline to compare a render "
              "against. Silhouette agreement — the only measure here that does not need "
              "a ground truth — cannot be computed.", file=sys.stderr)
        return 1

    model = read_model(dataset / "sparse" / "0")
    meshes = {"milo": load_mesh(args.milo), "openmvs": load_mesh(args.openmvs)}

    report = {"capture": str(args.capture), "mm_per_unit": mm_per_unit,
              "metric": decision["metric"], "shape_only": decision["shape_only"],
              "scale": ({t: without_scale_factors(sc)
                         for t, sc in decision["sidecars"].items()}
                        if decision["shape_only"] else decision["sidecars"]),
              "meshes": {}, "silhouette": {}, "thickness": {}}
    for tag, mesh in meshes.items():
        report["meshes"][tag] = describe(mesh, mm_per_unit)

    # Both meshes come from the same COLMAP model, so they share a coordinate frame and
    # need no alignment. If their sizes disagree they are not in the same units, and
    # every millimetre below would be meaningless.
    ext = np.array([meshes["milo"].extents, meshes["openmvs"].extents])
    ratio = float(np.max(ext[0] / np.maximum(ext[1], 1e-9)))
    if not (0.9 < ratio < 1.1):
        print(f"\nSTOP: the two meshes differ in size by a factor of about {ratio:.2f}.\n"
              "They are not in the same units, so no distance below would mean anything.\n"
              "Check whether scale_apply.py was run for one and not the other "
              "(see scripts/apply_scale.py).", file=sys.stderr)
        return 1

    renderer = Renderer()

    for tag, mesh in meshes.items():
        rows = silhouette_agreement(renderer, mesh, model, masks_dir, held_out,
                                    args.out, tag)
        ious = [r["iou"] for r in rows]
        report["silhouette"][tag] = {
            "n_views": len(rows),
            "iou_mean": float(np.mean(ious)) if ious else None,
            "iou_min": float(np.min(ious)) if ious else None,
            "per_view": rows,
        }
        raking_render(renderer, mesh, model, held_out[0] if held_out else None,
                      args.out / f"raking_{tag}.png", mm_per_unit=mm_per_unit)

    if decision["metric"]:
        report["disagreement_mm"] = surface_disagreement(
            meshes["milo"], meshes["openmvs"], mm_per_unit)

        if not args.skip_thickness:
            for tag, mesh in meshes.items():
                report["thickness"][tag] = wall_thickness(mesh, mm_per_unit)

    (args.out / "comparison.json").write_text(json.dumps(report, indent=2))

    # ---- read-out -------------------------------------------------------------------
    print(f"\nComparison written to {args.out}\n")
    for tag in ("milo", "openmvs"):
        d, s = report["meshes"][tag], report["silhouette"][tag]
        print(f"{tag:8s} {d['vertices']:>10,} vertices  {d['components']:>3} piece(s)  "
              f"watertight={d['watertight']}")
        if s["iou_mean"] is not None:
            print(f"         outline matches held-out photographs "
                  f"{s['iou_mean']:.1%} on average (worst view {s['iou_min']:.1%}, "
                  f"{s['n_views']} views)")
        t = report["thickness"].get(tag)
        if t:
            print(f"         wall thickness median {t['median']:.2f} mm "
                  f"(10-90%: {t['p10']:.2f}-{t['p90']:.2f} mm)")

    if decision["metric"]:
        dis = report["disagreement_mm"]
        print(f"\nThe two disagree by {dis['median']:.2f} mm at the median, "
              f"{dis['p90']:.2f} mm at the 90th percentile.")
        print("That says where they differ, not which one is right.")
    else:
        print("\nNo distance in millimetres is reported: --shape-only was asked for, so "
              "the\nonly measure run here was the one that does not depend on units.")

    best = max(("milo", "openmvs"), key=lambda t: report["silhouette"][t]["iou_mean"] or 0)
    worst_iou = min(report["silhouette"][t]["iou_mean"] or 0 for t in meshes)
    if worst_iou < SUSPECT_IOU:
        print(f"\nWARNING: the best outline agreement is only "
              f"{report['silhouette'][best]['iou_mean']:.1%}. Before concluding that a "
              "method failed, check that this script's camera convention is right — a "
              "renderer pointing the wrong way produces exactly this. Look at "
              f"{args.out}/silhouette_*.png.")
    else:
        print(f"\nOn this capture, {best} explains the held-out photographs better.")

    print("\nOne sherd is a lead, not a result. Look at the renders "
          f"({args.out}/raking_*.png) before taking any of these numbers further.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
