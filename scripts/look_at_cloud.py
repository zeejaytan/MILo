"""Render a dense point cloud and the camera positions, so they can be looked at.

Written because a reconstruction of tree A01 scored 0.55 px median reprojection error --
which is excellent -- while the conservator opening the cloud saw the same sherd repeated
at many different angles. A low reprojection error only says the solution is
self-consistent. It cannot tell you the solution is of the right object.

Orthographic, painter's algorithm, per-point and unbinned. Nothing is smoothed or
resampled, so what appears here is what is in the file.
"""
import argparse
import struct
import sys
from pathlib import Path

import numpy as np
from PIL import Image

# --------------------------------------------------------------------------- PLY reading


NUMPY_OF = {
    "float": "<f4", "float32": "<f4", "double": "<f8", "float64": "<f8",
    "uchar": "u1", "uint8": "u1", "char": "i1", "int8": "i1",
    "ushort": "<u2", "uint16": "<u2", "short": "<i2", "int16": "<i2",
    "uint": "<u4", "uint32": "<u4", "int": "<i4", "int32": "<i4",
}


def _parse_header(fh):
    if fh.readline().strip() != b"ply":
        raise ValueError("not a PLY file")
    fmt, in_vertex, count, props = None, False, None, []
    while True:
        line = fh.readline()
        if not line:
            raise ValueError("PLY header never ended")
        parts = line.split()
        if not parts:
            continue
        if parts[0] == b"format":
            fmt = parts[1].decode()
        elif parts[0] == b"element":
            # Stop RECORDING at the next element, but keep READING to end_header.
            # Breaking out here left the remaining header lines ("property list uchar int
            # vertex_indices", "end_header") in the byte stream, where they were read as
            # vertex data. Every coordinate came out NaN, which looked exactly like a
            # broken mesh rather than a broken reader.
            in_vertex = parts[1] == b"vertex"
            if in_vertex:
                count = int(parts[2])
        elif parts[0] == b"property" and in_vertex:
            if parts[1] == b"list":
                # ("name", None, count_type, item_type) -- variable length
                props.append((parts[4].decode(), None,
                              parts[2].decode(), parts[3].decode()))
            else:
                props.append((parts[2].decode(), parts[1].decode(), None, None))
        elif parts[0] == b"end_header":
            break
    if fmt != "binary_little_endian":
        raise ValueError(f"only binary_little_endian is handled here, got {fmt!r}")
    return count, props


def read_ply(path):
    """Binary PLY -> (xyz float32 [N,3], rgb uint8 [N,3]).

    Handles variable-length list properties on the *vertex* element. OpenMVS writes
    `view_indices` and `view_weights` per point, which makes each record a different
    length -- so a fixed-stride structured read silently returns garbage. It did exactly
    that here: the first attempt produced all-NaN coordinates.
    """
    with open(path, "rb") as fh:
        count, props = _parse_header(fh)
        blob = fh.read()

    buf = np.frombuffer(blob, dtype=np.uint8)
    fixed = [p for p in props if p[1] is not None]
    lists = [p for p in props if p[1] is None]

    offset_of, pos = {}, 0
    for name, typ, _, _ in fixed:
        offset_of[name] = pos
        pos += np.dtype(NUMPY_OF[typ]).itemsize

    if not lists:
        starts = np.arange(count, dtype=np.int64) * pos
    else:
        if len(props) != len(fixed) + len(lists) or props[:len(fixed)] != fixed:
            raise ValueError("list properties must follow all fixed ones")
        # Record length varies, so the start of each record has to be walked. Only the
        # list *counts* are read here; the payloads are skipped.
        sizes = [(np.dtype(NUMPY_OF[c]).itemsize, np.dtype(NUMPY_OF[i]).itemsize)
                 for _, _, c, i in lists]
        starts = np.empty(count, np.int64)
        p, mv = 0, memoryview(blob)
        for k in range(count):
            starts[k] = p
            p += pos
            for csize, isize in sizes:
                n = int.from_bytes(mv[p:p + csize], "little")
                p += csize + isize * n
        if p != len(blob):
            raise ValueError(f"walked {p} bytes of {len(blob)} -- header/data disagree")

    def column(name, typ):
        w = np.dtype(NUMPY_OF[typ]).itemsize
        raw = buf[(starts + offset_of[name])[:, None] + np.arange(w)]
        return np.ascontiguousarray(raw).view(NUMPY_OF[typ]).ravel()

    xyz = np.stack([column(c, "float32") for c in ("x", "y", "z")], axis=1)
    have = {p[0] for p in fixed}
    if {"red", "green", "blue"} <= have:
        rgb = np.stack([column(c, "uint8") for c in ("red", "green", "blue")], axis=1)
    else:
        rgb = np.full((len(xyz), 3), 200, np.uint8)
    return xyz.astype(np.float32), rgb.astype(np.uint8)


# ------------------------------------------------------------------ COLMAP camera centres


def read_camera_centres(model_dir):
    """images.bin -> (centres [M,3], forward directions [M,3], names)."""
    path = Path(model_dir) / "images.bin"
    centres, forwards, names = [], [], []
    with open(path, "rb") as fh:
        (n_images,) = struct.unpack("<Q", fh.read(8))
        for _ in range(n_images):
            # image_id, qw qx qy qz, tx ty tz, camera_id
            _, qw, qx, qy, qz, tx, ty, tz, _ = struct.unpack("<idddddddi", fh.read(64))
            name = b""
            while (ch := fh.read(1)) != b"\x00":
                name += ch
            (n_pts,) = struct.unpack("<Q", fh.read(8))
            fh.seek(24 * n_pts, 1)  # x, y, point3D_id per observation

            R = np.array([
                [1 - 2 * (qy * qy + qz * qz), 2 * (qx * qy - qz * qw), 2 * (qx * qz + qy * qw)],
                [2 * (qx * qy + qz * qw), 1 - 2 * (qx * qx + qz * qz), 2 * (qy * qz - qx * qw)],
                [2 * (qx * qz - qy * qw), 2 * (qy * qz + qx * qw), 1 - 2 * (qx * qx + qy * qy)],
            ])
            t = np.array([tx, ty, tz])
            centres.append(-R.T @ t)      # camera centre in world coordinates
            forwards.append(R.T @ np.array([0, 0, 1]))   # optical axis, world frame
            names.append(name.decode())
    return np.array(centres), np.array(forwards), names


# ------------------------------------------------------------------------------ rendering


def basis(direction, up=(0, 0, 1)):
    """Right-handed view basis looking along `direction`."""
    f = np.asarray(direction, float)
    f /= np.linalg.norm(f)
    u = np.asarray(up, float)
    if abs(f @ u) > 0.95:                       # degenerate: pick another up
        u = np.array([0.0, 1.0, 0.0])
    r = np.cross(f, u); r /= np.linalg.norm(r)
    u = np.cross(r, f)
    return np.stack([r, u, f])                  # rows: right, up, forward


def render(xyz, rgb, direction, size, centre=None, extent=None, point_px=1, bg=18):
    """Orthographic painter's-algorithm render. Nearer points overwrite farther ones."""
    B = basis(direction)
    p = xyz @ B.T                               # columns: right, up, depth

    if centre is None:
        centre = np.median(p[:, :2], axis=0)
    if extent is None:
        lo = np.percentile(p[:, :2], 0.2, axis=0)
        hi = np.percentile(p[:, :2], 99.8, axis=0)
        extent = float(max(hi - lo)) * 1.05

    scale = size / extent
    px = ((p[:, 0] - centre[0]) * scale + size / 2).astype(np.int32)
    py = ((centre[1] - p[:, 1]) * scale + size / 2).astype(np.int32)

    keep = (px >= 0) & (px < size) & (py >= 0) & (py < size)
    px, py, depth, col = px[keep], py[keep], p[keep, 2], rgb[keep]

    order = np.argsort(-depth)                  # far first, so near paints over it
    px, py, col = px[order], py[order], col[order]

    img = np.full((size, size, 3), bg, np.uint8)
    for dy in range(point_px):
        for dx in range(point_px):
            yy, xx = np.clip(py + dy, 0, size - 1), np.clip(px + dx, 0, size - 1)
            img[yy, xx] = col
    return img, centre, extent


def mark(img, pts_px, colour, radius=3):
    size = img.shape[0]
    for x, y in pts_px:
        x, y = int(x), int(y)
        if 0 <= x < size and 0 <= y < size:
            y0, y1 = max(0, y - radius), min(size, y + radius + 1)
            x0, x1 = max(0, x - radius), min(size, x + radius + 1)
            img[y0:y1, x0:x1] = colour
    return img


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cloud", required=True)
    ap.add_argument("--model", help="COLMAP sparse model dir, to overlay camera centres")
    ap.add_argument("--out", required=True)
    ap.add_argument("--size", type=int, default=1600)
    ap.add_argument("--max-points", type=int, default=0, help="0 = use every point")
    args = ap.parse_args()

    out = Path(args.out); out.mkdir(parents=True, exist_ok=True)

    print(f"reading {args.cloud} ...", flush=True)
    xyz, rgb = read_ply(args.cloud)
    print(f"  {len(xyz):,} points")
    if args.max_points and len(xyz) > args.max_points:
        idx = np.random.default_rng(0).choice(len(xyz), args.max_points, replace=False)
        xyz, rgb = xyz[idx], rgb[idx]
        print(f"  subsampled to {len(xyz):,}")

    # Robust bounds: the ROI-cropped cloud still has stray far-field points that would
    # otherwise shrink the object to a few pixels.
    lo, hi = np.percentile(xyz, [0.5, 99.5], axis=0)
    print(f"  extent (0.5-99.5%): {np.round(hi - lo, 3)}")

    views = {
        "01_top":    (0, 0, -1),
        "02_front":  (0, 1, 0),
        "03_side":   (1, 0, 0),
        "04_oblique": (0.7, 0.7, -0.4),
    }
    for name, d in views.items():
        img, centre, extent = render(xyz, rgb, d, args.size, point_px=1)
        Image.fromarray(img).save(out / f"{name}.png")
        print(f"  {name}: extent {extent:.3f} world units across {args.size}px "
              f"= {extent / args.size * 1000:.3f} mm-units/px")

    if args.model:
        centres, forwards, names = read_camera_centres(args.model)
        print(f"\ncamera centres: {len(centres)}")
        span = centres.max(0) - centres.min(0)
        obj = np.percentile(xyz, 99.5, axis=0) - np.percentile(xyz, 0.5, axis=0)
        print(f"  camera spread : {np.round(span, 3)}")
        print(f"  object extent : {np.round(obj, 3)}")
        print(f"  ratio         : {np.round(span / np.maximum(obj, 1e-9), 2)}")
        # A rig photographed all the way round puts cameras on a shell around the object.
        # A rotating object with a near-static camera collapses them to a small cluster.
        d = centres - centres.mean(0)
        r = np.linalg.norm(d, axis=1)
        print(f"  distance from camera-cloud centroid: "
              f"min {r.min():.3f}  median {np.median(r):.3f}  max {r.max():.3f}")

        both = np.vstack([xyz, centres])
        for name, dirn in (("05_cameras_top", (0, 0, -1)), ("05_cameras_side", (0, 1, 0))):
            B = basis(dirn)
            img, centre, extent = render(
                xyz, rgb, dirn, args.size,
                centre=np.median((both @ B.T)[:, :2], axis=0),
                extent=float(np.ptp((both @ B.T)[:, :2], axis=0).max()) * 1.1)
            cp = centres @ B.T
            scale = args.size / extent
            pix = np.stack([(cp[:, 0] - centre[0]) * scale + args.size / 2,
                            (centre[1] - cp[:, 1]) * scale + args.size / 2], axis=1)
            mark(img, pix, (255, 60, 60))
            Image.fromarray(img).save(out / f"{name}.png")
            print(f"  {name}: cameras in red")

    print(f"\nwrote to {out}")


if __name__ == "__main__":
    sys.exit(main())
