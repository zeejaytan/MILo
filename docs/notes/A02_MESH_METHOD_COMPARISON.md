# Which reconstruction method should we use for the sherds?

Status: **COMPLETE** (2026-08-18). One capture, A02. Laptop analysis plus two Spartan
jobs. Every claim here is paired with a figure in
`artifacts/A02_metric/verification/a02_plates.html` (13 plates, self-contained, opens
offline). Raw numbers in `artifacts/A02_metric/verification/metrics/`.

---

## The answer

**Use OpenMVS refined — and check the break edges sherd by sherd rather than assuming
them.**

OpenMVS wins on every measure of surface quality, usually by a factor rather than a few
percent. But on one sherd of the seven it smoothed the fracture edge out of existence, and
fracture surfaces are precisely what GARF and TORA match on. That single sherd matters
more than its share of any average, and no summary statistic revealed it.

| Measure (median over 7 sherds) | OpenMVS | MILo | Delaunay | Poisson |
|---|---|---|---|---|
| Noise on a surface known to be flat | **0.186 mm** | 0.485 mm | 0.326 mm | 0.337 mm |
| Loose debris pieces per sherd | **0** | 17 | 40 | 82 |
| Loose debris area per sherd | **0 mm²** | 2.4 mm² | 84 mm² | 533 mm² |
| Genuine interior holes | **0 mm** | 10 mm | 3 mm | **0 mm** |
| Surface scatter at 2 mm | **0.172 mm** | 0.179 mm | 0.250 mm | 0.257 mm |
| Sharp fold ÷ the sherd's own perimeter | **0.3×** | 4.2× | 25.9× | 4.2× |
| Sherd outline vs held-out photographs | 66.3% | 66.0% | 66.7% | 66.0% |

In plain terms: **OpenMVS's error on a surface we know is flat is about the thickness of
two sheets of paper. Poisson leaves roughly a postage stamp's worth of floating debris
around every sherd, in 82 separate pieces. OpenMVS leaves none at all, on all seven.**

The last row is not a tie-break — see *The silhouette test* below.

---

## What was compared

Four reconstructions of the same pottery tree, **A02** (17/06/2025, RBT 22/23 D9.1 Loc
1081 Bag 95, recorded as "Part 2" of a ceramic tray). One loading of the clamp rig, 162
registered photographs, one COLMAP model, so all four share a coordinate frame and load
aligned with no registration step.

| Method | Mesh |
|---|---|
| COLMAP Delaunay | `dense_masked/colmap_delaunay_mesh.ply` |
| COLMAP Poisson (depth 11, trim 12) | `dense_masked/colmap_poisson_mesh.ply` |
| OpenMVS refined | `dense_masked/scene_refined_mesh.ply` |
| MILo (learnable SDF, Gaussian splatting) | `output/17062025/A02/mesh_learnable_sdf.ply` |

Scaled copies in millimetres are in `artifacts/A02_metric/*_mm.ply` at
**377.5292439344579 mm per unit**, from the blue base top face (190 × 130 mm). The
measured aspect came out 1.446 against a true 1.4615, so the scale carries about **1%**.
That is shared by all four, so it shifts absolute figures together and does not affect
agreement between them.

---

## What we did

1. **Established the shared frame** (`stage0_survey.py`). Confirmed all four sit in one
   frame; found the vertical axis is world **x**, with the turntable at x ≈ −342 mm.
   MILo uncropped turned out to be the whole **room** — 3.0 × 8.7 × 10.3 m — so it needs
   cropping before any comparison.

2. **Found the sherds** (`stage1_boxes.py`, `stage1_verify.py`). Local flatness plus
   cluster area proposed 19 candidate plates; merging front and back walls gave 14; and
   **looking at every one** cut that to **seven confirmed sherds and seven rejected clamp
   jaws**. Polished flat metal passes a flatness test exactly as a sherd wall does, so no
   threshold could have separated them. SAM 3's mask record counts 9–14 sherd instances
   per frame, so seven covers most of the tree but not all of it.

3. **Measured each method over identical regions** (`stage2b_measure.py`). The same seven
   boxes for all four, so the comparison is like-for-like even where a box clips a little
   clamp.

4. **Corrected four measurements** after the conservator reviewed the plates
   (`stage5_noisefloor.py`, `stage5_scene_holes.py`) — see *Measurements that pointed the
   wrong way*.

5. **Scored against photographs no mesh was fitted to** (`scripts/silhouette_compare.py`,
   Spartan, GPU). Rendered each mesh from the 21 held-out views and compared outlines
   with SAM 3 masks. Run twice: whole scene, then sherds only.

6. **Measured one sherd as a physical object** (`stage6_sherd_dims.py`). SH6, the largest,
   with the clamp removed by SAM 3 multi-view voting over 41 photographs.

Supporting Spartan work: `undistort_masks.sh` was fixed to resolve the locally built
COLMAP itself (job 29332375 died in two seconds with `colmap: command not found`, reported
misleadingly as a disk-space problem). Masks were then undistorted from the camera's
5568 × 3712 down to the meshes' 3200 × 2133 — object masks in job 29332499, sherds-only in
29352965.

---

## Findings

### Poisson invents surface, directionally

Its bounding box is 843 × 435 × 499 mm against OpenMVS's 694 × 402 × 460. The direction is
what makes this invention rather than recovery: it reaches **113 mm further down** and
**82 mm further out**, but only **36 mm further up**. It balloons into the turntable and
into the thin-data region, not upward where more pot would be. A fuzzy dome under the base
is plainly visible once all four are drawn in one box.

It also prints a **diagonal grid across the sherd walls** — the signature of its octree at
depth 11, an artifact of the algorithm rather than anything on the ceramic.

### Delaunay's surface is faceted, not sharp

A sherd's break runs around its perimeter, so the mesh's sharp geometry should total
roughly **one perimeter**. Delaunay totals **26 perimeters' worth**. Drawing the folds
settles it: in OpenMVS the red traces a single clean line around the broken rim; in
Delaunay it blankets the entire wall. That is triangulation faceting. A reassembly
algorithm fed the Delaunay mesh would be matching on 26 perimeters of fake edges.

### MILo is clean of debris but noisy and gappy

Very little loose material (2.4 mm², 17 pieces) and surface scatter close to OpenMVS at
2 mm. But it is the **noisiest on a surface known to be flat** (0.485 mm), it has the only
genuine interior holes worth counting (10 mm per sherd, rising to 40 mm on SH7), and it
carries a great deal that is not the pot: even cropped to the shared box, only **67.4%** of
its vertices are inside, and the remainder is floor and backdrop.

### OpenMVS is best — with one real failure

Lowest noise, no debris on any of the seven, no genuine interior holes, lowest scatter, and
sharp folds that trace the break and nothing else.

**But on SH5 the fracture edge is gone.** Its fold angles decay to nothing there:
1,932 mm of gentle 15–30° curvature, 178 mm at 30–45°, 22 mm at 45–60°, and **8 mm above
60°**. The open boundary is only 127 mm of a 431 mm perimeter, so the edge is present in
the mesh and has simply been rounded over. Per sherd, OpenMVS gives 196, 141, 167, 36,
**10**, 162 and 95 mm of steep fold — the median of 141 mm looks perfectly healthy and
hides the failure completely.

> **Correction, 2026-09-03.** This paragraph originally continued "Poisson resolved
> 1,298 mm at 60–90° on the same sherd", and that comparison has been withdrawn. It was a
> broken measurement, not a real difference between the methods. Total steep-fold length
> does not distinguish *one continuous edge* from *scattered specks of the same total
> length* — the identical error that let Delaunay's triangulation faceting score as
> "26 perimeters' worth of sharp edges" earlier in this very note.
>
> Chaining the steep fold into connected runs on SH5, and drawing it per-vertex:
>
> | method | fold >60° | of that, in runs >10 mm | longest single run |
> |---|---|---|---|
> | OpenMVS refined | 10 mm | 0 mm (0%) | 2 mm |
> | COLMAP Poisson | 1,777 mm | 108 mm (6%) | 17 mm |
> | COLMAP Delaunay | 11,746 mm | 4,442 mm (38%) | 122 mm |
>
> SH5's perimeter is 431 mm. Poisson's longest unbroken run of steep fold is 17 mm — 4% of
> the way round the sherd — and rendered it is a speckled fringe around the rim plus the
> octree grid, not a crest along the break. **Poisson did not recover SH5's fracture edge.**
> (Delaunay's 38% is its faceting reaching the coherence threshold, not detail either.)
>
> So the conclusion here narrows rather than reverses: OpenMVS's SH5 perimeter is smooth,
> Poisson's is rough, and **no method in this comparison has SH5's fracture edge**. That
> points at the photographs of SH5, not at OpenMVS's smoothing — confirmed by a 2×2 over
> `ReconstructMesh --smooth` and `RefineMesh --regularity-weight` (job 29892523), which
> raised steep fold 14× to a longest connected run of 8 mm and added only surface noise.
> Method in `pottery-photogrammetry/scripts/experiments/measure_fold.py`.
>
> Caveat on the numbers above: the crop box from the original run was not retained, so this
> re-measurement gives 10 mm rather than 8 mm for baseline SH5. Every method above is cropped
> with the identical box, so the comparison between them is unaffected.

### The silhouette test cannot separate these methods

Run on the whole scene it ranked **Poisson first** (83.7% against OpenMVS's 79.5%). The
overlays showed why, and why it should be ignored: every sherd is green in all four, and
the disagreement sits on the **clamp rod** — thin specular metal that OpenMVS, Delaunay and
MILo all miss and Poisson's ballooning fills in. Outline agreement rewards *covering* the
mask, so a method that adds surface misses less and scores higher. This is the same shape
of error as the collapsed turntable solve that won on reprojection error (`docs/lessons.md`).

Re-run on the sherds alone — meshes cropped to the seven boxes, masks sherds-only, and the
comparison restricted to where those boxes project — all four land within **0.75 points**
of each other (66.0–66.7%) against a **6.1-point** spread between views. The ordering is
statistically consistent (Delaunay beats MILo in 20 of 21 paired views) but far too small
to choose on.

**The honest conclusion is that a silhouette confirms all four get sherd shape right and
cannot rank them, because what separates them — noise, debris, fracture edges — is
invisible to an outline.**

---

## SH6, measured as an object

The clamp was removed by SAM 3 multi-view voting (kept where SAM 3 calls it sherd in ≥60%
of the 41 views that see it). The cut falls at the clamp/sherd junction in all four
methods. This is semantic isolation, the pattern `measure_base.py` established here after
three colour-based attempts failed; shape-based isolation has now failed twice in this
project.

| | Max | Width | Wall (median) | Area |
|---|---|---|---|---|
| OpenMVS | 104.8 mm | 58.6 mm | 7.07 mm | 7,691 mm² |
| Delaunay | 105.5 mm | 60.8 mm | 7.22 mm | 8,741 mm² |
| Poisson | 105.3 mm | 60.2 mm | 7.17 mm | 8,047 mm² |
| MILo | 104.8 mm | 59.5 mm | 7.16 mm | 8,001 mm² |

**Maximum dimension 105.1 mm ± 0.7 mm (0.67%). Wall thickness 7.16 mm ± 0.15 mm (2.1%).**

Four independent reconstructions agreeing this closely is the strongest precision statement
available from this data. Thickness is cast like a caliper — from a point on one surface
straight through to the other — and reported as a distribution: median 7.09 mm, with 80.6%
of rays between 5 and 10 mm. The tail beyond 10 mm is rays escaping past the far wall near
a break edge, not thick pottery, which is why the median is quoted and not the mean.

This agrees with the wall thickness of 6–9 mm inferred independently from where local
flatness collapses as the measuring ball widens.

**No rim, and no vessel radius.** Six views of the boundary show irregular fracture the
whole way round, so SH6 is a body sherd and rim diameter does not apply. A sphere fitted to
the wall would have reported "vessel radius 278 mm" confidently; it was rejected because
the sherd departs from a flat plane by only 1.5–1.8 mm and a curved fit beats a plane by
just 1.2–1.6× where real curvature gives well over 2×. MILo's cylinder fit returned a
radius of **128 metres**, which is what an ill-conditioned fit looks like when allowed to
print a number anyway. This is consistent with the record calling A02 a **ceramic tray** —
a shallow form should resist a vessel-radius fit.

---

## What these numbers can and cannot bear

**This is a genuine difference between the methods** — not a broken measurement and not a
wrong reference answer — but only after six of the measurements built for it were caught
pointing the wrong way.

**No ground truth exists for these sherds.** Nothing here is scored against a correct
answer, because there is none. Every figure is either absolute (debris, holes, noise on
known-flat geometry) or a stated disagreement. The only accuracy available comes from the
one known object in the scene, and absolute sizes are good to about ±1%.

**Weight: one pottery tree, one capture, seven sherds of roughly ten, one run per method.**
The ordering holds across all seven and the margins are large, so this is a strong lead —
not a general result about the four methods.

---

## Measurements that pointed the wrong way

The most transferable part of this exercise. Each was plausible, each favoured the wrong
method or the wrong magnitude, and **none was caught by a number** — they were caught by
drawing the thing, or by anchoring it to something physical. Numbers 4 to 6 were found
because the conservator looked at the plates and asked why MILo's patch was a different
shape from everyone else's.

1. **Base-plate noise floor, 1.63 mm.** A plane fitted through a height band holding three
   surfaces at different heights. The base is *tapered* and its known 190 × 130 mm
   rectangle is only the top face.
2. **Sharp-edge count.** Rated Delaunay ~100× "sharper" than OpenMVS, which on the
   fracture-fidelity criterion would have named the noisiest method the winner. Chaining
   the edges did not fix it either — faceting forms one connected network and chained into
   a single 424 mm "feature" on a 140 mm sherd. Fixed by anchoring to each sherd's own
   perimeter and rendering the folds.
3. **Silhouette agreement, whole scene.** Ranked the ballooning mesh first, because
   covering the mask is rewarded and the mask is mostly clamp rig.
4. **Noise floor, per-method patch.** RANSAC chose a different surface for each method, and
   the 0.8 mm inlier band discarded the noisiest points *before* measuring noise. **A
   selection rule must never be the same quantity as the measurement.** MILo was
   understated by nearly half: 0.255 → 0.485 mm.
5. **Hole boundary.** About 95% of it was the crop box cutting the mesh, not holes.
   OpenMVS's "60 mm" is really 0 mm.
6. **Scene comparison.** Showed MILo uncropped — a whole room beside three meshes of a rig.

Two were caught by guards rather than by eye, which is the argument for writing the guard
into the script: MILo's first silhouette score of 28% was measuring the room, and the
sphere fit that would have invented a 278 mm vessel was rejected by its own residual test.

One measurement was tested and **survived**: surface roughness does conflate real curvature
with noise (scatter grows 2.4–2.9× between a 2 mm and a 4 mm ball, where pure noise gives
1× and pure curvature 4×), but the ranking is identical at both radii, so the comparison
holds even though the absolute values are inflated.

---

## What to do next

1. **Calipers on SH6.** Predicted wall **7.16 mm**, maximum dimension **105.1 mm**. One
   reading converts the entire sherd-scale half of this from precision into accuracy. It is
   the highest-value measurement available and it is not a computing task.
2. **Check break edges per sherd** before feeding OpenMVS meshes to GARF or TORA. SH5 shows
   the failure is real and invisible to averages.
3. **Repeat on a second tree** before treating the ranking as general.
4. **If fracture fidelity ever becomes the binding constraint, re-photograph — do not
   re-tune.** OpenMVS's smoothing was the obvious suspect and has been tested and cleared
   (job 29892523, see the correction above): loosening both smoothing knobs adds noise, not
   edges. No method here resolves SH5's break, which makes it a capture problem — closer
   range, or raking light across the fracture face.

---

## Files

- Report, 13 plates: `artifacts/A02_metric/verification/a02_plates.html`
- Numbers: `artifacts/A02_metric/verification/metrics/`
- Per-sherd meshes for hand-checking in CloudCompare:
  `artifacts/A02_metric/verification/crops/` (in **millimetres**, so *not* in the cameras'
  frame — do not render these against the photographs)
- SH6 with the clamp removed: `artifacts/A02_metric/verification/sherd_only/`
- Analysis scripts, in run order: `artifacts/A02_metric/verification/scripts/`
- Committed tooling: `scripts/silhouette_compare.py`, `scripts/run_silhouette_A02.sh`,
  `scripts/run_silhouette_A02_sherds.sh`, `scripts/A02_sherd_boxes.json`,
  `scripts/undistort_masks.sh`

`artifacts/` is gitignored, so the figures and meshes above are local only; this note and
the committed tooling are the durable record.
