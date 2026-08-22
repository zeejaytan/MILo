#!/usr/bin/env python3
"""Draw shrinking mask outlines on a sherd photograph, at a scale where 6 pixels show.

Surface masks are eroded before the mesh is built so clamp-straddling pixels never get a
depth. Vertex counts cannot say whether that also ate the fracture ridges. This script
answers that by putting the 0/2/4/6/8/12-pixel outlines on a tight crop of the photograph
itself. Nearest-neighbour zoom, not a whole-tree view: a 6-pixel step that is two pixels
on a contact sheet is invisible, and looking at it would answer the wrong question.

Two modes:

  survey   From the masks, find the smallest and largest sherd blobs and write a contact
           sheet of each, labelled with frame and a pixel inside the blob, so a person
           can pick four crops (small/large × break/clamp) without opening 164 frames.

  overlay  Draw the erosion contours on chosen crops. Source masks must be UNSHRUNK
           (--erode-surface 0). Growing a 6-pixel mask back does not restore eaten pixels.

Usage (on Spartan):
    python scripts/erode_fracture_overlay.py survey \\
        --images /data/.../Rabati2025/17062025/A03 \\
        --masks  /data/.../MILo/masks/17062025/A03_erode0/masks_sherds \\
        --out    /data/.../MILo/artifacts/A03_erode_overlay

    python scripts/erode_fracture_overlay.py overlay \\
        --images ... --masks ... --out ... \\
        --crop A32_1140.JPG@1200,800:small_break \\
        --sparse .../sparse_nosherdrig/0 --mm-per-unit 373.733
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

# Current production default, drawn thicker so it is the one you look at first.
LEVELS = (0, 2, 4, 6, 8, 12)
# Okabe–Ito, colourblind-safe. 6 px is the orange.
COLOURS = {
    0:  (86, 180, 233),
    2:  (0, 158, 115),
    4:  (240, 228, 66),
    6:  (230, 159, 0),
    8:  (213, 94, 0),
    12: (204, 121, 167),
}
MIN_BLOB_PX = 800          # speckle; a 30 mm sherd at this capture is thousands of pixels
PAD_PX = 48                # must exceed max LEVELS, so crop-then-erode does not hit the frame
ZOOM = 4
CONTACT_TILE = 280
# Sparse points used only for a millimetre bar. Distortion is ignored; the bar is labelled
# approximate. Alignment of the outlines themselves never uses this.
MM_PER_UNIT_DEFAULT = 373.733


def load_stored(path: Path) -> np.ndarray:
    """Pixels as stored, no EXIF transpose — same convention as sam3_masks.py / COLMAP."""
    img = Image.open(path)
    if img.mode != "RGB":
        img = img.convert("RGB")
    return np.asarray(img)


def mask_path(mask_dir: Path, photo_name: str) -> Path:
    p = mask_dir / f"{photo_name}.png"
    if p.exists():
        return p
    alt = mask_dir / f"{Path(photo_name).stem}.png"
    if alt.exists():
        return alt
    sys.exit(f"no mask for {photo_name} in {mask_dir}")


def components(mask: np.ndarray):
    """List of (area, bbox x,y,w,h, cx, cy, label) for blobs above MIN_BLOB_PX."""
    binary = (mask > 127).astype(np.uint8)
    n, labels, stats, cents = cv2.connectedComponentsWithStats(binary, connectivity=8)
    out = []
    for lab in range(1, n):
        area = int(stats[lab, cv2.CC_STAT_AREA])
        if area < MIN_BLOB_PX:
            continue
        x, y, w, h = (int(stats[lab, k]) for k in
                      (cv2.CC_STAT_LEFT, cv2.CC_STAT_TOP,
                       cv2.CC_STAT_WIDTH, cv2.CC_STAT_HEIGHT))
        cx, cy = (int(round(cents[lab][0])), int(round(cents[lab][1])))
        out.append(dict(area=area, x=x, y=y, w=w, h=h, cx=cx, cy=cy, label=int(lab)))
    out.sort(key=lambda r: r["area"])
    return out, labels


def crop_box(blob, W, H, pad=PAD_PX):
    x0 = max(0, blob["x"] - pad)
    y0 = max(0, blob["y"] - pad)
    x1 = min(W, blob["x"] + blob["w"] + pad)
    y1 = min(H, blob["y"] + blob["h"] + pad)
    return x0, y0, x1, y1


def isolate(labels, lab, erode_px):
    m = (labels == lab).astype(np.uint8) * 255
    if erode_px:
        k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE,
                                      (2 * erode_px + 1, 2 * erode_px + 1))
        m = cv2.erode(m, k)
    return m


def contours_on(rgb, mask_u8, colour, thickness):
    cnts, _ = cv2.findContours(mask_u8, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    cv2.drawContours(rgb, cnts, -1, colour, thickness, lineType=cv2.LINE_8)


def zoom_nn(img, z=ZOOM):
    h, w = img.shape[:2]
    return cv2.resize(img, (w * z, h * z), interpolation=cv2.INTER_NEAREST)


def font(size):
    for p in (r"C:\Windows\Fonts\arial.ttf",
              "/usr/share/fonts/dejavu/DejaVuSans.ttf",
              "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def annotate(rgb, lines, bar_px=None, bar_label=None):
    """Burn legend + optional scale bar onto a zoomed RGB crop."""
    im = Image.fromarray(rgb)
    dr = ImageDraw.Draw(im)
    f = font(18)
    y = 8
    for line, colour in lines:
        dr.text((10, y), line, fill=colour, font=f)
        y += 22
    if bar_px and bar_px > 4:
        x0, y0 = 12, im.size[1] - 36
        dr.rectangle([x0, y0, x0 + bar_px, y0 + 8], fill=(255, 255, 255))
        dr.text((x0, y0 - 20), bar_label or "", fill=(255, 255, 255), font=f)
    return np.asarray(im)


def photo_paths(images: Path):
    paths = sorted(p for p in images.iterdir()
                   if p.suffix.lower() in {".jpg", ".jpeg"} and p.is_file())
    if not paths:
        sys.exit(f"no photographs in {images}")
    return paths


def cmd_survey(args):
    images, masks, out = args.images, args.masks, args.out
    out.mkdir(parents=True, exist_ok=True)
    rows = []
    for path in photo_paths(images):
        m = cv2.imread(str(mask_path(masks, path.name)), cv2.IMREAD_GRAYSCALE)
        if m is None:
            continue
        blobs, _ = components(m)
        for b in blobs:
            rows.append(dict(frame=path.name, **b))
    rows.sort(key=lambda r: r["area"])
    (out / "blobs.json").write_text(json.dumps(rows, indent=2))
    print(f"{len(rows)} blobs in {len({r['frame'] for r in rows})} frames "
          f"(min area {MIN_BLOB_PX} px)")
    if not rows:
        return
    n = min(8, len(rows))
    write_contact(images, masks, rows[:n], out / "contact_smallest.png",
                  "smallest blobs — candidates for the small sherd")
    write_contact(images, masks, rows[-n:][::-1], out / "contact_largest.png",
                  "largest blobs — candidates for the large sherd")
    print(f"wrote {out / 'contact_smallest.png'}")
    print(f"wrote {out / 'contact_largest.png'}")
    print("pick four crops as  FRAME@cx,cy:label")
    print("  e.g.  --crop A32_1140.JPG@1200,800:small_break")


def write_contact(images, masks, blobs, dest: Path, title: str):
    tiles = []
    labels = []
    for b in blobs:
        photo = load_stored(images / b["frame"])
        H, W = photo.shape[:2]
        x0, y0, x1, y1 = crop_box(b, W, H)
        crop = photo[y0:y1, x0:x1].copy()
        m = cv2.imread(str(mask_path(masks, b["frame"])), cv2.IMREAD_GRAYSCALE)
        _, labs = components(m)
        outline = isolate(labs, b["label"], 0)[y0:y1, x0:x1]
        contours_on(crop, outline, (255, 80, 80), 2)
        z = zoom_nn(crop, 2)
        # Fit tile.
        h, w = z.shape[:2]
        scale = CONTACT_TILE / max(h, w)
        z = cv2.resize(z, (max(1, int(w * scale)), max(1, int(h * scale))),
                       interpolation=cv2.INTER_NEAREST)
        canvas = np.full((CONTACT_TILE, CONTACT_TILE, 3), 18, np.uint8)
        yy, xx = (CONTACT_TILE - z.shape[0]) // 2, (CONTACT_TILE - z.shape[1]) // 2
        canvas[yy:yy + z.shape[0], xx:xx + z.shape[1]] = z
        tag = f"{b['frame']}  @{b['cx']},{b['cy']}  {b['area']}px"
        canvas = annotate(canvas, [(tag, (255, 255, 255))])
        tiles.append(canvas)
        labels.append(tag)
    cols = 4
    rows = int(np.ceil(len(tiles) / cols))
    sheet = np.full((40 + rows * CONTACT_TILE, cols * CONTACT_TILE, 3), 12, np.uint8)
    sheet_im = Image.fromarray(sheet)
    ImageDraw.Draw(sheet_im).text((8, 10), title, fill=(255, 255, 255), font=font(16))
    sheet = np.array(sheet_im)
    for i, t in enumerate(tiles):
        r, c = divmod(i, cols)
        y, x = 40 + r * CONTACT_TILE, c * CONTACT_TILE
        sheet[y:y + CONTACT_TILE, x:x + CONTACT_TILE] = t
    Image.fromarray(sheet).save(dest)


def parse_crop(spec: str):
    """FRAME@x,y:label  — blob containing pixel (x,y) in stored coordinates."""
    if "@" not in spec or ":" not in spec.split("@", 1)[1]:
        sys.exit(f"crop must be FRAME@x,y:label, got {spec!r}")
    frame, rest = spec.split("@", 1)
    xy, label = rest.split(":", 1)
    x_s, y_s = xy.split(",")
    return frame.strip(), int(x_s), int(y_s), label.strip()


def load_sparse(sparse_dir: Path):
    here = Path(__file__).resolve()
    candidates = [
        here.parents[1] / "milo" / "scene",
        Path("/data/gpfs/projects/punim2657/MILo/repo/milo/scene"),
    ]
    for c in candidates:
        if (c / "colmap_loader.py").exists():
            sys.path.insert(0, str(c))
            break
    else:
        sys.exit("cannot find milo/scene/colmap_loader.py")
    import colmap_loader as cl
    cams = cl.read_intrinsics_binary(str(sparse_dir / "cameras.bin"))
    imgs = cl.read_extrinsics_binary(str(sparse_dir / "images.bin"))
    xyzs, _, _ = cl.read_points3D_binary(str(sparse_dir / "points3D.bin"))
    by_name = {im.name: im for im in imgs.values()}
    return cams, by_name, xyzs, cl.qvec2rotmat


def mm_per_px_in_crop(sparse, frame, box, mm_per_unit):
    """Approximate millimetres per original pixel at the depth of sparse points in the crop."""
    if sparse is None:
        return None
    cams, by_name, xyzs, qvec2rotmat = sparse
    im = by_name.get(frame)
    if im is None:
        return None
    cam = cams[im.camera_id]
    p = cam.params
    # COLMAP: PINHOLE/OPENCV store fx,fy,cx,cy; SIMPLE_* and RADIAL store f,cx,cy,...
    if cam.model in ("PINHOLE", "OPENCV", "FULL_OPENCV", "OPENCV_FISHEYE"):
        f, cx, cy = float(p[0]), float(p[2]), float(p[3])
    else:
        f, cx, cy = float(p[0]), float(p[1]), float(p[2])
    R = qvec2rotmat(im.qvec)
    t = np.asarray(im.tvec, np.float64)
    Xc = (R @ xyzs.T).T + t
    z = Xc[:, 2]
    ok = z > 1e-6
    u = f * Xc[ok, 0] / z[ok] + cx
    v = f * Xc[ok, 1] / z[ok] + cy
    x0, y0, x1, y1 = box
    inside = (u >= x0) & (u < x1) & (v >= y0) & (v < y1)
    if inside.sum() < 8:
        return None
    z_med = float(np.median(z[ok][inside]))
    return mm_per_unit * z_med / f


def cmd_overlay(args):
    if not args.crop:
        sys.exit("overlay needs one or more --crop FRAME@x,y:label")
    images, masks, out = args.images, args.masks, args.out
    out.mkdir(parents=True, exist_ok=True)
    sparse = None
    if args.sparse:
        sparse = load_sparse(args.sparse)
        print(f"sparse model {args.sparse}  mm/unit {args.mm_per_unit}")

    report = []
    for spec in args.crop:
        frame, px, py, label = parse_crop(spec)
        photo = load_stored(images / frame)
        H, W = photo.shape[:2]
        raw = cv2.imread(str(mask_path(masks, frame)), cv2.IMREAD_GRAYSCALE)
        if raw is None:
            sys.exit(f"failed to read mask for {frame}")
        if raw.shape[:2] != (H, W):
            sys.exit(f"{frame}: photograph {W}x{H} vs mask {raw.shape[1]}x{raw.shape[0]}")
        blobs, labs = components(raw)
        lab = int(labs[py, px])
        if lab == 0:
            # Centroid of a C-shaped blob (sherd around a clamp pin) can fall in the gap.
            found = None
            for rad in range(1, 25):
                for dy in range(-rad, rad + 1):
                    for dx in range(-rad, rad + 1):
                        yy, xx = py + dy, px + dx
                        if 0 <= yy < H and 0 <= xx < W and labs[yy, xx] != 0:
                            found = int(labs[yy, xx])
                            px, py = xx, yy
                            break
                    if found:
                        break
                if found:
                    break
            if not found:
                print(f"SKIP {spec}: pixel {px},{py} is not inside a sherd blob")
                continue
            lab = found
            print(f"  snapped {spec} to inside-blob pixel {px},{py}")
        blob = next(b for b in blobs if b["label"] == lab)
        if args.window:
            half = args.window // 2
            x0 = max(0, px - half)
            y0 = max(0, py - half)
            x1 = min(W, px + half)
            y1 = min(H, py + half)
        else:
            x0, y0, x1, y1 = crop_box(blob, W, H)
        crop = photo[y0:y1, x0:x1].copy()
        # 1 px contours on the original crop, then zoom — 6 original pixels become
        # ZOOM*6 pixels on the picture, which is the scale this test is about.
        for lv in LEVELS:
            m = isolate(labs, lab, lv)[y0:y1, x0:x1]
            thick = 2 if lv == 6 else 1
            contours_on(crop, m, COLOURS[lv], thick)
        zimg = zoom_nn(crop, args.zoom)
        mpp = mm_per_px_in_crop(sparse, frame, (x0, y0, x1, y1), args.mm_per_unit)
        legend = [(f"{label}   {frame}  blob {blob['area']} px", (255, 255, 255))]
        for lv in LEVELS:
            extra = "  <- current default" if lv == 6 else ""
            mm = f"  ~{lv * mpp:.2f} mm" if mpp else ""
            legend.append((f"{lv} px{mm}{extra}", COLOURS[lv]))
        bar_px = 6 * args.zoom
        if mpp:
            bar_label = f"6 px  ≈  {6 * mpp:.2f} mm  at this crop"
        else:
            bar_label = "6 px  (millimetres unknown here)"
        zimg = annotate(zimg, legend, bar_px=bar_px, bar_label=bar_label)
        dest = out / f"{label}.png"
        Image.fromarray(zimg).save(dest)
        rec = dict(label=label, frame=frame, xy=[px, py], area_px=blob["area"],
                   crop=[x0, y0, x1, y1], zoom=args.zoom, mm_per_px=mpp,
                   path=str(dest))
        report.append(rec)
        mm_txt = f"{mpp:.3f} mm/px" if mpp else "no mm"
        print(f"  {label}: {frame} @{px},{py}  {blob['area']} px  {mm_txt}  -> {dest}")

    (out / "overlays.json").write_text(json.dumps(report, indent=2))
    print(f"wrote {out / 'overlays.json'}")
    print("LOOK AT the PNGs before claiming anything about fracture detail.")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    def add_io(p):
        p.add_argument("--images", required=True, type=Path)
        p.add_argument("--masks", required=True, type=Path)
        p.add_argument("--out", required=True, type=Path)

    ps = sub.add_parser("survey")
    add_io(ps)
    po = sub.add_parser("overlay")
    add_io(po)
    po.add_argument("--crop", action="append", default=[],
                    help="FRAME@x,y:label  (repeatable). Pixel is in stored coordinates.")
    po.add_argument("--window", type=int, default=0,
                    help="If >0, crop a square of this many original pixels centred on "
                         "the pick point, not the whole sherd. Required for a large "
                         "sherd: a whole-piece crop cannot resolve a 6-pixel step.")
    po.add_argument("--sparse", type=Path, default=None)
    po.add_argument("--mm-per-unit", type=float, default=MM_PER_UNIT_DEFAULT)
    po.add_argument("--zoom", type=int, default=ZOOM)
    args = ap.parse_args()
    if args.cmd == "survey":
        cmd_survey(args)
    else:
        cmd_overlay(args)


if __name__ == "__main__":
    main()
