"""Where is the gap in the camera arc, and does it follow the shooting order?

check_turntable.py reports one number -- how much of the circle the cameras cover. That is
enough to catch a collapse, but not to explain a hole. A02 came out at 262 degrees with a
single 98-degree gap while registering all 162 photographs, which is not the GLOMAP-style
collapse (67 degrees, cameras piled in one place). Two explanations fit and they lead
somewhere different:

  CAPTURE     the turntable was never turned through those angles, so no photograph exists
              there. Nothing is wrong; the gate's threshold is simply wrong for this tree.

  SOLVE       photographs exist at those angles but were placed elsewhere, which would mean
              the reconstruction is bent even though every image registered.

The shooting order separates them. Frame numbers run in sequence as the turntable is
advanced, so if the gap is real the angle should step smoothly through the frames and
simply stop short of a full turn. If the solve is bent, consecutive frames will jump
across the gap.

Usage:
    python camera_arc_detail.py <sparse_model_dir> [more dirs ...]
"""
import struct
import sys
from pathlib import Path

import numpy as np


def read_model(model_dir):
    d = Path(model_dir)
    with open(d / "points3D.bin", "rb") as fh:
        (n,) = struct.unpack("<Q", fh.read(8))
        xyz = np.empty((n, 3))
        for i in range(n):
            _, x, y, z, _r, _g, _b, _e = struct.unpack("<QdddBBBd", fh.read(43))
            (t,) = struct.unpack("<Q", fh.read(8))
            fh.seek(8 * t, 1)
            xyz[i] = (x, y, z)
    centres, names = [], []
    with open(d / "images.bin", "rb") as fh:
        (n,) = struct.unpack("<Q", fh.read(8))
        for _ in range(n):
            _, qw, qx, qy, qz, tx, ty, tz, _c = struct.unpack("<idddddddi", fh.read(64))
            nm = b""
            while (ch := fh.read(1)) != b"\x00":
                nm += ch
            (p,) = struct.unpack("<Q", fh.read(8))
            fh.seek(24 * p, 1)
            R = np.array([
                [1-2*(qy*qy+qz*qz), 2*(qx*qy-qz*qw), 2*(qx*qz+qy*qw)],
                [2*(qx*qy+qz*qw), 1-2*(qx*qx+qz*qz), 2*(qy*qz-qx*qw)],
                [2*(qx*qz-qy*qw), 2*(qy*qz+qx*qw), 1-2*(qx*qx+qy*qy)]])
            centres.append(-R.T @ np.array([tx, ty, tz]))
            names.append(nm.decode())
    return xyz, np.array(centres), names


def basis(direction):
    f = np.asarray(direction, float); f /= np.linalg.norm(f)
    up = np.array([0.0, 0.0, 1.0])
    if abs(f @ up) > 0.95:
        up = np.array([0.0, 1.0, 0.0])
    r = np.cross(f, up); r /= np.linalg.norm(r)
    return np.stack([r, np.cross(r, f), f])


def analyse(model_dir):
    xyz, C, names = read_model(model_dir)
    lo, hi = np.percentile(xyz, [2, 98], axis=0)
    core = xyz[np.all((xyz > lo) & (xyz < hi), axis=1)]
    ctr = core.mean(0)
    _, _, Vt = np.linalg.svd(core - ctr, full_matrices=False)
    q = (C - ctr) @ basis(Vt[0]).T
    ang = np.degrees(np.arctan2(q[:, 1], q[:, 0]))

    order = np.argsort(names)
    ang_o, names_o = ang[order], [names[i] for i in order]

    srt = np.sort(ang)
    gaps = np.diff(np.concatenate([srt, [srt[0] + 360]]))
    k = int(np.argmax(gaps))
    gap_lo, gap_hi = srt[k], srt[(k + 1) % len(srt)]

    print(f"\n=== {Path(model_dir).parent.name}/{Path(model_dir).name} ===")
    print(f"  {len(C)} cameras, covering {360 - gaps.max():.1f} deg; "
          f"largest gap {gaps.max():.0f} deg (from {gap_lo:+.0f} to {gap_hi:+.0f})")

    # Step between CONSECUTIVE photographs, in shooting order. A capture that simply stops
    # short shows small steps throughout; a bent solve shows a jump across the gap.
    step = np.abs(np.diff(ang_o))
    step = np.minimum(step, 360 - step)
    big = np.where(step > 30)[0]
    print(f"  angle step between consecutive frames: median {np.median(step):.1f} deg, "
          f"max {step.max():.1f} deg")
    print(f"  steps over 30 deg: {len(big)}")
    for i in big[:6]:
        print(f"     {names_o[i]} -> {names_o[i+1]}   {ang_o[i]:+.0f} to {ang_o[i+1]:+.0f}"
              f"   ({step[i]:.0f} deg)")

    # Which frames sit at the edges of the hole: if the capture stopped, they are the
    # first and last of the sequence or of a prefix block.
    near_lo = [names_o[i] for i in range(len(ang_o)) if abs(ang_o[i] - gap_lo) < 6]
    near_hi = [names_o[i] for i in range(len(ang_o)) if abs(ang_o[i] - gap_hi) < 6]
    print(f"  frames at the start of the hole: {near_lo[:4]}")
    print(f"  frames at the end of the hole:   {near_hi[:4]}")

    # Coverage per filename prefix -- the camera was moved between prefixes.
    print("  arc covered by each filename prefix:")
    for pre in sorted({n.split('_')[0] for n in names_o}):
        a = np.sort([ang_o[i] for i, n in enumerate(names_o) if n.startswith(pre + "_")])
        if len(a) < 2:
            continue
        g = np.diff(np.concatenate([a, [a[0] + 360]]))
        print(f"     {pre}: {len(a):3d} frames, spans {360 - g.max():5.1f} deg "
              f"({a.min():+.0f} to {a.max():+.0f})")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    for d in sys.argv[1:]:
        analyse(d)
