"""Metric scale from the turntable marker board -- and an argument between three rulers.

THE PLAN THIS WAS WRITTEN AGAINST SAID THE WRONG THING, so start with what changed.

Tier 3 was specified as "board scale as a second, independent check that must agree with
the 13x19 cm base plate". Reading the Metashape project shows that cannot work as stated,
for two reasons found by looking rather than by assuming:

  1. The board's millimetres are DERIVED FROM THE BASE PLATE. Metashape's chunk scale is
     fitted to two scale bars, `point 3`-`point 4` = 0.130 m and `point 3`-`point 5` =
     0.190 m. Every metric length in that project, the board included, is downstream of
     those two numbers. Checking the board against the base is checking a ruler against
     itself.

  2. The base plate is not four measurements; it is four mouse clicks. Points 1, 3, 4 and 5
     have ZERO pinned projections across 69-116 images and reproject at exactly 0.000 px,
     which is Metashape drawing one 3D estimate into every frame. The coded targets are the
     opposite: 28 to 46 views each, every one pinned, every one a genuine detection.

So the base plate cannot arbitrate anything, and there is a scale-free way to show it. The
RATIO of the two base edges does not depend on any scale factor at all:

     measured  191.83 / 127.24 = 1.5077
     nominal        190 / 130  = 1.4615        off by +3.16 %

while the corner at point 3 measures 89.76 deg -- a true rectangle corner. The shape is
right and the proportions are wrong, which is what a mis-clicked corner looks like: point 4
sits about 4.5 mm from where it was declared to be. Metashape then fitted ONE scale to two
bars that disagree, and the compromise is wrong by over a per cent.

WHAT THE BOARD CAN ACTUALLY DO. The 16 coded targets sit on a printed square lattice. The
fit recovers a pitch of 40.557 mm with a residual of 0.196 mm rms, and bootstrapping over
targets puts the pitch itself at +/- 0.015 mm -- 0.036 %. That is roughly sixty times
tighter than the base plate's own internal disagreement. It is a far better ruler.

But a lattice pitch is only a ruler if its NOMINAL value is known, and that is the one
thing no amount of arithmetic here can supply. The board is a Metashape "Print Markers"
PDF page, cut into a disc and taped down (look at `artifacts/markers/crop_A42_8355.png`:
printed target numbers, page-corner squares, visibly wrinkled paper, tape strips).
Agisoft documents target SIZING -- 10-30 px centre dot, global diameter about 3.5x the
centre -- but publishes no grid pitch, and the print dialog's page layout is up to whoever
pressed the button. A printer set to "fit to page" would move it again.

So this module REFUSES TO GUESS. Without --pitch-nominal it reports the measurement and
says the scale is unverified. With it, it emits a correction factor and shows its working
against the base plate so the disagreement stays visible instead of being averaged away.
The number to put there costs one minute with a ruler on the physical sheet, and until
somebody spends that minute the honest answer is that this model's scale is uncertain at
about the per-cent level -- which on a 100 mm sherd is 1.4 mm.

Usage:
    python scripts/board_scale.py docs/reference/turntable-board-03072025-N01.json
    python scripts/board_scale.py docs/reference/turntable-board-03072025-N01.json --pitch-nominal 40
    python scripts/board_scale.py ... --psx artifacts/markers/psx --write
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np

# A lattice fit that lands worse than this is not measuring a printed grid, and its pitch
# means nothing. The paper is taped to a turntable and visibly wrinkled, so this is loose
# on purpose: N01 comes in at 0.196 mm and a sheet twice as bad would still be usable.
MAX_LATTICE_RMS_MM = 1.0
MIN_TARGETS = 8

# How far the board and the base plate may disagree before the disagreement is the finding.
# Two rulers that differ by more than this are not measuring the same object well; averaging
# them would produce a number with no owner.
SCALE_AGREE_PCT = 1.0


def _rot(t):
    return np.array([[np.cos(t), -np.sin(t)], [np.sin(t), np.cos(t)]])


def fit_lattice(xy, pitch_guess=40.0):
    """Fit a square lattice to coplanar points; return (pitch, cell index, residual).

    Solved for pitch, rotation and origin together, with the cell indices snapped to
    integers inside the residual. Started from many rotations because the objective is
    periodic in orientation and a single start lands in whichever cell it began in.
    """
    from scipy.optimize import least_squares

    def resid(p, S=xy):
        g, t, ox, oy = p
        u = (S - [ox, oy]) @ _rot(t) / g
        return (u - np.round(u)).ravel() * g

    best = None
    for g0 in (pitch_guess, pitch_guess * 1.02):
        for t0 in np.radians(np.arange(0, 90, 2)):
            r = least_squares(resid, [g0, t0, 0.0, 0.0])
            if best is None or r.cost < best.cost:
                best = r
    g, t, ox, oy = best.x
    g = abs(g)
    u = (xy - [ox, oy]) @ _rot(t) / g
    idx = np.round(u).astype(int)
    res = (u - idx) * g
    return g, idx, res, best.x


def fit_affine(xy, square):
    """Refit the grid letting the two lattice axes be independent -- shear and all.

    Run because the RENDER asked for it. With a square lattice the leftover arrows were not
    random: they leaned the same way across the whole board, which is what a sheared grid
    looks like and what noise does not. Testing it was the test that could have refuted the
    pitch, so it had to be run rather than admired.

    It refutes the SQUARE model and confirms the SCALE. The axes meet at 89.74 deg, not 90,
    and allowing that halves the residual, 0.196 -> 0.089 mm rms. Letting the two pitches
    differ without shear barely helps (0.185), so the effect really is shear, not a printer
    stretching one direction.

    WHAT CAUSES THE SHEAR IS NOT KNOWN, and this docstring used to claim it was wrinkled
    paper on a domed turntable. That was a story, not a measurement. Wrinkling a sheet and
    flattening it onto a plane compresses it radially; it does not obviously shear it. A
    systematic in the solve -- calibration, or the board being seen from a limited range of
    elevations -- would do this too. The base plate cannot settle the question: its corner
    reads 89.76 deg, which looks like agreement until you notice its own points are wrong by
    about 4.5 mm, making that corner uncertain by +/- 2 deg. Two numbers agreeing to 0.02 deg
    when one of them carries 2 deg of error is a coincidence, not a confirmation.

    It is left open on purpose, because it does not have to be settled to use the board.

    But the number this module exists to produce barely moves: the area-equivalent pitch,
    sqrt(|det M|), is 40.592 mm against the square fit's 40.557 -- a difference of 0.087 %,
    smaller than the gap to any nominal value worth arguing about. So the shear is a real
    property of the board and NOT a threat to the scale, which is worth saying explicitly
    because a halved residual looks alarming until you check what it does to the answer.
    """
    from scipy.optimize import least_squares
    g, t, ox, oy = square
    M0 = [g * np.cos(t), g * np.sin(t), -g * np.sin(t), g * np.cos(t), ox, oy]

    def resid(p):
        M = np.array([[p[0], p[1]], [p[2], p[3]]])
        u = (xy - [p[4], p[5]]) @ np.linalg.inv(M)
        return ((u - np.round(u)) @ M).ravel()

    f = least_squares(resid, M0)
    M = np.array([[f.x[0], f.x[1]], [f.x[2], f.x[3]]])
    org = f.x[4:6]
    u = (xy - org) @ np.linalg.inv(M)
    idx = np.round(u).astype(int)
    res = (u - idx) @ M
    lens = np.linalg.norm(M, axis=1)
    corner = float(np.degrees(np.arccos(M[0] @ M[1] / (lens[0] * lens[1]))))
    return {
        "pitch_mm": float(np.sqrt(abs(np.linalg.det(M)))),
        "axis_a_mm": float(lens[0]), "axis_b_mm": float(lens[1]),
        "corner_deg": corner,
        "rms_mm": float(np.sqrt((res ** 2).sum(1).mean())),
        "worst_mm": float(np.linalg.norm(res, axis=1).max()),
    }, M, org, idx, res


def pitch_uncertainty(xy, start, n=400, seed=0):
    """Bootstrap the pitch over targets -- how much does it move if the board were reshot?

    Resampling the targets, not the images, because the question is whether SIXTEEN points
    pin a pitch, not whether the projections are noisy. With 16 points and a residual of
    0.2 mm the answer is about 0.015 mm, and quoting the residual instead would have
    understated the pitch's precision by a factor of thirteen.

    `start` MUST be the full fitted parameter vector, rotation and origin included. Starting
    each resample from rotation 0 instead reported 2.73 mm -- a 6.7 % uncertainty that would
    have thrown away a real result. The objective is periodic in orientation, so a bad start
    settles into a neighbouring lattice cell and measures a diagonal or a harmonic rather
    than the pitch. Resamples that land more than 20 % away have done exactly that and are
    dropped, with the count reported so a silent collapse cannot hide inside the spread.
    """
    from scipy.optimize import least_squares
    rng = np.random.default_rng(seed)
    out = []
    for _ in range(n):
        S = xy[rng.choice(len(xy), len(xy), replace=True)]

        def resid(p):
            g, t, ox, oy = p
            u = (S - [ox, oy]) @ _rot(t) / g
            return (u - np.round(u)).ravel() * g

        try:
            out.append(abs(least_squares(resid, start).x[0]))
        except Exception:
            pass
    out = np.array(out)
    good = np.abs(out / start[0] - 1) < 0.20
    return float(np.std(out[good])), int(good.sum()), int((~good).sum())


def board_lattice(ref):
    """Flatten the board's targets onto their own best-fit plane and fit the grid."""
    B = ref["board_targets_mm"]
    nums = sorted(int(k) for k in B)
    if len(nums) < MIN_TARGETS:
        raise SystemExit(f"only {len(nums)} targets; need {MIN_TARGETS} to pin a lattice")
    P = np.array([B[str(n)] for n in nums], float)
    c = P.mean(0)
    _, _, Vt = np.linalg.svd(P - c, full_matrices=False)
    xy = (P - c) @ Vt[:2].T

    g, idx, res, params = fit_lattice(xy)
    rms = float(np.sqrt((res ** 2).sum(1).mean()))
    worst = float(np.linalg.norm(res, axis=1).max())
    sd, nboot, ncollapsed = pitch_uncertainty(xy, params)
    aff, _, _, _, _ = fit_affine(xy, params)
    cells = sorted(set(map(tuple, idx)))

    # The unfitted cross-check, and the one a person can repeat with a ruler.
    #
    # Everything above comes out of a lattice fit over all 16 targets at once, which is
    # the right way to get a precise number but is also a model with assumptions in it.
    # A conservator with a ruler measures something simpler and more direct: the distance
    # from one printed dot to the dot beside it. So measure exactly that, from the
    # triangulated positions alone, with no grid fitted and nothing averaged across the
    # board. If the fit had gone wrong -- picked the wrong cell size, folded two rows
    # together -- these two numbers would part company, and they do not.
    # Cut at 20 % of the MEDIAN nearest-neighbour distance, not at some multiple of the
    # fitted pitch. Two reasons. It keeps this check independent of the fit it is meant
    # to test; and the first version cut at 1.5x the pitch, which is above sqrt(2), so it
    # quietly admitted a DIAGONAL. Target 7 sits alone with no target in the cell beside
    # it, so its nearest partner is 57.4 mm away across a corner -- one value that dragged
    # the mean from 40.49 to 41.55 and the reported correction from -1.4 % to -3.7 %.
    # Diagonals sit at 1.41x and one-cell steps at 1.00x, so 1.2x separates them with room
    # to spare.
    D = np.linalg.norm(xy[:, None, :] - xy[None, :, :], axis=2)
    np.fill_diagonal(D, np.inf)
    nn = D.min(1)
    step = nn[nn < 1.2 * np.median(nn)]
    return {
        "n_targets": len(nums),
        "target_ids": nums,
        # The affine fit is the better model of this board and the square fit is the
        # headline number; they agree to 0.087 %, so the choice does not change the answer.
        "pitch_measured_mm": float(g),
        "neighbour_step": {
            "n": int(step.size),
            "mean_mm": float(step.mean()),
            "sd_mm": float(step.std()),
            "min_mm": float(step.min()),
            "max_mm": float(step.max()),
        },
        "affine": aff,
        "pitch_sd_mm": sd,
        "bootstrap_n": nboot,
        "bootstrap_collapsed": ncollapsed,
        "lattice_rms_mm": rms,
        "lattice_worst_mm": worst,
        "grid_cols": int(np.ptp(idx[:, 0])) + 1,
        "grid_rows": int(np.ptp(idx[:, 1])) + 1,
        "distinct_cells": len(cells),
        "per_target": {str(n): {"col": int(i[0]), "row": int(i[1]),
                                "off_mm": float(np.linalg.norm(r))}
                       for n, i, r in zip(nums, idx, res)},
    }


def base_plate(psx_dir):
    """What the base-plate scale bars actually solved to, and the scale-free ratio test."""
    sys.path.insert(0, str(Path(__file__).parent))
    from psx_reader import Project, find_project

    proj = Project(*find_project(psx_dir))
    S = proj.chunk_scale * 1000
    X = {m.number: m.ref for m in proj.markers.values()
         if m.kind == "point" and m.ref is not None}
    pinned = {m.number: sum(1 for k, v in m.pinned.items() if v)
              for m in proj.markers.values() if m.kind == "point"}
    views = {m.number: len(m.proj) for m in proj.markers.values() if m.kind == "point"}

    bars = []
    for a, b, d, en in proj.scalebars:
        na, nb = int(a.split()[-1]), int(b.split()[-1])
        if na in X and nb in X:
            m = float(np.linalg.norm(X[na] - X[nb]) * S)
            bars.append({"from": na, "to": nb, "declared_mm": d * 1000,
                         "solved_mm": m, "residual_mm": m - d * 1000,
                         "enabled": en})
    out = {"bars": bars,
           "points": {str(k): {"views": views.get(k, 0), "pinned": pinned.get(k, 0)}
                      for k in sorted(X)}}
    # The ratio test: no scale factor can change a ratio, so a wrong ratio is a wrong
    # point, not a wrong scale. This is the whole reason the base plate loses the argument.
    if len(bars) == 2 and bars[0]["from"] == bars[1]["from"]:
        r_meas = bars[1]["solved_mm"] / bars[0]["solved_mm"]
        r_nom = bars[1]["declared_mm"] / bars[0]["declared_mm"]
        a = X[bars[0]["to"]] - X[bars[0]["from"]]
        b = X[bars[1]["to"]] - X[bars[1]["from"]]
        out["ratio_test"] = {
            "measured": float(r_meas), "nominal": float(r_nom),
            "disagreement_pct": float((r_meas / r_nom - 1) * 100),
            "corner_deg": float(np.degrees(np.arccos(
                np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))))),
        }
    return out


def render(ref, lat, out_path, exaggerate=40):
    """Draw the lattice fit -- the residual itself, per target, at a scale that shows it.

    The pitch claim rests on offsets of a fifth of a millimetre across a 200 mm board. Drawn
    true-to-scale those are invisible and the picture would show a perfect grid whatever the
    fit had done, which is the failure the workspace scale rule exists to stop. So the grid
    is drawn in millimetres and the residuals are drawn as arrows magnified 40x, with the
    magnification stated on the figure and a scale bar for the real size. A wrinkle in taped
    paper should look like a smooth field of arrows; a bad fit looks like a pinwheel.
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    B = ref["board_targets_mm"]
    nums = sorted(int(k) for k in B)
    P = np.array([B[str(n)] for n in nums], float)
    c = P.mean(0)
    _, _, Vt = np.linalg.svd(P - c, full_matrices=False)
    xy = (P - c) @ Vt[:2].T
    g, idx, res, params = fit_lattice(xy)
    _, t, ox, oy = params
    fit = (idx * g) @ _rot(t).T + [ox, oy]

    fig, ax = plt.subplots(figsize=(9, 9))
    # The lattice is drawn as LINES, not as dots. Dotted, it was verified correct to
    # 0.0000 mm and still read to the eye as a random scatter, because the grid sits at
    # 48.9 deg and the cells the targets occupy are hidden under their own markers. A
    # picture a reader misinterprets has failed at its job even when the arithmetic behind
    # it is right -- so the grid has to LOOK like a grid.
    i0, i1 = int(idx[:, 0].min()) - 1, int(idx[:, 0].max()) + 1
    j0, j1 = int(idx[:, 1].min()) - 1, int(idx[:, 1].max()) + 1
    def cell(i, j):
        return (np.array([i, j], float) * g) @ _rot(t).T + [ox, oy]
    for i in range(i0, i1 + 1):
        a_, b_ = cell(i, j0), cell(i, j1)
        ax.plot([a_[0], b_[0]], [a_[1], b_[1]], "-", color="#ccc", lw=0.8, zorder=1)
    for j in range(j0, j1 + 1):
        a_, b_ = cell(i0, j), cell(i1, j)
        ax.plot([a_[0], b_[0]], [a_[1], b_[1]], "-", color="#ccc", lw=0.8, zorder=1)
    ax.plot(fit[:, 0], fit[:, 1], "s", mfc="none", mec="#888", ms=13, zorder=2,
            label="where a perfect grid puts it")
    ax.plot(xy[:, 0], xy[:, 1], "o", color="#1b6ca8", ms=6, zorder=4,
            label="where the target actually is")
    for n, a_, b_ in zip(nums, fit, xy):
        d = (b_ - a_) * exaggerate
        ax.arrow(a_[0], a_[1], d[0], d[1], color="#c0392b", width=0.35,
                 length_includes_head=True, zorder=5)
        ax.annotate(str(n), b_, xytext=(9, 6), textcoords="offset points", fontsize=8)
    x0 = xy[:, 0].min() - 25
    y0 = xy[:, 1].min() - 25
    ax.plot([x0, x0 + 1.0 * exaggerate], [y0, y0], "k-", lw=3)
    ax.annotate(f"1.0 mm of real offset, at {exaggerate}x", (x0, y0),
                xytext=(0, 7), textcoords="offset points", fontsize=9)
    ax.set_aspect("equal")
    ax.grid(alpha=0.2)
    ax.set_xlabel("mm"); ax.set_ylabel("mm")
    title_top = f"{ref['capture']}  -- the printed grid on the turntable board"
    ax.set_title(title_top + "\n" +
                 f"pitch {g:.3f} mm; targets sit {np.sqrt((res**2).sum(1).mean()):.3f} mm rms "
                 f"off a perfect lattice (arrows {exaggerate}x)", fontsize=11)
    ax.legend(fontsize=9, loc="upper right")
    fig.tight_layout()
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=110)
    plt.close(fig)
    return out_path


def report(ref, lat, base, nominal):
    print(f"\n{ref['capture']}  -- metric scale from the marker board\n")
    print(f"  {lat['n_targets']} coded targets on a {lat['grid_cols']}x{lat['grid_rows']} "
          f"lattice, {lat['distinct_cells']} cells occupied")
    print(f"  pitch          {lat['pitch_measured_mm']:.4f} mm  "
          f"+/- {lat['pitch_sd_mm']:.4f} ({lat['pitch_sd_mm']/lat['pitch_measured_mm']*100:.3f} %)"
          f"   [{lat['bootstrap_n']} bootstrap fits, {lat['bootstrap_collapsed']} discarded]")
    print(f"  off-lattice    {lat['lattice_rms_mm']:.3f} mm rms, worst "
          f"{lat['lattice_worst_mm']:.3f} mm")
    ns = lat.get("neighbour_step")
    if ns:
        print(f"  dot to dot     {ns['mean_mm']:.3f} mm mean of {ns['n']} single steps "
              f"(sd {ns['sd_mm']:.3f}, range {ns['min_mm']:.3f}-{ns['max_mm']:.3f})")
        print(f"                 -- no grid fitted; this is what a ruler measures")
    af = lat.get("affine")
    if af:
        # Reported even though it does not change the scale, because the leftover arrows in
        # the render lean the same way across the board and a reader will notice. Saying
        # "the board is slightly sheared and it costs 0.09 % of scale" is a finding; leaving
        # it unexplained invites someone to rediscover it as a bug.
        print(f"  the grid is not quite square: axes {af['axis_a_mm']:.3f} and "
              f"{af['axis_b_mm']:.3f} mm meeting at {af['corner_deg']:.2f} deg")
        print(f"  allowing that halves the residual to {af['rms_mm']:.3f} mm and moves the "
              f"pitch to {af['pitch_mm']:.3f} mm ({(af['pitch_mm']/lat['pitch_measured_mm']-1)*100:+.3f} %)")
        print(f"  -- cause unknown (paper, or a systematic in the solve); it does not "
              f"threaten the scale")
    if lat["lattice_rms_mm"] > MAX_LATTICE_RMS_MM:
        print(f"  -> NOT A GRID  residual above {MAX_LATTICE_RMS_MM} mm; pitch is meaningless")
        return None

    if base:
        print("\n  the base plate, for comparison:")
        for b in base["bars"]:
            print(f"    point {b['from']}-point {b['to']}  declared {b['declared_mm']:.1f} mm,"
                  f"  solved {b['solved_mm']:.2f},  off by {b['residual_mm']:+.2f} mm")
        rt = base.get("ratio_test")
        if rt:
            print(f"    edge ratio {rt['measured']:.4f} vs {rt['nominal']:.4f} nominal "
                  f"-> {rt['disagreement_pct']:+.2f} %  (scale-free: no scale can fix this)")
            print(f"    corner {rt['corner_deg']:.2f} deg -- the shape is a rectangle, so it is"
                  f" a point that is misplaced, not the plate")
        p = base["points"]
        gen = [k for k, v in p.items() if v["pinned"] == 0]
        if gen:
            print(f"    points {', '.join(gen)} have NO pinned projection: Metashape drew "
                  f"them into every frame from one estimate.")
            print(f"    They are {len(gen)} mouse clicks, not "
                  f"{sum(p[k]['views'] for k in gen)} measurements.")

    if nominal is None:
        print("\n  SCALE UNVERIFIED.  The pitch above is measured well; what it is measured")
        print("  in is unknown, because the printed sheet's designed pitch is not recorded")
        print("  and Agisoft does not publish one. Re-run with --pitch-nominal <mm> once")
        print("  somebody puts a ruler across the physical board. Until then this model's")
        print("  scale rests on the base plate, which the ratio test above shows is wrong.")
        return None

    f = nominal / lat["pitch_measured_mm"]
    print(f"\n  declared nominal pitch  {nominal:.3f} mm")
    print(f"  -> multiply this model's lengths by {f:.5f}  ({(f-1)*100:+.2f} %)")
    print(f"     a 100 mm sherd changes by {(f-1)*100:+.2f} mm; "
          f"a 5 mm break ridge by {(f-1)*5:+.3f} mm")
    if ns:
        # Both routes to the same correction, printed side by side. The ruler measured
        # single dot-to-dot steps, so the honest thing is to show what those alone say
        # as well as what the whole-board fit says, and to quote the SPREAD between them
        # rather than the tighter of the two. They differ by 0.16 %, which is the size of
        # the shear reported above -- consistent, and not something to hide inside an
        # average.
        fn = nominal / ns["mean_mm"]
        lo, hi = sorted(((f - 1) * 100, (fn - 1) * 100))
        print(f"     dot-to-dot alone would say {fn:.5f} ({(fn-1)*100:+.2f} %); "
              f"whole-board fit says {(f-1)*100:+.2f} %")
        print(f"     -> quote the correction as {lo:+.2f} to {hi:+.2f} %, not a single "
              f"figure to four places")
    if base:
        print("\n  what that does to the base plate:")
        agree = []
        for b in base["bars"]:
            v = b["solved_mm"] * f
            pct = (v / b["declared_mm"] - 1) * 100
            agree.append(abs(pct))
            print(f"    point {b['from']}-point {b['to']}  {v:.2f} mm vs {b['declared_mm']:.1f}"
                  f" declared  ({pct:+.2f} %)")
        if min(agree) <= SCALE_AGREE_PCT:
            print(f"    -> the better edge agrees to {min(agree):.2f} %, within "
                  f"{SCALE_AGREE_PCT} %. Two rulers built on different")
            print("       evidence land together, which neither could prove alone.")
        else:
            print(f"    -> BOTH edges disagree by more than {SCALE_AGREE_PCT} %. Do not average")
            print("       them: something is wrong that a scale factor cannot express.")
    return f


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("reference", help="reference_<capture>.json from board_frame.py build")
    ap.add_argument("--pitch-nominal", type=float, default=None,
                    help="designed pitch of the printed sheet, in mm, MEASURED WITH A RULER. "
                         "Omitted on purpose by default: guessing it silently invents scale.")
    ap.add_argument("--pitch-source", default=None,
                    help="where --pitch-nominal came from: who measured it, on what, when. "
                         "Stored in the reference file. The whole scale rests on this one "
                         "number, so an unattributed value is barely better than a guess.")
    ap.add_argument("--psx", default=None, help="project dir, for the base-plate cross-check")
    ap.add_argument("--render", default=None, help="write a picture of the lattice fit here")
    ap.add_argument("--write", action="store_true",
                    help="write the scale block back into the reference file")
    a = ap.parse_args()

    ref = json.loads(Path(a.reference).read_text())
    lat = board_lattice(ref)
    base = base_plate(a.psx) if a.psx else None
    f = report(ref, lat, base, a.pitch_nominal)

    lat["pitch_nominal_mm"] = a.pitch_nominal
    lat["nominal_source"] = (a.pitch_source or "declared on the command line, unattributed"
                             ) if a.pitch_nominal else "NOT SUPPLIED -- scale unverified"
    lat["correction_factor"] = f
    if base:
        lat["base_plate"] = base
    if a.render:
        print("\n  wrote " + str(render(ref, lat, a.render)))
    if a.write:
        ref["scale"] = lat
        Path(a.reference).write_text(json.dumps(ref, indent=1))
        print(f"\n  wrote the scale block into {a.reference}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
