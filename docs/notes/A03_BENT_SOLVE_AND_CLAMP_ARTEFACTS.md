# Tree A03: a bent camera solve, and what masking the clamps costs

Status: **the solve is fixed and verified; the clamp-contact question is open.**
2026-08-17 to 2026-08-20. One tree, A03 (17062025), with A01 and A02 as comparisons.

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
   possible but limited; not creating them is better.

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

### Open, and it matters

- **The break edges have not been checked specifically.** Per-piece vertex counts and
  extents look reassuring, but "the sherd is the same size" is not "the fracture surface
  kept its detail" — and a 6-pixel rim taken off a fracture edge is exactly the geometry the
  matcher consumes. Judging this by a global number would repeat the reprojection-error
  mistake.
- **Erosion costs proportionally more on small sherds**: 2.2% of the largest, 13.4% of the
  smallest, and the smallest lost 2.8 mm of its longest dimension (29.6 → 26.8 mm). A
  size-aware erosion may be needed.
- **The clamp-contact surface was never observed by any method** and cannot be recovered
  (no rescan is possible). It is currently closed over by the reconstruction and not marked
  as interpolated. A per-vertex observed/never-observed flag would let the reassembly
  pipeline exclude it and would state plainly, in the file, which surface was measured. The
  heritage literature is direct about this: *"informed CH curators usually do not accept
  that an algorithm is used to guess portions of a surface."*

---

## 4. MILo: masking starves it

| | training mask | Gaussians | mesh |
|---|---|---|---|
| A01 | none | 116.6 MB | 179.7 MB |
| A02 | none | 95.6 MB | 147.2 MB |
| **A03** | `masks_measure` (4.1% of frame) | **4.2 MB** | **8.8 MB** |

**23× fewer Gaussians**, and a visibly coarser mesh. The mechanism is in our own fork: the
loss replaces everything outside the mask with flat background, so 96% of every frame
becomes trivially easy and gradient-driven densification barely fires.

Retraining with `masks_object` (21.5% of frame — room removed, rig kept) and stripping the
rig afterwards with the silhouette filter. **Train on more, keep less.**

The risk in that plan: a clamp jaw resting against a sherd projects *inside* that sherd's
outline from many angles, so carving may not remove all of it. If so, the answer is to carve
against `masks_measure` while having trained on `masks_object`.

---

## What is where

| | |
|---|---|
| corrected solve | `A03/work_colmap_openmvs/sparse_nosherdrig/0` |
| meshes from it | `dense_fixed/` — and `dense_eroded/` with eroded masks |
| the bent solve, kept for comparison | `sparse/0`, `dense_masked/`, `dense_dial/` |
| metric meshes | `MILo/metric/17062025/A03/` at 373.733 mm per unit |
| masked-training MILo, kept as evidence | `MILo/output/17062025/A03_masksmeasure` |
| dilated masks, kept for comparison | `MILo/masks/17062025/A03_dilated` |
