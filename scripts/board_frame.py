"""Where the turntable actually was, for every photograph -- from the marker board.

WHAT PROBLEM THIS SOLVES. `check_turntable.py` can tell a collapsed or bent solve from a
good one, but only by asking whether the solve is self-consistent: do the camera positions
span a circle, do consecutive frames sit next to each other. It has never had anything to
compare a solve AGAINST. A capture could be wrong in a way that is smooth and plausible
and it would pass.

The marker board fixed to the turntable is that missing reference. It is rigid, it is in
the photographs, and it does not care what any reconstruction believes. This script turns
it into a per-frame rotation angle, so a solve can be checked against a measurement of the
rig rather than against its own opinion of itself.

WHERE THE ANGLES COME FROM. For N01 the conservator's own Metashape project is in the
Mediaflux archive, and it holds 16 machine-decoded coded targets with sub-pixel image
positions in every frame that sees them, plus all 119 camera poses. This script reads that
(see psx_reader.py -- no Metashape licence needed), triangulates the board, fits the axis
the turntable actually spun about, and reads off each camera's azimuth around it.

WHAT IS AND IS NOT INDEPENDENT HERE. The reference is derived from Metashape's solve, so
it is not independent OF Metashape -- it is independent of COLMAP, which is the thing being
checked. Calling it "ground truth" would be too strong. What can be said is that it is a
second, professionally-produced answer for the same photographs, and the checks below are
searching for reasons to distrust it rather than reasons to believe it:

  - the 16 targets reproject into their own 589 measured image positions at 0.25 px rms;
  - each camera stays at a constant distance from the fitted axis to within 1.2 mm, on a
    radius of about 1.5 m;
  - the five circle centres, at five different heights, lie on ONE straight line to 0.15 mm;
  - the 15 deg per frame this yields agrees with the 15 deg implied by the shutter
    timestamps, which is a completely separate measurement of the same rig.

A solve that had quietly collapsed could not produce any of those four.

ONE THING THAT WOULD HAVE BEEN A SILENT ERROR. The rotation axis is NOT the board's
normal. The board sits on the turntable, so the two ought to coincide, and they are 1.07
deg apart -- enough that assuming the normal would have put a frame several degrees out at
the top of the camera arc. The axis is therefore fitted from the camera circles rather
than assumed, and the residual of that fit is printed so a bad fit cannot pass quietly.

Usage:
    python board_frame.py build <psx_dir> --capture 2025-07-03/N01 -o reference.json
    python board_frame.py show  <reference.json>            # render it, then trust it
"""
import argparse
import json
from pathlib import Path

import numpy as np

from psx_reader import Project, find_project

# A pass is one revolution at one camera height. Frames are numbered in shooting order, so
# a pass is a contiguous run of frame numbers -- but the heights are NOT in order (N01 goes
# 0.08, 0.40, 0.16, 0.52, 0.75 m), so passes must be cut on height change, not on height
# rank. HEIGHT_JUMP is what counts as "the tripod was moved" rather than "the arm sagged":
# within a pass the spread is under 15 mm, between passes the smallest step is 75 mm.
HEIGHT_JUMP_M = 0.04

# Fit quality beyond which the reference should not be believed. The N01 numbers are ~30x
# inside all three, so these are not tuned to pass -- they are tuned to catch a solve that
# is nothing like N01's.
MAX_REPROJ_PX = 1.0        # targets vs their own measured image positions
MAX_CIRCLE_MM = 5.0        # camera centres vs a circle
MAX_AXIS_MM = 2.0          # per-pass circle centres vs one straight line


def board_and_axis(proj):
    """Triangulate the coded targets, then fit the axis the cameras orbit.

    Returns (targets, centroid, axis_point, axis_dir, diagnostics).
    """
    targets = {t.number: proj.triangulate(t) for t in proj.targets()}
    targets = {k: v for k, v in targets.items() if v is not None}
    if len(targets) < 4:
        raise SystemExit(f"only {len(targets)} coded targets triangulated; nothing to fit")

    A = np.array(list(targets.values()))
    centroid = A.mean(0)
    _, _, Vt = np.linalg.svd(A - centroid, full_matrices=False)
    normal = Vt[2]
    plane_rms = float(np.sqrt((((A - centroid) @ normal) ** 2).mean()))

    names = sorted(proj.cameras, key=_frame_no)
    C = np.array([proj.cameras[n].centre for n in names])
    if ((C - centroid) @ normal).mean() < 0:
        normal = -normal

    passes = _split_passes(C, centroid, normal, proj.chunk_scale)

    # The axis direction and the per-pass circle centres determine each other, so alternate
    # between them. Starting from the board normal this settles in a handful of rounds.
    axis = normal.copy()
    for _ in range(50):
        cs = _circle_centres(C, passes, centroid, axis)
        m = cs.mean(0)
        _, _, V = np.linalg.svd(cs - m, full_matrices=False)
        new = V[0] if V[0] @ axis > 0 else -V[0]
        moved = np.degrees(np.arccos(np.clip(new @ axis, -1, 1)))
        axis = new
        if moved < 1e-7:
            break

    cs = _circle_centres(C, passes, centroid, axis)
    point = cs.mean(0)
    off_axis = cs - point - ((cs - point) @ axis)[:, None] * axis
    diag = {
        "n_targets": len(targets),
        "board_plane_rms_mm": plane_rms,
        "axis_vs_board_normal_deg": float(np.degrees(np.arccos(np.clip(axis @ normal, -1, 1)))),
        "axis_straightness_mm": float(np.linalg.norm(off_axis, axis=1).max()),
    }
    return targets, centroid, point, axis, passes, names, C, diag


def _frame_no(name):
    tail = name.rsplit("_", 1)[-1]
    return int(tail) if tail.isdigit() else -1


def _split_passes(C, centroid, normal, scale):
    """Group frames into revolutions: contiguous in shooting order, constant in height.

    `scale` converts chunk units to metres, because the threshold is a physical distance
    and the coordinates are not.
    """
    h = (C - centroid) @ normal * scale
    passes, cur = [], [0]
    for i in range(1, len(C)):
        if abs(h[i] - h[i - 1]) > HEIGHT_JUMP_M:
            passes.append(cur)
            cur = []
        cur.append(i)
    passes.append(cur)
    return passes


def _circle_centres(C, passes, centroid, axis):
    e1 = np.cross(axis, [0.0, 0.0, 1.0])
    if np.linalg.norm(e1) < 1e-6:
        e1 = np.cross(axis, [0.0, 1.0, 0.0])
    e1 /= np.linalg.norm(e1)
    e2 = np.cross(axis, e1)
    out = []
    for idx in passes:
        P = C[idx] - centroid
        q = np.stack([P @ e1, P @ e2], 1)
        # Algebraic (Kasa) circle fit: exact least squares, no iteration, and the camera
        # centres here are far too clean for its bias toward small radii to matter.
        M = np.c_[2 * q, np.ones(len(q))]
        s, *_ = np.linalg.lstsq(M, (q ** 2).sum(1), rcond=None)
        out.append(centroid + s[0] * e1 + s[1] * e2 + (P @ axis).mean() * axis)
    return np.array(out)


def basis_for(axis):
    e1 = np.cross(axis, [0.0, 0.0, 1.0])
    if np.linalg.norm(e1) < 1e-6:
        e1 = np.cross(axis, [0.0, 1.0, 0.0])
    e1 /= np.linalg.norm(e1)
    return e1, np.cross(axis, e1)


def build(psx_dir, capture, out_path):
    proj = Project(*find_project(psx_dir))
    S = proj.chunk_scale                    # chunk units -> metres

    targets, centroid, point, axis, passes, names, C, diag = board_and_axis(proj)

    # -- how far can this reference be trusted? measure, then decide -------------------
    reproj = _target_reprojection(proj, targets)
    diag["target_reproj_rms_px"] = float(np.sqrt((reproj ** 2).mean()))
    diag["target_reproj_max_px"] = float(reproj.max())
    diag["board_plane_rms_mm"] *= 1000 * S
    diag["axis_straightness_mm"] *= 1000 * S

    e1, e2 = basis_for(axis)
    q = np.stack([(C - point) @ e1, (C - point) @ e2], 1)
    deg = np.degrees(np.arctan2(q[:, 1], q[:, 0]))
    radius = np.linalg.norm(q, axis=1) * S
    # Height is measured from the BOARD, not from `point`. `point` is the mean of the five
    # pass circle centres, which sits partway up the axis and means nothing physically --
    # measuring from it made turn 1 read as 30 cm BELOW the turntable it was pointing at.
    # The board plane is the real datum: the turntable surface the sherds stand on.
    base = point + ((centroid - point) @ axis) * axis
    height = ((C - base) @ axis) * S

    circ = []
    for idx in passes:
        r = radius[idx]
        circ.append(np.abs(r - r.mean()).max() * 1000)
    diag["circle_resid_max_mm"] = float(max(circ))

    frames = {}
    for i, nm in enumerate(names):
        frames[nm] = {"deg": float(deg[i]), "radius_m": float(radius[i]),
                      "height_m": float(height[i])}

    turns = []
    for k, idx in enumerate(passes):
        a = np.sort(deg[idx])
        gap = float(np.diff(np.r_[a, a[0] + 360]).max())
        step = np.diff(deg[idx]) % 360
        step = np.minimum(step, 360 - step)
        turns.append({
            "turn": k + 1, "n": len(idx),
            "frames": [names[i] for i in idx],
            "arc_deg": 360 - gap,
            "median_step_deg": float(np.median(step)),
            "radius_m": float(radius[idx].mean()),
            "height_m": float(height[idx].mean()),
        })

    a = np.sort(deg)
    ref = {
        "capture": capture,
        "source": str(Path(psx_dir)),
        "how": "Metashape coded targets triangulated, turntable axis fitted to camera circles",
        "units": {"board": "mm", "angles": "degrees about the fitted axis"},
        "board_targets_mm": {str(k): (np.asarray(v) - centroid).tolist()
                             for k, v in targets.items()},
        "axis": {"origin_chunk": point.tolist(), "direction_chunk": axis.tolist(),
                 "board_datum_chunk": base.tolist()},
        "quality": diag,
        "coverage": {"n_frames": len(names),
                     "arc_deg": float(360 - np.diff(np.r_[a, a[0] + 360]).max()),
                     "largest_gap_deg": float(np.diff(np.r_[a, a[0] + 360]).max())},
        "turns": turns,
        "frames": frames,
    }
    for k, v in list(ref["board_targets_mm"].items()):
        ref["board_targets_mm"][k] = [x * 1000 * S for x in v]

    Path(out_path).write_text(json.dumps(ref, indent=1))
    _report(ref)
    return ref


def _target_reprojection(proj, targets):
    import cv2
    K, D = proj.calib.K, proj.calib.dist
    res = []
    for t in proj.targets():
        X = targets.get(t.number)
        if X is None:
            continue
        for nm, xy in t.proj.items():
            cam = proj.cameras.get(nm)
            if cam is None:
                continue
            W = cam.world_to_cam
            r, _ = cv2.Rodrigues(W[:3, :3])
            p, _ = cv2.projectPoints(X.reshape(1, 3), r, W[:3, 3], K, D)
            res.append(np.linalg.norm(p.reshape(2) - np.array(xy)))
    return np.array(res)


def _report(ref):
    q = ref["quality"]
    print(f"\n{ref['capture']}  -- turntable reference from the marker board")
    print(f"  {q['n_targets']} coded targets, board flat to {q['board_plane_rms_mm']:.2f} mm rms")
    print(f"  targets reproject into their own measured positions at "
          f"{q['target_reproj_rms_px']:.2f} px rms (worst {q['target_reproj_max_px']:.2f})")
    print(f"  camera centres lie on their pass circle to {q['circle_resid_max_mm']:.1f} mm")
    print(f"  the {len(ref['turns'])} circle centres lie on one line to "
          f"{q['axis_straightness_mm']:.2f} mm")
    print(f"  that line is {q['axis_vs_board_normal_deg']:.2f} deg off the board's own normal"
          " -- so the normal is NOT the axis")

    bad = []
    if q["target_reproj_rms_px"] > MAX_REPROJ_PX:
        bad.append(f"targets reproject at {q['target_reproj_rms_px']:.2f} px (limit {MAX_REPROJ_PX})")
    if q["circle_resid_max_mm"] > MAX_CIRCLE_MM:
        bad.append(f"camera circles off by {q['circle_resid_max_mm']:.1f} mm (limit {MAX_CIRCLE_MM})")
    if q["axis_straightness_mm"] > MAX_AXIS_MM:
        bad.append(f"axis bends by {q['axis_straightness_mm']:.2f} mm (limit {MAX_AXIS_MM})")

    print(f"\n  {'turn':5s} {'n':>3s} {'height':>8s} {'radius':>8s} {'arc':>7s} {'step':>7s}")
    for t in ref["turns"]:
        print(f"  {t['turn']:<5d} {t['n']:3d} {t['height_m']:7.3f}m {t['radius_m']:7.3f}m "
              f"{t['arc_deg']:6.1f}d {t['median_step_deg']:6.2f}d")
    c = ref["coverage"]
    print(f"  all {c['n_frames']}: {c['arc_deg']:.1f} deg covered, largest gap "
          f"{c['largest_gap_deg']:.2f} deg")

    if bad:
        print("\n  DO NOT USE THIS AS A REFERENCE:")
        for b in bad:
            print(f"    - {b}")
    else:
        print("\n  -> usable as a reference for checking other solves of this capture")
    return not bad


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("psx_dir")
    b.add_argument("--capture", required=True)
    b.add_argument("-o", "--out", required=True)
    s = sub.add_parser("show")
    s.add_argument("reference")
    s.add_argument("-o", "--out", default=None)
    a = ap.parse_args()

    if a.cmd == "build":
        build(a.psx_dir, a.capture, a.out)
    else:
        from board_render import render
        ref = json.loads(Path(a.reference).read_text())
        out = a.out or str(Path(a.reference).with_suffix(".png"))
        render(ref, out)
        print(f"wrote {out}")


if __name__ == "__main__":
    main()
