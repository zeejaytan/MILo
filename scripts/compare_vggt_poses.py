"""Compare VGGT demo_colmap poses against the COLMAP solve on the same capture.

Reads two COLMAP-format sparse models (cameras.bin/images.bin), matches views by
filename stem, aligns VGGT camera centres to COLMAP with a Sim(3) Umeyama fit
(scale anchored separately via --mm_per_unit), and reports pose agreement.

An unscaled comparison is refused: pass --mm_per_unit from the capture's own
measurement.env (same source every other A03 millimetre figure uses).

Usage:
    python compare_vggt_poses.py --colmap <sparse_dir> --vggt <sparse_dir> \\
        --mm_per_unit <mm> --out <report.json>
"""

import argparse
import json
import struct
import sys
from pathlib import Path

import numpy as np


def qvec_to_rotmat(qvec):
    w, x, y, z = qvec
    return np.array([
        [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
        [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
        [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)],
    ])


def read_images_bin(path):
    """Minimal reader for COLMAP images.bin (no pycolmap dependency)."""
    images = {}
    with open(path, "rb") as f:
        (num,) = struct.unpack("<Q", f.read(8))
        for _ in range(num):
            (img_id,) = struct.unpack("<i", f.read(4))
            qvec = np.array(struct.unpack("<4d", f.read(32)))
            tvec = np.array(struct.unpack("<3d", f.read(24)))
            (cam_id,) = struct.unpack("<i", f.read(4))
            name = b""
            while True:
                ch = f.read(1)
                if ch == b"\x00":
                    break
                name += ch
            name = name.decode("utf-8")
            (n_pts,) = struct.unpack("<Q", f.read(8))
            f.read(24 * n_pts)  # x, y, point3d_id per observation
            R = qvec_to_rotmat(qvec / np.linalg.norm(qvec))
            C = -R.T @ tvec
            images[name] = (R, C)
    return images


def stem(name):
    # A31_1100.JPG vs A31_1100.JPG.png style mismatches: compare first stem.
    return Path(name).stem.split(".")[0]


def umeyama(src, dst):
    """Sim(3) aligning src onto dst. Returns scale, R, t."""
    mu_s = src.mean(0)
    mu_d = dst.mean(0)
    S = (src - mu_s).T @ (dst - mu_d) / len(src)
    U, D, Vt = np.linalg.svd(S)
    R = Vt.T @ U.T
    if np.linalg.det(R) < 0:
        Vt[-1, :] = -Vt[-1, :]
        R = Vt.T @ U.T
    var_s = ((src - mu_s) ** 2).sum() / len(src)
    scale = D.sum() / var_s
    t = mu_d - scale * R @ mu_s
    return scale, R, t


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--colmap", required=True)
    ap.add_argument("--vggt", required=True)
    ap.add_argument("--mm_per_unit", required=True, type=float)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    if not np.isfinite(args.mm_per_unit) or args.mm_per_unit <= 0:
        sys.exit("refusing: --mm_per_unit must be a positive measured figure")

    col = read_images_bin(str(Path(args.colmap) / "images.bin"))
    vgg = read_images_bin(str(Path(args.vggt) / "images.bin"))
    vgg_by_stem = {stem(k): v for k, v in vgg.items()}

    pairs = [(c, vgg_by_stem[stem(k)]) for k, c in col.items()
             if stem(k) in vgg_by_stem]
    n_col, n_vgg, n_match = len(col), len(vgg), len(pairs)
    if n_match < 3:
        sys.exit(f"refusing: only {n_match} matched views "
                 f"(colmap {n_col}, vggt {n_vgg})")

    C_col = np.array([c for (_, c), _ in pairs])
    R_col = [r for (r, _), _ in pairs]
    C_vg = np.array([c for _, (_, c) in pairs])
    R_vg = [r for _, (r, _) in pairs]

    scale, R_align, t_align = umeyama(C_vg, C_col)
    C_fit = (scale * (R_align @ C_vg.T)).T + t_align

    trans_mm = np.linalg.norm(C_fit - C_col, axis=1) * args.mm_per_unit
    rot_deg = np.array([
        np.degrees(np.arccos(np.clip((np.trace(rc.T @ R_align @ rv) - 1) / 2,
                                     -1, 1)))
        for rc, rv in zip(R_col, R_vg)
    ])

    report = {
        "n_colmap": n_col,
        "n_vggt": n_vgg,
        "n_matched": n_match,
        "registration_rate": n_match / n_col,
        "scale_vggt_to_colmap": float(scale),
        "rot_err_deg": {"mean": float(rot_deg.mean()),
                        "median": float(np.median(rot_deg)),
                        "p90": float(np.percentile(rot_deg, 90))},
        "trans_err_mm": {"mean": float(trans_mm.mean()),
                         "median": float(np.median(trans_mm)),
                         "p90": float(np.percentile(trans_mm, 90))},
        "auc": {f"@{t}deg": float((rot_deg < t).mean()) for t in (3, 5, 10)},
        "mm_per_unit": args.mm_per_unit,
    }
    Path(args.out).write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
