"""How much detail did each capture physically record, in pixels per millimetre?

This is the ceiling on everything downstream. No amount of training or meshing recovers
detail the photographs never held. It is set by three things only: the lens focal length in
pixels, how far the camera stood from the object, and the millimetre scale of the model.

    pixels per mm on the object = focal_px / distance_mm

Reported per capture, with the spread across views, plus the object's size so the numbers
can be sanity-checked against something physical.
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, "/data/gpfs/projects/punim2657/MILo/repo/scripts")
from measure_base import read_cameras, read_images, read_points3D   # noqa: E402


def analyse(label, sparse_dir, mm_per_unit):
    sparse_dir = Path(sparse_dir)
    cams = read_cameras(sparse_dir / "cameras.bin")
    imgs = read_images(sparse_dir / "images.bin")
    P, _rgb = read_points3D(sparse_dir / "points3D.bin")
    P = np.asarray(P)[:, :3]

    # Robust scene centre: the middle of the point cloud, trimmed so strays do not drag it.
    lo, hi = np.percentile(P, [5, 95], axis=0)
    core = P[np.all((P >= lo) & (P <= hi), axis=1)]
    ctr = core.mean(0)

    # Camera centres:  C = -R^T t
    C = np.array([-im["R"].T @ im["t"] for im in imgs])
    d_units = np.linalg.norm(C - ctr, axis=1)
    d_mm = d_units * mm_per_unit

    cam = cams[imgs[0]["cam"]]
    f = cam["params"][0]

    ppm = f / d_mm
    ext = np.ptp(core, 0) * mm_per_unit
    print(f"\n{label}")
    print(f"  {len(imgs)} views, {cam['w']}x{cam['h']} px, focal {f:.0f} px")
    print(f"  camera stood {np.median(d_mm):.0f} mm from the object "
          f"(range {d_mm.min():.0f}-{d_mm.max():.0f})")
    print(f"  object core spans {ext[0]:.0f} x {ext[1]:.0f} x {ext[2]:.0f} mm")
    print(f"  --> {np.median(ppm):.1f} pixels per mm on the object "
          f"({np.percentile(ppm,10):.1f}-{np.percentile(ppm,90):.1f})")
    print(f"      i.e. one pixel covers {1000/np.median(ppm):.0f} microns of the sherd")
    return np.median(ppm)


if __name__ == "__main__":
    R = "/data/gpfs/projects/punim2657/MILo/data"
    out = {}
    out["A01"] = analyse("A01  16062025 (MILo trained unmasked)",
                         f"{R}/16062025/sparse/0", 377.53)
    out["A02"] = analyse("A02  17062025 (MILo trained unmasked)",
                         f"{R}/17062025/A02/sparse/0", 377.53)
    out["A03"] = analyse("A03  17062025 (MILo trained on masks_object)",
                         f"{R}/17062025/A03/sparse/0", 373.73)
    print("\nratio A02 : A03 = %.2f x" % (out["A02"] / out["A03"]))
