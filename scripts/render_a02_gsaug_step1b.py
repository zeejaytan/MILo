"""Real-vs-render crops on SH5-framing views (GS-augment A02 cheap test, step 1b).

CPU-only. Projects the sherd box into each requested view with the COLMAP
cameras, crops the MILo render and its ground-truth twin to that window, and
reports PSNR inside the window. A full-frame score would be dominated by the
room; the matcher reads the break, so the window is the honest instrument.

Render/gt files are index-named by milo/render.py in the ordermilO loads
cameras: all names sorted, every 8th (0-based idx % llffhold == 0) held out as
test, the rest train in order. This mapping is verified against
capture.json's held_out_views before anything is read.
"""
from __future__ import annotations

import argparse
import json
import struct
from pathlib import Path

import numpy as np
from PIL import Image


def read_cameras(model_dir: Path):
    cams = {}
    with open(model_dir / "cameras.bin", "rb") as fh:
        (n,) = struct.unpack("<Q", fh.read(8))
        for _ in range(n):
            cam_id, model_id, w, h = struct.unpack("<iiQQ", fh.read(24))
            nparams = {0: 4, 1: 4, 2: 5, 3: 5, 4: 8, 5: 8, 6: 12}[model_id]
            params = struct.unpack("<" + "d" * nparams, fh.read(8 * nparams))
            fx, fy, cx, cy = params[:4]
            cams[cam_id] = (w, h, np.array([[fx, 0, cx], [0, fy, cy], [0, 0, 1]]))
    return cams


def read_images(model_dir: Path):
    out = {}
    with open(model_dir / "images.bin", "rb") as fh:
        (n,) = struct.unpack("<Q", fh.read(8))
        for _ in range(n):
            img_id, qw, qx, qy, qz, tx, ty, tz, cam_id = struct.unpack("<idddddddi", fh.read(64))
            nm = b""
            while (ch := fh.read(1)) != b"\x00":
                nm += ch
            (p,) = struct.unpack("<Q", fh.read(8))
            fh.seek(24 * p, 1)
            R = np.array([
                [1 - 2 * (qy * qy + qz * qz), 2 * (qx * qy - qz * qw), 2 * (qx * qz + qy * qw)],
                [2 * (qx * qy + qz * qw), 1 - 2 * (qx * qx + qz * qz), 2 * (qy * qz - qx * qw)],
                [2 * (qx * qz - qy * qw), 2 * (qy * qz + qx * qw), 1 - 2 * (qx * qx + qy * qy)]])
            out[nm.decode()] = (cam_id, R, np.array([tx, ty, tz]))
    return out


def project_box(K, R, T, lo, hi):
    corners = np.array([[x, y, z] for x in (lo[0], hi[0])
                        for y in (lo[1], hi[1]) for z in (lo[2], hi[2])])
    cam = (R @ corners.T + T[:, None]).T
    assert np.all(cam[:, 2] > 0), "box corner behind camera"
    uv = (K @ cam.T).T
    uv = uv[:, :2] / uv[:, 2:3]
    return uv.min(0), uv.max(0)


def psnr(a: np.ndarray, b: np.ndarray) -> float:
    mse = float(np.mean((a.astype(float) - b.astype(float)) ** 2))
    return float("inf") if mse == 0 else 10 * np.log10(255.0 ** 2 / mse)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sparse", required=True)
    ap.add_argument("--boxes", required=True)
    ap.add_argument("--sherd", default="SH5")
    ap.add_argument("--images-dir", required=True, help="sorted names define render indices")
    ap.add_argument("--data-dir", required=True, help="MILo dataset dir (capture.json check)")
    ap.add_argument("--renders", required=True, help="train/ours_*/renders")
    ap.add_argument("--gts", required=True, help="train/ours_*/gt")
    ap.add_argument("--views", nargs="+", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--pad", type=float, default=0.15)
    a = ap.parse_args()

    names = sorted(p.name for p in Path(a.images_dir).iterdir() if p.is_file())
    assert len(names) == 162, f"expected 162 images, found {len(names)}"
    test = [n for i, n in enumerate(names) if i % 8 == 0]
    train = [n for i, n in enumerate(names) if i % 8 != 0]
    cap = json.loads((Path(a.data_dir) / "capture.json").read_text())
    assert set(test) == set(cap["held_out_views"]), "index mapping disagrees with capture.json"
    tr_idx = {n: i for i, n in enumerate(train)}

    d = json.loads(Path(a.boxes).read_text())
    scale = float(d["mm_per_unit"])
    box = next(b for b in d["boxes"] if b["id"] == a.sherd)
    lo = np.array(box["min_mm"], float) / scale
    hi = np.array(box["max_mm"], float) / scale

    cams = read_cameras(Path(a.sparse))
    imgs = read_images(Path(a.sparse))
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)

    print(f"{'view':18s} {'train_idx':>9s} {'window':>16s} {'PSNR':>7s}")
    for v in a.views:
        assert v in tr_idx, f"{v} is held-out, not train"
        cam_id, R, T = imgs[v]
        w, h, K = cams[cam_id]
        mn, mx = project_box(K, R, T, lo, hi)
        pad = (mx - mn) * a.pad
        x0, y0 = np.maximum(np.floor(mn - pad), 0).astype(int)
        x1, y1 = np.minimum(np.ceil(mx + pad), [w, h]).astype(int)
        r = np.array(Image.open(Path(a.renders) / f"{tr_idx[v]:05d}.png").convert("RGB"))
        g = np.array(Image.open(Path(a.gts) / f"{tr_idx[v]:05d}.png").convert("RGB"))
        assert r.shape == g.shape, (r.shape, g.shape)
        # renders/gt may differ in size from COLMAP frame; scale window accordingly
        sy, sx = r.shape[0] / h, r.shape[1] / w
        X0, Y0, X1, Y1 = int(x0 * sx), int(y0 * sy), int(x1 * sx), int(y1 * sy)
        rc, gc = r[Y0:Y1, X0:X1], g[Y0:Y1, X0:X1]
        side = np.concatenate([gc, rc], axis=1)
        Image.fromarray(side).save(out / f"{Path(v).stem}_sidebyside.png")
        print(f"{v:18s} {tr_idx[v]:9d} {X1-X0:4d}x{Y1-Y0:<4d}      {psnr(gc, rc):6.2f}")
    print(f"crops in {out}")


if __name__ == "__main__":
    main()
