# M6 — Does 2D Gaussian Splatting get sherds out of the rig at the resolution a break face needs?

**Status:** open · **Blocked by:** the OpenMVS baseline only (requirement ~1 mm
stated and concurred; the MILo-specific boxes — depth disagreement on MILo's
Gaussians, MILo renders — do not gate this: a different method needs its own
depth probe, which is part of its evaluation below, not a prerequisite) ·
**Effort:** roughly 1–2 weeks (pinned build, one-capture A/B on existing data,
no Slurm campaign)

**Settled scope, 2026-09-06:** end-to-end swap (2DGS training + its TSDF extraction) on
the existing `A03_sherds` dataset, compared same-ruler against MILo's DTU route; bar is
parity-plus (match MILo with voxel size and truncation band stated in mm; the M1 ridge
requirement becomes the real bar once set); rig removal reuses the existing fusion-time
sherd masks — pruning stays retired per M4 and is not relitigated under 2DGS without
fresh justification. M5 retires masked training on MILo only and does NOT retire
Rogge-style masked training on 2DGS (arXiv:2501.08174); that masked-2DGS A/B is the live
branch below. **Sequencing, corrected 2026-09-06:** the "M1 first, 2DGS waits"
order below was over-strict — only the requirement (done) and the OpenMVS baseline
transfer to a new method. 2DGS build prep proceeds in parallel; its own
depth-disagreement probe is part of its evaluation, not a prerequisite.

**Pinned build, 2026-09-06:** `hbb1/2d-gaussian-splatting@f3e3b9f`,
rasterizer `hbb1/diff-surfel-rasterization@e0ed020` (both HEAD at pin date; no job
submitted on this pin yet). Vanilla training at this commit reads **no mask**
(`train.py`: full-frame L1+SSIM; the `gt_alpha_mask *= photo` line in
`scene/cameras.py` is commented out) — the rig trains, and leaves at fusion via the
shipped `mask_backgrond` depth-zeroing (`utils/mesh_utils.py`), the same construction
as MILo's DTU path. The Rogge masked-training fork (`MarcelRogge/object-centric-2dgs`,
background loss weight 0.5) is the separate live branch.

**Small-object sweep, 2026-09-06 (partly done, at-scale demo still missing):**
adjacent only — ISPRS 2026 tests MILo/GS variants on complex detailed objects (MILo
promising on detail, plain splatting noisy as geometry); ObjSplat digitises cultural
artefacts on a motorised turntable in minutes (surfel-based, robotic views, not our
capture); single-object 2DGS with YOLO+SAM probability masks reaches ~1/10 the
Gaussians at comparable quality (arXiv:2603.14316); masked/object-centric 2DGS method
plus code (arXiv:2501.08174). Nothing at the 0.2 mm ridge scale on sherd-like clay —
build-prep proceeds, the verdict still needs the trial's own depth check.

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
"TSDF fusion for extracting mesh is based on Open3D") — but through a **different
Open3D class**: 2DGS's bounded path integrates into `ScalableTSDFVolume`
(`utils/mesh_utils.py:extract_mesh_bounded`), not the `VoxelBlockGrid` whose
`extract_triangle_mesh` scratch overflows at 32,768 blocks, and its unbounded path is a
custom contracted-TSDF plus marching-cubes (`extract_mesh_unbounded`). Whether an
equivalent ceiling binds either is **unmeasured** (source audit 2026-09-06 at the pinned
commit) — do not read a 2DGS extraction failure as the known cliff without checking; the rig fills the masks (644 cm² steel against 61 cm²
clay per view on A03) upstream of any extractor; and masked training drained 91% of
density on MILo ([M5](M5-can-masked-training-exclude-rig.md)) — a 2DGS swap needs its own
masked-training A/B, it cannot inherit an exemption. Small-object literature stood
partly done 2026-09-06 (see pin note above); M1's requirement and OpenMVS baseline have
landed since, and per the 2026-09-06 verdict they gate this trial's verdict, not its
build-prep.

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

## Gate / stop condition (amended 2026-09-06 per user: OpenMVS is the ceiling, not a stop-baseline)

- OpenMVS (0.186 mm wobble on A02 + the A03 outline direction) is the **ceiling to
  beat**, not a bar that stops this trial. The trial runs to a measured verdict
  whatever OpenMVS meets — a different method with its own failure modes is worth
  measuring, and two independent routes agreeing is evidence neither gives alone.
- "Earns its keep" means one of three measured outcomes: (a) it matches or beats
  OpenMVS on sherd surface within the ~1 mm requirement with ridge-resolving renders
  — mesh of record; (b) it clears ~1 mm with **complementary coverage** OpenMVS
  misses (different honest holes, clamp-shadowed faces) — combined record; (c)
  viewing-only — fast high-quality novel views for inspection, judged on renders,
  never in millimetres.
- Retire as a mesh route if its depth-disagreement floor sits far above ~1 mm with
  nothing complementary (one capture, eye verification) — record which of the three
  it is (method failed / ruler broken / reference wrong), do not fund a second seed.
- If 2DGS hits an extraction ceiling at the required voxel (whichever Open3D class —
  the 32,768-block cliff as measured binds `VoxelBlockGrid`, not 2DGS's
  `ScalableTSDFVolume`): this question becomes the tiling question — amend, do not
  build around it.
- If masked 2DGS training drains density the way M5 did: retire NO at the same weight
  (one capture, eye verification), do not fund a second architecture to re-learn it.

## Source

User proposal 2026-09-06 (`hbb1/2d-gaussian-splatting`, official 2DGS implementation);
Rogge-style object-centric masked 2DGS (arXiv:2501.08174 — M5 does not retire this branch,
amended 2026-09-06 per user OK); [M1](M1-resolution-the-material-needs.md),
[M4](M4-can-rig-gaussians-be-pruned-after-training.md),
[M5](M5-can-masked-training-exclude-rig.md); MILo `AGENTS.md` domain notes (0.21 mm
photo support, block-cliff arithmetic, mask-content split).
