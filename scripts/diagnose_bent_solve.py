"""What did the misplaced frames actually match on?

The camera-arc gate says a solve is bent -- consecutive frames placed far apart around the
rig. It cannot say WHY. This does, by going back to the database and asking three questions
about the pairs involving those frames:

  WHICH PART OF THE SCENE.   Every inlier keypoint is classified by the mask it falls in:
      sherds, blue base, or dial-and-hardware. If the frames that went wrong matched mostly
      on one of those, that part of the rig is what misled the solve.

  HOW FAR AWAY THE PARTNER IS.  A frame should match most strongly to its neighbours around
      the turn. If its strongest partners sit tens of degrees away, features are matching
      across turntable positions -- which is what a repeating pattern, like a graduated
      dial, does to a rotating capture.

  WHAT GEOMETRY COLMAP INFERRED.  two_view_geometries records a config per pair. PLANAR,
      PANORAMIC and PLANAR_OR_PANORAMIC are DEGENERATE: a pair whose matches all lie on one
      flat surface does not determine the relative pose uniquely. A big flat board in an
      otherwise sparse scene is exactly how that happens.

Usage:
    python diagnose_bent_solve.py --work <work_colmap_openmvs> --masks <masks dir> \\
        [--model sparse/0] [--db database.db]
"""
import argparse
import sqlite3
import struct
import sys
from collections import Counter
from pathlib import Path

import numpy as np

CONFIG = {0: "UNDEFINED", 1: "DEGENERATE", 2: "CALIBRATED", 3: "UNCALIBRATED",
          4: "PLANAR", 5: "PANORAMIC", 6: "PLANAR_OR_PANORAMIC", 7: "WATERMARK",
          8: "MULTIPLE"}
DEGENERATE = {1, 4, 5, 6}
MAX_PAIR_ID = 2147483647


def read_images_bin(path):
    out = {}
    with open(path, "rb") as fh:
        (n,) = struct.unpack("<Q", fh.read(8))
        for _ in range(n):
            iid, qw, qx, qy, qz, tx, ty, tz, _c = struct.unpack("<idddddddi", fh.read(64))
            nm = b""
            while True:
                c = fh.read(1)
                if c == b"\x00":
                    break
                nm += c
            (npts,) = struct.unpack("<Q", fh.read(8))
            fh.seek(24 * npts, 1)
            R = np.array([
                [1-2*(qy*qy+qz*qz), 2*(qx*qy-qz*qw), 2*(qx*qz+qy*qw)],
                [2*(qx*qy+qz*qw), 1-2*(qx*qx+qz*qz), 2*(qy*qz-qx*qw)],
                [2*(qx*qz-qy*qw), 2*(qy*qz+qx*qw), 1-2*(qx*qx+qy*qy)]])
            out[nm.decode("utf-8", "replace")] = -R.T @ np.array([tx, ty, tz])
    return out


def read_points(path):
    xyz = []
    with open(path, "rb") as fh:
        (n,) = struct.unpack("<Q", fh.read(8))
        for _ in range(n):
            _, x, y, z, _r, _g, _b, _e = struct.unpack("<QdddBBBd", fh.read(43))
            (t,) = struct.unpack("<Q", fh.read(8))
            fh.seek(8 * t, 1)
            xyz.append((x, y, z))
    return np.asarray(xyz)


def angles_around_rig(centres, xyz):
    lo, hi = np.percentile(xyz, [2, 98], axis=0)
    core = xyz[np.all((xyz > lo) & (xyz < hi), axis=1)]
    ctr = core.mean(0)
    _, _, Vt = np.linalg.svd(core - ctr, full_matrices=False)
    f = Vt[0] / np.linalg.norm(Vt[0])
    up = np.array([0., 0., 1.])
    if abs(f @ up) > 0.95:
        up = np.array([0., 1., 0.])
    r = np.cross(f, up); r /= np.linalg.norm(r)
    B = np.stack([r, np.cross(r, f), f])
    return {nm: float(np.degrees(np.arctan2(*( (c - ctr) @ B.T )[[1, 0]])))
            for nm, c in centres.items()}


def sep(a, b):
    d = abs(a - b) % 360
    return min(d, 360 - d)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", required=True, type=Path)
    ap.add_argument("--masks", required=True, type=Path, help="masks_object directory")
    ap.add_argument("--sherds", type=Path, default=None, help="masks_sherds directory")
    ap.add_argument("--measure", type=Path, default=None, help="masks_measure directory")
    ap.add_argument("--model", default="sparse/0")
    ap.add_argument("--db", default="database.db")
    ap.add_argument("--limit-deg", type=float, default=30.0)
    ap.add_argument("--frames", type=int, default=6, help="how many suspect frames to open")
    args = ap.parse_args()

    from PIL import Image

    model = args.work / args.model
    centres = read_images_bin(model / "images.bin")
    ang = angles_around_rig(centres, read_points(model / "points3D.bin"))

    # --- the jumps -----------------------------------------------------------------
    groups = {}
    for nm in ang:
        groups.setdefault(nm.split("_")[0], []).append(nm)
    jumps = []
    for pref, mem in sorted(groups.items()):
        mem.sort()
        for a, b in zip(mem, mem[1:]):
            d = sep(ang[a], ang[b])
            if d > args.limit_deg:
                jumps.append((d, a, b))
    jumps.sort(reverse=True)
    print(f"{len(jumps)} consecutive pairs more than {args.limit_deg:.0f} deg apart\n")
    for d, a, b in jumps:
        print(f"  {a} -> {b}   {d:5.0f} deg")

    # Which frame of each pair is the odd one out: compare each to the frame BEFORE the
    # pair and AFTER it, and blame whichever sits away from that local run.
    suspects = []
    for pref, mem in sorted(groups.items()):
        mem.sort()
        for i in range(1, len(mem) - 1):
            prev, cur, nxt = mem[i-1], mem[i], mem[i+1]
            if sep(ang[prev], ang[cur]) > args.limit_deg and sep(ang[cur], ang[nxt]) > args.limit_deg \
               and sep(ang[prev], ang[nxt]) < args.limit_deg:
                suspects.append(cur)
    print(f"\nframes displaced from BOTH neighbours (the clearest culprits): "
          f"{len(suspects)}")
    for s in suspects:
        print(f"  {s}")
    if not suspects:
        suspects = sorted({b for _, _, b in jumps})
        print("  none isolated that way; using the later frame of each jump instead")

    # --- the database --------------------------------------------------------------
    db = sqlite3.connect(str(args.work / args.db))
    name_by_id = {i: n for i, n in db.execute("SELECT image_id, name FROM images")}
    id_by_name = {n: i for i, n in name_by_id.items()}

    print("\n=== two-view geometry of every verified pair ===")
    cfgs = Counter()
    for cfg, cnt in db.execute("SELECT config, COUNT(*) FROM two_view_geometries "
                               "WHERE rows>0 GROUP BY config"):
        cfgs[cfg] = cnt
    tot = sum(cfgs.values())
    for cfg, cnt in cfgs.most_common():
        flag = "  <-- DEGENERATE: does not determine the pose" if cfg in DEGENERATE else ""
        print(f"  {CONFIG.get(cfg, cfg):<20} {cnt:6,}  {100*cnt/tot:5.1f}%{flag}")

    # same, restricted to pairs that involve a suspect frame
    sus_ids = {id_by_name[s] for s in suspects if s in id_by_name}
    if sus_ids:
        c2 = Counter()
        for pid, cfg in db.execute("SELECT pair_id, config FROM two_view_geometries WHERE rows>0"):
            i2 = pid % MAX_PAIR_ID
            i1 = (pid - i2) // MAX_PAIR_ID
            if i1 in sus_ids or i2 in sus_ids:
                c2[cfg] += 1
        t2 = sum(c2.values())
        print(f"\n  restricted to the {len(sus_ids)} displaced frames ({t2:,} pairs):")
        for cfg, cnt in c2.most_common():
            flag = "  <-- DEGENERATE" if cfg in DEGENERATE else ""
            print(f"  {CONFIG.get(cfg, cfg):<20} {cnt:6,}  {100*cnt/t2:5.1f}%{flag}")

    # --- what did they match ON, and how far away -----------------------------------
    def load(dirp, nm):
        p = dirp / (nm + ".png")
        return np.asarray(Image.open(p).convert("L")) > 127 if p.exists() else None

    print("\n=== for each displaced frame: strongest partners, and what the inliers sit on ===")
    kp_cache = {}

    def keypoints(iid):
        if iid not in kp_cache:
            row = db.execute("SELECT rows, cols, data FROM keypoints WHERE image_id=?",
                             (iid,)).fetchone()
            n, c, blob = row
            kp_cache[iid] = np.frombuffer(blob, np.float32).reshape(n, c)[:, :2]
        return kp_cache[iid]

    for s in suspects[:args.frames]:
        sid = id_by_name.get(s)
        if sid is None:
            continue
        rows = []
        for pid, nrows, cols, blob, cfg in db.execute(
                "SELECT pair_id, rows, cols, data, config FROM two_view_geometries WHERE rows>0"):
            i2 = pid % MAX_PAIR_ID
            i1 = (pid - i2) // MAX_PAIR_ID
            if sid not in (i1, i2):
                continue
            other = i2 if i1 == sid else i1
            rows.append((nrows, other, cfg, blob, cols, i1 == sid))
        rows.sort(reverse=True)
        print(f"\n{s}   ({len(rows)} verified partners)")
        obj = load(args.masks, s)
        sh = load(args.sherds, s) if args.sherds else None
        me = load(args.measure, s) if args.measure else None
        kps = keypoints(sid)
        for nrows, other, cfg, blob, cols, first in rows[:6]:
            onm = name_by_id[other]
            d = sep(ang[s], ang[onm]) if onm in ang else float("nan")
            m = np.frombuffer(blob, np.uint32).reshape(nrows, cols)
            idx = m[:, 0] if first else m[:, 1]
            pts = kps[idx[idx < len(kps)]]
            desc = ""
            if obj is not None and len(pts):
                H, W = obj.shape
                u = np.clip(pts[:, 0].astype(int), 0, W-1)
                v = np.clip(pts[:, 1].astype(int), 0, H-1)
                on_sh = sh[v, u] if sh is not None else np.zeros(len(pts), bool)
                on_me = me[v, u] if me is not None else np.zeros(len(pts), bool)
                base = on_me & ~on_sh
                rig = obj[v, u] & ~on_me
                desc = (f"  inliers on: sherds {100*on_sh.mean():4.0f}%  "
                        f"base {100*base.mean():4.0f}%  dial+rig {100*rig.mean():4.0f}%")
            print(f"   {onm}  {nrows:5d} inliers  {d:5.0f} deg away  "
                  f"{CONFIG.get(cfg, cfg):<12}{desc}")
    db.close()


if __name__ == "__main__":
    sys.exit(main())
