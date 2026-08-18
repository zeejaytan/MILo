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

Usage:
    python check_turntable.py <colmap_sparse_model_dir> [more dirs ...]
"""
import struct
import sys
from pathlib import Path

import numpy as np

FULL_TURN_MIN_DEG = 270.0   # a capture that goes right round should clear this comfortably

# Frame-order limits. A02, which is correct, steps 11.1 deg between consecutive frames and
# has NO within-pass step above 30 deg. A03, which is bent, steps 11.6 deg in the median and
# has sixteen, the worst 109 deg. Either term alone would be fragile: the multiple adapts to
# how finely a tree was shot, the floor stops a coarsely shot one tripping on every frame.
STEP_ABS_MIN_DEG = 30.0
STEP_MEDIAN_MULT = 2.5


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


def check(model_dir):
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
    return covered


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    for d in sys.argv[1:]:
        check(d)
