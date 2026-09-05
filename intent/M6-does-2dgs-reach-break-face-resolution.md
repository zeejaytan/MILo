# M6 — Does 2D Gaussian Splatting get sherds out of the rig at the resolution a break face needs?

**Status:** open · **Blocked by:** [M1](M1-resolution-the-material-needs.md) (the required
ridge scale and the OpenMVS baseline are still unstated — without them no extractor swap
can be shown to help or hurt) · **Effort:** roughly 1–2 weeks (pinned build, one-capture
A/B on existing data, no Slurm campaign)

**Settled scope, 2026-09-06:** end-to-end swap (2DGS training + its TSDF extraction) on
the existing `A03_sherds` dataset, compared same-ruler against MILo's DTU route; bar is
parity-plus (match MILo with voxel size and truncation band stated in mm; the M1 ridge
requirement becomes the real bar once set); rig removal reuses the existing fusion-time
sherd masks — pruning and masked training stay retired per M4/M5 and are not relitigated
under 2DGS without fresh justification. **Settled sequencing, 2026-09-06:** M1's boxes
run first and the 2DGS build waits for them; laptop prepares the pinned build + Slurm
scripts, user approves any submission.

## Why it matters

This decides between three different next moves: tile MILo's extraction past the block
cliff, swap the extractor to 2DGS, or accept what OpenMVS already produces. A swap that
clears a bar MILo cannot is worth doing; a swap that lands on the same ceiling is motion
without progress. If nothing reaches the bar, say which of the three it is — the method
failed on this material (1), the ruler was wrong (2), or there was never valid material
to score against (3) — because those lead to opposite decisions.

Opinion before acting (workspace rule — researched, then stated): worth doing in
general, not yet shown worth doing **for this**. 2DGS is a legitimate surface
reconstruction (2D oriented surfels with depth-distortion and normal-consistency
regularization, SIGGRAPH 2024, `hbb1/2d-gaussian-splatting` README). But on this
material every established failure sits somewhere a representation swap does not touch:
the mesh comes out through **Open3D TSDF fusion in both routes** (2DGS README:
"TSDF fusion for extracting mesh is based on Open3D"), so the measured 32,768-block
cliff binds 2DGS too until tiled; the rig fills the masks (644 cm² steel against 61 cm²
clay per view on A03) upstream of any extractor; and masked training drained 91% of
density on MILo ([M5](M5-can-masked-training-exclude-rig.md)) — a 2DGS swap needs its own
masked-training A/B, it cannot inherit an exemption. Web search for independent
small-object experience was attempted and unavailable in this session; that half of the
research is still owed before building. Measure M1's three boxes first — they are cheap
and they gate this question either way.

## Done when

- [ ] 2DGS built at a pinned commit on Spartan, trained on the existing `A03_sherds`
      dataset at full capture resolution, mesh extracted with voxel size and truncation
      band stated in **millimetres**. The commit is pinned in this file before any job
      is submitted — an unpinned build is unrepeatable
- [ ] Cross-view depth disagreement in **millimetres** for 2DGS versus MILo's DTU route
      on the same capture, on the same ruler (scale sidecars, per
      [M3](M3-is-the-mesh-at-true-scale.md))
- [ ] Same-ruler comparison against OpenMVS on A03 — fraction of sherd surface within
      the M1 requirement (in **mm**); reuses M1's second box, not a second ruler
- [ ] Break-face close-up renders, 2DGS versus MILo, at a view that resolves ~0.2 mm
      ridges — a whole-sherd view looks fine at every resolution and has misled here
      repeatedly
- [ ] Rig check: `mask_content.py` steel-vs-clay split for the inputs actually used, and
      remaining steel surface area in the extracted mesh, stated in cm²

## Gate / stop condition

- If OpenMVS already meets the M1 requirement: **stop** — record it and do not swap,
  whatever 2DGS's merits elsewhere.
- If 2DGS hits the 32,768-block cliff at the required voxel: this question becomes the
  tiling question — amend, do not build around it.
- If masked 2DGS training drains density the way M5 did: retire NO at the same weight
  (one capture, eye verification), do not fund a second architecture to re-learn it.

## Source

User proposal 2026-09-06 (`hbb1/2d-gaussian-splatting`, official 2DGS implementation);
[M1](M1-resolution-the-material-needs.md),
[M4](M4-can-rig-gaussians-be-pruned-after-training.md),
[M5](M5-can-masked-training-exclude-rig.md); MILo `AGENTS.md` domain notes (0.21 mm
photo support, block-cliff arithmetic, mask-content split).
