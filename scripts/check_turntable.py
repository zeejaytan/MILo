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
    path = Path(model_dir) / "images.bin"
    centres = []
    with open(path, "rb") as fh:
        (n,) = struct.unpack("<Q", fh.read(8))
        for _ in range(n):
            _, qw, qx, qy, qz, tx, ty, tz, _cam = struct.unpack("<idddddddi", fh.read(64))
            while fh.read(1) != b"\x00":
                pass
            (pts,) = struct.unpack("<Q", fh.read(8))
            fh.seek(24 * pts, 1)
            R = np.array([
                [1 - 2 * (qy * qy + qz * qz), 2 * (qx * qy - qz * qw), 2 * (qx * qz + qy * qw)],
                [2 * (qx * qy + qz * qw), 1 - 2 * (qx * qx + qz * qz), 2 * (qy * qz - qx * qw)],
                [2 * (qx * qz - qy * qw), 2 * (qy * qz + qx * qw), 1 - 2 * (qx * qx + qy * qy)],
            ])
            centres.append(-R.T @ np.array([tx, ty, tz]))
    return np.array(centres)


def basis(direction):
    f = np.asarray(direction, float); f /= np.linalg.norm(f)
    up = np.array([0.0, 0.0, 1.0])
    if abs(f @ up) > 0.95:
        up = np.array([0.0, 1.0, 0.0])
    r = np.cross(f, up); r /= np.linalg.norm(r)
    return np.stack([r, np.cross(r, f), f])


def check(model_dir):
    xyz = read_points(model_dir)
    C = read_camera_centres(model_dir)
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
    return covered


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    for d in sys.argv[1:]:
        check(d)
