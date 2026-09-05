"""The picture that can actually show a scale error: two meshes cut through the wall.

A scale error is a PROPORTIONAL change, and a three-quarter view of a whole sherd cannot
show one -- a sherd 8% too large looks like a sherd. What shows it is a section: cut both
meshes with the same plane, draw the two outlines in one frame, and burn in a millimetre
bar. A wall that should be 6 mm and is drawn 6.5 mm is visible; the same error on the
overall silhouette is not.

NOT A RENDER, A CUT. This started as a plan to rasterise a view with nvdiffrast on a GPU
node. That was the wrong instrument twice over: nothing here needs gradients or a GPU, and
more importantly a rasterised viewpoint is the thing that has already failed in this repo
four times by being too coarse for the effect being tested. A planar cut has no viewpoint
to get wrong. `../AGENTS.md`: "When a proxy view keeps failing, render the measured
quantity itself." So the wall thickness is measured off the section, in millimetres, and
the measurement is drawn on the picture as the chords it was taken across.

THE VIEW IS SIZED FROM THE SCALE IT MUST RESOLVE. The frame is chosen so the wall spans at
least `--min-wall-px` pixels, zooming in on the wall and showing a locator inset of the
whole section beside it. Note what that does and does not buy: because the window is
DERIVED from the wall figure, the pixels-per-millimetre printed on the picture follows from
that figure and cannot contradict it. It is a statement of the view, not a check on the
measurement. The measurement is checked by the spread printed beside it -- the longest and
the thinnest-5% chord -- and by the self-test.

Exit status: 0 drawn; 2 a mesh has no scale record; 3 the records disagree; 4 the plane
misses every mesh. Nothing is written except on 0.

Units come from the sidecar contract in `scale_sidecar.py` and from nowhere else: two
meshes are drawn together in millimetres only when both can say what units they are in and
agree. `--shape-only` is the named way to get a unit-free picture, and it draws no bar and
quotes no millimetre (see `docs/adr/0001-refuse-rather-than-degrade-when-scale-is-unknown.md`).

Usage:
    python section_overlay.py --mesh milo=a.ply --mesh openmvs=b.ply --out section.png
    python section_overlay.py ... --shape-only          # no bar, no millimetre
    python section_overlay.py --self-test               # no data needed; proves the gate
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import trimesh
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
from scale_sidecar import (                                          # noqa: E402
    RC_OK, exit_code_for_scale, provenance_lines, scale_decision, sidecar_path,
)

# The fourth exit status, and the only one this script adds. 0, 2 and 3 are the shared
# scale gate's and are named in `scale_sidecar.py`; this one is about geometry, not scale.
# It is named rather than written as a bare 4 for the reason ADR 0001 turns on: the self-
# test asserts exit STATUS, and a status that exists only as a literal in two places is
# one edit away from being asserted against itself.
RC_PLANE_MISSES = 4    # the cutting plane touches none of the meshes

# The frame. A wide panel because a section of a turntable tray is wider than it is tall,
# and a locator inset in the corner so the zoom cannot hide where it was taken from.
PANEL_W, PANEL_H = 1000, 660
HEAD_H, FOOT_H = 58, 74
INSET = 190
BG = (22, 22, 26)
INK = (232, 232, 236)
DIM = (140, 140, 148)
# Two hues that stay distinguishable in greyscale as well as in colour, because these
# pictures get printed into notes.
COLOURS = [(240, 138, 62), (86, 166, 240), (150, 220, 130), (222, 120, 200)]
# Dimmer than either outline: the chords are the working shown, not the finding.
CHORD = (104, 104, 116)

# How many pixels the wall must span before the picture is allowed to claim it resolves
# the wall. Six is not a lot; it is the point below which a half-millimetre difference
# stops being a difference you can see rather than one you have to be told about.
MIN_WALL_PX = 6


# --------------------------------------------------------------------------------------
# Cutting
# --------------------------------------------------------------------------------------

def plane_basis(normal):
    """A 2D frame for the cutting plane, built ONCE and shared by every mesh.

    trimesh's `Path3D.to_planar()` picks its own frame per path, which is fine for one
    mesh and wrong for an overlay: two meshes cut on the same plane would land in two
    different 2D frames and the outlines would not line up, while still looking like a
    picture of two meshes that disagree. Building the basis here means the only thing the
    two outlines can disagree about is the geometry.
    """
    n = np.asarray(normal, float)
    n = n / np.linalg.norm(n)
    seed = np.array([0.0, 0.0, 1.0]) if abs(n[2]) < 0.9 else np.array([1.0, 0.0, 0.0])
    u = np.cross(seed, n)
    u /= np.linalg.norm(u)
    return u, np.cross(n, u), n


def section_loops(mesh, origin, basis, mm_per_unit=1.0):
    """The mesh's outline where the plane cuts it, as 2D polylines in millimetres.

    Returns [] when the plane misses the mesh entirely -- which is a fact about the plane,
    not an error, and the caller says so rather than crashing.
    """
    u, v, n = basis
    cut = mesh.section(plane_normal=n, plane_origin=origin)
    if cut is None:
        return []
    out = []
    for line in cut.discrete:
        p = np.asarray(line, float) - np.asarray(origin, float)
        out.append(np.column_stack([p @ u, p @ v]) * mm_per_unit)
    return out


def resample(loop, spacing):
    """Points at even spacing along a polyline, so thickness is measured evenly.

    Without this the measurement is biased towards wherever the mesh happens to be finely
    triangulated, which is not where the wall happens to be interesting.
    """
    seg = np.linalg.norm(np.diff(loop, axis=0), axis=1)
    arc = np.concatenate([[0.0], np.cumsum(seg)])
    if arc[-1] <= 0:
        return loop[:1]
    want = np.arange(0.0, arc[-1], max(spacing, arc[-1] / 4000.0))
    return np.column_stack([np.interp(want, arc, loop[:, 0]),
                            np.interp(want, arc, loop[:, 1])])


def _inside(pts, A, B):
    """Even-odd test: is each point inside the outline made by segments A->B?

    Used to throw away chords that leave the clay. A ray cast from one sherd across an
    empty turntable will happily land on a different sherd 700 mm away, and the median of
    those is a number with no physical meaning that still prints to two decimals. This was
    visible in the first real render and invisible in every figure printed beside it.
    """
    if len(A) == 0:
        return np.zeros(len(pts), bool)
    ay, by = A[None, :, 1], B[None, :, 1]
    py, px = pts[:, None, 1], pts[:, None, 0]
    straddles = (ay > py) != (by > py)
    with np.errstate(divide="ignore", invalid="ignore"):
        xcross = (A[None, :, 0]
                  + (py - ay) / np.where(by - ay == 0, np.nan, by - ay)
                  * (B[None, :, 0] - A[None, :, 0]))
    return ((straddles & (px < xcross)).sum(axis=1) % 2).astype(bool)


def carrying_loops(loops, min_fraction_of_longest=0.1):
    """The outlines that carry the material, dropping specks shorter than a tenth of the
    longest. Shared by the measurement and by the caption that reports it, so the picture
    cannot say it measured more outlines than it did."""
    lens = [float(np.linalg.norm(np.diff(l, axis=0), axis=1).sum()) for l in loops]
    longest = max(lens) if lens else 0.0
    return [l for l, n in zip(loops, lens)
            if n > 0 and n >= min_fraction_of_longest * longest]


def wall_chords(loops, max_samples=600):
    """Wall thickness measured across the section, as the chords it was measured on.

    THE MEASUREMENT, NOT A PROXY FOR IT. From each sample point on the outline, a ray is
    cast along the local normal -- both ways -- and the nearest crossing of any other part
    of the outline is the wall at that point. That is the same quantity a conservator takes
    with a caliper across a sherd, and it does not depend on the viewpoint, the framing or
    the triangulation.

    NOT THE SAME "WALL" AS `compare_meshes.wall_thickness()`, and the two will not agree.
    That one samples ~20,000 rays over the WHOLE surface in 3D and reports median with
    p10/p90; this one measures only where the cut is, in 2D, and reports median with its
    longest and thinnest-5% chord. A section figure answers "how thick is the wall HERE,
    at a place I can point to and put callipers on"; the 3D one answers "how thick is this
    sherd overall". Say which is being quoted -- a conservator handed both without that
    will read the difference as an error in one of them.

    Returns (chords, widths): chords is (K, 2, 2) of endpoint pairs to draw, widths is (K,)
    in the same units the loops are in. Both are empty when the section has no closed
    outline to measure across, which is what a plane clipping a corner produces.
    """
    if not loops:
        return np.zeros((0, 2, 2)), np.zeros(0)

    # SPECKS ARE NOT WALLS. A section of a real reconstruction is the sherd plus dozens of
    # stray fragments a few tenths of a millimetre across. Every one of them contributes
    # chords, they outnumber the clay, and the median then reports the size of the noise --
    # 0.13 mm on the first real crop, printed with the same confidence as a real figure.
    # Outlines shorter than a tenth of the longest are dropped from the MEASUREMENT only;
    # they are still drawn, because hiding them would be a different lie.
    loops = carrying_loops(loops)
    if not loops:
        return np.zeros((0, 2, 2)), np.zeros(0)

    total = sum(np.linalg.norm(np.diff(l, axis=0), axis=1).sum() for l in loops)
    if total <= 0:
        return np.zeros((0, 2, 2)), np.zeros(0)
    spacing = total / max_samples

    segA, segD, seg_loop, seg_arc = [], [], [], []
    pts, nrm, pt_loop, pt_arc = [], [], [], []
    loop_len = []
    for k, loop in enumerate(loops):
        step = np.linalg.norm(np.diff(loop, axis=0), axis=1)
        arc = np.concatenate([[0.0], np.cumsum(step)])
        loop_len.append(float(arc[-1]))
        segA.append(loop[:-1])
        segD.append(np.diff(loop, axis=0))
        seg_loop.append(np.full(len(loop) - 1, k))
        seg_arc.append((arc[:-1] + arc[1:]) / 2.0)
        r = resample(loop, spacing)
        if len(r) < 3:
            continue
        t = np.gradient(r, axis=0)
        t /= np.maximum(np.linalg.norm(t, axis=1, keepdims=True), 1e-12)
        pts.append(r)
        nrm.append(np.column_stack([-t[:, 1], t[:, 0]]))
        pt_loop.append(np.full(len(r), k))
        pt_arc.append(np.linspace(0.0, arc[-1], len(r), endpoint=False))
    if not pts:
        return np.zeros((0, 2, 2)), np.zeros(0)
    P, N = np.concatenate(pts), np.concatenate(nrm)
    PL, PA = np.concatenate(pt_loop), np.concatenate(pt_arc)
    A, D = np.concatenate(segA), np.concatenate(segD)
    SL, SA = np.concatenate(seg_loop), np.concatenate(seg_arc)
    L = np.array(loop_len, float)

    # WHICH SEGMENTS A RAY IS ALLOWED TO HIT. A ray leaving a point on the outline starts
    # on that point's own segment and grazes its neighbours, so those have to go. The
    # obvious way -- discard crossings nearer than some distance -- is the mistake this
    # whole script exists to catch, one level down: any distance wide enough to clear the
    # neighbours can be wider than the wall, and then the ray sails through the wall and
    # measures the far side of the pot instead. That is a ruler too coarse for the effect,
    # and it reports a confident number rather than failing.
    #
    # So the guard is in ARC LENGTH ALONG THE OUTLINE, which is what "neighbouring" means,
    # and it has no opinion about distance across the wall. A segment is excluded only
    # when it is on the same loop AND within a few samples' walk of the origin; the wall
    # opposite is many samples away however thin it is.
    guard = spacing * 3.0
    same = PL[:, None] == SL[None, :]
    darc = np.abs(PA[:, None] - SA[None, :])
    circ = np.where(same, np.minimum(darc, np.abs(L[PL][:, None] - darc)), np.inf)
    blocked = same & (circ < guard)

    hits = np.full(len(P), np.inf)
    end = np.zeros((len(P), 2))
    # Solve `o + t*d = A + s*D` for every (sample, segment) pair at once. Cross-products,
    # not a per-axis division: the per-axis form has to pick which axis to divide by and
    # gets it wrong for a ray running along one of them.
    W = A[None, :, :] - P[:, None, :]                       # (K, M, 2)
    for sign in (1.0, -1.0):
        d = N * sign                                        # (K, 2)
        den = d[:, None, 0] * D[None, :, 1] - d[:, None, 1] * D[None, :, 0]
        with np.errstate(divide="ignore", invalid="ignore"):
            t = (W[:, :, 0] * D[None, :, 1] - W[:, :, 1] * D[None, :, 0]) / den
            s = (W[:, :, 0] * d[:, None, 1] - W[:, :, 1] * d[:, None, 0]) / den
        good = ((np.abs(den) > 1e-12) & (s >= 0.0) & (s <= 1.0) & (t > 0.0)
                & np.isfinite(t) & ~blocked)
        t = np.where(good, t, np.inf)
        best = t.min(axis=1)
        # A chord counts only if it stayed in the clay. There is no boundary between the
        # sample point and its FIRST crossing, so the whole chord is on one side of the
        # material and its midpoint decides which.
        live = np.isfinite(best)
        if live.any():
            mid = P[live] + d[live] * (best[live, None] / 2.0)
            keep_dir = _inside(mid, A, A + D)
            idx = np.flatnonzero(live)[~keep_dir]
            best[idx] = np.inf
        take = best < hits
        hits[take] = best[take]
        end[take] = P[take] + d[take] * best[take, None]

    keep = np.isfinite(hits)
    if not keep.any():
        return np.zeros((0, 2, 2)), np.zeros(0)
    return np.stack([P[keep], end[keep]], axis=1), hits[keep]


# --------------------------------------------------------------------------------------
# Framing -- the part that decides whether the picture answers the right question
# --------------------------------------------------------------------------------------

def panel_px_per_mm(span):
    """Pixels per millimetre on the main panel, given the span it shows.

    ONE definition, because the scale bar, the caption and the window sizing must agree.
    The projection fits the span to the SHORT side of the panel, so computing this from the
    long side promises a resolution the picture does not deliver -- the self-test caught
    exactly that, and it was four separate copies of the expression that let it happen.
    """
    return min(PANEL_W, PANEL_H) / span


def whole_view(loops):
    """(centre, span) showing every outline, with a small margin. The unzoomed view."""
    P = np.concatenate(loops)
    lo, hi = P.min(axis=0), P.max(axis=0)
    return (lo + hi) / 2.0, float(max(hi - lo)) * 1.06


def choose_window(loops, wall, min_wall_px):
    """(centre, span) for the main panel, zoomed until the wall is worth looking at.

    Returns the whole section when the whole section already resolves the wall; otherwise
    a window centred on the wall. `span` is in the units the loops are in.

    A picture can answer the wrong question as easily as a statistic can, and looks just as
    convincing while doing it. Four views in this repo have already failed that way. The
    only defence is to state the scale the view must resolve and then check the view
    against it -- which is what this does, and why `px_per_mm` is printed on the picture.
    """
    full_centre, full = whole_view(loops)
    if not np.isfinite(wall) or wall <= 0:
        return full_centre, full
    # The span at which `panel_px_per_mm` returns exactly `min_wall_px / wall` -- i.e. the
    # widest view that still puts `min_wall_px` pixels across the wall. Inverting the one
    # helper rather than repeating its expression is the whole point of having it.
    want = wall * min(PANEL_W, PANEL_H) / float(min_wall_px)
    if want >= full:
        return full_centre, full
    P = np.concatenate(loops)
    lo, hi = P.min(axis=0), P.max(axis=0)
    # Centre on the middle of the outline's own extent rather than on a hand-picked
    # feature, then nudge onto the nearest actual outline point so the zoom cannot land
    # in the hollow middle of a pot and show nothing at all.
    c = (lo + hi) / 2.0
    return P[np.argmin(np.linalg.norm(P - c, axis=1))], want


# --------------------------------------------------------------------------------------
# Drawing
# --------------------------------------------------------------------------------------

_MEASURE = ImageDraw.Draw(Image.new("RGB", (1, 1)))


def _text_px(text):
    """Width of `text` in pixels, in the font the caption is drawn with."""
    return float(_MEASURE.textlength(text))


def _wrap_notes(notes, width_px):
    """Caption lines wrapped to `width_px`, continuations indented so a wrapped line is
    visibly part of the note above it rather than a new claim."""
    out = []
    for note in notes:
        words, line, indent = note.split(" "), "", ""
        for w in words:
            trial = (line + " " + w) if line else (indent + w)
            if line and _text_px(trial) > width_px:
                out.append(line)
                indent, line = "    ", "    " + w
            else:
                line = trial
        out.append(line)
    return out


def _project(pts, centre, span, w, h, ox=0, oy=0):
    s = min(w, h) / span
    x = (pts[:, 0] - centre[0]) * s + ox + w / 2.0
    y = oy + h / 2.0 - (pts[:, 1] - centre[1]) * s
    return np.column_stack([x, y]), s


def _nice_bar(span_mm):
    """A round number of millimetres that spans roughly a quarter of the panel."""
    target = span_mm / 4.0
    for step in (0.1, 0.2, 0.5, 1, 2, 5, 10, 20, 50, 100, 200, 500):
        if step >= target:
            return step
    return 1000


def draw(sections, out_path, centre, span, metric, wall_mm, title, notes,
         chords=None, locator=None):
    """Write the picture. Returns what it actually drew, so a test can assert on it.

    `metric` False means --shape-only: no bar, no millimetre anywhere on the image. The
    dict this returns is the honest record of that -- asserting on the drawn pixels would
    test the font, and asserting on stdout would test the wording.
    """
    # THE CAPTION MUST FIT ON THE PICTURE. It did not: the first real render of this file
    # ran the sentence about the spread off the right-hand edge, so the one line telling a
    # reader how to judge the number was cut in half by the frame. A caption is not a log
    # entry -- it travels with the image into a report, where nobody can go and read the
    # rest of it. So the lines are wrapped to the panel here and the footer is grown to
    # hold however many that comes to, rather than a fixed height that silently clips.
    wrapped = _wrap_notes(notes, PANEL_W - 28)
    foot_h = max(FOOT_H, 16 + 14 * len(wrapped))
    img = Image.new("RGB", (PANEL_W, HEAD_H + PANEL_H + foot_h), BG)
    d = ImageDraw.Draw(img)
    d.text((14, 12), title, fill=INK)

    # The cut is drawn on its OWN image and pasted in, so a zoomed view is clipped at the
    # panel edge instead of spilling across the scale bar and the caption. A picture whose
    # geometry overlaps its own units is one misreading away from being quoted wrong.
    panel = Image.new("RGB", (PANEL_W, PANEL_H), BG)
    pd = ImageDraw.Draw(panel)

    # The chords the wall was measured on, UNDER the outlines and dimmer than them: they
    # are the evidence for the caption's number, not the subject of the picture. A number
    # in the footer that cannot be traced to where it was taken is exactly the kind of
    # statistic that survived three rounds of validation here while being wrong.
    if metric and chords is not None and len(chords):
        step = max(1, len(chords) // 70)
        for c in chords[::step]:
            xy, _ = _project(c, centre, span, PANEL_W, PANEL_H)
            pd.line([tuple(xy[0]), tuple(xy[1])], fill=CHORD, width=1)

    for i, (tag, loops) in enumerate(sections):
        col = COLOURS[i % len(COLOURS)]
        for loop in loops:
            xy, _ = _project(loop, centre, span, PANEL_W, PANEL_H)
            pd.line([tuple(p) for p in xy], fill=col, width=2)
        d.text((14, 30 + 14 * i), "%s  %s" % ("---", tag), fill=col)

    img.paste(panel, (0, HEAD_H))

    px_per_mm = panel_px_per_mm(span) if metric else None
    bar_drawn = False
    if metric:
        step = _nice_bar(span)
        px = step * px_per_mm
        x0, y0 = 26, HEAD_H + PANEL_H - 30
        d.line([(x0, y0), (x0 + px, y0)], fill=INK, width=3)
        for x in (x0, x0 + px):
            d.line([(x, y0 - 6), (x, y0 + 6)], fill=INK, width=2)
        d.text((x0, y0 + 10), "%g mm" % step, fill=INK)
        bar_drawn = True

    if locator is not None:
        lx, ly = PANEL_W - INSET - 14, HEAD_H + 14
        d.rectangle([lx, ly, lx + INSET, ly + INSET], outline=DIM)
        lc, lspan = locator
        for i, (tag, loops) in enumerate(sections):
            for loop in loops:
                xy, _ = _project(loop, lc, lspan, INSET, INSET, lx, ly)
                d.line([tuple(p) for p in xy], fill=COLOURS[i % len(COLOURS)], width=1)
        s = INSET / lspan
        per_mm = panel_px_per_mm(span)
        hw, hh = PANEL_W / (2 * per_mm), PANEL_H / (2 * per_mm)
        bx = lx + INSET / 2 + (centre[0] - lc[0]) * s
        by = ly + INSET / 2 - (centre[1] - lc[1]) * s
        d.rectangle([bx - hw * s, by - hh * s, bx + hw * s, by + hh * s], outline=INK)
        d.text((lx, ly - 14), "whole section", fill=DIM)

    y = HEAD_H + PANEL_H + 8
    for line in wrapped:
        d.text((14, y), line, fill=DIM)
        y += 14
    overflow = max([_text_px(l) - (PANEL_W - 28) for l in wrapped] + [0.0])

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path)
    return {"path": str(out_path), "bar_drawn": bar_drawn, "px_per_mm": px_per_mm,
            "wall_mm": wall_mm if metric else None, "span": span,
            # The window, so a caller -- the self-test -- can reproject a known distance
            # and check the picture is drawn at the scale the caption claims for it.
            "centre": [float(centre[0]), float(centre[1])],
            # How far the widest caption line runs past the edge of the image, in pixels.
            # 0 means the whole caption is readable. Anything above 0 means the picture is
            # carrying a sentence nobody can finish reading.
            "caption_overflow_px": float(overflow), "caption_lines": len(wrapped),
            "wall_px": (wall_mm * px_per_mm) if (metric and wall_mm) else None}


# --------------------------------------------------------------------------------------
# The one operation
# --------------------------------------------------------------------------------------

def section_overlay(paths, out_path, axis="z", offset=0.0, shape_only=False,
                    min_wall_px=MIN_WALL_PX, quiet=False):
    """Cut, measure, draw. Returns (exit_status, info).

    `info` is None whenever nothing was drawn, so a caller cannot mistake a refusal for a
    picture. The refusal happens BEFORE any mesh is loaded -- a gate that runs after the
    expensive part still costs the expensive part, and a gate that writes its output first
    and then prints REFUSED has not refused anything.
    """
    decision = scale_decision(paths, shape_only=shape_only)
    status = exit_code_for_scale(decision)
    lines = provenance_lines(decision)
    if not quiet:
        for line in lines:
            print(line)
    if status != RC_OK:
        if not quiet:
            print("")
            for r in decision["reasons"]:
                print("  " + r)
            print("\nNo section is drawn. A picture of two meshes whose units are unknown "
                  "would carry a scale bar that means nothing, or none at all and imply a "
                  "size anyway. Rerun with --shape-only for the unit-free half.")
        return status, None

    metric = decision["metric"]
    basis = plane_basis({"x": [1, 0, 0], "y": [0, 1, 0], "z": [0, 0, 1]}[axis])
    meshes = {t: trimesh.load(str(p), process=False) for t, p in paths.items()}

    # ONE plane, ONE origin, for every mesh. Taking each mesh's own centroid would cut two
    # meshes with two different planes and then re-centre each outline on itself, so two
    # sherds 20 mm apart would be drawn on top of each other and a placement error would
    # vanish into the frame. The reference is the first mesh named on the command line;
    # --offset moves the shared plane, never one mesh's plane.
    #
    # NO `.get(tag, 1.0)` HERE. Defaulting a missing factor to 1.0 is the degrade ADR 0001
    # exists to ban: it would silently treat a metre-scale mesh as millimetres. Past the
    # gate above, `metric` means every mesh has a factor, so index it and let a KeyError be
    # loud if that ever stops being true. In shape-only there is no factor to miss, and
    # --offset is then in the mesh's own units, which the caption says.
    first = next(iter(paths))
    factors = decision["mm_per_unit"]
    origin = (np.asarray(meshes[first].centroid, float)
              + basis[2] * (offset / factors[first] if metric else offset))

    sections, raw = [], {}
    for tag, mesh in meshes.items():
        mm = factors[tag] if metric else 1.0
        loops = section_loops(mesh, origin, basis, mm_per_unit=mm)
        raw[tag] = loops
        if loops:
            sections.append((tag, loops))

    missed = [t for t, l in raw.items() if not l]
    if not sections:
        if not quiet:
            print("\nThe plane misses every mesh -- nothing to draw. Try another --axis or "
                  "--offset.")
        return RC_PLANE_MISSES, None

    if not metric:
        # SHAPE ONLY. The outlines are normalised, so the picture compares shape and cannot
        # be read for size. Drawing them at their raw coordinates beside a scale bar would
        # be a size comparison in units nobody has established -- the degrade-to-default
        # ADR 0001 exists to ban, wearing a picture's clothes.
        #
        # ONE normalisation for both, taken from the first mesh. Normalising each mesh to
        # its own extent would slide them apart on the page and invite the reader to see a
        # disagreement that is not in the geometry -- which is what the first shape-only
        # render of A02 did. Sharing the transform keeps their relative placement and
        # relative size honest while removing the absolute size, which is the whole point.
        ref = np.concatenate(sections[0][1])
        c = (ref.min(0) + ref.max(0)) / 2.0
        e = float(max(ref.max(0) - ref.min(0))) or 1.0
        sections = [(tag, [(l - c) / e for l in loops]) for tag, loops in sections]

    allloops = [l for _, loops in sections for l in loops]
    # The wall is measured on ONE named mesh, not on the pile of both. Two meshes of the
    # same sherd have nearly coincident outlines, and a ray crossing from one to the other
    # would report the gap between the two reconstructions as if it were the thickness of
    # the pot. The caption says which mesh the figure belongs to.
    ref_tag, ref_loops = sections[0]
    chords, widths = wall_chords(ref_loops) if metric else (None, np.zeros(0))
    wall = float(np.median(widths)) if len(widths) else float("nan")

    if metric:
        centre, span = choose_window(allloops, wall, min_wall_px)
    else:
        centre, span = whole_view(allloops)

    locator = whole_view(allloops)
    zoomed = span < locator[1] * 0.999

    title = "section through the wall - %s" % ", ".join(t for t, _ in sections)
    notes = []
    if metric:
        px_mm = panel_px_per_mm(span)
        if len(widths):
            notes.append("wall %.2f mm on '%s' - median of %d chords across %d of its %d "
                         "outlines (thinnest 5%%: %.2f mm, longest: %.2f mm). Specks under "
                         "a tenth of the longest outline are drawn but not measured."
                         % (wall, ref_tag, len(widths), len(carrying_loops(ref_loops)),
                            len(ref_loops), np.percentile(widths, 5), np.max(widths)))
            # NOT A CHECK, A CONSEQUENCE. The window is SIZED from the wall figure, so
            # "%.1f px across" is arithmetic on that figure and cannot disagree with it --
            # an earlier draft printed it as though it verified the view, which is the
            # tautology this repo keeps rebuilding. What a reader can actually check is
            # beside it: a longest chord far above the median means rays crossed a gap
            # rather than a wall, and a thinnest 5% far below it means they crossed the
            # air between two fragments.
            notes.append("the view is SIZED from that figure to put the wall at least "
                         "%d px across, so %.1f px/mm and %.1f px follow from it rather "
                         "than confirm it. Judge it by the spread: a longest chord well "
                         "above the median means rays crossed a gap, not a wall."
                         % (min_wall_px, px_mm, wall * px_mm))
        else:
            notes.append("NO WALL COULD BE MEASURED on '%s': the cut left %d outlines and "
                         "no chord across any of them. The outlines are drawn and the bar "
                         "is correct; there is no thickness figure to read."
                         % (ref_tag, len(ref_loops)))
        notes.append("cut on the %s axis at offset %+.1f mm - ONE plane for every mesh, "
                     "through the centroid of '%s', which is also the mesh measured. "
                     "Naming a different mesh first gives a different cut and a different "
                     "figure." % (axis, offset, ref_tag))
    else:
        notes.append("SHAPE ONLY - ONE scaling for every outline, taken from '%s', so "
                     "relative size and placement are as measured. No absolute size is "
                     "implied and no scale bar is drawn." % ref_tag)
        # The offset belongs on the picture in EVERY mode. Leaving it off here meant a cut
        # the user had deliberately moved looked identical to one through the centroid --
        # a caption that misdescribes its own picture, which is the fault this file has
        # already shipped once. Without a scale record there is no physical unit to state
        # it in, so it is stated in the mesh's own units and said to be. Note the wording
        # avoids naming a unit even to deny one: the self-test's shape-only check is a
        # blunt search for unit words in the caption, and a blunt check that cannot be
        # talked around is worth more here than a caption that gets to be clever.
        notes.append("cut on the %s axis at offset %+.1f in the mesh's OWN units - there "
                     "is no scale record, so that offset is not a physical length - ONE "
                     "plane for every mesh, through the centroid of '%s'"
                     % (axis, offset, ref_tag))
    if missed:
        notes.append("the plane missed: %s" % ", ".join(sorted(missed)))

    info = draw(sections, out_path, centre, span, metric, wall, title, notes,
                chords=chords, locator=locator if zoomed else None)
    info["zoomed"] = zoomed
    info["missed"] = sorted(missed)
    info["loops"] = {t: len(l) for t, l in sections}
    # The caption is part of the picture and can go stale on its own: this file has already
    # shipped a shape-only footer that described the previous version of the code. The
    # self-test reads these back, so a caption that starts implying a size fails a check
    # rather than waiting to be spotted by eye.
    info["notes"] = list(notes)
    # WHAT A MEDIAN HIDES. The median wall survives a lot of nonsense: chords that leave the
    # clay and land on a sherd 200 mm away, or a ray that sails through a thin wall and
    # measures the far side of the pot, are both a minority of the chords and both leave the
    # median at its honest value. Every one of those was a real defect here, found by eye
    # after the number beside it read fine. The longest chord and the number of outlines
    # actually measured are where they show, so they are reported and asserted.
    info["wall_max_mm"] = float(np.max(widths)) if len(widths) else None
    info["wall_p05_mm"] = float(np.percentile(widths, 5)) if len(widths) else None
    info["wall_n"] = int(len(widths))
    info["measured_loops"] = len(carrying_loops(ref_loops)) if metric else None
    info["ref_loops"] = len(ref_loops)
    if not quiet:
        print("")
        for line in notes:
            print("  " + line)
        print("\nwrote %s" % info["path"])
    return RC_OK, info


# --------------------------------------------------------------------------------------
# Self-test
# --------------------------------------------------------------------------------------
#
# Same shape as `compare_meshes.py --self-test` and `check_turntable.py`: synthetic
# geometry with the answer known in advance, and the assertions are on the EXIT STATUS and
# on what was drawn -- never on the wording, which would pass on a gate that never stops
# anything.
#
# The case this exists for is the last one: a wall too thin to see at whole-object framing.
# That is the failure this repo keeps making, so the fixture is built to trigger it.

def _wall_fixture(path, r_out, wall, height=30.0, sidecar=None):
    """A hollow cylinder -- the simplest thing with a wall of a size known in advance."""
    import json
    m = trimesh.creation.annulus(r_min=r_out - wall, r_max=r_out, height=height,
                                 sections=192)
    m.export(str(path))
    if sidecar is not None:
        sidecar_path(Path(path)).write_text(json.dumps(sidecar))
    return path


def _sherd_fixture(path, r_out, wall, span_deg=100.0, height=30.0, n=96,
                   extra=(), sidecar=None):
    """A curved fragment -- a SHERD, not a pot -- with a wall of a size known in advance.

    WHY THIS EXISTS ALONGSIDE THE CYLINDER. A hollow cylinder cuts as two separate
    outlines, inner and outer, and that quietly disables two of the things being tested
    here: a ray from the outer outline always finds the inner one (so nothing about
    excluding a point's own neighbours is exercised), and casting both ways always finds
    the 6 mm wall before anything else (so nothing about rays leaving the material is
    exercised either). Both guards passed their tests by not being needed. A sherd cuts as
    ONE outline that runs out along the outside and back along the inside, which is what
    this repo's material actually is, and it exercises both.

    `extra` is a list of (dx, dy, rotate_deg) placements of further copies, for the case
    that matters most on a real tray: a second fragment standing nearby.
    """
    import json

    def band(dx=0.0, dy=0.0, rot=0.0):
        th = np.radians(np.linspace(-span_deg / 2, span_deg / 2, n)) + np.radians(rot)
        O = np.column_stack([r_out * np.cos(th), r_out * np.sin(th)])
        I = np.column_stack([(r_out - wall) * np.cos(th), (r_out - wall) * np.sin(th)])
        ring = np.vstack([O, I]) + np.array([dx, dy])
        V = np.vstack([np.column_stack([ring, np.full(2 * n, -height / 2)]),
                       np.column_stack([ring, np.full(2 * n, height / 2)])])

        def q(a, b, c, d):
            return [[a, b, c], [a, c, d]]

        F = []
        for i in range(n - 1):
            o0, o1, i0, i1 = i, i + 1, n + i, n + i + 1
            F += q(o0, i0, i1, o1)                              # bottom
            F += q(2 * n + o0, 2 * n + o1, 2 * n + i1, 2 * n + i0)   # top
            F += q(o0, o1, 2 * n + o1, 2 * n + o0)              # outside
            F += q(i1, i0, 2 * n + i0, 2 * n + i1)              # inside
        F += q(0, n, 2 * n + n, 2 * n)                          # break face
        F += q(n - 1, 2 * n + n - 1, 4 * n - 1, 2 * n - 1)      # break face
        return trimesh.Trimesh(vertices=V, faces=np.array(F), process=True)

    parts = [band()] + [band(*p) for p in extra]
    trimesh.util.concatenate(parts).export(str(path))
    if sidecar is not None:
        sidecar_path(Path(path)).write_text(json.dumps(sidecar))
    return path


def _sidecar(units="millimetres"):
    return {"units": units, "mm_per_unit": 1.0, "source": "fixture",
            "capture": "fixture", "method": "fixture", "scaled_at": "fixture",
            "caveat": "fixture, exact by construction"}


def self_test() -> int:
    import tempfile

    ran, failures = [], []

    def check(cond, what):
        ran.append(what)
        print(("  ok   " if cond else "  FAIL ") + what)
        if not cond:
            failures.append(what)

    def case(got, want, what):
        check(got == want, "%s (exit %s, wanted %s)" % (what, got, want))

    with tempfile.TemporaryDirectory() as td:
        t = Path(td)
        out = t / "out.png"

        print("-- two walls of a size known in advance, both declaring millimetres")
        a = _wall_fixture(t / "a.ply", 40.0, 6.0, sidecar=_sidecar())
        b = _wall_fixture(t / "b.ply", 40.0, 6.0, sidecar=_sidecar("mm"))
        st, info = section_overlay({"milo": a, "openmvs": b}, out, quiet=True)
        case(st, RC_OK, "a pair that can state its units is drawn")
        check(out.exists(), "and the picture is on disk")
        check(info and abs(info["wall_mm"] - 6.0) < 0.3,
              "the wall measures %.2f mm against the 6.00 mm it was built with"
              % (info or {}).get("wall_mm", float("nan")))
        check(info and info["bar_drawn"], "and a millimetre bar is drawn")
        check(info and info["wall_px"] >= MIN_WALL_PX,
              "and the view resolves the wall: %.1f px, %d asked for"
              % ((info or {}).get("wall_px") or 0, MIN_WALL_PX))
        # THE BAR MUST MEASURE THE PICTURE IT IS DRAWN ON. `px_per_mm` is printed in the
        # caption and sets the length of the scale bar, while the outlines are drawn by
        # `_project`, which works out its own scale from the same span. Nothing forces the
        # two to agree; if they drift, the picture carries a bar that measures nothing on
        # it -- a ruler wrong about its own subject, which is the fault class this whole
        # script exists to catch one level up. So project a known 10 mm and count pixels.
        wc = np.asarray(info["centre"], float)
        proj, _s = _project(np.array([wc, wc + [10.0, 0.0]]), wc, info["span"],
                            PANEL_W, PANEL_H)
        drawn_px = float(np.linalg.norm(proj[1] - proj[0]))
        check(abs(drawn_px - 10.0 * info["px_per_mm"]) < 0.5,
              "and 10 mm of geometry is %.1f px on the page against the %.1f px the "
              "caption promises -- the bar measures its own picture"
              % (drawn_px, 10.0 * info["px_per_mm"]))

        # THE CAPTION IS PART OF THE PICTURE, and it goes stale on its own. A footer
        # describing a version of the code that no longer existed shipped from this file
        # once and was caught only by reading the PNG. The shape-only caption has been
        # checked below since; this checks the metric one, which is the caption that
        # carries every number a conservator would act on. Each line is compared against
        # what the SAME run reported, so a caption that drifts from its own picture fails
        # here rather than waiting to be noticed by eye.
        cap = " ".join((info or {}).get("notes", []))
        check("'milo'" in cap, "the caption names the mesh the wall was measured on")
        check(("%.2f mm" % info["wall_mm"]) in cap,
              "and prints that mesh's wall figure -- the %.2f mm the run reported"
              % info["wall_mm"])
        check(("longest: %.2f mm" % info["wall_max_mm"]) in cap
              and ("thinnest 5%%: %.2f mm" % info["wall_p05_mm"]) in cap,
              "and the spread beside it, so a chord that crossed a gap rather than a wall "
              "is visible to the reader")
        check("ONE plane for every mesh" in cap and "a different cut" in cap,
              "and says the cut is one plane, and that naming another mesh first moves it")
        # A caption that runs off the edge of the picture is half a caption, and the half
        # that went missing on the first real render was the sentence saying how to judge
        # the number. The image travels into a report where the rest cannot be looked up.
        check(info and info["caption_overflow_px"] == 0.0,
              "the whole caption fits on the picture -- %d lines, none running past the "
              "edge" % (info or {}).get("caption_lines", 0))
        check("follow from it rather than confirm it" in cap,
              "and does NOT claim the pixels-per-millimetre confirms the measurement: the "
              "window is sized FROM that figure, so saying so would be a tautology")

        print("\n-- 'mm' and 'millimetres' are the same unit, not a conflict")
        # This exact bug shipped once and told the conservator a correctly scaled mesh had
        # never been scaled. It is asserted here so the second script cannot reintroduce it.
        case(section_overlay({"milo": a, "openmvs": b}, t / "u.png", quiet=True)[0],
             RC_OK, "a pair declaring 'millimetres' and 'mm' is accepted")

        print("\n-- a mesh NOT in millimetres is drawn in millimetres, using its own factor")
        # The fixtures above are all 1 mm per unit, so a script that ignored the sidecar
        # and assumed 1.0 would pass every one of them. This pair is modelled in
        # CENTIMETRES -- 4.0 units across a 0.6-unit wall -- and the picture must still say
        # 6 mm. Without this case the ticket's "does not fall back to assuming 1.0" is
        # untested, and a mutation that hard-codes 1.0 goes unnoticed. It did.
        ca = _wall_fixture(t / "ca.ply", 4.0, 0.6, height=3.0, sidecar=_sidecar("centimetres"))
        cb = _wall_fixture(t / "cb.ply", 4.0, 0.6, height=3.0, sidecar=_sidecar("cm"))
        st, infoc = section_overlay({"milo": ca, "openmvs": cb}, t / "cm.png", quiet=True)
        case(st, RC_OK, "a pair declaring centimetres is drawn")
        check(infoc and abs(infoc["wall_mm"] - 6.0) < 0.3,
              "and its 0.6-unit wall reads %.2f mm, not %.2f -- the sidecar's factor was "
              "applied" % ((infoc or {}).get("wall_mm", float("nan")), 0.6))

        print("\n-- an 8% scale error is present in the geometry the picture is drawn from")
        big = _wall_fixture(t / "big.ply", 43.2, 6.48, sidecar=_sidecar())
        st, info2 = section_overlay({"true": a, "toolarge": big}, t / "err.png", quiet=True)
        case(st, RC_OK, "the pair is drawn")
        rad = {tag: float(np.abs(np.concatenate(l)).max())
               for tag, l in [("true", section_loops(trimesh.load(str(a), process=False),
                                                     [0, 0, 0], plane_basis([0, 0, 1]))),
                              ("toolarge", section_loops(trimesh.load(str(big), process=False),
                                                         [0, 0, 0], plane_basis([0, 0, 1])))]}
        ratio = rad["toolarge"] / rad["true"]
        check(abs(ratio - 1.08) < 0.01,
              "and the two outlines differ by %.1f%%, which is what is on the picture"
              % ((ratio - 1) * 100))

        print("\n-- a mesh that cannot say what units it is in is REFUSED, and nothing is drawn")
        bare = _wall_fixture(t / "bare.ply", 40.0, 6.0)
        gone = t / "never.png"
        case(section_overlay({"milo": a, "openmvs": bare}, gone, quiet=True)[0], 2,
             "one sidecar missing")
        check(not gone.exists(),
              "and NO picture was written -- a refusal that leaves the file behind is not "
              "a refusal")

        print("\n-- two meshes that disagree on units are refused separately")
        metres = _wall_fixture(t / "m.ply", 40.0, 6.0, sidecar=_sidecar("metres"))
        gone2 = t / "never2.png"
        case(section_overlay({"milo": a, "openmvs": metres}, gone2, quiet=True)[0], 3,
             "units disagree -- 3, not 2: they are different faults")
        check(not gone2.exists(), "and again nothing is drawn")

        print("\n-- --shape-only draws the picture and no millimetre at all")
        so = t / "shape.png"
        st, info3 = section_overlay({"milo": a, "openmvs": bare}, so, shape_only=True,
                                    quiet=True)
        case(st, RC_OK, "no sidecar, but --shape-only was asked for")
        check(so.exists(), "the picture is drawn")
        check(info3 and not info3["bar_drawn"], "and NO scale bar is on it")
        check(info3 and info3["wall_mm"] is None and info3["px_per_mm"] is None,
              "and no millimetre figure is reported anywhere")
        caption = " ".join(info3["notes"]).lower() if info3 else "mm"
        check(not any(w in caption for w in (" mm", "millimetre", "millimeter")),
              "and the caption itself names no unit either")
        # Unit-free must not mean placement-free. Two meshes 20 mm apart, both without
        # sidecars: if each were normalised to its own extent they would land on top of
        # each other and the picture would deny a difference that is in the geometry.
        shifted = trimesh.load(str(bare), process=False)
        shifted.apply_translation([20.0, 0.0, 0.0])
        shifted.export(str(t / "bare_shifted.ply"))
        apart = t / "so_apart.png"
        st, info3b = section_overlay({"a": bare, "b": t / "bare_shifted.ply"}, apart,
                                     shape_only=True, quiet=True)
        case(st, RC_OK, "a shape-only pair 20 mm apart is drawn")
        check(info3b and info3b["span"] > 1.2,
              "and they stay apart on the page (frame %.2f of one mesh's extent), rather "
              "than each being re-centred onto the other"
              % (info3b or {}).get("span", 0))

        print("\n-- two sherds far apart: the wall is measured across clay, not across the tray")
        # A real capture is ten sherds standing apart on a turntable, and this is what the
        # first render of one showed: chords 700 mm long joining one sherd to another,
        # medianed into a confident "wall 14.59 mm". The picture showed it at once; the
        # number beside it did not. Two islands 200 mm apart, walls of 6 mm.
        import json as _json
        pair = trimesh.util.concatenate([
            trimesh.creation.annulus(r_min=34.0, r_max=40.0, height=30.0, sections=192),
            trimesh.creation.annulus(r_min=34.0, r_max=40.0, height=30.0,
                                     sections=192).apply_translation([200.0, 0, 0])])
        pair.export(str(t / "two.ply"))
        (t / "two.scale.json").write_text(_json.dumps(_sidecar()))
        st, info5 = section_overlay({"two": t / "two.ply", "same": t / "two.ply"},
                                    t / "two.png", quiet=True)
        case(st, RC_OK, "the two-sherd section is drawn")
        check(info5 and abs(info5["wall_mm"] - 6.0) < 0.5,
              "and the wall reads %.2f mm, not the %d mm gap between the sherds"
              % ((info5 or {}).get("wall_mm", float("nan")), 200))
        # The median alone does not test this: cross-tray chords are a minority and the
        # median stays at 6 mm while 200 mm lines are drawn across the picture. The LONGEST
        # chord is where they show.
        check(info5 and info5["wall_max_mm"] < 20.0,
              "and the longest single chord is %.1f mm -- no ray crossed the empty tray"
              % ((info5 or {}).get("wall_max_mm") or 0.0))

        print("\n-- a sherd surrounded by noise specks still reports the sherd's wall")
        # A real crop of A02 came back as one sherd plus dozens of sub-millimetre stray
        # fragments, and the median chord across all of them read 0.13 mm. The specks
        # outnumber the clay, so they win a median.
        #
        # THIS FIXTURE HAD TO BE REBUILT TWICE BEFORE IT TESTED ANYTHING. Forty 0.4 mm
        # squares: a whole outline shorter than one sampling step is never sampled, so no
        # number of them moves a median. Then flakes around a hollow cylinder: a cylinder's
        # outline is only ~250 mm, so the flakes had to be short to stay under a tenth of
        # it, and short outlines are eaten by the neighbour guard instead. Both versions
        # passed with the filter DELETED. A test that cannot fail is not a test.
        #
        # What works is what the real crop is: ONE fragment with a long outline -- 451 mm,
        # out along the outside and back along the inside -- surrounded by long thin
        # flakes, 18 mm of outline and 0.13 mm across, which is the figure A02 printed.
        # With the filter the wall reads 6.00 mm; without it, 0.13 mm.
        rng = np.random.default_rng(0)
        parts = [trimesh.load(str(_sherd_fixture(t / "noisy_sherd.ply", 40.0, 6.0,
                                                 span_deg=340.0, n=220)), process=False)]
        for c in rng.uniform(-90, 90, size=(20, 2)):
            parts.append(trimesh.creation.box(extents=[18.0, 0.13, 30.0])
                         .apply_transform(trimesh.transformations.rotation_matrix(
                             rng.uniform(0, np.pi), [0, 0, 1]))
                         .apply_translation([c[0], c[1], 0.0]))
        trimesh.util.concatenate(parts).export(str(t / "noisy.ply"))
        (t / "noisy.scale.json").write_text(_json.dumps(_sidecar()))
        st, infon = section_overlay({"noisy": t / "noisy.ply", "same": t / "noisy.ply"},
                                    t / "noisy.png", quiet=True)
        case(st, RC_OK, "the noisy section is drawn")
        check(infon and abs(infon["wall_mm"] - 6.0) < 0.5,
              "and the wall reads %.2f mm, not the 0.13 mm of the flakes around it"
              % (infon or {}).get("wall_mm", float("nan")))
        # And the filter's own bookkeeping: the fragment's ONE outline was measured, out of
        # the 21 drawn. The flakes are on the picture; they are not in the number.
        check(infon and infon["measured_loops"] == 1 and infon["ref_loops"] == 21,
              "and %s of the %s outlines were measured -- the flakes are drawn, not "
              "measured" % ((infon or {}).get("measured_loops"),
                            (infon or {}).get("ref_loops")))

        print("\n-- two meshes 20 mm apart are drawn 20 mm apart, not on top of each other")
        # Cutting each mesh at its OWN centroid and re-centring each outline on itself
        # makes two meshes in different places look identical. That is not a hypothetical:
        # it is what this script did until a real A02 render showed the two outlines
        # sitting in different parts of the tray while the caption said nothing.
        off = _wall_fixture(t / "off.ply", 40.0, 6.0, sidecar=_sidecar())
        shifted = trimesh.load(str(off), process=False)
        shifted.apply_translation([20.0, 0.0, 0.0])
        shifted.export(str(t / "off2.ply"))
        (t / "off2.scale.json").write_text(_json.dumps(_sidecar()))
        st, info6 = section_overlay({"here": off, "20mm_away": t / "off2.ply"},
                                    t / "off.png", quiet=True)
        case(st, RC_OK, "the offset pair is drawn")
        w = section_loops(trimesh.load(str(off), process=False), [0, 0, 0],
                          plane_basis([0, 0, 1]))
        one = float(np.ptp(np.concatenate(w)[:, 0]))
        check(info6 and info6["span"] > one + 15.0,
              "and the frame is %.0f mm wide, not the %.0f mm of one mesh -- the offset "
              "is on the picture" % ((info6 or {}).get("span", 0), one))

        print("\n-- a wall too thin to see at whole-object framing makes the view zoom")
        # 0.8 mm of wall on an 80 mm object: at whole-object framing that is 6.6 px on a
        # 660 px panel, which is the failure this repo keeps making. The view must not
        # accept it.
        thin_a = _wall_fixture(t / "ta.ply", 40.0, 0.8, sidecar=_sidecar())
        thin_b = _wall_fixture(t / "tb.ply", 40.0, 0.8, sidecar=_sidecar())
        st, info4 = section_overlay({"milo": thin_a, "openmvs": thin_b}, t / "thin.png",
                                    min_wall_px=40, quiet=True)
        case(st, RC_OK, "the thin-walled pair is drawn")
        check(info4 and info4["zoomed"],
              "and the view zoomed in rather than showing the whole object")
        # The wall in MILLIMETRES first. "40 px across" is true by construction once the
        # window is sized from whatever wall was measured, so it cannot tell a 0.8 mm wall
        # from a ray that skipped the wall and measured the far side of the pot -- which is
        # exactly what the distance-based exclusion did before the arc-length guard.
        check(info4 and abs(info4["wall_mm"] - 0.8) < 0.15,
              "and the wall reads %.2f mm, the 0.8 mm that is there -- the ray did not "
              "skip the wall and measure the 79 mm bore"
              % ((info4 or {}).get("wall_mm", float("nan"))))
        check(info4 and info4["wall_px"] >= 40,
              "and the wall is %.0f px across, the 40 px asked for"
              % ((info4 or {}).get("wall_px") or 0))

        print("\n-- a SHERD, not a pot: one outline, out along the outside and back inside")
        # Every fixture above is a hollow cylinder, and a cylinder cuts as two separate
        # outlines. That quietly excused two of the guards in this file from ever being
        # tested: a ray from the outer outline always finds the inner one, so excluding a
        # point's own neighbours never touches a wall crossing, and casting both ways always
        # meets the 6 mm wall first, so a ray leaving the clay never wins. A fragment cuts as
        # ONE outline and exercises both -- and a fragment is what this repo measures.
        # A thin wall on a LARGE fragment is the case that bites: the sample points are
        # spread along the whole perimeter, so the spacing between them can exceed the wall.
        sherd = _sherd_fixture(t / "sherd.ply", r_out=40.4, wall=0.8, span_deg=340.0,
                               n=220, sidecar=_sidecar())
        st, infos = section_overlay({"sherd": sherd, "same": sherd}, t / "sherd.png",
                                    quiet=True)
        case(st, RC_OK, "the thin-walled fragment is drawn")
        check(infos and infos["loops"]["sherd"] == 1,
              "and it cuts as ONE outline, the way a fragment does")
        check(infos and abs(infos["wall_mm"] - 0.8) < 0.1,
              "and the wall reads %.2f mm, the 0.8 mm that is there"
              % ((infos or {}).get("wall_mm", float("nan"))))
        # Excluding a point's own neighbours by DISTANCE rather than by arc length eats the
        # measurement here: the exclusion is wider than the wall, so nearly every ray sails
        # through it. Both of these say so -- the chords that survive, and how far they ran.
        check(infos and infos["wall_n"] > 300,
              "and %s chords survived, not the handful left when the exclusion is wider "
              "than the wall" % (infos or {}).get("wall_n"))
        check(infos and infos["wall_max_mm"] < 5.0,
              "and the longest chord is %.1f mm -- none crossed the 79 mm bore"
              % ((infos or {}).get("wall_max_mm") or 0.0))
        # THE OUTLINE HAS NO PREFERRED DIRECTION, and neither may the measurement. Which
        # way round `section()` happens to trace a loop decides which side of it the local
        # normal points at, and that is an accident of the mesh, not a fact about the pot.
        # So the ray is cast BOTH ways and the material test decides which one counts. That
        # second cast looked like belt-and-braces -- every fixture here happens to be traced
        # the agreeable way, and deleting the cast changed no result. Reversing the outline
        # is the input that tells them apart: with one cast it measures nothing at all.
        sherd_mesh = trimesh.load(str(sherd), process=False)
        sherd_loops = carrying_loops(section_loops(
            sherd_mesh, np.asarray(sherd_mesh.centroid, float),
            plane_basis([0, 0, 1]), mm_per_unit=1.0))
        _c, w_fwd = wall_chords(sherd_loops)
        _c, w_rev = wall_chords([l[::-1].copy() for l in sherd_loops])
        # 1e-4 mm, not zero: walking the outline the other way puts the samples in
        # slightly different places along it, which moves the median by about a
        # ten-thousandth of a millimetre. Casting one way instead measures NOTHING, so the
        # tolerance is nowhere near loose enough to let that through.
        check(len(w_rev) == len(w_fwd) and abs(float(np.median(w_rev))
                                               - float(np.median(w_fwd))) < 1e-4,
              "and tracing that same outline backwards measures the same %d chords and "
              "the same %.2f mm wall" % (len(w_fwd), float(np.median(w_fwd)) if len(w_fwd)
                                         else float("nan")))

        print("\n-- a fragment standing 2 mm from its neighbour: the gap is not the wall")
        # The tray case at close quarters. A ray leaving the outside of one fragment reaches
        # the next one in 2 mm, which is nearer than its own 6 mm wall, so without the test
        # for staying in the clay the THINNEST chords stop being the wall and start being
        # the air between two fragments. The median survives it; the fifth percentile does
        # not, which is the point of looking at more than one number.
        pair2 = _sherd_fixture(t / "pair2.ply", r_out=40.0, wall=6.0,
                               extra=[(82.0, 0.0, 180.0)], sidecar=_sidecar())
        st, infop = section_overlay({"pair": pair2, "same": pair2}, t / "pair2.png",
                                    quiet=True)
        case(st, RC_OK, "the close pair is drawn")
        check(infop and infop["wall_p05_mm"] > 5.0,
              "and the thinnest chords are %.2f mm of wall, not the 2 mm gap between them"
              % ((infop or {}).get("wall_p05_mm") or 0.0))

        print("\n-- a plane that misses everything says so instead of drawing nothing")
        far = t / "far.png"
        case(section_overlay({"milo": a, "openmvs": b}, far, offset=500.0, quiet=True)[0],
             4, "the plane misses both meshes")
        check(not far.exists(), "and no empty picture is left behind")

    print("\nself-test: %s -- %d checks, %d failed"
          % ("FAIL" if failures else "PASS", len(ran), len(failures)))
    return 1 if failures else 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__.splitlines()[0],
        formatter_class=argparse.RawDescriptionHelpFormatter,
        # The exit statuses belong where somebody reaching for the script will see them.
        # `RC_PLANE_MISSES` was a bare `4` in the code and nowhere in the help, which is
        # how a status ends up asserted against a literal that has since moved.
        epilog="\n".join((
            "exit status:",
            "  0  the section was drawn",
            "  1  a bad argument",
            "  2  a mesh has no scale record  (--shape-only draws it without one)",
            "  3  the scale records disagree",
            "  4  the cutting plane misses every mesh",
            "Nothing is written except on 0.",
        )))
    ap.add_argument("--mesh", action="append", default=[], metavar="TAG=PATH",
                    help="a mesh to cut, named: --mesh milo=a.ply --mesh openmvs=b.ply")
    ap.add_argument("--out", help="where to write the picture")
    ap.add_argument("--axis", choices=("x", "y", "z"), default="z",
                    help="normal of the cutting plane (default z: a horizontal cut)")
    ap.add_argument("--offset", type=float, default=0.0,
                    help="move the plane along that axis, in millimetres (with "
                         "--shape-only, in the mesh's own units)")
    ap.add_argument("--min-wall-px", type=int, default=MIN_WALL_PX,
                    help="how many pixels the wall must span; the view is SIZED "
                         "to make that true, it is not a test of the view")
    ap.add_argument("--shape-only", action="store_true",
                    help="draw the outlines with no scale bar and no millimetre figure")
    ap.add_argument("--self-test", action="store_true",
                    help="prove the gate on synthetic geometry; needs no data")
    args = ap.parse_args()

    if args.self_test:
        return self_test()
    if not args.mesh or not args.out:
        ap.error("--mesh (at least one, TAG=PATH) and --out are required")

    paths = {}
    for spec in args.mesh:
        if "=" not in spec:
            ap.error("--mesh wants TAG=PATH, got %r. The tag is what the picture and the "
                     "provenance block call this mesh." % spec)
        tag, path = spec.split("=", 1)
        paths[tag] = Path(path)

    status, _ = section_overlay(paths, args.out, axis=args.axis, offset=args.offset,
                                shape_only=args.shape_only, min_wall_px=args.min_wall_px)
    return status


if __name__ == "__main__":
    sys.exit(main())
