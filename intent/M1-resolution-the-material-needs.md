# M1 — Can either route reach the resolution a break face needs?

**Status:** **answered for the production route, one box from closed.** COLMAP → OpenMVS
meets the stated ~1 mm bar with margin (verdict 2026-09-06, below); MILo tiling is STOPPED.
Open only on the eye check — a ridge-resolving render — and on the 3DGS exploratory track,
which continues under a screening gate rather than as a blocker
**Blocked by:** none. The second box was blocked on [M3](M3-is-the-mesh-at-true-scale.md)
— `compare_meshes.py` could report a millimetre figure that was not in millimetres, and
"the same ruler" is the whole point. **Lifted 2026-09-04**: the script now refuses a mesh
that cannot state its units, and A02 and A03 both carry a scale sidecar, so the OpenMVS
comparison can be run on the same ruler

## Why it matters

A break face is the surface a reassembly model reads. If the mesh smooths it below the
scale of its ridges, every downstream result is about a smoothed object, and the model
will be blamed for something the scanner did. This is failure mode 2 — **the measurement
was broken** — and it is the one that has already faked a finding here once.

**The bar is ~1 mm of break-face relief**, argued from grain sizes measured in the
photographs (~0.7–1.2 mm, 2026-09-06) and concurred by the conservator the same day. That is
the number that matters, and it is the one to compare routes against.

Two other figures appear in this file and neither is the bar. **0.21 mm** is roughly what the
photographs could in principle support — a ceiling, not a requirement; earlier wording here
described a "fourfold shortfall" against it, which measured MILo against the wrong target.
**0.822 mm** was MILo's finest voxel, which is beside the point once the depth feeding it is
known to wobble 4.1 mm. Read the Gate below, not either of those numbers.

## What is already known

- The authors' DTU extraction route is closed on quality grounds (2026-09-01).
- First ridge-scale lead (2026-09-06): break-face brightness relief correlates over
  3–5 px ≈ 0.36–0.60 mm (~0.7–1.2 mm grains), 6 native crops, 1 capture — albedo and
  shading conflated, scale ±20%. Conservator concurred 2026-09-06: the working
  requirement is ~1 mm relief. See `docs/notes/2026-09-06-breakface-ridge-scale.md`.
- The 32,768-block cliff is **per extraction call**, so per-sherd tiling should reach about
  **0.45 mm** — better, still not 0.21 mm.
- Ticket-level (2026-09-06): `resolution-gates/02` is answered by job 30133070 (see
  box 1); `resolution-gates/03`'s compare refused on a content mismatch (MILo mesh
  spans ~1 m of surroundings, OpenMVS a tray crop — same factor, different
  content), and the same-ruler baseline now proceeds under
  `alt-extractors/01` via a common-box crop, not a blind resubmit.
- Load-bearing for all A03 cross-route work (2026-09-06): `dense_fixed` and
  `dense_masked` are different reconstructions, not one frame (camera-pair unit
  ratios spread 0.29–1.11; similarity fit leaves 2.5 m residual on a 1.4 m
  ring). An OpenMVS mesh from the mask frame scaled with the MILo factor is
  wrong-scaled — one such file was made and deleted. The valid pair is the
  fixed-frame refined mesh plus the MILo mesh cropped to its box (98.8% kept).
- Sherd-only outlines on A03 (2026-09-06, job 30158911, 21 held-out views):
  OpenMVS 42.2% vs MILo 8.6% — direction honest per overlays (OpenMVS green on
  sherds with overfill fringes; MILo mostly rig steel). Below A02's 66%;
  flat-noise half still open.

## Two tracks, and which one carries the pipeline

Conservator, 2026-09-18: **COLMAP → OpenMVS is the golden standard and the safe choice.
3DGS is actively explored, as the area most likely to advance on speed, precision and
resource cost.** That is the standing position and this question is organised around it.

**The posture is sound.** It is not a hedge: the production route is settled on measured
evidence, and the exploratory track is aimed at the part of the field that is actually
moving. One qualification makes it cheap rather than open-ended.

**Five 3DGS-family routes have been tried here and none has replaced OpenMVS — but they did
not fail for one reason, and the difference matters:**

| Route | Outcome | Why it failed |
|---|---|---|
| MILo tiling ([M1](M1-resolution-the-material-needs.md) gate) | STOPPED | **depth disagreement** — 4.1 mm median-of-medians across 15 view pairs, against a ~1 mm bar |
| 2DGS ([M6](M6-does-2dgs-reach-break-face-resolution.md)) | NO | **depth disagreement** — own depths differ across adjacent views by 0.28–0.66 mm median, p90 11–36 mm; 13.2% of surface within 1 mm of OpenMVS |
| Rig-Gaussian pruning ([M4](M4-can-rig-gaussians-be-pruned-after-training.md)), masked training ([M5](M5-can-masked-training-exclude-rig.md)) | NO | density collapse, not resolution |
| VGGT + InstantSplat++ ([M7](M7-toposurfel-vggt-rig-separation.md)) | NO | poses collapse, BA refuses — never reached a depth map to judge |
| PGSR ([M8](M8-does-pgsr-replace-milo.md)) | NO as mesh route | regularisation catch-22, 0.75 mm grid, OOM ceiling — also never judged on depth |
| **SAGA** ([M7](M7-toposurfel-vggt-rig-separation.md)) | **EARNS** | outlines 73.7%, zero steel, full density on one capture. **Close-ups and a second capture owed.** This is the live lead in this direction and it is currently unfollowed |

**Of the routes that got far enough to be judged, every one failed on the same thing:
cross-view depth consistency.** Gaussians are view-dependent; on ceramic under rig lighting
the depth each view implies disagrees with its neighbours by more than the feature being
measured, so finer meshing samples the disagreement instead of the relief.

**That is exactly what the field is now working on**, which is the evidence for the
conservator's instinct rather than against it. The 2025–26 line of work is explicitly aimed
at multi-view geometric inconsistency in 3DGS: Geo-3DGS (multi-view geometry consistency),
multi-view normal-and-distance guidance, *Revisiting Photometric Ambiguity for Accurate
Gaussian-Splatting Surface Reconstruction* (arXiv:2605.12494 — photometric ambiguity is
directly relevant to burnished or glazed ceramic under fixed rig lighting), and SparseSurf
(AAAI 2026). The blocker here is the blocker the field has named.

### The screening gate for any new 3DGS route

**Measure cross-view depth agreement in millimetres before building any mesh from it.**

- It is about a day's work and it needs no mesh, no comparison and no baseline.
- It would have correctly predicted **both** routes that got far enough to be judged.
- A method that cannot agree with itself to ~1 mm across adjacent views cannot deliver ~1 mm
  of relief, whatever its renders look like — and its renders will look good, which is the
  trap this workspace has fallen into four times.
- A route that clears the gate earns a full comparison against OpenMVS on the same ruler.
  A route that does not is recorded and dropped, without a training run.

**This track does not block the pipeline.** [U16](../../intent/U16-shortest-route-to-one-reassembled-pot.md)
runs on OpenMVS. If a 3DGS route later clears the gate and beats OpenMVS, it replaces stage 1
without changing anything downstream — which is the whole point of the handoff contract U16
asks for.

## Done when

- [x] **Cross-view depth disagreement measured in millimetres** on at least one
      capture (2026-09-06, A03, job 30133070: median-of-medians **4.1 mm** over
      15 view pairs, worst pair 6.0 mm; p90/max carry a metre-scale tail —
      floater and rig pixels in the unprojection, not surface noise. One
      capture, first successful run after two script bugs; reading it against
      the bar is the gate's job, not this box's)
- [x] **What OpenMVS achieves**: via the A02 result by capture substitution
      (2026-09-06): flat-surface wobble 0.186 mm on same-rig-class material —
      under the ~1 mm bar with margin — plus A03 sherd-only outlines at 42% vs
      MILo 8.6% pointing the same way (overfill fringes explain the gap to
      A02's 66%). Substitution caveats travel too: different capture and
      coarser fabric, and A02's SH5 warning that one smoothed edge hid in an
      average. A03 flat-noise and per-sherd millimetres stay struck; they
      return only if a future outline disagrees with this direction. Scale stays
      established by the tool, not by hand: `compare_meshes.py` refuses a mesh
      without a sidecar rather than measuring it — see
      [M3](M3-is-the-mesh-at-true-scale.md).
- [x] A stated requirement in millimetres: **~1 mm break-face relief** (grains
      ~0.7–1.2 mm from 2026-09-06 photo measurement; conservator concurred 2026-09-06).
      Argued from visible relief in the photographs, not from what any tool delivers
- [ ] Meshes rendered at a view that resolves ridges — a whole-sherd view looks fine at
      every resolution and has already misled here four times running. **This is the one box
      standing between the production route and closed**, and until it is ticked the verdict
      below is *met on measurement, not witnessed by eye*
- [ ] **SAGA's owed follow-up run** — close-ups plus a second capture ([M7](M7-toposurfel-vggt-rig-separation.md)).
      It is the only 3DGS-family route here that has earned anything, and it has been left
      where it stood
- [ ] **The screening gate written as a script**, not as the paragraph above: cross-view
      depth agreement in mm, run on one capture, refusing to report a figure it cannot state
      units for. Prefer a gate over a paragraph — three prose rules failed to stop the GLOMAP
      error and one thirty-line script made it impossible to repeat

## Gate

If OpenMVS already meets the stated requirement, MILo tiling is **not worth doing for
this**, whatever its merits otherwise. Write that down and stop, rather than lifting a
ceiling nothing is pressing against.

**Verdict recorded 2026-09-06:** (a) MILo tiling is STOPPED — the depth going in
wobbles 4.1 mm against a ~1 mm bar, so finer grids sample noise, not relief;
(b) OpenMVS meets the bar — 0.186 mm wobble on A02 plus the A03 outline
direction; (c) 2DGS and TopoSurfel/VGGT go to their own one-capture trials,
judged by their own depth checks against these same two bars — this verdict
closes MILo's ceiling work, not their trials.

## Source

`docs/notes/A03_DTU_EXTRACTION_RESULT.md` and its 2026-09-02 addendum;
`docs/notes/A02_MESH_METHOD_COMPARISON.md`.
