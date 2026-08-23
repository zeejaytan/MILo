"""Are the turntable's coded targets readable, and for how much of the turn?

The conservator put a white disc of coded targets under the tree from the 2025-07-03 N01
batch onwards, recorded as "Use base as scale, marker on turntable for alignment". Nothing
in this workspace has ever read it. Before anything is wired into a reconstruction the
question is whether the board is legible often enough to constrain anything, and that is a
measurement rather than an assumption.

WHAT THE TARGETS ARE. Not ArUco, not ChArUco, not AprilTag. They are Agisoft Metashape
circular coded targets: a solid black centre dot, a thin white gap, then a ring cut into
arc segments that encodes the ID, with the ID printed alongside. OpenCV's aruco module
returns nothing on them -- all 27 built-in dictionaries over six N01 frames found zero
markers, while the same detector read a synthetic DICT_4X4_50 tag that had been slanted,
blurred and contrast-reduced. The detector is fine; the board is a different family.

WHY THIS DOES NOT DECODE THE ID -- AND WHY THAT IS A CHOICE, NOT A LIMIT. An earlier
version of this note claimed the targets were "far too coarse to read arc segments
reliably", on a guess of a 4-5 px centre dot. That was wrong twice over. Measured over the
674 detections in artifacts/markers/targets_03072025_N01.json the median centre-dot radius
is 6.6 px, which puts a 12-bit coded ring at r ~ 21 px with each sector spanning ~11 px of
arc -- countable, and visibly so in artifacts/markers/decode_native.png (six targets at
native resolution, 8x nearest-neighbour, no invented detail). And the conservator's own
Metashape project for this capture DID decode them: all 16 IDs, correctly, matching the
numbers printed beside each target on the board.

So the reason this script stops at the centre is not resolution. It is that a misread ID is
worse than no ID -- it puts a correspondence on the wrong point -- and for the job this
script exists to do (is the board readable, and over how much of the turn) the centre is
sufficient. Where identities ARE needed, take them from the Metashape project rather than
re-deriving them here: see docs/notes/2026-08-22-turntable-markers.md.

The centre is what this measures: a ~13 px black dot on white gives it to well under a
pixel -- confirmed against Metashape's own sub-pixel measurements at a median 0.70 px,
90th percentile 0.92 px, over 468 targets matched across all 119 frames.

HOW A TARGET IS TOLD FROM A SMUDGE. Dark ink alone is not enough; the sherd labels, the
clamp shadows and the printed numbers are all dark on light, and an early version of this
script happily returned all of them. A coded target is the only thing on the rig that is a
dark blob inside a concentric broken ring which is itself surrounded by clean board. Each
candidate is therefore sampled on circles in its OWN elliptical frame -- the disc is viewed
at up to about 75 degrees, so a target is an ellipse, not a circle -- and must show ink at
ring radius AND clean board beyond it. That third term is what rejects the labels: a
printed digit has ink around it, a coded target has emptiness.

EXIF. Every frame carries orientation 8, so the stored pixels lie on their side. COLMAP
reads stored pixels and ignores the tag, and so does this, for the same reason
scripts/build_masks.py does: anything derived here has to line up with a COLMAP model. Only
the contact sheet is rotated upright, and only so that a person can look at it.

Usage:
    python scripts/detect_markers.py D:/03072025/N01
    python scripts/detect_markers.py D:/03072025/M04 --allow-unusable   # negative control
    python scripts/detect_markers.py D:/03072025/N01 --limit 8
"""
import argparse
import json
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

REPO = Path(__file__).resolve().parent.parent
RECORD = REPO / "docs" / "reference" / "scanning-record.json"

# Every one of these was measured off three targets in A42_8355 rather than guessed; the
# radial profiles are in docs/notes/2026-08-22-turntable-markers.md. A target there has a
# dot of radius 4-5 px, ring ink out to r ~ 20 px, and clean board by r ~ 30 px. The bands
# below are those numbers expressed in units of the dot's OWN radius, which is what lets
# them survive the disc being nearer to or further from the camera.
# The disc is small in frame and ringed by a black backdrop, which is what rules out
# adaptive-mean thresholding: any window wide enough to average the board straddles that
# edge, drags the local mean down, and turns bare board into speckle -- while a window
# narrow enough to avoid the edge is comparable to a whole target and adapts to the
# target's own ink instead. Both failure modes were rendered before this was changed.
# Black-hat has neither problem: it closes the image with a disc slightly larger than the
# ink, subtracts, and so keeps exactly the dark features SMALLER than the element,
# wherever they sit and whatever the local exposure. The black backdrop contributes
# nothing to it, being uniformly dark already.
BLACKHAT_SE = 25                  # a little larger than a target's ink stroke
BLACKHAT_MIN = 40                 # grey levels below the local surround

RING_IN, RING_OUT = 2.0, 4.5      # the coded ring lives in this band
CLEAN_IN, CLEAN_OUT = 7.0, 9.0    # and beyond it the board must be empty
RING_MIN_DARK = 0.12              # some of the ring must be ink, or it is not a target
CLEAN_MAX_DARK = 0.20             # a sherd label fails here: it has neighbours
RING_OVER_CLEAN = 0.08            # and the ring must be darker than its own surroundings

MIN_TARGETS_FOR_POSE = 3          # three points is the least that fixes a plane's pose

# N01 is not one sweep. Its shutter times fall into five bursts of 23-24 frames, 2-5 s
# apart within a burst and 60-123 s apart between them -- the turntable running round once
# per burst while the camera is moved to a new height in between. That is what makes
# "degrees of the turn" a measured quantity here rather than a guess: 24 stations to a
# revolution is 15 deg a frame, so an unreadable run of four frames is a 60 deg blind arc,
# and it can be named as such. A gap anywhere near this threshold would be ambiguous; the
# observed ones are an order of magnitude either side of it.
PASS_GAP_S = 30
FULL_TURN_DEG = 360.0


def capture_id_for(directory):
    """Look this capture up in the conservator's record.

    The marker cutoff is a POSITION in the record, not a date -- M01-M04 were shot on the
    same day as N01 and carry the badly placed marker. So the folder is looked up rather
    than the date parsed.
    """
    d = Path(directory)
    if not RECORD.exists():
        return None, None
    key = f"{d.parent.name}/{d.name}" if d.parent.name else d.name
    rec = json.loads(RECORD.read_text(encoding="utf-8"))
    for season in rec.get("seasons", []):
        for entry in season.get("entries", []):
            if (entry.get("on_disk") or {}).get("dir") in (key, d.name):
                return entry.get("capture_id"), entry.get("markers_usable")
    return None, None


def shot_time(path):
    """Seconds since the epoch of day, from EXIF DateTimeOriginal. None if absent."""
    try:
        exif = Image.open(path)._getexif() or {}
    except Exception:
        return None
    stamp = exif.get(36867) or exif.get(306)          # DateTimeOriginal, then DateTime
    if not isinstance(stamp, str):
        return None
    try:
        hh, mm, ss = stamp.split()[1].split(":")
    except (IndexError, ValueError):
        return None
    return int(hh) * 3600 + int(mm) * 60 + int(ss)


def split_passes(frames):
    """One list per revolution of the turntable, cut where the shutter went quiet.

    Filename order alone would run the five revolutions together and make the 119 frames
    look like a single 3 deg-per-step sweep, which would understate every blind arc by a
    factor of five. If the timestamps cannot be read the frames are returned as one pass
    and the caller says so, rather than inventing a step angle.
    """
    times = [shot_time(f) for f in frames]
    if any(t is None for t in times):
        return [list(frames)], False
    passes, current = [], [frames[0]]
    for prev, this, f in zip(times, times[1:], frames[1:]):
        if this - prev > PASS_GAP_S:
            passes.append(current)
            current = []
        current.append(f)
    passes.append(current)
    return passes, True


def longest_blind_run(ok):
    """Longest run of unreadable stations, counted round the circle.

    Wrapping matters and is not a nicety. A revolution ends where it began, so a board that
    goes dark over the last two stations and the first three has a five-station blind arc,
    not a three and a two. Read linearly it would be reported as the smaller number, which
    is the flattering direction.
    """
    if all(ok):
        return 0
    if not any(ok):
        return len(ok)
    start = ok.index(True)
    rolled = ok[start:] + ok[:start]
    run = worst = 0
    for good in rolled:
        run = 0 if good else run + 1
        worst = max(worst, run)
    return worst


def sample_ring(gray, ell, k, nbin=128):
    """Intensities around the circle at k times the dot's radius, in the dot's own frame."""
    (cx, cy), (major, minor), angle_deg = ell
    a, b = k * major / 2.0, k * minor / 2.0
    t = np.radians(angle_deg)
    ct, st = np.cos(t), np.sin(t)
    th = np.linspace(0, 2 * np.pi, nbin, endpoint=False)
    u, v = a * np.cos(th), b * np.sin(th)
    x = np.clip((cx + u * ct - v * st).round().astype(int), 0, gray.shape[1] - 1)
    y = np.clip((cy + u * st + v * ct).round().astype(int), 0, gray.shape[0] - 1)
    return gray[y, x].astype(float)


def dark_fraction(gray, ell, k0, k1, white, step=0.25):
    ks = np.arange(k0, k1 + 1e-9, step)
    return max((sample_ring(gray, ell, k) < 0.60 * white).mean() for k in ks)


def find_targets(gray):
    """Every coded target this frame can be SHOWN to contain."""
    # Local, because the disc is brightly lit through part of the turn and in the tree's own
    # shadow through the rest; one global threshold reads the shadowed half as bare board.
    se = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (BLACKHAT_SE, BLACKHAT_SE))
    ink = (cv2.morphologyEx(gray, cv2.MORPH_BLACKHAT, se) > BLACKHAT_MIN).astype(np.uint8)
    contours, _ = cv2.findContours(ink, cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE)
    height, width = gray.shape
    found = []
    for c in contours:
        if len(c) < 8:
            continue
        area = cv2.contourArea(c)
        if not (12.0 <= area <= 600.0):
            continue
        x, y, w, h = cv2.boundingRect(c)
        if max(w, h) > 60 or area / max(1, w * h) < 0.55:
            continue
        ell = cv2.fitEllipse(c)
        (cx, cy), (major, minor), _ = ell
        if major < 2 or minor < 2 or min(major, minor) / max(major, minor) < 0.25:
            continue                                    # past ~75 deg the dot is a line
        rdot = float(np.sqrt(area / np.pi))
        if not (1.6 <= rdot <= 14.0):
            continue

        pad = int(10 * rdot)
        patch = gray[max(0, int(cy) - pad):int(cy) + pad,
                     max(0, int(cx) - pad):int(cx) + pad]
        if patch.size < 100:
            continue
        white = float(np.percentile(patch, 92))
        if white < 90:                                  # not sitting on a lit white board
            continue
        dot = float(np.mean(gray[max(0, int(cy) - 1):int(cy) + 2,
                                 max(0, int(cx) - 1):int(cx) + 2]))
        if dot > 0.50 * white:                          # not solid ink
            continue

        ring = dark_fraction(gray, ell, RING_IN, RING_OUT, white)
        clean = dark_fraction(gray, ell, CLEAN_IN, CLEAN_OUT, white)
        if ring < RING_MIN_DARK or clean > CLEAN_MAX_DARK or ring - clean < RING_OVER_CLEAN:
            continue

        found.append(dict(
            x=float(cx), y=float(cy), rdot=rdot, ring=float(ring), clean=float(clean),
            touches_edge=bool(cx < 6 * rdot or cy < 6 * rdot
                              or cx > width - 6 * rdot or cy > height - 6 * rdot),
        ))
    return merge_duplicates(found)


def merge_duplicates(found):
    """One detection per target, not one per piece of ink.

    A target's centre dot and each arc of its ring are separate blobs, and an arc sitting
    beside the dot passes the same tests the dot does -- it too has ink at ring radius and
    clean board beyond. Rendered on A42_8355 this showed up at once: target 5 carried three
    overlapping circles, 10 and 25 two each, so a disc of fourteen targets was reported as
    twenty. Counting ink instead of targets would have inflated every readability figure in
    the report, in the flattering direction.

    Anything inside a stronger detection's own ring band is part of that same target, so
    RING_OUT is the merge radius rather than an invented constant. The strongest is kept,
    where strength is the margin by which the ring beat its surroundings.
    """
    kept = []
    for t in sorted(found, key=lambda h: h["ring"] - h["clean"], reverse=True):
        if any((t["x"] - k["x"]) ** 2 + (t["y"] - k["y"]) ** 2
               < (RING_OUT * max(t["rdot"], k["rdot"])) ** 2 for k in kept):
            continue
        kept.append(t)
    return kept


def contact_sheet(tiles, path):
    """Detections drawn on the photographs.

    Not optional. A mask that silently did nothing cost 1h37m on A02, and a detector that
    silently finds nothing looks exactly like a board that is not there.
    """
    if not tiles:
        return
    if len(tiles) > 6:
        # ceil, and pad the short row. An earlier floor-divide silently dropped the last
        # tile of any odd-length turn -- turn 3 has 23 stations and the sheet showed 22,
        # so the one frame a reader would have gone looking for was the one missing. A
        # sheet that quietly omits frames is the same failure as a metric that quietly
        # omits them.
        half = -(-len(tiles) // 2)
        rows = [tiles[:half], tiles[half:]]
        rows[1] += [np.zeros_like(tiles[0])] * (half - len(rows[1]))
        sheet = np.vstack([np.hstack(r) for r in rows])
    else:
        sheet = np.hstack(tiles)
    cv2.imwrite(str(path), sheet)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("directory")
    ap.add_argument("--out", default=str(REPO / "artifacts" / "markers"))
    ap.add_argument("--limit", type=int, default=0, help="first N frames only (smoke test)")
    ap.add_argument("--allow-unusable", action="store_true",
                    help="run on a capture the record flags markers_usable=false. Only for "
                         "the negative control -- those boards are badly placed and any "
                         "number off them is meaningless as alignment evidence.")
    args = ap.parse_args()

    src = Path(args.directory)
    # The record is consulted BEFORE the frames are even listed. A capture flagged
    # markers_usable=false should cost nothing to refuse, and the refusal should not
    # depend on whether its photographs happen to be on this machine yet.
    capture, usable = capture_id_for(src)
    print(f"{src}  ->  record: {capture or 'NOT IN RECORD'}   markers_usable={usable}")
    if usable is False and not args.allow_unusable:
        sys.exit("the record says this capture's marker is badly placed; refusing.\n"
                 "Pass --allow-unusable only to use it as a negative control.")
    if usable is None:
        print("  WARNING: not in the record -- treating as unknown", file=sys.stderr)

    # dict.fromkeys, not a plain concatenation: Windows globs case-insensitively, so
    # "*.JPG" and "*.jpg" return the SAME files here and every frame was being processed
    # and counted twice. On Linux they return disjoint sets and both are needed.
    frames = sorted(dict.fromkeys(list(src.glob("*.JPG")) + list(src.glob("*.jpg"))))
    if args.limit:
        frames = frames[:args.limit]
        print("  --limit: a partial capture. Target counts are real; every ANGLE below is\n"
              "           not, because the stations of a turn are no longer all present.",
              file=sys.stderr)
    if not frames:
        sys.exit(f"no JPGs under {src}")

    passes, timed = split_passes(frames)
    where = {f: (p, i, FULL_TURN_DEG / len(grp))
             for p, grp in enumerate(passes, 1) for i, f in enumerate(grp)}

    outdir = Path(args.out)
    outdir.mkdir(parents=True, exist_ok=True)
    rows = []
    tiles = {}                       # turn -> its stations, in order

    for i, f in enumerate(frames):
        img = cv2.imread(str(f), cv2.IMREAD_COLOR | cv2.IMREAD_IGNORE_ORIENTATION)
        if img is None:
            print(f"  {f.name}: unreadable", file=sys.stderr)
            continue
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        hits = find_targets(gray)
        p, station, step = where[f]
        rows.append(dict(frame=f.name, n=len(hits), turn=p, station=station,
                         deg=round(station * step, 1),
                         clipped=sum(h["touches_edge"] for h in hits), targets=hits))
        print(f"  {f.name}  turn {p} at {station * step:5.1f} deg   targets {len(hits):3d}")

        # A sheet per revolution, every station of it, rather than a scatter across all
        # five. The sheet then IS the turn the degrees figure describes, so a blind arc has
        # to appear in both or one of them is wrong. Sheets are written for the readable
        # turns as well as the blind ones: a turn that reads 360 deg has to LOOK like a
        # board that was visible all the way round, or the number is measuring something
        # else.
        if True:
            vis = img.copy()
            for h in hits:
                cv2.circle(vis, (int(h["x"]), int(h["y"])), int(8 * h["rdot"]), (0, 255, 0), 3)
            vis = cv2.rotate(vis, cv2.ROTATE_90_COUNTERCLOCKWISE)   # upright, to look at
            tile = cv2.resize(vis, (330, 495), interpolation=cv2.INTER_AREA)
            cv2.putText(tile, f"{f.stem[-4:]} {station * step:.0f}deg n={len(hits)}", (6, 24),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
            tiles.setdefault(p, []).append(tile)

    sheets = []
    for p, group in sorted(tiles.items()):
        path = outdir / f"contact_{src.parent.name}_{src.name}_turn{p}.png"
        contact_sheet(group, path)
        sheets.append(path)

    counts = np.array([r["n"] for r in rows])
    readable = int((counts >= MIN_TARGETS_FOR_POSE).sum())

    print(f"\n{len(rows)} frames in {len(passes)} revolution(s) of the turntable")
    if not timed:
        print("  WARNING: no EXIF shutter times, so the frames could not be split into")
        print("           revolutions. Every angle below assumes one turn and is wrong if")
        print("           this capture was shot at more than one camera height.")
    print(f"  targets per frame: median {np.median(counts):.0f}, max {counts.max()}, "
          f"none at all in {(counts == 0).sum()} frames")
    print(f"  frames with >= {MIN_TARGETS_FOR_POSE} targets (enough to fix the board's "
          f"pose): {readable}/{len(rows)} = {100 * readable / len(rows):.0f}%")
    clipped = sum(1 for r in rows if r["clipped"])
    print(f"  board runs off the edge of the picture in {clipped} frames")

    print("\n  how much of each turn the board can be read on:")
    worst_arc = 0.0
    for p, grp in enumerate(passes, 1):
        seq = [r for r in rows if r["turn"] == p]
        if not seq:
            continue
        step = FULL_TURN_DEG / len(grp)
        ok = [r["n"] >= MIN_TARGETS_FOR_POSE for r in seq]
        arc = longest_blind_run(ok) * step
        worst_arc = max(worst_arc, arc)
        print(f"    turn {p} ({len(grp)} stations, {step:.1f} deg apart): "
              f"readable at {sum(ok):2d} of them = {sum(ok) * step:5.1f} deg of 360;  "
              f"largest blind arc {arc:5.1f} deg")
    print(f"  worst blind arc anywhere in the capture: {worst_arc:.1f} deg")
    if counts.max() == counts.min():
        print("  WARNING: an identical count in every frame. A detector that cannot vary")
        print("           is a bug until proven otherwise -- do not report this as a result.")
    for path in sheets:
        print(f"  contact sheet    -> {path}")

    detail = outdir / f"targets_{src.parent.name}_{src.name}.json"
    detail.write_text(json.dumps(dict(capture=capture, markers_usable=usable, frames=rows),
                                 indent=1), encoding="utf-8")
    print(f"  per-frame detail -> {detail}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
