# Tree A03: a bent camera solve, and what masking the clamps costs

Status: **the MILo retrain is done and the starvation claim did not survive it; the solve is fixed and verified; 6-pixel mask shrink is at the limit on fracture ridges; clamp-contact surface is still unobserved.**
2026-08-17 to 2026-08-21. One tree, A03 (17062025), with A01 and A02 as comparisons.

---

## The short version

Three separate things went wrong, and for most of a day I treated them as one.

1. **A03's camera solve was bent** — photographs shot one turntable click apart were placed
   up to a third of a turn from each other. Every number said the capture was *better* than
   the tree that was correct. The blue base plate was consequently built **twice**, at an
   angle, and every mesh faithfully reproduced it.
2. **The apparent size difference between A02's and A03's base plate was not real.** It was
   measured off the doubled board. Once the solve was fixed the two agree to **1%**.
3. **Masking the clamps leaves spikes on the sherds**, because a pixel on the object's
   outline straddles sherd and clamp and returns a wrong depth. Removing them afterwards is
   possible but limited; not creating them is better. Shrinking the surface masks by 6
   pixels stops the spikes from forming. On the photographs that shrink is already on the
   fracture ridges — **0.6–0.9 mm**, not a safety margin. Do not shrink further.

---

## 1. The bent solve

### What the numbers said

A03 looked like the better capture on every measure available:

| | A02 (correct) | A03 (bent) |
|---|---|---|
| photographs registered | 162 / 162 | 164 / 164 |
| features per image | 17,716 | **24,165** |
| median inliers per verified pair | 175 | **247** |
| inliers between consecutive frames | 2,889 | **3,778** |
| consecutive pairs with **zero** inliers | **31** | 0 |
| mean reprojection error | 0.841 px | **0.809 px** |
| camera arc | 348.4° | 321.1° — still past the 270° gate |

More features, more matches, better chaining, better reprojection error. The camera-arc
gate passed it. Nothing objected.

### What was actually true

Frames shot one turntable step apart — about 11° — had been placed as much as **138°**
apart. Sixteen consecutive pairs exceeded 30°; A02 had **one**, and that one was the
expected restart between camera passes.

The solve was **bent**, not collapsed. A collapse piles the cameras into a narrow arc and
the coverage gate catches it. A bend keeps the coverage and scrambles the order, and
coverage cannot see it.

### What caught it

`scripts/camera_arc_detail.py`, run as a comparison against A02. It groups frames by
filename prefix — one prefix is one pass of the turntable at one camera height — and
measures the angular step between consecutive frames within a pass.

That check is now part of the gate (`check_turntable.py`), so it runs on every tree.

### Why it happened

The matching was dominated by the **rig**, which is a repetitive structure: a row of
near-identical clamps along a rod, plus a graduated dial.

| inliers landing on | A02 | A03 |
|---|---|---|
| sherds | **48%** | 37% |
| rig + dial + base | 52% | **63%** |

For the two frames displaced from *both* neighbours it was **70–76%** on the rig.

Repeated structure is the one thing geometric verification does not catch, because the
wrong matches are *mutually consistent*: clamp *n* matched to clamp *n+1* all along the rod
produces a large set of correspondences that agree with each other and with a wrong
relative pose. RANSAC confirms them. The inlier count rises, the reprojection error falls,
and the rotation is wrong by roughly one repeat of the pattern.

A03's sherds cover **2.2%** of the frame against A02's 5.2% — less than half the
distinctive geometry to outvote the repeats.

### The fix

Re-solve using `masks_measure` (sherds + base only), so the repetitive rig is never matched.

| | before | after |
|---|---|---|
| camera arc | 321.1°, 39° gap | **349.0°, 11° gap** |
| out-of-order frames | **16** | **0** |
| mean track length | 5.44 | **6.96** |
| mean reprojection error | 0.809 px | **0.768 px** |
| features per image | 24,165 | 5,463 |
| mapper runtime | **157 min** | **4 min** |

A fifth of the features and a third of the 3D points, but tracks **28% longer** and a lower
reprojection error. The 70,000 points it lost were the repeats: many, mutually agreeing,
and wrong.

**The 157 → 4 minute collapse was the honest early warning and nothing was watching it.**
The old mapper spent two and a half hours fighting contradictory evidence.

### Caveats

- The fix discards **77% of the features**. It worked here because A03's base supplied
  enough structure. A tree with smaller or fewer sherds may not survive it.
- The finer instruments were not needed but remain the better long-term answer, because
  they remove the *bad* matches rather than all rig matches: `--SiftMatching.max_ratio`
  (currently at its 0.8 default) and
  [cvg/sfm-disambiguation-colmap](https://github.com/cvg/sfm-disambiguation-colmap), which
  implements Yan (CVPR 2017), Cui (ICCV 2015) and Kataria (3DV 2020) and filters matches
  before the mapper. Its own README warns that no method works across datasets with one set
  of hyperparameters.
- **A01 also fails the frame-order check** — 6 out-of-order pairs, concentrated in
  `A11_0704–0708`. Its solve was made before masking existed, so the cause is more likely
  the static backdrop than the rig. A01 is the baseline the cross-method comparison rests
  on, so this needs settling.

---

## 2. The base plate: a measurement problem that was really a reconstruction problem

The base measurement refused on A03: aspect **2.341** against a true 1.462, the two edges
disagreeing by **46%**. Refusing was correct — a scale 46% wrong would have corrupted every
measurement from all four meshes with nothing downstream to reveal it.

But the reading "the measurement is broken" was wrong. **The reconstruction was broken**,
and those are opposite findings leading to opposite actions.

Once the solve was fixed:

| | A02 | A03 (bent) | A03 (fixed) |
|---|---|---|---|
| aspect ratio | 1.4465 | 2.341 | **1.441** |
| edge disagreement | 1.0% | 46.3% | **1.4%** |
| mm per unit | 377.53 | rejected | **373.73** |

**The two trees' boards agree to 1%.** They are the same physical object at the same size;
the apparent difference was arbitrary units from a different camera distance, which is
exactly what the metric step exists to remove.

`measure_base.py` now measures the plate in **both** the sparse and dense clouds and reports
a gap above 3% as a fault in the reconstruction, naming which half disagrees. On A03 that
would have pointed at the cause on day one instead of reporting a broken ruler.

### One correction it taught us

The first version preferred the *sparse* figure when both passed, reasoning that
multi-view-verified points are more trustworthy. That is true for **where** something is and
false for **how big a low-texture flat thing is**: a featureless plate yields features only
at its rim, so sparse fits a rectangle to an *outline* — 8,467 points against 666,682 in
dense. The tie-break now takes whichever fit's own two edges agree best.

---

## 3. Masking the clamps: what it costs

### The spikes

Masking the clamps puts a hard depth discontinuity at the sherd's edge, which is the least
constrained place for stereo matching. A pixel **inside** the sherd mask given a wrong depth
lands in 3D beside the sherd — the classic flying-pixel artefact.

Measured on one protrusion: **95%** of its vertices never project inside the kept mask in
any view, yet **97.7%** have a dense point within 3 mm. So the dense stage really produced
them; they are not a meshing artefact, and no "remove unsupported geometry" filter finds
them.

### Carving them off, and where that stops working

`scripts/silhouette_filter.py` — visual-hull carving (Laurentini 1994) used as cleanup. A
point belonging to the object must project inside its outline; one that falls outside view
after view cannot be part of it.

It removes the spikes. It **cannot** remove the stub left where the spike met the sherd,
because that lies *inside* the visual hull, where the method is blind by construction.

**And raising the threshold is not the answer.** Colouring a carved sherd by silhouette
support shows the marginal 0.60–0.90 band covers not only the stub but the **entire break
edge** — a thin, steeply-angled surface that sits near the silhouette in most views.
Carving harder eats the fracture surfaces, which are what the reassembly models consume.

### Why the stub matters more than it looks

The reassembly models are trained on perfectly formed, synthetically fractured sherds. A
stub is a shape they have never seen, and the clamps grip the sherds **at their edges**, so
the artefact sits on or beside the fracture surface — the one surface the model reads.

That establishes an asymmetry for this project:

> **Added geometry is worse than missing geometry.** Missing surface only weakens a match.
> Added surface creates false ones, and can physically block a sherd from seating.

### The fix: grow for solving, shrink for building

`sam3_masks.py` used to dilate **every** mask by 8 px. That is right for matching — a
feature on the outline is real and helps solve the cameras. It is exactly wrong for stereo,
where the same pixel straddles object and clamp.

Now `masks_object` is dilated 8 px and every surface set is **eroded 6 px**.

| against the carved mesh (both spike-free) | |
|---|---|
| vertices lost | **−4.7%** overall, 2.2–13.4% per sherd |
| longest dimension change | **≤0.3 mm on ten of eleven pieces** |
| spikes remaining | **none** — they never form |

Erosion removes the spikes **at source**, so carving becomes a safety net rather than a
required step. That takes a destructive operation out of the normal path.

It also closes the sherds. Measured 2026-08-20 on the eleven `eroded_sherd_*.ply`: **ten of
eleven are watertight and genus 0 with no open boundary at all**, the eleventh being the
192 × 226 mm base plate rather than a sherd. The carved route left all three of its sherds
open, with eleven openings between them. Erosion also cleared a defect carving never
addressed — `sherd_2.ply` was watertight but **genus 2**, carrying two tunnels straight
through it, and after carving had a pinch vertex besides; `eroded_sherd_2` is a clean
genus-0 shell. Both were artefacts of building against dilated masks and then cutting.

The catch is in the next two sections. Carving was honest and ugly: it left a hole where the
data stopped, and anyone opening the mesh could see it. Erosion is tidy and silent — the
mesher closes smoothly over the unobserved patch and the result looks identical to measured
pottery. Better route, but the marker is gone while the missing data is not. And the
reassuring size numbers did not ask whether the **break** survived.

### How far shrinking actually goes (2026-08-20)

Vertex counts and overall size said the sherds survived a 6-pixel shrink: **−4.7%** of
vertices overall, 2.2–13.4% per sherd, longest dimension **≤0.3 mm on ten of eleven
pieces**, 2.8 mm lost on the smallest (29.6 → 26.8 mm). Those numbers cannot speak for the
ridges: a 6-pixel rim taken off a fracture edge is exactly the geometry a reassembly matcher
reads. This test looks at the photographs, at a scale where 6 pixels are obvious.

Design: `2026-08-20-erosion-fracture-overlay-design.md`. Script:
`scripts/erode_fracture_overlay.py`. Unshrunk SAM 3 run: job **29448323**, written to
`masks/17062025/A03_erode0`. Production `masks/17062025/A03` was not touched. Outlines at
0 / 2 / 4 / 6 / 8 / 12 pixels, nearest-neighbour ×4. Millimetres from the corrected
`sparse_nosherdrig` cameras and 373.733 mm per unit.

Verdict, written before looking:

| where the outline sits | call |
|---|---|
| still on the clamp | that amount is not enough *there* |
| on the outer wall, short of the break ridges | usable |
| across the break face, ridges inside the discarded rim | gone too far *there* |

**What the pictures say.** Six pixels is already on the fracture, not a safety margin
around it. On these crops it is **0.60–0.86 mm**, not the “~1 mm” first guessed. If
those ridge pixels are discarded in the photograph they cannot appear in the mesh.

| crop | photograph | what it is | 6 px in mm | call |
|---|---|---|---|---|
| `large_break.png` | A35_1240 @3027,1870 | large sherd, break facing the camera | **0.60** | 0–2 follow the jagged ridge; 4 starts rounding the finest peaks; **6 (current) bridges small crevices**; 8–12 are a smoothed cartoon |
| `small_piece.png` | A34_1222 @1729,2190 | complete piece ~30 mm | **0.74** | same pattern; 12 px (1.5 mm) eats the break from every side |
| `pin_clamp.png` | A32_1140 @2634,1481 | outline next to a clamp pin | **0.86** | SAM 3’s *unshrunk* line already stops at the pottery; 6 px then eats pottery, not clamp |
| `small_prong.png` | A31_1115 @3916,3222 | another ~30 mm piece, clamp prongs in frame | **0.75** | same millimetre bite as `small_piece` |
| `large_clamp.png` | A35_1239 @2775,2327 | left edge of the large sherd | **0.61** | same millimetre bite as `large_break`; clamp jaws less clear than `pin_clamp` |

Discarded: `small_break.png` (A31_1102, 1667 px blob). It is a sliver beside a blue knob,
not a complete sherd. Smallest-blob-by-area is the wrong way to pick a small *piece*.

Pictures: `artifacts/A03_metric/erode_overlay/` (laptop) and
`MILo/output/17062025/A03_erode_overlay/overlays/` (Spartan).

Applied after looking: 0–2 px usable; 4 px borderline (major shape kept, finest ridges
going); **6 px is the last amount that still resembles the break**; 8 and 12 have gone too
far. Do not raise the default. If it changes, try 4, not 8.

This is a photograph-outline result, not a rebuilt mesh. Whether stereo then smooths what
remains was not asked here.

**Which of the three this is.** The method is taking fracture-ridge pixels. The size
numbers were the wrong instrument, not evidence that the sherds were unharmed.

**Weight.** One tree, four crops kept. A lead, not a rule for every capture.

**What it means for the work.** Keep 6 as a ceiling. Size-aware shrinking is still
plausible — 0.74 mm is a larger fraction of a 30 mm sherd than 0.60 mm is of a large one —
but the millimetre bite itself is similar; the pixel count is not the thing that changes.
The remaining argument for shrinking at all is the mixed-pixel stereo band (a few pixels),
not “get off the clamp”. That also argues for 4 rather than 6, untested on a rebuilt mesh.

### Still open

- **The clamp-contact surface was never observed by any method** and cannot be recovered
  (no rescan is possible). It is currently closed over by the reconstruction and not marked
  as interpolated. A per-vertex observed/never-observed flag would let the reassembly
  pipeline exclude it and would state plainly, in the file, which surface was measured. The
  heritage literature is direct about this: *"informed CH curators usually do not accept
  that an algorithm is used to guess portions of a surface."* — source not recorded; find it
  or drop the quote before this feeds a chapter.

  Designed out in `2026-08-20-visibility-and-hole-fill-design.md`, as a per-vertex **count**
  of observing views rather than a flag: photogrammetry cannot place a point it saw once, so
  a yes/no would stamp thinly-seen surface as measured. Now the only thing being built —
  erosion having removed the holes that the rest of that note was originally about.
- **A rebuilt mesh at 4 pixels** — the photograph test says 4 is the next number to try,
  not 8. That is a dense-stereo job on the existing corrected cameras, not a new solve. Not
  done.


---

## 4. MILo: the "starvation" was mostly a counting error

### What I claimed

| | training mask | Gaussians | mesh |
|---|---|---|---|
| A01 | none | 377,425 | 4.49 M verts |
| A02 | none | 309,391 | 3.68 M verts |
| **A03** | `masks_measure` (4.1% of frame) | **13,586** | **0.22 M verts** |

I read that as **23× fewer Gaussians** caused by masked training starving the densifier: the
loss replaces everything outside the mask with flat background, 96% of the frame becomes
trivially easy, and gradient-driven densification barely fires. The mechanism is real and is
in our own fork. The size of the effect **on the sherds** was not.

### What the retrain actually showed

Job **29434692**, `masks_object` (23.9% of frame — room removed, rig kept), same corrected
solve, 6 h 01 m on one A100. Gaussians went 13,586 → **93,234**, a 6.9× rise, and the
23× gap to A02 all but closed once you allow for coverage:

| training mask coverage | Gaussians | Gaussians per unit coverage |
|---|---|---|
| 4.1% (`masks_measure`) | 13,586 | 331k |
| 23.9% (`masks_object`) | 93,234 | 390k |
| 100% (A02, unmasked) | 309,391 | 309k |

**Gaussian count is very nearly proportional to how much of the frame is being modelled.**
So the totals were never a statement about sherd detail; they were a statement about how much
room was in the picture. Comparing A03's total against A02's compared a masked object with an
entire studio.

### The measurement that should have been made first

Carve both A03 meshes down to the same object with the same masks, and measure the spacing
between neighbouring vertices **on a sherd**, in millimetres:

| | verts after carving | median vertex spacing on sherds |
|---|---|---|
| MILo, `masks_measure` (4%) | 186,162 | **0.58 mm** |
| MILo, `masks_object` (24%) | 246,650 | **0.53 mm** |
| Photogrammetry, `dense_eroded` | 315,358 | **0.45 mm** |

A **6.9× rise in Gaussians bought about 10% finer sampling on the sherds** — 0.58 mm to
0.53 mm. Almost all the new capacity went to the rig and the room, which is where the extra
mask area was. Rendered side by side the two meshes are hard to tell apart; see
`artifacts/milo_retrain/`.

### And A03 was never coarser than A02

Comparing like with like — both whole-scene MILo meshes, before any carving:

| | verts | median edge |
|---|---|---|
| A02, unmasked | 3,675,831 | 0.713 mm |
| A03, `masks_object` | 1,395,626 | **0.584 mm** |
| A03, `masks_measure` | 219,114 | 0.655 mm |

A03 is **finer** than A02 scene-wide. A02's much larger vertex count is entirely the room.

### What this does and does not settle

Vertex spacing is the **sampling rate**, not the amount of detail. A smooth blob sampled every
0.5 mm is still a smooth blob. So this rules out the explanation "the mesh is too coarse to
carry the detail" and does **not** establish that MILo's sherd surfaces carry as much real
detail as the photogrammetry ones. That needs a detail measure — mesh-to-mesh distance
against `dense_eroded`, and raking-light renders of the same fracture face at matched camera
and scale — which has not been run.

**Train on more, keep less** still looks right, and it is now the cheaper option too (the wide
mask is what the solving mask already is). But it should be adopted because carving works, not
because of a densification gain that turns out to be about a tenth of what the totals implied.

---

## What is where

| | |
|---|---|
| corrected solve | `A03/work_colmap_openmvs/sparse_nosherdrig/0` |
| meshes from it | `dense_fixed/` — and `dense_eroded/` with eroded masks |
| the bent solve, kept for comparison | `sparse/0`, `dense_masked/`, `dense_dial/` |
| metric meshes | `MILo/metric/17062025/A03/` at 373.733 mm per unit |
| masked-training MILo, kept as evidence | `MILo/output/17062025/A03_masksmeasure` |
| unshrunk masks (fracture overlay test) | `MILo/masks/17062025/A03_erode0` |
| fracture-outline pictures | `MILo/output/17062025/A03_erode_overlay/overlays/` (Spartan); fetched `artifacts/A03_metric/erode_overlay/` |
| dilated masks, kept for comparison | `MILo/masks/17062025/A03_dilated` |
