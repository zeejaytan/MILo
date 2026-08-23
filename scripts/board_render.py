"""Draw the turntable reference, at a scale that resolves what is being claimed.

Two rules from the workspace notes are doing the work here, and they pull in opposite
directions. "Render geometry before reporting any result about it" says draw the rig.
"Check the view resolves the scale being tested" says a plan view of a 1.5 m camera orbit
CANNOT show a 1.2 mm radius wobble -- four successive views of a wear simulation failed
exactly that way, each one too coarse for the effect and each one convincing.

So this draws the same rig at two scales that differ by a factor of a thousand:

  panel 1  the orbit, in metres        -- resolves the 15 deg steps and any bent frame
  panel 2  the radius residual, in mm  -- resolves the 1.2 mm the claim rests on
  panel 3  the elevation, in metres    -- shows the five heights and that two are low
  panel 4  the board itself, in mm     -- resolves the 40 mm target grid and its flatness

Panel 2 is the one that matters. Panels 1 and 3 could look perfect while the rig was
wrong by centimetres; panel 2 is the measured quantity itself, per frame, unbinned.
"""
from pathlib import Path

import numpy as np

TURN_COLOURS = ["#1b6ca8", "#e07b39", "#2e8b57", "#a13d63", "#6a4c93"]


def render(ref, out_path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    turns = ref["turns"]
    frames = ref["frames"]
    q = ref["quality"]

    fig, ax = plt.subplots(2, 2, figsize=(15, 12))
    fig.suptitle(f"{ref['capture']}  -- turntable geometry measured from the marker board",
                 fontsize=14, y=0.98)

    # -- 1. the orbit, looking down the axis ------------------------------------------
    a = ax[0][0]
    for k, t in enumerate(turns):
        col = TURN_COLOURS[k % len(TURN_COLOURS)]
        d = np.radians([frames[f]["deg"] for f in t["frames"]])
        r = np.array([frames[f]["radius_m"] for f in t["frames"]])
        a.plot(r * np.cos(d), r * np.sin(d), "-", color=col, lw=0.8, alpha=0.5)
        a.plot(r * np.cos(d), r * np.sin(d), "o", color=col, ms=4,
               label=f"turn {t['turn']}  h={t['height_m']:+.2f} m  {t['arc_deg']:.0f}°")
    B = np.array(list(ref["board_targets_mm"].values())) / 1000.0
    a.plot(0, 0, "k+", ms=14, mew=2)
    a.annotate("turntable axis", (0, 0), xytext=(8, 8), textcoords="offset points", fontsize=8)
    a.set_aspect("equal")
    a.set_xlabel("metres"); a.set_ylabel("metres")
    a.set_title("Camera positions, looking down the turntable axis\n"
                "(each dot is one photograph; even spacing = a steady 15° step)",
                fontsize=10)
    a.legend(fontsize=8, loc="upper right")
    a.grid(alpha=0.25)

    # -- 2. the millimetres -- the scale the claim actually rests on -------------------
    a = ax[0][1]
    worst = 0.0
    for k, t in enumerate(turns):
        col = TURN_COLOURS[k % len(TURN_COLOURS)]
        d = np.array([frames[f]["deg"] for f in t["frames"]])
        r = np.array([frames[f]["radius_m"] for f in t["frames"]])
        resid = (r - r.mean()) * 1000
        worst = max(worst, np.abs(resid).max())
        o = np.argsort(d)
        a.plot(d[o], resid[o], "o-", color=col, ms=3, lw=0.8, label=f"turn {t['turn']}")
    a.axhline(0, color="k", lw=0.6)
    a.set_xlabel("angle round the turntable (degrees)")
    a.set_ylabel("distance from the axis, minus this turn's mean (mm)")
    a.set_title(f"Does the camera hold a constant radius?  worst {worst:.1f} mm on ~1.5 m\n"
                "(this is the measured quantity itself -- per frame, unbinned)", fontsize=10)
    a.legend(fontsize=8, ncol=5); a.grid(alpha=0.25)

    # -- 3. elevation ------------------------------------------------------------------
    a = ax[1][0]
    for k, t in enumerate(turns):
        col = TURN_COLOURS[k % len(TURN_COLOURS)]
        r = np.array([frames[f]["radius_m"] for f in t["frames"]])
        h = np.array([frames[f]["height_m"] for f in t["frames"]])
        a.plot(r, h, "o", color=col, ms=5)
        a.annotate(f"turn {t['turn']}", (r.mean(), h.mean()), xytext=(10, 0),
                   textcoords="offset points", fontsize=9, color=col)
    a.axhline(0, color="k", lw=0.8, ls="--")
    a.annotate("board / turntable surface", (a.get_xlim()[0], 0), xytext=(4, 4),
               textcoords="offset points", fontsize=8)
    a.set_xlabel("distance from the axis (m)"); a.set_ylabel("height above the board (m)")
    a.set_title("Where the camera stood, in side view\n"
                "(turns 1 and 3 sit nearest the board -- which is why they cannot read it)",
                fontsize=10)
    a.grid(alpha=0.25)

    # -- 4. the board, in millimetres --------------------------------------------------
    a = ax[1][1]
    nums = sorted(int(k) for k in ref["board_targets_mm"])
    P = np.array([ref["board_targets_mm"][str(n)] for n in nums])
    c = P.mean(0)
    _, _, Vt = np.linalg.svd(P - c, full_matrices=False)
    xy = (P - c) @ Vt[:2].T
    off = (P - c) @ Vt[2]
    s = a.scatter(xy[:, 0], xy[:, 1], c=off, cmap="coolwarm", s=260,
                  vmin=-abs(off).max(), vmax=abs(off).max(), zorder=3)
    for n, p in zip(nums, xy):
        a.annotate(str(n), p, ha="center", va="center", fontsize=8, zorder=4)
    plt.colorbar(s, ax=a, label="height off the best-fit plane (mm)")
    a.set_aspect("equal"); a.grid(alpha=0.25)
    a.set_xlabel("mm"); a.set_ylabel("mm")
    a.set_title(f"The board, reconstructed -- {len(nums)} coded targets\n"
                f"flat to {q['board_plane_rms_mm']:.2f} mm rms; numbers are the printed IDs",
                fontsize=10)

    foot = (f"targets reproject at {q['target_reproj_rms_px']:.2f} px rms   |   "
            f"axis straight to {q['axis_straightness_mm']:.2f} mm   |   "
            f"axis is {q['axis_vs_board_normal_deg']:.2f}° off the board normal   |   "
            f"{ref['coverage']['n_frames']} frames cover {ref['coverage']['arc_deg']:.1f}°")
    fig.text(0.5, 0.005, foot, ha="center", fontsize=9, color="#444")
    fig.tight_layout(rect=[0, 0.02, 1, 0.97])
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=110)
    plt.close(fig)
    return out_path
