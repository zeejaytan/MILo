# The turntable marker: what it is, how much of the turn it covers, and what it is good for

Captures measured: **2025-07-03/N01** (119 photographs) and, as a control,
**2025-07-03/M04** (120 photographs, flagged unusable in the record). Work done 2026-08-22/23
on the laptop. **No reconstruction was run and no Slurm job was submitted** — this is the
"measure first" half of the marker question.

---

## The short version

The conservator's note in the scanning record — *"Use base as scale, marker on turntable
for alignment"* — describes a board that **is there, is legible, and has never been read by
anything in this workspace**.

On this capture the turntable board can be read on **three of the five revolutions, at
every single station of all three — a full 360° each time**. On the other two revolutions
it cannot be read at all, and the photographs show why: on those passes the camera was low
enough that the board is edge-on and hidden behind the blue base plate. It is not there to
be found.

So the answer to "which of the three things is true" is the **middle one, sharpened**:

> The markers are **readable**. The marker-handling code that exists in this project's
> orbit is **built for a different family of marker**, is **switched off**, and is
> **bypassed** by the route MILo actually runs. Nothing is mis-wired; nothing is wired.

That is a claim about **tooling**, not about the method and not about the material. No
reconstruction was scored here, so nothing in this note says whether markers would make a
reconstruction better — only that the raw ingredient exists and is good enough to be worth
the next step.

**Sections 7 to 10 are what happened next.** Tier 1 (the board as an absolute rotation
reference) and Tier 3 (metric scale) are built and verified. Tier 2 (marker-guided matching)
was measured and is **recommended against for this material** — it would take long-range
matches away from the 47 photographs that cannot see the board.

Two results from that work change what should be believed about this capture:

> **The N01 Metashape model is 1.2–1.4 % too large**, and the reason is one misplaced click.
> Metashape fitted its scale to two hand-clicked bars on the blue base plate; those bars
> disagree with each other by 3.16 % in a way no scale factor can fix. The marker board is a
> ruler about sixty times tighter, and with its printed pitch measured (40 mm, ruler on the
> physical sheet, 2026-08-23) it puts the error at **1.2 to 1.4 mm on a 100 mm sherd**.
>
> **The blue plate itself is fine.** Section 10 settles this without circular reasoning: two
> other trees measure the plate's shape by a route that never touches Metashape, and both
> land where a 190 × 130 mm plate should. So the record is right, `scripts/measure_base.py`
> is right, and **the finished A01–A04 meshes need no correction** — they were never scaled
> through the broken reference. What they gain is a checked reference instead of an
> unchecked one.

---

## 1. What the marker is

![a coded target at native resolution](../../artifacts/markers/nat_0_0_650.png)

A white paper disc lying flat on the turntable, under the blue base plate that carries the
pottery tree. Printed on it are **Agisoft Metashape circular coded targets**: a solid black
centre dot, a thin white gap, then a ring cut into arc segments that encodes the target's
identity, with the identity printed in small type beside it. Around the rim are
black-and-white tick rectangles and a single orientation arrow.

Fourteen distinct identities are legible on the disc by eye: 4, 5, 6, 9, 10, 11, 12, 14,
15, 16, 21, 22, 25, 26.

![the disc with every detection drawn](../../artifacts/markers/det_8355_final.png)

**These are not ArUco, ChArUco or AprilTag, and that was established by test rather than by
opinion.** OpenCV's ArUco detector was run over six N01 frames against all 27 of its
built-in dictionaries: **zero detections, 162 attempts**. The same detector, in the same
session, correctly read a synthetic `DICT_4X4_50` tag that had been slanted, blurred and
contrast-reduced. The detector works; the board is a different family.

This matters because the coded-target subsystem in the sister pipeline on Spartan
(`Photogrammetry/pipeline/`, five libraries totalling roughly 1,900 lines plus three entry-point scripts) is written against
`DICT_4X4_50`. Even if it were switched on — it is not; `coded_targets.enabled: false` —
and even if MILo's `reconstruct_group.slurm` called it — it does not; that script replaces
`run_colmap.py`, which is the stage that would have invoked the detector — **it would
return nothing on this board.**

---

## 2. How much of the turn the board covers

N01 is **not one sweep**. Its shutter times fall into five bursts of 23–24 frames, 2–5 s
apart within a burst and 60–123 s apart between them: the turntable running round once per
burst, with the camera moved to a new height in between. That is what makes "degrees" a
measured quantity here — **24 stations to a revolution is 15° per frame** — rather than a
guess. A blind run of four frames is a 60° blind arc and can be named as such.

Three targets is the least that fixes a flat board's pose, so "readable" below means
**three or more targets found**.

| revolution | frames | targets per frame (median) | range | stations readable | degrees readable | largest blind arc | board clipped by frame edge |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 24 | 0 | 0–1 | 0 / 24 | **0° of 360** | 360° | 0 |
| 2 | 24 | 9 | 5–13 | 24 / 24 | **360° of 360** | 0° | 0 |
| 3 | 23 | 0 | 0–1 | 0 / 23 | **0° of 360** | 360° | 0 |
| 4 | 24 | 8 | 5–13 | 24 / 24 | **360° of 360** | 0° | 15 |
| 5 | 24 | 11 | 3–15 | 24 / 24 | **360° of 360** | 0° | 11 |

Across the whole capture: **72 of 119 frames readable (61%)**, median 6 targets per frame,
best frame 15.

The 61% is the less useful number of the two. The useful one is that the split is **not
scattered** — it is exactly the three high camera positions against the two low ones. Where
the board is visible at all it is visible for the entire revolution, with margin: even the
weakest readable turn never drops below 5 targets except at one station.

### The pictures say the same thing as the numbers

This is checked, not assumed. A contact sheet was written per revolution, every station of
it, so that the sheet **is** the turn the degrees figure describes.

Revolution 5 — camera high, board visible all the way round, 3–15 targets per frame:

![turn 5](../../artifacts/markers/contact_03072025_N01_turn5.png)

Revolution 3 — camera low, board edge-on and hidden behind the blue base plate, 0–1
targets per frame:

![turn 3](../../artifacts/markers/contact_03072025_N01_turn3.png)

**The blind revolutions are blind because the board is not visible, not because the
detector failed.** That distinction is the whole point of looking, and it is the difference
between "we cannot use markers on the low passes" (true, and a framing fact the conservator
controls) and "the marker detector does not work" (false).

### The external control: 2025-07-03/M04, and what "placed incorrectly" actually means

M04 was shot on the same afternoon, on the same rig, and the record flags it
`markers_usable: false` — *"Marker placed incorrectly. Do NOT use it for feature
recognition, registration or alignment — it will pull the solve off."* All 120 frames were
fetched and run as a control (`--allow-unusable`, which the script demands): **0 of 120
frames readable, 0° of every revolution.**

Looking at it explains the record's note better than the note does:

![the M04 marker, on the table rather than on the turntable](../../artifacts/markers/m04_card.png)

The M04 markers are the **same family — Metashape circular coded targets, identities 3 and
6 visible here — but printed large, on paper strips, and lying on the black table beside
the turntable.** The turntable is the dark disc with the white tick marks; the strips are
not on it.

**So they do not turn with the object.** Every photograph sees them from the same angle in
the same place. Handing that to a solver tells it the camera never moved relative to those
targets, which is the opposite of what the turntable geometry says — hence "it will pull
the solve off". The conservator's judgement is exactly right, and this is the picture of
why.

What those targets *are* good for is the thing the record actually used them for: the M04
measurement line reads `mark3-4: 42.4cm, mark3-6: 8.7cm, mark4-5: 11cm` — **scale bars**
between marker centres. As a ruler, a static board is fine. As an alignment reference it is
worse than nothing.

**One caveat on this control, stated so it is not over-read.** The detector is tuned to the
scale of the N01 turntable disc — a centre dot of radius 1.6 to 14 px. The M04 strip
targets have a centre dot of roughly 27 px, so they fall outside that window and are
rejected on size before any of the ring tests run. The zero is therefore *"this detector,
built for the turntable disc, sees nothing on M04"* — **not** *"M04's targets are
illegible"*. They are perfectly legible; they are in the wrong place. The protection that
matters is the record gate, which refuses the capture outright.

---

## 3. How the reading is done, and what is wrong with it

`scripts/detect_markers.py`. Run it as:

```
python scripts/detect_markers.py <dir named like 03072025/N01>
```

**It refuses to run on a capture the record flags `markers_usable: false`**, before it even
lists the frames, unless `--allow-unusable` is passed. Checked: `2025-07-03/M04` is refused,
`2025-07-03/N01` runs.

Three decisions in it are worth knowing about, because each replaced something that was
wrong:

- **The identity is not decoded here — but it is decodable, and it has already been
  decoded.** An earlier draft of this note said the targets were "far too coarse to read
  arc segments reliably". **That was wrong**, and it is worth recording why, because it was
  a guess presented as a measurement. The guess was a 4–5 px centre dot. Measured across
  all 674 detections, the median centre-dot radius is **6.6 px**, which puts a 12-bit
  coded ring at r ≈ 21 px with each sector spanning **≈ 11 px of arc**. Rendered at native
  resolution (`artifacts/markers/decode_native.png`, 8× nearest-neighbour, no invented
  detail) the arcs are individually countable. And the conservator's own Metashape project
  decoded **all 16 IDs correctly** — they match the numbers printed beside each target.
  What this script measures is still the **centre**, because for its job — *is the board
  readable, over how much of the turn* — the centre is enough and a misread identity would
  be worse than none. Where identities are needed, they should be **read out of the
  Metashape project**, not re-derived here.
- **Black-hat morphology, not adaptive thresholding.** The disc is small in frame and
  ringed by a black backdrop. Any averaging window wide enough to see the board straddles
  that edge, drags the local mean down and turns bare board into speckle; any window narrow
  enough to avoid it is comparable in size to a whole target and adapts to the target's own
  ink. Both failure modes were rendered (`artifacts/markers/thresh_compare.png`) before the
  method was changed.
- **One detection per target, not one per piece of ink.** A target's centre dot and each
  arc of its ring are separate blobs, and an arc beside a dot passes the same tests the dot
  does. Drawn on frame 8355 this was obvious: target 5 carried three overlapping circles,
  10 and 25 two each — **a disc of fourteen targets was being reported as twenty**. Nothing
  in the statistics said so. Every readability figure in this note would have been inflated,
  in the flattering direction.

### Known limitations, quantified

- **About 5% of detections are false positives that are not on the disc at all.** Measured:
  of 662 detections in frames with five or more, **32 (4.8%)** sit more than three times
  the cloud's own spread away from the rest — on a clamp or a sherd up the tree. Removing
  all of them changes the readability figure from 72 frames to 71. It does not change any
  conclusion here, **but it would poison a board-pose estimate**, so Tier 1 must reject
  points that do not lie on the disc.
- **Two known targets are missed on the best frame**: identity 9, which is under a
  translucent tape patch, and identity 4, which abuts the blue base plate.
- **The board is clipped by the edge of the picture in 26 frames**, all in revolutions 4
  and 5. It reduces the count without ever making a frame unreadable, except one station
  (frame 8359, three targets).
- **One frame per 0.5 s** on the laptop; 119 frames in about a minute, single core. This is
  laptop work, not cluster work.

---

## 4. What this is worth, and what it is not

**One object, one capture, no repeat.** Everything above is N01 — a single pottery tree,
photographed once, on one afternoon. It is a **lead, not a conclusion**. What generalises
is likely to be the *shape* of the finding (the board reads on high passes and not on low
ones, because of where it sits relative to the base plate) rather than the exact figures.

**Nothing here says markers improve a reconstruction.** No solve was run. The only claim is
about ingredient quality.

**What would change the answer:** a capture where the base plate is smaller or the board
larger, so the low passes see it too; or a capture where the disc is further off-centre and
clipped more often. Both are framing choices, not software problems.

---

## 5. Recommended next piece of work — Tier 1

**Use the board as an instrument, not as an input.** Recover the board's rotation angle in
each photograph and compare it against the angle COLMAP placed that photograph at.

Why this one first: it **changes no reconstruction**, so it cannot break anything, and it
turns `scripts/check_turntable.py` from *"does the camera arc look plausible"* — which
infers the rotation from where the cameras landed — into *"is every frame at the angle the
board says it is"*, against an independent reference. It would have caught the A03 bent
solve immediately and by name, instead of that solve scoring a **better** reprojection
error than a correct one. The workspace rule is to prefer a gate over a paragraph; this is
the gate.

It is also directly supported by what was measured: 15° stations, three full revolutions
with 5–15 targets each, and a centre measurable to well under a pixel.

What it needs, in order:

1. Fit the disc ellipse per frame and **reject detections that are not on it** — this kills
   the 4.8% off-disc false positives, and is a prerequisite, not a refinement.
2. Recover each frame's board rotation. The camera is fixed and the object rotates, so the
   disc's image is a near-fixed ellipse and the targets move along it — the rotation is
   recoverable from the constellation without decoding any identity.
3. Check the recovered angles are a clean 15° ladder. **This is self-checking**: if the
   recovered angles do not come out as 24 even steps, the instrument is wrong and it says
   so before it is trusted for anything else.
4. Add it to `check_turntable.py` as an extra gate, active only on captures the record
   flags `markers_usable: true`, and only on the revolutions where the board reads.

**Cost: a day on the laptop, no cluster time, no new dependencies** beyond OpenCV. Steps
1–3 are measurable on the 72 readable frames already pulled. Step 4 is a small addition to
an existing script.

Tier 2 (marker-guided matching through `matches_importer` / `feature_importer`) and Tier 3
(metric scale via `model_aligner`, cross-checked against the 13 × 19 cm base) remain worth
doing but should wait: both change what the solver sees, and neither should be attempted
before the board's own geometry is verified by Tier 1.

**Not recommended at any tier:** making a solve *depend* on the markers. The board is at
the base of the tree, well away from the break surfaces, it is planar, it is clipped in 26
frames, and it is invisible on two of five revolutions. It can discipline camera poses; it
cannot contribute break-surface geometry, and a solve that needs it would fail on every
capture before the N01 batch.

**For future captures — raise, do not act on.** Printing a ChArUco or AprilGrid disc and
placing it on the turntable **alongside** the existing sheet would cost a sheet of paper,
make every future capture readable by standard open tooling, and not disturb the Metashape
workflow at all. Placing it so the low camera passes can see it would double the usable
coverage.

## 6. Are Tier 2 and Tier 3 possible? Yes — and most of the work is already done

Asked after the above was written. The short answer changed the plan, so it is recorded in
full.

### 6.1 The conservator's Metashape project already contains everything Tier 2 and 3 need

`N01.files/0/chunk.zip` and `N01.files/0/0/frame.zip` in the Mediaflux archive are **zipped
XML**, readable without a Metashape licence, 340 KB unpacked. They contain:

| What | Count | Meaning |
|---|---|---|
| Coded targets, **decoded** | 16 | `target 4,5,6,7,9,10,11,12,13,14,15,16,21,22,25,26` |
| Target projections | 589 | sub-pixel image coordinates, per photo |
| Hand-marked base points | 4 | `point 1,3,4,5` — corners of the blue plate |
| Base-point projections | 382 | |
| **Scale bars** | 2 | `point 3–point 4 = 0.13 m`, `point 3–point 5 = 0.19 m` |
| **Solved camera poses** | 119 of 119 | every photograph aligned |

The two scale bars *are* the 13 × 19 cm base named in the scanning record. The
conservator's note — *"Use base as scale, marker on turntable for alignment"* — is
implemented literally in this file.

### 6.2 The coordinates transfer to COLMAP with no conversion, and the detector was right

Metashape stores its sensor as **5568 × 3712 — the stored pixel frame**, the same one
COLMAP reads and the same one this detector used (`IMREAD_IGNORE_ORIENTATION`). Tested
against all four candidate rotations:

| Mapping | Median nearest-neighbour distance |
|---|---|
| **identity** | **0.78 px** |
| rotate 90° CW | 1668 px |
| rotate 90° CCW | 3110 px |
| rotate 180° | 4601 px |

No EXIF rotation is needed anywhere in the chain. Across all 119 frames, this script's
detections and Agisoft's agree to a **median 0.70 px, 90th percentile 0.92 px, worst
1.16 px** over 468 matched targets — two entirely independent detectors on the same ink.

It also settles the coverage figure by a second route. Metashape saw the board in
**72 frames**; this script saw it in 81, of which the extra 9 are the known off-disc false
positives. Per revolution:

| Revolution | Photos seeing the disc | Arc |
|---|---|---|
| turn 1 | 0 / 24 | **0°** |
| turn 2 | 24 / 24 | **360°** |
| turn 3 | 0 / 23 | **0°** |
| turn 4 | 24 / 24 | **360°** |
| turn 5 | 24 / 24 | **360°** |

Turns 2, 4 and 5 are readable at **every single station**. Turns 1 and 3 are the two camera
heights nearly level with the table: `artifacts/markers/psx_turn3_why.png` shows the disc
there compressed to an unreadable sliver, mostly occluded by the blue plate and off the
focal plane. **Both detectors are right to find nothing.** This is the board being
invisible, not either detector failing.

### 6.3 Tier 3 is possible, and it has now been demonstrated on this capture

COLMAP has **no ground-control-point support in any version** — `model_aligner` aligns to
*camera* positions (`--ref_images_path`, `--alignment_type {plane,ecef,enu,custom}`), never
to known object points or known distances; the open request is
[colmap#767](https://github.com/colmap/colmap/issues/767). So "align to a scale bar" is not
a COLMAP command. It is three steps around COLMAP: triangulate the two endpoints, divide
the known distance by the measured one, apply the factor with `model_transformer` (present
in this build, confirmed).

That was run here on Metashape's own solve, as a test of the method:

| Distance | Recovered | Known |
|---|---|---|
| point 3 → point 4 | 12.76 cm | 13.0 cm (constrained) |
| point 3 → point 5 | 19.23 cm | 19.0 cm (constrained) |
| **point 4 → point 5** | **23.03 cm** | **nothing — free check.** A 13 × 19 cm rectangle's diagonal is **23.02 cm** |

The third distance was constrained by nothing and lands **0.1 mm** from the diagonal the
other two imply. The rectangle closes. Separately, the 16 coded targets triangulate onto a
plane to **0.75 mm** — a flat printed disc, which also means no ID was misread, since a
mis-decoded target would land off the plane.

Two honest caveats. The triangulation above ignores lens distortion and assumes the
principal point is centred, so roughly 1–2 mm of the 12.76-vs-13.0 gap is the *method's*
approximation, not the data's. And the base points are flagged `pinned="false"` in the XML,
which in Metashape can mean a projection it propagated rather than one a person clicked —
they land on the plate corners in every frame checked (`psx_8344_turn4.png`,
`psx_8250_turn1_blind.png`), but before they are used as a metric reference they should be
re-detected, or the plate simply measured with callipers.

### 6.4 Tier 2 is possible, and the co-visibility is strong where it exists

The 16 decoded IDs give exactly what `matches_importer` wants — named correspondences that
cannot be confused between two similar sherds:

| | Pairs |
|---|---|
| All photo pairs | 7021 |
| Pairs sharing ≥ 2 coded targets | **2148 (30.6%)** |
| Pairs sharing ≥ 3 coded targets | 1781 |

and critically **1476 of those 2148 are cross-revolution** (turn 2↔4: 423, 2↔5: 513,
4↔5: 540). Long-range links between camera heights are precisely the correspondences whose
absence let A03 build the blue base twice, 35° apart.

**But 47 of 119 photographs — all of turns 1 and 3 — get nothing.** The markers help least
at the two lowest camera heights, which are the frames that see the least of the object and
are therefore the most likely to be placed wrongly in the first place. This is the single
biggest limitation and it is not fixable in post: the board is not in those pictures.

One unexplored route to close it: the **white tape ticks on the black turntable rim** are
visible in all five revolutions, including the level ones. They are identical to one
another, so they cannot name an absolute angle — but they can measure a rotation
*increment*, which is enough to catch a bent solve. Worth a look; not yet examined.

### 6.5 The finding that matters more than either tier

**All 119 cameras are solved in that project, and the solve is a good one.** Measured from
the camera centres:

| Revolution | Arc covered | Median step |
|---|---|---|
| turn 1 | 339.0° | 15.06° |
| turn 2 | 342.5° | 15.91° |
| turn 3 | 337.4° | 15.41° |
| turn 4 | 340.4° | 14.62° |
| turn 5 | 341.3° | 14.77° |
| **all 119** | **351.8°** | largest gap 8.2° |

The 15° step derived here from **shutter timestamps** and the 15° step in **Metashape's
solved camera positions** are two completely independent measurements of the same rig, and
they agree. `check_turntable.py`'s thresholds (270° minimum arc, 30° maximum step) pass
comfortably.

So this workspace now has something it has never had for turntable geometry: **a reference
answer.** A COLMAP solve of N01 can be compared camera-by-camera against a professional
solve of the same photographs, rather than judged by reprojection error — the metric that
`docs/lessons.md` records rating a *collapsed* solve as better than a correct one.

### 6.6 Revised recommendation

Tier 1 still goes first, and it is now cheaper: the angles it must recover can be checked
against Metashape's solved poses instead of only against themselves.

Tier 3 is next and is nearly free — the correspondences exist, the method is demonstrated
above, and it gives a second scale route that must agree with `scripts/measure_base.py`.

Tier 2 is sound and worth doing, but its honest value is **insurance, not improvement**.
Two things temper it:

1. **N01 does not need it.** It already solves cleanly. Markers cannot fix the captures
   that actually failed — A01 and A03 are from the 17 June batch, **before** the marker was
   introduced. Nothing in the archive that broke can be rescued this way.
2. **It will not improve the mesh.** The board is flat, at the base of the stand, roughly
   10 cm from the axis, while the sherds sit up to half a metre above it. It contributes no
   break-surface geometry. It can only help the mesh indirectly, by improving camera poses
   — and where poses are already good, that is not a measurable gain. There is even a mild
   risk in the other direction: weighting extra tie points on a single plane at the base
   can pull a bundle adjustment toward that plane.

The value of Tier 2 is that a capture which *would* have bent instead fails loudly or does
not fail at all. That is worth having. It is not a sharper mesh.

---

## 7. Tier 1, built: the board as an absolute rotation reference

`check_turntable.py` could previously only ask questions the solve answers about *itself*.
A solve that is wrong *smoothly* — every frame displaced, but displaced consistently —
satisfies both coverage and frame-order. `--reference` closes that hole.

**How it is built.** `psx_reader.py` reads the Metashape project with no licence (the
`.psx` is XML pointing at zipped XML). `board_frame.py` triangulates the 16 coded targets,
fits the board plane, splits the 119 frames into five passes on height change, and
alternates between the axis direction and the per-pass circle centres until settled.
`check_turntable.py --reference` then fits one similarity transform between the solve's
camera centres and the board's, refitting robustly so the very frames being hunted cannot
drag the alignment onto themselves — the failure mode that makes a bent solve hard to catch.

**What the reference is worth**, all measured rather than assumed:

| Quantity | Value |
|---|---|
| Board flatness | 0.75 mm rms over 16 targets |
| Targets reprojected into their own measured image positions | 0.25 px rms, worst 0.76 |
| Camera radius held, per pass | 1.2 mm on a ~1.5 m radius |
| Five pass-circle centres, distance off one straight line | 0.15 mm |
| Coverage | 119 frames over 351.7°, largest gap 8.35° |

**Proven to fail, not only to pass.** `--self-test` builds synthetic solves with known
damage: a faithful one in a different frame and scale → 0 bad; a bent one with six frames
rotated 40° → exactly those six, at 40.00°; a collapsed one squeezed into a 60° arc → 108
of 119. A gate only ever seen to pass is indistinguishable from one that always passes.

**Three findings from building it.**

1. **The rotation axis is 1.07° off the board's own normal.** The board is not quite level
   on the turntable. Taking the normal as the axis — the obvious shortcut — puts a silent
   1° error into every angle.
2. **The camera heights are not monotonic**: 0.082, 0.398, 0.159, 0.514, 0.750 m. The
   conservator alternated low and high passes. This is why turns 1 and 3 read the board
   worst — they are the two lowest and see it nearly edge-on.
3. **The turntable has no detents.** Across 114 within-pass steps it advances 15.1° by hand
   with a standard deviation of 2.3°, extremes 7.4° and 22.7°. That measures the existing
   frame-order threshold's headroom instead of hoping for it: the limit for N01 would be
   max(30, 2.5 × 15.1) = 37.7°, clearing the worst honest step by 1.7×.

**A correction to section 6.** The Tier 3 "free diagonal check" reported there — 23.03 cm
against 23.02 cm — was flattering and should not have been led with. With Metashape's lens
distortion handled correctly (see below) the two base edges measure 12.72 cm against 13.0
and 19.18 cm against 19.0: errors of −2.8 mm and +1.8 mm, in opposite directions, which
largely cancel in the diagonal. The honest bound from that check is about ±3 mm.

**A convention that would have been a silent few-pixel error.** Metashape and OpenCV both
call their tangential distortion coefficients `p1` and `p2` and mean the opposite things by
them: Metashape puts `p1` on the `(r² + 2x²)` term, OpenCV puts `p2` there. Proven by
measurement, not by reading docs — projecting Metashape's own solved marker positions
against its own stored image measurements gives 0.00 px rms with the terms swapped, 8.84 px
as written, and 8.27 px with no distortion model at all. Feeding them straight through is
worse than ignoring distortion entirely.

## 8. Tier 3, built: metric scale — and the plan was wrong about it

Tier 3 was specified as "board scale as a second, *independent* check that must agree with
the 13×19 cm base plate". Reading the project shows that cannot work as stated.

**The board's millimetres are derived from the base plate.** Metashape's chunk scale is
fitted to two scale bars, `point 3`–`point 4` = 0.130 m and `point 3`–`point 5` = 0.190 m.
Every metric length in the project, the board included, is downstream of those two numbers.
Checking the board against the base is checking a ruler against itself.

**The base plate is four mouse clicks, not four measurements.** Points 1, 3, 4 and 5 have
*zero* pinned projections across 69–116 images and reproject at exactly 0.000 px — that is
Metashape drawing one 3D estimate into every frame. The coded targets are the opposite:
28 to 46 views each, every one pinned, every one machine-detected.

**A scale-free test settles it.** The *ratio* of the two base edges cannot be changed by any
scale factor:

```
measured  191.83 / 127.24 = 1.5077
nominal        190 / 130  = 1.4615      off by +3.16 %
```

while the corner at point 3 measures 89.76° — a true rectangle corner. Right shape, wrong
proportions: point 4 sits about 4.5 mm from where it was declared to be. Metashape then
fitted *one* scale to two bars that disagree, and the compromise is wrong by over a per cent.

**This does not impugn `scripts/measure_base.py`.** That script measures the plate itself
from the reconstruction (isolated semantically with SAM 3) and validates it with the same
scale-free aspect-ratio idea. Under the board's ruler the 190 mm edge is right to 0.42% and
only the 130 mm edge is wrong, so it is Metashape's clicked *point*, not the plate, that is
misplaced. The 13×19 cm assumption stands.

> **That last step was circular as first written and is now settled properly.** Saying "the
> 190 mm edge is right and the 130 mm one is wrong" assumes the plate is 190×130, which is
> the thing in question. **Section 10** decides it without that assumption, using the
> scale-free aspect ratio measured on two other trees by a route that never touches
> Metashape. The conclusion survives; the argument for it did not.

**What the board can actually do.** The 16 targets sit on a printed square lattice, pitch
**40.557 mm ± 0.015 (0.036%)**, residual 0.196 mm rms — roughly sixty times tighter than
the base plate's own internal disagreement. It is a far better ruler.

**The refutation test, run because the render asked for it.** The leftover arrows in
`lattice_N01.png` leaned the same way across the whole board, which is what a sheared grid
looks like and what noise does not. Refitting with shear allowed: the axes meet at
**89.74°**, not 90°, and the residual halves to 0.088 mm. Letting the two pitches differ
*without* shear barely helps (0.185 mm), so the effect is genuinely shear. **The cause is
not known** — paper on a slightly domed turntable, or a systematic in the solve. The base
plate cannot arbitrate: its corner reads 89.76°, which looks like agreement until you
notice its own points carry ~4.5 mm of error, making that corner uncertain by ±2°. Two
numbers agreeing to 0.02° when one carries 2° of error is a coincidence, not a
confirmation. Crucially the scale barely moves: the area-equivalent pitch is 40.592 mm,
+0.087%.

**The blocker, stated plainly.** A lattice pitch is only a ruler if its *nominal* value is
known, and no arithmetic here can supply it. The board is a Metashape "Print Markers" PDF
page cut into a disc and taped down (`artifacts/markers/crop_A42_8355.png`: printed target
numbers, page-corner squares, visibly wrinkled paper, tape strips). Agisoft documents target
*sizing* — 10–30 px centre dot, global diameter ≈3.5× the centre — but publishes no grid
pitch, and the print dialog's page layout is up to whoever pressed the button. A printer set
to "fit to page" moves it again.

So `board_scale.py` **refuses to guess**: without `--pitch-nominal` it reports the
measurement and says the scale is unverified. **One minute with a ruler on the physical
sheet closes this.** If the pitch is the obvious 40.0 mm, this model is 1.37% too large —
a 100 mm sherd measuring 1.4 mm wrong — and the board and the good base edge then agree to
0.42%, which neither could establish alone.

**The apply step is free.** `check_turntable.py --reference` already had to solve for a
similarity scale to compare the two rigs at all, and that factor *is* the conversion into
the reference's metres — built on 119 camera positions spread over 350° and half a metre of
height, rather than on four clicks. It is now printed, and asserted in the self-test: the
synthetic model is built at 3.4× and the recovery is exactly 1/3.4, on the bent case as well
as the faithful one, since the robust refit drops the planted frames. Only the collapsed
case is allowed to get it wrong — a solve that folded the turn has no true scale left, and
reporting a confident metre there would be a lie.

---

### Resolved, 2026-08-23: the printed pitch is 40 mm

The conservator put a ruler across the physical sheet: dot centre to dot centre is **4 cm**,
measured in two directions from the same target (8→2 and 8→9). That is the number section 8
said no arithmetic here could supply, and it closes the scale.

**Two checks were run before accepting it.**

*Is a single step really what was measured?* The lattice fit assigns every target a
(column, row). Across the 16 decoded targets a one-cell step **down** a column is a number
difference of exactly **+1**, and a step **across** a column is **±5 or ±6**. The
conservator's 8→9 is +1 and 8→2 is −6, so both are genuine single steps. Had either been a
two-cell span read as one, the pitch would have been wrong by a factor of two and the model
by 100 % — this is the check that rules that out. (The across-column difference is not a
constant 5, so the printed page is not a plain numeric raster. No explanation is offered
here; it does not affect the result and inventing one would be the mistake section 8 already
had to correct.)

*Does the ruler's quantity match the script's?* It did not. `board_scale.py` reported a
pitch from a lattice fit over all 16 targets at once; a ruler measures one dot to the dot
beside it. Those are different quantities and can disagree, so the direct one is now
computed as well, with no grid fitted:

```
pitch (whole-board fit)   40.5570 mm  +/- 0.0146
dot to dot (15 steps)     40.491 mm   sd 0.076, range 40.423 - 40.667
```

The first version of that cross-check was wrong and is worth recording. It selected
one-cell steps by cutting at 1.5x the fitted pitch — above sqrt(2), so it silently admitted
a **diagonal**. Target 7 has no target in the cell beside it, so its nearest partner is
57.4 mm away across a corner. That single value pulled the mean from 40.49 to 41.55 mm and
the reported correction from −1.4 % to **−3.7 %**, which would have been reported as a real
disagreement between two methods. The cut is now 1.2x the *median* nearest-neighbour
distance: independent of the fit it is meant to test, and comfortably below sqrt(2).

**The answer.**

| | |
|---|---|
| Correction, whole-board fit | ×0.98627 (**−1.37 %**) |
| Correction, dot-to-dot alone | ×0.98786 (**−1.21 %**) |
| Honest range | **−1.2 % to −1.4 %** |
| On a 100 mm sherd | 1.2 – 1.4 mm too large |
| On a 5 mm break ridge | 0.06 – 0.07 mm |

The two routes differ by 0.16 %, which is the size of the shear reported above — consistent,
and quoted as a range rather than averaged into one four-figure number.

**And the base plate cross-check now passes on the good edge.** Applying the correction:
the 190 mm edge measures 189.20 mm (**−0.42 %**) while the 130 mm edge measures 125.49 mm
(−3.47 %). A ruler built on 16 machine-detected targets and a ruler built on the plate's
long edge land within half a per cent of each other, which neither could establish alone —
and they jointly convict Metashape's clicked `point 4`, not the plate. The 13×19 cm
assumption in `scripts/measure_base.py` stands.

**What would sharpen it further.** A ruler laid dot-to-dot reads about ±0.5 mm, which on a
40 mm span is ±1.25 % — as large as the correction itself. That does not invalidate the
result, because a printed pitch is a *designed* value and the ruler's job was to say which
round number it is (40, not 45 or 35), which it does decisively. But it can be made
independent of that assumption: **measure the longest straight run of dots on the sheet and
report the span and the number of steps.** Ten steps at 400 mm read to ±0.5 mm is ±0.13 %,
which would pin the scale about ten times harder and would also detect a printer that
scaled the page.

`docs/reference/turntable-board-03072025-N01.json` now carries the pitch, its provenance (who measured it, on what, when)
and the correction factor in its `scale` block.

---

## 9. Tier 2, measured and not built: marker-guided matching

Tier 2 was to feed marker co-visibility to `matches_importer` as a pair list, reusing the
sister pipeline's implementation. Before writing anything, that implementation was read and
its effect on N01's real detections was computed. It should not be run on this material.

**What the sister pipeline actually does.** `lib/target_pairing.py` builds a pair list from
images sharing at least one marker ID, plus a temporal sliding window, and
`bin/run_colmap.py` then uses `matches_importer` **instead of** `exhaustive_matcher`. It
restricts matching; it does not add anything.

**On N01 that restriction removes exactly the links that stop a solve bending.**

| | |
|---|---|
| Frames that see at least one coded target | 72 of 119 (61%) |
| Frames that see none | 47 |
| Pairs kept, min_shared=1, window=3 | 2,568 of 7,021 — **37%** |
| Pairs for a frame that sees no target | 3 to 6, against 118 under exhaustive |
| Of those, pairs to a non-neighbouring frame | **0** |

Those 47 frames become a pure sequential chain. `run_colmap.py`'s own comment on the
exhaustive branch says it is used "for turntable captures (120-170 images). This ensures
cross-ring connections that sequential matching often misses." The code argues against its
own coded-target branch on this data.

**And it is solving a cost problem this data does not have.** Job 29479735 (A04, 163
photographs): feature extraction 5.4 min, exhaustive matching **4.6 min**, mapper 35.2 min.
Cutting 63% of the pairs saves about three minutes of a forty-seven minute reconstruction,
in exchange for taking the long-range constraints away from the weakest frames.

**The additive version is not available in COLMAP 4.1.1.** `feature_importer` is an
image-reader that imports a feature set from disk *instead of* running SIFT — there is no
append. `matches_importer` takes match lists indexed into keypoints that must already
exist. Injecting marker centres therefore means hand-writing the entire feature set outside
COLMAP, or patching the SQLite database after extraction. Neither is a small change, and
both put a hand-built feature table in front of the mapper.

**A finding that goes the other way, and still does not rescue Tier 2.** The board is
currently masked out entirely. `artifacts/markers/maskoverlay_A04_1264.png` shows the SAM 3
object mask following the sherds, clamps, rod and blue base plate and stopping above the
turntable. COLMAP has never seen a board pixel. Since the board rotates *with* the object,
its features would be legitimate — unlike the static backdrop, which is why the mask exists.
So the obvious cheap Tier 2 becomes: widen the mask, and let the ordinary matcher have the
board. Measured before proposing it:

- Each coded target draws about **19 SIFT keypoints** within 40 px. With 12–15 targets
  visible, that is **230–280 of roughly 35,000 keypoints in the frame — under 1%**, in 61%
  of frames, all on one plane at the base and far from any break surface.
- `artifacts/markers/maskboard_A42_8355_view.png` shows why: the disc is plain paper. The
  dense keypoints in that crop are on the blue plate edge, the disc rim and the tape, not
  on the targets.
- Worse, the board carries **repeated identical texture** — white tape strips and evenly
  spaced black rim ticks, each indistinguishable from the next. Feeding a rotationally
  ambiguous pattern to a matcher on a turntable capture is the ingredient of the A03
  failure, not a cure for it.

**Verdict.** Marker-guided matching is worth doing — for captures of thousands of images
where exhaustive matching is genuinely unaffordable, and for boards whose markers dominate
the texture. It is not worth doing for this material: 119 photographs, exhaustive matching
already affordable and already run, markers under 1% of features, and the pair list
subtracting from the frames that can least afford it.

The board's value here is the one Tier 1 already takes: an **absolute record of the
rotation**, used to check the solve rather than to build it. That catches the failure Tier 2
was meant to prevent, and it cannot corrupt a reconstruction, because it never touches one.

**A bug found on the way.** `scripts/build_masks.py` read frames with plain
`cv2.IMREAD_COLOR` under a comment asserting that OpenCV ignores EXIF orientation. It does
not: on the OpenCV in `envs/milo` (5.0.0) that call returns 3712×5568 for a 5568×3712 stored
frame, so the mask would come out rotated a quarter turn — still loadable, silently masking
the wrong region. Now `cv2.IMREAD_COLOR | cv2.IMREAD_IGNORE_ORIENTATION`. The
`reconstruct_group.slurm` size check would have caught it, so nothing shipped wrong; the
comment was written from memory instead of measured, which is the part worth remembering.

---

## 10. The blue base plate: which reading is right, and what it changes for A01–A04

Section 8 found the plate's two declared edges disagreeing by 3.16 % and concluded that
Metashape's clicked `point 4` is misplaced by about 4.5 mm. That conclusion was reached by
*assuming* the plate really is 130 mm on the short edge, which is the thing in question.
Stated honestly, section 8 left two readings open and picked one:

| Reading | Then the plate is | And `measure_base.py` is |
|---|---|---|
| **A.** Point 4 was clicked 4.5 mm off the corner | 190 × 130 mm, as recorded | correct, unchanged |
| **B.** Points 3, 4, 5 are on the corners and the record is wrong | 189.2 × **125.5** mm | wrong by **3.5 %** on every capture it has ever scaled |

These lead to opposite actions, so it is worth settling rather than asserting. It settles
without a ruler, because **the aspect ratio is scale-free and has already been measured
twice, by a completely different route.**

**The evidence.** `scripts/measure_base.py` isolates the plate with SAM 3 and fits a
rectangle to its top face, in COLMAP reconstructions that never touch Metashape. Two trees
from the 17 June 2025 batch:

| | A02 | A03 (bent solve) | A03 (rebuilt correctly) |
|---|---|---|---|
| measured aspect | **1.4465** | 2.341 — refused | **1.4415** |
| edges disagree by | 1.03 % | 46 % | 1.38 % |
| points fitted | 683,581 | — | 666,682 |

Reading A predicts **1.4615**. Reading B predicts **1.5077**. Both trees measure
**1.44**, and — this is the part that decides it — they miss on the ***low*** side, while
reading B is 3.2 % ***high***. The data does not merely fail to support B; it points the
other way. Reading A stands: **the plate is 190 × 130 mm, Metashape's `point 4` is the
thing that is wrong, and `scripts/measure_base.py` needs no change.**

The residual 1.0–1.4 % is a known bias of the fit, not of the plate. `minAreaRect` is fitted
to the outline of a semantic segment that has been grown slightly, which lengthens the short
edge proportionally more than the long one — exactly the direction and roughly the size seen.
Both trees show it, in the same direction, which is what a systematic bias looks like and
what a wrong reference does not.

### What this means for the finished A01–A04 meshes: nothing to apply

The instruction was to make the correction apply to the already-finished meshes. It does
not, and the reason is worth stating plainly rather than quietly skipping.

**They were never scaled through the broken reference.** There are two independent scale
routes in this workspace and they share no arithmetic:

```
N01 (2025-07-03)     board targets  ->  Metashape chunk scale, fitted to TWO clicked
                                        base bars, one of which is 4.5 mm wrong
                                        -> this is the thing that is 1.2-1.4 % too large

A01-A04 (17 June)    blue plate  ->  measure_base.py measures the plate IN THAT
                                     RECONSTRUCTION and multiplies by 190/130 mm
                                     -> no Metashape, no clicked points, no chunk scale
```

`grep` confirms it: no script in the A01–A04 path reads a `.psx`, and
`milo_mm.scale.json` records `"source": "blue base top face 190x130 mm"` for both trees.
A02 was scaled at 377.529 mm per unit, A03 at 373.733. Applying −1.37 % to those would
shrink two meshes that were never inflated.

**There is also no way to measure the correction on them even if one were wanted.** A01–A04
are from 17 June 2025. The marker board first appears in the N01 batch on 3 July. There is
no board in those photographs to read, and the only reference the two batches share is the
blue plate — which is the reference this whole section was called on to adjudicate.

**What the board work does do for A01–A04 is remove a caveat, not change a number.**
Every metric mesh carries this line in its `.scale.json`:

> `"caveat": "precision ~1%; accuracy capped by the nominal 190x130 mm reference"`

That caveat was honest: the 190 × 130 mm came from the conservator's record and nothing had
ever checked it. It has now been checked, by a ruler built on 16 machine-detected targets
that reaches the plate's long edge to within **0.42 %**. The ceiling on A01–A04's accuracy
is therefore about half a per cent, not the unbounded "whatever the record says". On a
100 mm sherd that is **0.4 mm**, and it is the first time that figure has had any evidence
under it.

To be exact about what is and is not established: the board confirms the **190 mm** edge to
0.42 %. It cannot confirm the 130 mm edge, because that is the edge whose clicked endpoint
is misplaced. `measure_base.py` uses both and takes the mean, so about half its reference is
now independently checked and half is not.

### Summary of the corrections, and where each one bites

| Correction | Applies to | Size | Action taken |
|---|---|---|---|
| Board pitch → chunk scale | The **N01 Metashape chunk** only | −1.2 to −1.4 % | recorded in `docs/reference/turntable-board-03072025-N01.json`; apply if any N01 measurement is taken from Metashape |
| Metashape `point 4` misplaced | The N01 `.psx`, in the conservator's hands | ~4.5 mm on one bar | **report to the conservator** — re-clicking that one point and refitting would remove the whole −1.37 % at source |
| Blue plate = 190 × 130 mm | `measure_base.py`, A01–A04 | **none** — confirmed | caveat in `.scale.json` can be tightened from "capped by the record" to "long edge checked to 0.42 %" |


## 11. Wiring it into the pipeline: what the gate now does, and the two gates that could not gate

Tier 1's whole point is that the board becomes a *check the pipeline runs by itself*, not a
report someone remembers to read. `slurm/reconstruct_group.slurm` now branches at the
"turntable check" step:

- **A reference exists for this capture** (`docs/reference/turntable-board-<date>-<tree>.json`,
  derived from `$GROUP`) → the check is **strict**. The board was bolted to the turntable and
  photographed; if the frames are not where it says they were, the job stops before the dense
  stage. Nothing downstream gets built from a bent solve.
- **No reference** (every capture before 3 July 2025, which is most of them) → the old
  camera-arc check runs, and stays **advisory**. It catches a collapsed solve but demonstrably
  not a bent one — A03 passed it — so it prints and does not stop.

Before the strict branch runs, the scanning record is consulted. If the record says this
capture's marker is unusable *and* a reference file exists anyway, the job stops: one of the
two is wrong, and guessing which would be the worst of the three options.

### Exit statuses, and why 3 is not 0

| status | meaning | job |
|---|---|---|
| 0 | the solve agrees with the board | continues |
| 1 | the solve **disagrees** with the board | stops |
| 2 | no board; the inferred check failed | advisory — prints |
| 3 | the check could not be made at all | stops |

A model that has a reference is judged **only** on the reference. The inferred checks are
noisier, and reporting them as failures beside a passing board reading would teach everyone
here to ignore the exit code — which is how a gate stops being a gate.

Status 3 deserves its own row. It means a reference was supplied and could not be applied:
the usual cause is pointing one capture's board at another capture, or renamed frames. That
is not a pass. The check the caller asked for did not happen, and a gate that was asked for
and silently skipped is worse than no gate, because the log says it ran.

### Both gates were broken in the same way, and neither would have shown it

Two things had to be fixed before any of the above was true. They are worth recording
together because they are the same mistake wearing different clothes — **a check that
reports and a check that stops the job are not the same thing, and only one of them is a
gate.**

1. **`check_turntable.py` could not fail.** It was called with `|| true`, and `check()`
   returned nothing but a coverage number. The strict branch above would have printed a full
   page of disagreeing frames and then run the dense stage anyway. Fixed by giving the script
   an exit status (`exit_code_for`), removing the `|| true`, and — this is the part that
   matters — making the **self-test assert the status**, not the frame count. The frame count
   was already correct while the status was 0.
2. **`build_scanning_record.py --check` exited 1 for an environment reason.** It imported
   `openpyxl` at module level; the cluster node where the gate runs has no `openpyxl`. "Please
   pip install openpyxl" and "this capture's marker must not be used" are the same exit code
   to a shell script. Fixed by importing lazily and reading the committed
   `docs/reference/scanning-record.json`, which is what everything downstream already reads —
   `--check` never needed the spreadsheets.

A third, found while wiring: `compare_to_reference()` returned a bare `None` on the
name-mismatch path, into a two-value unpack in the caller. That is a crash, in the exact path
the N01 gate takes. Under `set -e` a crash does stop the job, so it would have failed *safe* —
but with a Python traceback instead of a sentence, for a mistake (wrong reference file) whose
fix is obvious the moment it is named. It is now status 3, and it is one of the self-test's
four cases rather than an assurance.

### Proven, on real data and on synthetic

`python scripts/check_turntable.py --self-test --reference docs/reference/turntable-board-03072025-N01.json`
**PASSES**, with the exit status checked on all four cases: a faithful solve in a different
frame and scale → 0; a solve with six frames rotated 40° → 1; a solve squeezed into a 60° arc
→ 1; a faithful solve judged against the wrong capture's reference → 3. The metric scale is
asserted too, and recovers 1/3.4 to better than 0.01 % on the two cases where a true scale
still exists.

On the cluster, against a real 162-image, 139,950-point COLMAP model: the wrong-reference path
prints *"reference names do not match this model (0 of 119 matched)"* and returns 3, and the
advisory path reads 348.4° of turn and returns 0. Both without a traceback.

### The first real solve: 03072025/N01, job 29527687

Built 24 August 2026 on an A100, 119 photographs, `masks_object`, incremental mapper,
`STAGE=colmap`. **119 of 119 registered, 88,107 sparse points, and the strict gate passed**
— the first time the board has judged a COLMAP reconstruction rather than a synthetic one.

| | |
|---|---|
| frames matched to the reference | 119 of 119 |
| angle vs the board | median 0.003 deg, worst 0.016 |
| position vs the board | median 0.30 mm, worst 0.85 mm |
| the reference's own circle residual | 1.24 mm |
| metric scale from the board | 1 model unit = 0.3938 m, from 119 cameras |

**That agreement is too good to report unchecked**, and the workspace has been burned by a
metric that never moved. Two things were done before believing it.

*Is the needle stuck?* Three pairs of frames a third of a turn apart had their names swapped
in a copy of the real model — the A03 failure exactly, every camera position untouched, six
photographs simply claiming to be somewhere else. The gate named **all six and no others**,
reported 135.9 deg and 2.9 m out, dropped them from the alignment (113 used), and exited 1.
The scale it recovered moved by 5 parts in a million. The measurement has range on this data,
not only on synthetic data.

*Does the picture agree with the number?* `artifacts/markers/n01_solve_vs_board.png`, drawn at
two scales because the overview panel would look identical for a solve 20 mm wrong. Down the
axis: one clean circle of 119 cameras, evenly spaced, with a single compact object at the
centre — not the two objects 35 deg apart that A03 built. The third panel is the residual
itself, per photograph, unbinned: every frame under 0.9 mm, no structure, the whole
distribution below the reference's own 1.24 mm noise floor.

So the honest statement is not "the solve agrees with the board perfectly". It is **no
disagreement is detectable above about a millimetre, which is the finest this reference can
resolve.** For a rig 3.2 m across that is agreement to roughly 3 parts in 10,000.

`build_scanning_record.py --check` was verified on the node with no `openpyxl` present:
`03072025/N01` → 0 (marker OK), `03072025/M04` → 2 (marker unusable), `17062025/A02` → 2,
`nope/X99` → 3.


### The rest of the pipeline: dense cloud, mesh, and millimetres

**Scope of this section: one surface method of the four.** A02, A03 and A04 were each built
with *four independent* surface reconstructions from the same solve — OpenMVS
(`scene_refined_mesh.ply`), COLMAP Delaunay, COLMAP Poisson, and MILo's learnable SDF. What
is described below is the OpenMVS one only. The other three were submitted afterwards
(jobs **29543378** `colmap_mesh.slurm`, **29543431** `milo_prepare.slurm`) and are reported
in the section that follows. Until all four exist, N01 is not comparable to A02–A04 and no
statement here should be read as a property of *the N01 reconstruction* — only of the
OpenMVS surface.

The gate was the point of this work, but a gate is only worth having if the thing it guards
runs. It does. `slurm/dense_from_model.slurm 03072025/N01 sparse/0`, job **29542525**,
**11 min 41 s**:

| | |
|---|---|
| dense cloud | 1,812,107 points from 88,107 sparse |
| mesh | 445,861 vertices / 891,658 faces |
| refined (decimation off) | 446,778 / 893,379 |
| surface masks | 119 of 119, `masks_measure` — sherds and base only, no clamps, rod or dial |

**Ten sherds and one base plate, each appearing exactly once.** That is the check that
matters and it is a picture, not a number: `artifacts/markers/n01_refined_render.png`. The
A03 failure looks like a base plate built twice 35° apart, and this base plate is a single
sharp-cornered rectangle. Fourteen connected components: the plate, ten sherds, and three
specks of 7–23 vertices.

#### extract_sherds.py kept the base plate and threw away ten sherds

Run on this mesh it accepted **2 of 14** components — one of which is the base plate — and
rejected every other real sherd as *too blocky*. Its own docstring predicted this: thinness
is a bounding-box ratio, so **a curved piece of pot wall fills a chunky box** while a flat
tray scores like a perfect sherd. The contact sheet
(`artifacts/markers/n01_contact_sheet.png`) shows it plainly — one green tile is a thin white
sliver, which is the plate seen edge-on.

Naming which of the three this is: **the measurement is wrong, not the method and not the
reference.** The mesh is right; the selector is fitted to nothing. Its thresholds were
deliberately never tuned, because the only mesh available to tune them on was already known
to be faulty. There are now two good meshes to tune them on. Until that is done, the
component list from `render_mesh.py` is the honest inventory and the verdict from
`extract_sherds.py` is not.

#### The plate is a tray with a rim, which resolves a 5 % scale disagreement

Scaling N01 raised a real disagreement that had to be settled before any millimetre figure
was written down. Two rulers:

| Ruler | mm per model unit |
|---|---|
| Marker board, 119 cameras, pitch-corrected | **388.40** |
| Plate long edge ÷ 190 mm | 370.3 |
| Plate short edge ÷ 130 mm | 361.7 |

Nearly 5 % apart — and the plate's two edges disagree with **each other** by 2.4 %, which is
the tell. A ruler that cannot agree with itself is not measuring what it is assumed to be
measuring.

Rendering the plate on its own answered it in seconds (`artifacts/markers/n01_plate.png`):
it is **a shallow tray with a raised rim**, not a flat plate. The face view shows a bright
band of points all the way round the perimeter and the edge-on view shows the lip turned up
at both ends. So the reconstructed outer envelope is the **outside of the rim**, and the
190 × 130 mm figures are not.

A rim adds the same amount to both directions, so it cancels in the **difference** of the two
edges, and 190 − 130 = 60 mm needs no assumption about how wide the rim is:

```
60 mm / (0.51313 - 0.35944 units) = 390.4 mm/unit      (391.8 by a second fit)
```

against the board's **388.40**. The two independent rulers agree to **0.5–0.9 %**. The
implied rim is **≈5 mm per side**, and that same 5 mm reconciles the Metashape project too:
the clicked bar 3→5 solves to 189.20 mm corrected, while the mesh's outer long edge is
199.4 mm — 10.2 mm more, or 5.1 mm per side. The short edge needs 7 mm per side to close,
and the 2 mm difference is the already-known ~4.5 mm misplacement of `point 4` pointing the
same way. Three separate measurements, one explanation.

Treat the board as the ruler and the plate as the check, not the other way round. The
difference-of-edges trick amplifies noise about tenfold — 1 mm of error in the edge
difference moves the scale 1.7 % — so its agreement is a genuine confirmation but a coarse
one.

#### The metric mesh

`scripts/scale_mesh.py` now takes `--board-reference` and `--model` as an alternative to
`--measurement`, applying both corrections that a board factor needs: the model-to-board
similarity scale (reused from `check_turntable.py`, not reimplemented) and the reference's
own `correction_factor`, without which every length is 1.2–1.4 % too large. **A model that
disagrees with its board is refused rather than scaled** — a solve that put frames in the
wrong place has no trustworthy scale either, and the millimetre figure would outlive the
warning.

```
scene_refined_mesh_mm.ply    388.401 mm per model unit
```

Measured off it, and checked against a 100 mm bar drawn into the render
(`artifacts/markers/n01_mm.png`):

| | length | width | depth |
|---|---|---|---|
| blue base tray, rim to rim | 199.4 mm | 139.9 mm | 17.6 mm |
| ten sherds | 42–94 mm (median 72) | 23–64 mm | 14–38 mm |

The third column is the sherd's **curvature depth** — how far it bows out of flat — not its
wall thickness. These meshes are hollow shells photographed from outside, so wall thickness
is not measurable from them at all; that was established when it made a clamp bar read
thinner than any sherd.

**Weight this carries: one object, one capture, no repeat.** N01 is the first capture with a
board on the turntable and the only one built through the gate so far. The gate working here
does not establish that it works on captures with fewer readable targets, and the 0.5–0.9 %
agreement between board and plate is one comparison on one plate.

## Files

| Path | What it is |
|---|---|
| `scripts/detect_markers.py` | The detector and the coverage measurement. |
| `artifacts/markers/contact_03072025_N01_turn{1..5}.png` | One contact sheet per revolution, every station. |
| `artifacts/markers/targets_03072025_N01.json` | Per-frame detections, with turn, station and degrees. |
| `artifacts/markers/nat_0_0_650.png` | A coded target at native resolution. |
| `artifacts/markers/det_8355_final.png` | The disc with every detection drawn. |
| `artifacts/markers/contact_03072025_M04_turn{1..5}.png` | The negative control: 0 of 120 frames readable. |
| `artifacts/markers/m04_card.png` | Why M04's marker is unusable — it is on the table, not the turntable. |
| `artifacts/markers/psx/chunk.xml`, `psx/frame.xml` | The Metashape project metadata: 16 decoded IDs, 971 projections, 2 scale bars, 119 solved poses. |
| `artifacts/markers/psx_8344_turn4.png` | Metashape markers drawn on a photograph - IDs match the printed numbers. |
| `artifacts/markers/psx_8250_turn1_blind.png` | Why turn 1 reads nothing: the camera is level with the table. |
| `artifacts/markers/psx_turn3_why.png` | Turn 2 vs turn 3 at native resolution - the disc collapses to a sliver. |
| `artifacts/markers/psx_full_views.png` | The rig, one frame from each of four revolutions. |
| `artifacts/markers/decode_native.png` | Six targets at native resolution, 8x nearest-neighbour: the arcs are countable. |
| `artifacts/markers/n01_refined_render.png` | The N01 mesh, two views: ten sherds and one base plate, each once. |
| `artifacts/markers/n01_contact_sheet.png` | Every component tiled. Shows `extract_sherds.py` keeping the plate and dropping the sherds. |
| `artifacts/markers/n01_plate.png` | The base plate alone, face on and edge on. The picture that found the rim. |
| `artifacts/markers/n01_mm.png` | The metric mesh with a 100 mm bar drawn in, so the scale is checkable by eye. |
| `scripts/scale_mesh.py` | Now carries `--board-reference`, and refuses a model that disagrees with its board. |
| `scripts/check_turntable.py` | Now carries `--reference` and `--self-test`, and reports metric scale. |
| `scripts/psx_reader.py` | Reads a Metashape project without a licence. Holds the p1/p2 fix. |
| `scripts/board_frame.py` | Builds the board reference: targets, axis, passes, per-frame angles. |
| `scripts/board_render.py` | Four panels at scales differing by 1000x, so each resolves its own claim. |
| `scripts/board_scale.py` | Fits the printed lattice, tests it against the base plate, refuses to guess the pitch. |
| `docs/reference/turntable-board-03072025-N01.json` | The reference itself: 16 targets, axis, 119 frame angles, scale block. **Committed**, unlike the rest of `artifacts/` — a gate whose ruler is not in the repository cannot be re-run by anyone else. |
| `artifacts/markers/reference_N01.png` | The reference drawn: board, axis, five camera circles. |
| `artifacts/markers/lattice_N01.png` | The printed grid with residuals at 40x. The picture that found the shear. |
| `artifacts/markers/crop_A42_8355.png` | The board close up: a Print Markers page, cut to a disc, taped, wrinkled. |
| `artifacts/markers/maskoverlay_A04_1264.png` | The SAM 3 object mask on a frame: it stops above the turntable. |
| `artifacts/markers/maskboard_A42_8355_view.png` | The board with SIFT keypoints drawn: the disc is plain paper. |
