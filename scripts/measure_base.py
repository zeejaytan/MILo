"""Measure the blue base plate in a reconstruction, and refuse if it cannot be trusted.

The base is the only physical scale in these captures: its TOP FACE is a known 13 x 19 cm
(the conservator's record says "Top of the tree base (blue metal base) = 13x19cm" -- top,
because the base is a trapezoid and tapers). Measuring it in reconstruction units gives the
factor that turns every downstream mesh metric.

WHY NOT COLOUR. Three attempts at isolating the plate by colour failed, all the same way:
the clamp knobs are blue too, there are dozens of them along the whole rod, and they
dominate any fit. The rendered selection made it obvious and the numbers never did --
aspect ratios of 1.66, 1.95, 2.50 against a true 1.462, and scale factors disagreeing by
13-29%. SAM 3 prompted with "blue board" finds exactly ONE region at 0.94 confidence and no
knobs, so the isolation is done semantically and the geometry is only asked to measure.

WHAT MAKES THE ANSWER CHECKABLE. A rectangle of known proportions is self-validating: the
long and short edges give two independent scale factors, and they can only agree if the
thing measured really is the plate. The aspect ratio is the same check stated as a shape,
and it is scale-free, so it catches a wrong region before any factor is computed. This
script refuses rather than reports when the checks fail -- a wrong scale is worse than no
scale, because nothing downstream would ever reveal it.

BOTH CLOUDS, AND THE COMPARISON IS A THIRD CHECK. The plate is measured in the SPARSE model
as well as the dense one. They share a coordinate frame and describe the same physical
object, so the two figures should match -- but they are produced by opposite methods.
Sparse keeps only points that many views agreed on and throws the rest away; dense must
return a depth for every pixel and has no way to abstain. On a smooth, low-texture surface
like this plate that difference matters: tree A03's dense stage built the plate TWICE, at
an angle, while its sparse model held one. Measuring only the dense cloud reported a
nonsense aspect ratio with no indication of why. A gap between the two is therefore not a
measurement problem to be tuned away -- it says the reconstruction is wrong, and which half.

When both pass, the figure taken is whichever fit's own two edges agree best -- a property
of the fit, not of the stage that produced it. Sparse is the more trustworthy cloud for
WHERE something is, but not for how big a low-texture flat thing is: a featureless plate
gives features only at its rim, so its rectangle is fitted to an outline. On A03 rebuilt
correctly that meant 8,467 sparse points against 666,682 dense, and the dense figure was
the right one. Use --dense-only to skip the cross-check, though that removes the check
that catches a duplicated plate.

Usage:
    python measure_base.py --dense <dense_workspace> --cloud <fused .ply> \\
        --out <dir> [--views 24] [--dense-only] [--write-measurement-env]
"""
import argparse
import json
import struct
import sys
from pathlib import Path

import numpy as np
from PIL import Image

LONG_MM, SHORT_MM = 190.0, 130.0          # top face of the base, from the record
TRUE_ASPECT = LONG_MM / SHORT_MM          # 1.4615
ASPECT_TOL = 0.05                         # ~3.4%; looser than this and the region is wrong


# ----------------------------------------------------------------- COLMAP model (undistorted)
def read_cameras(path):
    cams = {}
    with open(path, "rb") as f:
        (n,) = struct.unpack("<Q", f.read(8))
        for _ in range(n):
            cid, model, w, h = struct.unpack("<iiQQ", f.read(24))
            npar = {0: 3, 1: 4, 2: 4, 3: 5, 4: 8}.get(model, 4)
            par = struct.unpack("<" + "d" * npar, f.read(8 * npar))
            cams[cid] = dict(model=model, w=w, h=h, params=par)
    return cams


def read_images(path):
    out = []
    with open(path, "rb") as f:
        (n,) = struct.unpack("<Q", f.read(8))
        for _ in range(n):
            _, qw, qx, qy, qz, tx, ty, tz, cid = struct.unpack("<idddddddi", f.read(64))
            nm = b""
            while (c := f.read(1)) != b"\x00":
                nm += c
            (p,) = struct.unpack("<Q", f.read(8))
            f.seek(24 * p, 1)
            R = np.array([
                [1-2*(qy*qy+qz*qz), 2*(qx*qy-qz*qw), 2*(qx*qz+qy*qw)],
                [2*(qx*qy+qz*qw), 1-2*(qx*qx+qz*qz), 2*(qy*qz-qx*qw)],
                [2*(qx*qz-qy*qw), 2*(qy*qz+qx*qw), 1-2*(qx*qx+qy*qy)]])
            out.append(dict(name=nm.decode(), R=R, t=np.array([tx, ty, tz]), cam=cid))
    return out


def project(P, im, cam):
    """World points -> pixels, for an UNDISTORTED (pinhole) camera."""
    X = (im["R"] @ P.T).T + im["t"]
    z = X[:, 2]
    ok = z > 1e-6
    p = np.full((len(P), 2), -1.0)
    pr = X[ok, :2] / z[ok, None]
    m, par = cam["model"], cam["params"]
    if m == 1:                                    # PINHOLE fx fy cx cy
        fx, fy, cx, cy = par[:4]
    else:                                         # SIMPLE_PINHOLE / fallback
        fx = fy = par[0]; cx, cy = par[1], par[2]
    p[ok, 0] = fx * pr[:, 0] + cx
    p[ok, 1] = fy * pr[:, 1] + cy
    return p, ok


# ----------------------------------------------------------------- PLY (binary, list-tolerant)
def read_ply_xyzrgb(path):
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from look_at_cloud import read_ply
    return read_ply(path)


def read_points3D(path):
    """The SPARSE cloud, straight out of the model, in the same frame as the dense one.

    Undistortion rewrites images and intrinsics but never moves a 3D point, so the model
    beside the dense workspace shares its coordinates and the two measurements are directly
    comparable -- which is the whole point of taking both.
    """
    xyz, rgb = [], []
    with open(path, "rb") as fh:
        (n,) = struct.unpack("<Q", fh.read(8))
        for _ in range(n):
            _, x, y, z, r, g, b, _err = struct.unpack("<QdddBBBd", fh.read(43))
            (track,) = struct.unpack("<Q", fh.read(8))
            fh.seek(8 * track, 1)
            xyz.append((x, y, z))
            rgb.append((r, g, b))
    return np.asarray(xyz), np.asarray(rgb, np.uint8)


def measure_cloud(tag, xyz, rgb, cams, imgs, args, model, proc, dev, cv2, torch):
    """Isolate the blue plate in one cloud and measure its top face.

    Returns None when the cloud cannot support a measurement at all, so that the other
    cloud still gets its turn rather than the whole job stopping.
    """
    print("\n=== %s cloud: %s points ===" % (tag.upper(), format(len(xyz), ",")))
    r, g, b = rgb[:, 0].astype(int), rgb[:, 1].astype(int), rgb[:, 2].astype(int)
    cand = np.where((b > r + 8) & (b > 30))[0]
    print("  loose blue candidates: %s (SAM 3 decides which are the plate)"
          % format(len(cand), ","))
    floor = 5000 if tag == "dense" else 300      # a sparse cloud is 50-100x smaller
    if len(cand) < floor:
        print("  too few blue candidates (%d < %d) -- skipping this cloud" % (len(cand), floor))
        return None

    step = max(1, len(imgs) // args.views)
    chosen = imgs[::step][:args.views]
    inside = np.zeros(len(cand), np.int32)
    seen = np.zeros(len(cand), np.int32)
    P = xyz[cand]

    for k, im in enumerate(chosen):
        fp = args.dense / "images" / im["name"]
        if not fp.exists():
            continue
        pil = Image.open(fp).convert("RGB")
        W, H = pil.size
        small = pil.copy()
        small.thumbnail((args.seg_side, args.seg_side))
        inputs = proc(images=small, text="blue board", return_tensors="pt").to(dev)
        with torch.inference_mode():
            out = model(**inputs)
        res = proc.post_process_instance_segmentation(
            out, threshold=0.3, mask_threshold=0.5,
            target_sizes=[(small.size[1], small.size[0])])[0]
        m = res.get("masks")
        if m is None or not len(m):
            continue
        mm = m.detach().cpu().numpy()
        if mm.ndim == 4:
            mm = mm[:, 0]
        mask = np.any(mm > 0.5, axis=0)
        mask = cv2.resize(mask.astype(np.uint8), (W, H), interpolation=cv2.INTER_NEAREST)

        px, ok = project(P, im, cams[im["cam"]])
        u = np.round(px[:, 0]).astype(int)
        v = np.round(px[:, 1]).astype(int)
        vis = ok & (u >= 0) & (u < W) & (v >= 0) & (v < H)
        seen += vis
        inside[vis] += mask[v[vis], u[vis]] > 0
        if (k + 1) % 8 == 0:
            print("  %d/%d views" % (k + 1, len(chosen)), flush=True)

    ratio = np.divide(inside, np.maximum(seen, 1))
    keep = (seen >= 4) & (ratio >= args.vote)
    B = P[keep]
    print("  base points after voting: %s" % format(len(B), ","))
    if len(B) < (2000 if tag == "dense" else 150):
        print("  too few points survived the vote -- no stable plate in this cloud")
        return None

    # The plate is a tapered solid and the record's 190 x 130 is the TOP face, so the face
    # has to be chosen rather than averaged over.
    ctr = B.mean(0)
    _, _, Vt = np.linalg.svd(B - ctr, full_matrices=False)
    n = Vt[2]
    rig_dir = xyz.mean(0) - ctr
    if n @ rig_dir < 0:
        n = -n
    d = (B - ctr) @ n
    top = np.percentile(d, 97)
    face = B[d > top - 0.12 * (d.max() - d.min())]
    if len(face) < (1000 if tag == "dense" else 80):
        face = B[d > np.percentile(d, 80)]

    e1 = Vt[0] - (Vt[0] @ n) * n
    e1 /= np.linalg.norm(e1)
    e2 = np.cross(n, e1)
    uv = np.stack([(face - face.mean(0)) @ e1,
                   (face - face.mean(0)) @ e2], 1).astype(np.float32)
    c2 = np.median(uv, axis=0)
    rad = np.linalg.norm(uv - c2, axis=1)
    rect = cv2.minAreaRect(uv[rad < np.percentile(rad, 99.5)])
    w_r, h_r = rect[1]
    L, Sh = max(w_r, h_r), min(w_r, h_r)
    aspect = L / Sh
    s_long, s_short = LONG_MM / L, SHORT_MM / Sh
    disagree = abs(s_long - s_short) / ((s_long + s_short) / 2)

    print("  fitted top face: %.5f x %.5f units from %s points"
          % (L, Sh, format(len(face), ",")))
    print("  aspect ratio   : %.3f      (true %.3f)" % (aspect, TRUE_ASPECT))
    print("  mm/unit  long %9.3f   short %9.3f   disagreeing by %.1f%%"
          % (s_long, s_short, 100 * disagree))

    # Always render the selection. Every failure here came from fitting geometry to a
    # selection nobody had looked at.
    from look_at_cloud import render, basis
    vis_rgb = rgb.copy()
    vis_rgb[cand[keep]] = [255, 40, 40]
    for nm, dirn in (("side", (0, 1, 0)), ("face", tuple(n))):
        Bb = basis(dirn)
        q = xyz @ Bb.T
        c = np.median(q[cand[keep]][:, :2], axis=0)
        e = float(np.ptp(q[cand[keep]][:, :2], axis=0).max()) * 2.0
        img, _, _ = render(xyz, vis_rgb, dirn, 1200, centre=c, extent=e, point_px=1)
        Image.fromarray(img).save(args.out / ("base_%s_%s.png" % (tag, nm)))

    ok_aspect = abs(aspect - TRUE_ASPECT) <= ASPECT_TOL
    return dict(cloud=tag, long_units=float(L), short_units=float(Sh), aspect=float(aspect),
                mm_per_unit_long=float(s_long), mm_per_unit_short=float(s_short),
                mm_per_unit=float(0.5 * (s_long + s_short)),
                disagreement=float(disagree), points=int(len(face)),
                accepted=bool(ok_aspect and disagree < 0.02))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dense", required=True, type=Path,
                    help="undistorted workspace: images/ and sparse/ inside")
    ap.add_argument("--cloud", required=True, type=Path, help="dense point cloud (.ply)")
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--views", type=int, default=24)
    ap.add_argument("--vote", type=float, default=0.6)
    ap.add_argument("--seg-side", type=int, default=1600)
    ap.add_argument("--dense-only", action="store_true",
                    help="skip the sparse cross-check. Not recommended: that check is what "
                         "catches a dense cloud that has built the plate twice.")
    ap.add_argument("--write-measurement-env", action="store_true")
    args = ap.parse_args()

    import cv2
    import torch
    from transformers import Sam3Model, Sam3Processor

    args.out.mkdir(parents=True, exist_ok=True)
    cams = read_cameras(args.dense / "sparse" / "cameras.bin")
    imgs = read_images(args.dense / "sparse" / "images.bin")
    print("model: %d views, %d camera(s)" % (len(imgs), len(cams)))

    dev = "cuda" if torch.cuda.is_available() else "cpu"
    model = Sam3Model.from_pretrained("facebook/sam3").to(dev).eval()
    proc = Sam3Processor.from_pretrained("facebook/sam3")

    # BOTH CLOUDS, and the comparison is the point. They describe the same plate, in the
    # same coordinate frame, by two different routes: sparse keeps only points that many
    # views agreed on and discards the rest, while dense must assign a depth to every pixel
    # and cannot abstain. Agreement means the scale is corroborated by two independent
    # methods. Disagreement means the reconstruction is at fault, not the ruler -- which is
    # what happened on tree A03, where the dense stage built the plate TWICE at an angle
    # while the sparse model had one. Measuring the dense cloud alone reported a bad aspect
    # ratio and left the cause invisible.
    xyz_d, rgb_d = read_ply_xyzrgb(args.cloud)
    results = []
    r = measure_cloud("dense", xyz_d, rgb_d, cams, imgs, args, model, proc, dev, cv2, torch)
    if r:
        results.append(r)
    if not args.dense_only:
        pts = args.dense / "sparse" / "points3D.bin"
        if pts.exists():
            xyz_s, rgb_s = read_points3D(pts)
            r = measure_cloud("sparse", xyz_s, rgb_s, cams, imgs, args, model, proc, dev,
                              cv2, torch)
            if r:
                results.append(r)
        else:
            print("\n  no sparse points at %s -- cross-check skipped" % pts)

    print("\n" + "=" * 70)
    print("%-8s %8s %10s %15s  verdict" % ("cloud", "aspect", "mm/unit", "edge disagree"))
    for r in results:
        print("%-8s %8.3f %10.2f %14.1f%%  %s"
              % (r["cloud"], r["aspect"], r["mm_per_unit"], 100 * r["disagreement"],
                 "ok" if r["accepted"] else "FAILS ITS OWN CHECKS"))

    by = {r["cloud"]: r for r in results}
    cross = None
    if "dense" in by and "sparse" in by:
        a, b = by["dense"]["mm_per_unit"], by["sparse"]["mm_per_unit"]
        cross = abs(a - b) / ((a + b) / 2)
        print("\nsparse vs dense scale: %.1f%% apart" % (100 * cross))
        if cross > 0.03:
            print("  THE TWO CLOUDS DISAGREE ABOUT THE SAME PLATE. Two things cause this")
            print("  and they lead opposite ways, so LOOK AT base_dense_face.png AND")
            print("  base_sparse_face.png side by side before deciding which:")
            print("    DENSE built the plate more than once. It is smooth and low-texture,")
            print("      and dense stereo must return a depth for every pixel whether the")
            print("      photographs support one or not. A03 did exactly this while its")
            print("      camera solve was bent: aspect 2.341 against a true 1.462.")
            print("    SPARSE has too few points to fit a rectangle. A featureless plate")
            print("      yields features only at its edges and marks, so the fit rests on a")
            print("      rim rather than a face. On A03 rebuilt correctly that was 8,467")
            print("      points against 666,682 -- and the sparse figure was the wrong one.")
            print("  The per-cloud edge disagreement above says which fit is internally")
            print("  consistent, and that is a better guide than which stage produced it.")
        else:
            print("  they agree -- the scale is corroborated by two independent routes")

    ok = [r for r in results if r["accepted"]]
    # When both pass, take whichever fit's OWN two edges agree best. That is a property of
    # the fit rather than of the pipeline stage, and it is the honest tie-break: sparse is
    # the more trustworthy cloud for WHERE a thing is, but not for how big a low-texture
    # flat thing is, because it only carries points around its rim.
    chosen = min(ok, key=lambda r: r["disagreement"]) if ok else None
    out = dict(measurements=results, cross_cloud_disagreement=cross,
               chosen=(chosen["cloud"] if chosen else None), accepted=bool(chosen))
    if chosen:
        out.update({k: v for k, v in chosen.items() if k != "cloud"})
    (args.out / "base_measurement.json").write_text(json.dumps(out, indent=2))
    print("\nwrote %s/base_measurement.json and the selection renders -- LOOK AT THEM"
          % args.out)

    if not chosen:
        print("\n  REJECTED: neither cloud produced a plate that passes its own checks.")
        print("  A wrong scale is worse than no scale -- nothing downstream would reveal it.")
        return 1
    if len(ok) == 1 and len(results) == 2:
        print("\n  NOTE: only the %s cloud passed. The other measured the same plate and"
              % chosen["cloud"])
        print("  failed, which is a finding about that cloud -- look at it before trusting")
        print("  anything else built from it.")

    print("\n  ACCEPTED from the %s cloud: %.3f mm per reconstruction unit"
          % (chosen["cloud"], chosen["mm_per_unit"]))
    if args.write_measurement_env:
        env = args.dense.parent / "measurement.env"
        env.write_text("d1_real_m=%.4f\nd1_rec_units=%.9f\nd2_real_m=%.4f\nd2_rec_units=%.9f\n"
                       % (LONG_MM / 1000, chosen["long_units"],
                          SHORT_MM / 1000, chosen["short_units"]))
        print("  wrote %s for scale_apply.py" % env)
    return 0


if __name__ == "__main__":
    sys.exit(main())
