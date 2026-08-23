"""Did the reconstruction understand that the turntable turned?

For a capture where the object rotates and the camera stays put, structure-from-motion has
a choice of two answers, and only one of them is useful:

  the object's frame  -- the tree is held still and the camera travels right round it.
                         This is correct, and the camera positions span close to 360 degrees.
  the room's frame    -- the camera is held still and the tree is described as if it never
                         turned. The only way to then account for photographs of a turning
                         tree is to place a fresh copy of every sherd at every turntable
                         position. The camera positions stay bunched in a narrow arc.

Both explain the photographs equally well, so REPROJECTION ERROR CANNOT TELL THEM APART --
on tree A01 the wrong answer scored 0.54 px, which is excellent. The camera arc can tell
them apart, and needs no ground truth.

THE THIRD QUESTION, AND WHY IT IS DIFFERENT. Coverage and frame order are both questions
the solve answers about ITSELF. A solve that is wrong smoothly -- every frame displaced,
but displaced consistently -- satisfies both. `--reference` closes that hole by comparing
the solve against a rotation angle measured from the marker board bolted to the turntable,
which does not care what the reconstruction believes. See board_frame.py.

Usage:
    python check_turntable.py <colmap_sparse_model_dir> [more dirs ...]
    python check_turntable.py --reference ref.json <colmap_sparse_model_dir>
    python check_turntable.py --self-test
"""
import argparse
import json
import struct
import sys
from pathlib import Path

import numpy as np

FULL_TURN_MIN_DEG = 270.0   # a capture that goes right round should clear this comfortably

# Frame-order limits. A02, which is correct, steps 11.1 deg between consecutive frames and
# has NO within-pass step above 30 deg. A03, which is bent, steps 11.6 deg in the median and
# has sixteen, the worst 109 deg. Either term alone would be fragile: the multiple adapts to
# how finely a tree was shot, the floor stops a coarsely shot one tripping on every frame.
#
# N01's marker board lets that headroom be measured rather than hoped for, because the board
# gives the true angle of all 119 frames without reference to any solve. The turntable is
# advanced BY HAND and has no detents: across 114 within-pass steps the median is 15.1 deg
# with a standard deviation of 2.3 deg, and the extremes are 7.4 and 22.7 deg. So a correct
# capture really does wander by a few degrees a step, and the limit this rule would apply to
# N01 -- max(30, 2.5 * 15.1) = 37.7 deg -- clears the worst honest step by 1.7x. The check is
# not close to a false alarm on good data, which is the only thing that makes it safe to fail
# a tree on.
STEP_ABS_MIN_DEG = 30.0
STEP_MEDIAN_MULT = 2.5

# How far a frame may sit from where the marker board says it was. The board reference for
# N01 reproduces its own rig to a small fraction of a degree, and a turntable step is 15
# deg, so 5 deg is a third of a step -- far too small to be a rounding artefact and far too
# large to trip on solve noise. A03's bent frames were out by 35 to 109 deg.
REFERENCE_TOL_DEG = 5.0
REFERENCE_MAX_BAD = 0        # any frame past the tolerance is a failure, not a warning


def read_points(model_dir):
    path = Path(model_dir) / "points3D.bin"
    with open(path, "rb") as fh:
        (n,) = struct.unpack("<Q", fh.read(8))
        xyz = np.empty((n, 3))
        for i in range(n):
            _, x, y, z, _r, _g, _b, _err = struct.unpack("<QdddBBBd", fh.read(43))
            (track,) = struct.unpack("<Q", fh.read(8))
            fh.seek(8 * track, 1)
            xyz[i] = (x, y, z)
    return xyz


def read_camera_centres(model_dir):
    """Camera centres AND the filename each came from.

    The name matters as much as the position: frame numbers run in shooting order as the
    turntable is advanced, so they are the only record of what the rotation was SUPPOSED to
    be. Without them a bent solve is indistinguishable from a correct one.
    """
    path = Path(model_dir) / "images.bin"
    centres, names = [], []
    with open(path, "rb") as fh:
        (n,) = struct.unpack("<Q", fh.read(8))
        for _ in range(n):
            _, qw, qx, qy, qz, tx, ty, tz, _cam = struct.unpack("<idddddddi", fh.read(64))
            nm = b""
            while True:
                c = fh.read(1)
                if c == b"\x00":
                    break
                nm += c
            names.append(nm.decode("utf-8", "replace"))
            (pts,) = struct.unpack("<Q", fh.read(8))
            fh.seek(24 * pts, 1)
            R = np.array([
                [1 - 2 * (qy * qy + qz * qz), 2 * (qx * qy - qz * qw), 2 * (qx * qz + qy * qw)],
                [2 * (qx * qy + qz * qw), 1 - 2 * (qx * qx + qz * qz), 2 * (qy * qz - qx * qw)],
                [2 * (qx * qz - qy * qw), 2 * (qy * qz + qx * qw), 1 - 2 * (qx * qx + qy * qy)],
            ])
            centres.append(-R.T @ np.array([tx, ty, tz]))
    return np.array(centres), names


def basis(direction):
    f = np.asarray(direction, float); f /= np.linalg.norm(f)
    up = np.array([0.0, 0.0, 1.0])
    if abs(f @ up) > 0.95:
        up = np.array([0.0, 1.0, 0.0])
    r = np.cross(f, up); r /= np.linalg.norm(r)
    return np.stack([r, np.cross(r, f), f])


def frame_order(names, ang_by_name):
    """Do consecutive photographs sit next to each other around the turn?

    Coverage alone cannot answer this, and that is the hole this fills. Tree A03 covered
    321 deg -- comfortably past the collapse threshold -- with every photograph registered
    and a mean reprojection error BETTER than a tree that was correct (0.809 vs 0.841 px).
    It was still wrong: sixteen pairs of consecutive frames sat more than 30 deg apart, one
    of them 109 deg, and the blue base plate was consequently built twice, 35 deg apart, in
    the sparse model and in every mesh derived from it.

    Frames are grouped by filename prefix, because each prefix is one pass of the turntable
    at one camera height. Within a pass the turntable advances by one small step per shot,
    so the angle must walk smoothly round; the jump BETWEEN passes is expected and is not
    counted. What is measured is therefore the thing the capture actually controlled.
    """
    groups = {}
    for nm in names:
        groups.setdefault(nm.split("_")[0], []).append(nm)

    steps, offenders = [], []
    for pref, members in sorted(groups.items()):
        members.sort()                      # frame numbers ascend in shooting order
        for a, b in zip(members, members[1:]):
            d = abs(ang_by_name[b] - ang_by_name[a]) % 360
            d = min(d, 360 - d)
            steps.append(d)
            offenders.append((d, pref, a, b))
    if not steps:
        return None

    steps = np.array(steps)
    med = float(np.median(steps))
    # A step is out of order when it is far beyond the pace the capture was shot at. Both
    # terms matter: the multiple catches a fine-grained capture, the floor stops a very
    # coarse one flagging every frame.
    limit = max(STEP_ABS_MIN_DEG, STEP_MEDIAN_MULT * med)
    bad = sorted((o for o in offenders if o[0] > limit), reverse=True)

    print(f"  consecutive frames step {med:.1f} deg apart (median), "
          f"{len(groups)} camera pass(es)")
    if not bad:
        print(f"  -> ORDER OK  no frame sits more than {limit:.0f} deg from the one before it")
        return 0
    print(f"  -> OUT OF ORDER  {len(bad)} consecutive pair(s) more than {limit:.0f} deg apart:")
    for d, pref, a, b in bad[:6]:
        print(f"       {a} -> {b}   {d:.0f} deg")
    if len(bad) > 6:
        print(f"       ... and {len(bad)-6} more")
    print("     These were shot one turntable step apart, so they cannot be this far")
    print("     around the rig. The solve is BENT: registered, low reprojection error,")
    print("     and still placing frames at the wrong rotation. Geometry seen mainly by")
    print("     the misplaced frames gets built more than once.")
    return len(bad)


def umeyama(A, B):
    """Similarity transform taking A onto B (scale, rotation, translation). No reflection.

    Reflection is refused on purpose. A COLMAP model and the reference are both
    right-handed, so a fit that only works mirrored is telling you the two disagree about
    which way the turntable turned -- which is a finding, not something to absorb into the
    fit and hide.
    """
    ca, cb = A.mean(0), B.mean(0)
    X, Y = A - ca, B - cb
    U, S, Vt = np.linalg.svd(X.T @ Y)
    D = np.eye(3)
    D[2, 2] = np.sign(np.linalg.det(U @ Vt))     # keeps the rotation proper
    R = (U @ D @ Vt).T
    s = (S * np.diag(D)).sum() / (X ** 2).sum()
    return s, R, cb - s * R @ ca


def compare_to_reference(model_dir, ref_path):
    """Is every frame where the marker board says it was?

    The reference gives each photograph a position on the rig -- angle round the turn,
    distance from the axis, height. The solve gives its own camera centres in its own
    arbitrary frame. Fitting one similarity transform between the two removes that
    arbitrariness and nothing else: after it, any frame still in the wrong place IS in the
    wrong place.

    The fit is made robust by dropping frames that disagree badly and refitting, because
    otherwise the very frames being looked for would drag the alignment onto themselves
    and shrink their own residuals. That failure mode is the whole reason a bent solve is
    hard to catch.
    """
    ref = json.loads(Path(ref_path).read_text())
    frames = ref["frames"]
    C, names = read_camera_centres(model_dir)
    stem = {Path(n).stem: i for i, n in enumerate(names)}

    common = [k for k in frames if k in stem]
    if len(common) < 8:
        print(f"  -> reference names do not match this model "
              f"({len(common)} of {len(frames)} matched); nothing to compare")
        return None

    th = np.radians([frames[k]["deg"] for k in common])
    r = np.array([frames[k]["radius_m"] for k in common])
    P = np.stack([r * np.cos(th), r * np.sin(th),
                  [frames[k]["height_m"] for k in common]], 1)
    Q = np.array([C[stem[k]] for k in common])

    keep = np.ones(len(common), bool)
    for _ in range(6):
        s, R, t = umeyama(Q[keep], P[keep])
        res = np.linalg.norm((s * (R @ Q.T).T + t) - P, axis=1)
        med = np.median(res[keep])
        new = res < max(3 * med, 0.005)          # 5 mm floor: never reject on pure noise
        if new.sum() < 8 or (new == keep).all():
            break
        keep = new

    A = s * (R @ Q.T).T + t
    got = np.degrees(np.arctan2(A[:, 1], A[:, 0]))
    d = np.abs((got - np.degrees(th) + 180) % 360 - 180)
    mm = np.linalg.norm(A - P, axis=1) * 1000

    print(f"  compared against {Path(ref_path).name}: {len(common)} of {len(frames)} "
          f"reference frames present, {keep.sum()} used to align")
    print(f"  angle vs the board: median {np.median(d):.2f} deg, "
          f"90th pct {np.percentile(d, 90):.2f}, worst {d.max():.2f}")
    print(f"  position vs the board: median {np.median(mm):.1f} mm, worst {mm.max():.0f} mm")

    # METRIC SCALE, free. The alignment above already had to solve for `s` to compare the
    # two rigs at all, and `s` is exactly the factor that turns this model's arbitrary units
    # into the reference's metres. It is worth saying out loud because of what it is built
    # on: 119 camera positions spread over 350 deg and half a metre of height, from a solve
    # that used every frame. The alternative route -- the base plate in the Metashape
    # project -- rests on four mouse clicks whose own edge ratio is wrong by 3.16 %. More
    # evidence is not automatically better evidence, but here it also happens to be the
    # only route whose inputs were machine-detected.
    #
    # The reference's OWN scale is a separate question and not settled here; see
    # `board_scale.py`, which will not invent the printed sheet's pitch. If that pitch is
    # later measured, this factor moves with it and nothing else changes.
    print(f"  metric scale: multiply this model's lengths by {s:.6f} to get metres")
    print(f"                (from {int(keep.sum())} camera positions, not from the base plate)")

    bad = sorted(zip(d, mm, common), reverse=True)
    n_bad = int((d > REFERENCE_TOL_DEG).sum())
    if n_bad <= REFERENCE_MAX_BAD:
        print(f"  -> AGREES WITH THE BOARD  every frame within {REFERENCE_TOL_DEG:.0f} deg "
              "of where the turntable actually was")
    else:
        print(f"  -> DISAGREES WITH THE BOARD  {n_bad} frame(s) more than "
              f"{REFERENCE_TOL_DEG:.0f} deg from where the turntable actually was:")
        for dd, mmm, nm in bad[:8]:
            if dd <= REFERENCE_TOL_DEG:
                break
            print(f"       {nm}  {dd:6.1f} deg  ({mmm:.0f} mm) out")
        if n_bad > 8:
            print(f"       ... and {n_bad - 8} more")
        print("     This is not a question about whether the solve is self-consistent.")
        print("     The board was bolted to the turntable and photographed; these frames")
        print("     are not where it says they were.")
    missing = [k for k in frames if k not in stem]
    if missing:
        print(f"  note: {len(missing)} reference frame(s) absent from this model "
              f"(e.g. {', '.join(sorted(missing)[:3])})")
    return n_bad, float(s)


def check(model_dir, reference=None):
    xyz = read_points(model_dir)
    C, names = read_camera_centres(model_dir)
    if len(xyz) < 100 or len(C) < 8:
        print(f"{model_dir}: too small to judge ({len(xyz)} points, {len(C)} images)")
        return None

    # The rig is a tree on a base: its longest axis is the trunk, which is also the axis
    # the turntable spins about. Trim outliers first so the backdrop cannot tilt the fit.
    lo, hi = np.percentile(xyz, [2, 98], axis=0)
    core = xyz[np.all((xyz > lo) & (xyz < hi), axis=1)]
    ctr = core.mean(0)
    _, _, Vt = np.linalg.svd(core - ctr, full_matrices=False)
    axis = Vt[0]

    q = (C - ctr) @ basis(axis).T
    ang = np.sort(np.degrees(np.arctan2(q[:, 1], q[:, 0])))
    # Coverage is the circle minus the largest unvisited gap -- ptp would read 360 for a
    # cluster that merely straddles the +/-180 wrap.
    gap = np.diff(np.concatenate([ang, [ang[0] + 360]])).max()
    covered = 360 - gap

    verdict = "OK" if covered >= FULL_TURN_MIN_DEG else "COLLAPSED"
    print(f"\n{Path(model_dir).parent.name}/{Path(model_dir).name}")
    print(f"  images {len(C)},  points {len(xyz):,}")
    print(f"  camera positions cover {covered:6.1f} deg around the rig  (largest gap {gap:.0f} deg)")
    print(f"  -> {verdict}", end="")
    if verdict == "OK":
        print("  the camera travels round the object, so the turn was understood")
    else:
        print(f"  the camera sits in a {covered:.0f} deg arc, so the turntable's rotation")
        print("     has been absorbed into duplicated geometry instead")

    # SECOND, INDEPENDENT QUESTION. Coverage asks how much of the circle was visited;
    # this asks whether the frames were visited in the order they were shot. A solve can
    # pass the first and fail the second, and A03 did.
    ang_by_name = dict(zip(names, np.degrees(np.arctan2(q[:, 1], q[:, 0]))))
    n_bad = frame_order(names, ang_by_name)
    if n_bad:
        print("  -> BENT")

    # THIRD QUESTION, and the only one with an outside answer: does the solve agree with
    # the turntable itself? The two above can both pass on a solve that is wrong smoothly.
    ref_bad = None
    if reference:
        ref_bad, _ = compare_to_reference(model_dir, reference)
    return dict(covered=covered, collapsed=verdict != "OK", bent=bool(n_bad),
                ref_bad=ref_bad)


def exit_code_for(result):
    """One check()'s result -> the status the job scheduler sees. See __main__ for the map.

    A model with a reference is judged ONLY on the reference. The inferred checks are
    noisier and the board outranks them; reporting them as failures beside a passing board
    reading would train everyone to ignore the exit code.
    """
    if result is None:
        return 3
    if result["ref_bad"] is not None:
        return 1 if result["ref_bad"] else 0
    return 2 if (result["collapsed"] or result["bent"]) else 0


def self_test(reference):
    """Prove the reference check can both pass and fail.

    A gate that has only ever been seen to pass is indistinguishable from a gate that
    always passes -- a mask that silently did nothing cost 1h37m in this repo, and a
    metric that never moved faked a whole finding in TORA. So: take the reference, turn it
    into a synthetic COLMAP model, and run three cases whose right answers are known in
    advance.
    """
    import tempfile

    ref = json.loads(Path(reference).read_text())
    names = sorted(ref["frames"])
    th = np.radians([ref["frames"][n]["deg"] for n in names])
    r = np.array([ref["frames"][n]["radius_m"] for n in names])
    P = np.stack([r * np.cos(th), r * np.sin(th),
                  [ref["frames"][n]["height_m"] for n in names]], 1)

    # An arbitrary rigid change of frame plus a scale, of the kind a COLMAP model always
    # differs by. The check must see through this and report zero.
    ang = 0.7
    R = np.array([[np.cos(ang), -np.sin(ang), 0], [np.sin(ang), np.cos(ang), 0], [0, 0, 1]])
    R = R @ np.array([[1, 0, 0], [0, np.cos(0.3), -np.sin(0.3)], [0, np.sin(0.3), np.cos(0.3)]])

    cases = {
        "a faithful solve, in a different frame and scale": P.copy(),
        "a BENT solve: six frames rotated 40 deg round the axis": None,
        "a COLLAPSED solve: every frame squeezed into a 60 deg arc": None,
    }
    bent = P.copy()
    for i in range(3, 3 + 6 * 7, 7):
        a = th[i] + np.radians(40)
        bent[i, :2] = [r[i] * np.cos(a), r[i] * np.sin(a)]
    cases["a BENT solve: six frames rotated 40 deg round the axis"] = bent
    coll = P.copy()
    a = th * (60.0 / 360.0)
    coll[:, 0], coll[:, 1] = r * np.cos(a), r * np.sin(a)
    cases["a COLLAPSED solve: every frame squeezed into a 60 deg arc"] = coll

    expect = [0, 6, "many"]
    ok = True
    with tempfile.TemporaryDirectory() as td:
        for (label, pts), want in zip(cases.items(), expect):
            d = Path(td) / label[:12].replace(" ", "_")
            d.mkdir()
            C = 3.4 * (R @ pts.T).T + np.array([5.0, -2.0, 9.0])
            _write_images_bin(d, names, C)
            _write_points_bin(d, C)
            print(f"\n-- {label}")
            got, scale = compare_to_reference(d, reference)
            good = (got == want) if isinstance(want, int) else (got > 20)
            print(f"   expected {want} bad frame(s), got {got}  -> {'OK' if good else 'WRONG'}")

            # The EXIT STATUS, not just the frame count. This is what the Slurm script
            # branches on, so it is what has to be proven -- the number above could be
            # perfect while the status stayed 0 and the dense stage ran anyway. That is
            # not hypothetical: it was true of this script until 2026-08-23.
            want_rc = 0 if want == 0 else 1
            rc = exit_code_for(check(d, reference))
            print(f"   exit status {rc}, expected {want_rc}  "
                  f"-> {'OK' if rc == want_rc else 'WRONG'}")
            ok &= bool(rc == want_rc)
            # The metric scale is asserted, not just printed. The synthetic model is built
            # at 3.4x, so a correct recovery is exactly 1/3.4. The BENT case must recover it
            # too: the robust refit drops the six planted frames, so scale must survive
            # damage that the angle check is meanwhile required to catch. Only the COLLAPSED
            # case may get it wrong -- a solve that folded the turn has no true scale left,
            # and a checker that still reported a confident metre there would be lying.
            if want != "many":
                serr = abs(scale * 3.4 - 1) * 100
                sgood = serr < 0.01
                print(f"   metric scale {scale:.6f} vs 1/3.4 = {1/3.4:.6f}  "
                      f"({serr:.4f} % off)  -> {'OK' if sgood else 'WRONG'}")
                ok &= bool(sgood)
            ok &= bool(good)
    print("\nself-test:", "PASSED" if ok else "FAILED")
    return 0 if ok else 1


def _write_points_bin(d, C):
    """A synthetic points3D.bin, so the self-test can run check() rather than only the
    reference comparison underneath it.

    check() infers the turntable axis from the point cloud, so the cloud has to be shaped
    like the rig, or the inferred half would fail for reasons unrelated to what is being
    tested. A tall thin column through the middle of the cameras is enough: its longest
    axis is the trunk, which is the axis the turntable spins about.
    """
    ctr = C.mean(0)
    up = np.linalg.svd(C - ctr, full_matrices=False)[2][2]      # the thin direction
    rng = np.random.default_rng(0)
    span = float(np.linalg.norm(C - ctr, axis=1).max())
    pts = (ctr + np.outer(rng.uniform(-span, span, 600), up)
           + rng.normal(0, 0.02 * span, (600, 3)))
    with open(Path(d) / "points3D.bin", "wb") as fh:
        fh.write(struct.pack("<Q", len(pts)))
        for i, (x, y, z) in enumerate(pts):
            fh.write(struct.pack("<QdddBBBd", i, x, y, z, 128, 128, 128, 0.5))
            fh.write(struct.pack("<Q", 0))


def _write_images_bin(d, names, C):
    """Minimal COLMAP images.bin holding just camera poses -- enough for the checks here."""
    with open(Path(d) / "images.bin", "wb") as fh:
        fh.write(struct.pack("<Q", len(names)))
        for i, (nm, c) in enumerate(zip(names, C)):
            # identity rotation, so t = -R @ C reduces to -C
            fh.write(struct.pack("<idddddddi", i, 1.0, 0.0, 0.0, 0.0, *(-c), 0))
            fh.write(nm.encode() + b"\x00")
            fh.write(struct.pack("<Q", 0))


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("models", nargs="*", help="COLMAP sparse model directories")
    ap.add_argument("--reference", help="turntable reference JSON from board_frame.py")
    ap.add_argument("--self-test", action="store_true",
                    help="prove the --reference check can both pass and fail")
    a = ap.parse_args()
    if a.self_test:
        if not a.reference:
            sys.exit("--self-test needs --reference")
        sys.exit(self_test(a.reference))
    if not a.models:
        sys.exit(__doc__)

    # EXIT STATUS, because this is called from slurm/reconstruct_group.slurm and a gate
    # that cannot fail is not a gate. It was one for a while: the caller had `|| true` on
    # it and this function returned nothing but coverage, so the strict form would have
    # printed a page of disagreeing frames and let the dense stage run anyway.
    #
    #   0  every model checked agrees with what it was checked against
    #   1  a model disagrees with the MARKER BOARD -- an outside measurement, not an
    #      opinion about self-consistency. Stop and look.
    #   2  no reference was given and the inferred check found a collapsed or bent solve.
    #      Distinct from 1 because the evidence is weaker: it is the solve judging itself.
    #   3  a model was too small to judge. Not a pass.
    #
    # A model with a reference is judged ONLY on the reference. The inferred checks are
    # noisier and the board outranks them -- reporting them as failures beside a passing
    # board reading would train everyone to ignore the exit code.
    worst = 0
    for d in a.models:
        worst = max(worst, exit_code_for(check(d, a.reference)))
    sys.exit(worst)
