# M6 — Does 2D Gaussian Splatting get sherds out of the rig at the resolution a break face needs?

**Status:** retired 2026-09-13 — answered NO on A03 (type-1 method-on-material
failure; keep-options (a), (b) and (c) all fail, do not fund a second seed) ·
**Blocked by:** none (M1 requirement ~1 mm and OpenMVS baseline both landed 2026-09-06;
the MILo-specific boxes never gated this) ·
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

**Masked branch scoped 2026-09-07 (tickets 07–08):** the Rogge repo ships NO code
(README recipe @`bdbabdc` only) — this is a hand-port into our pin, not a drop-in.
07 ports the two losses (masked photometric + background λ=0.5, alphas already
returned, masks from the RGBA band — no rasterizer change) and probes at ~7k
iters with a GO/NO-GO; occlusion pruning (CUDA edits + rebuild) is deferred to
08 only if the probe survives. M5's rim-erosion and density-drain warnings travel
with the branch.

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

- [x] 2DGS built at a pinned commit on Spartan (`f3e3b9f` + rasterizer `e0ed020`,
  2026-09-06), trained on the existing `A03_sherds` dataset at full capture
  resolution, mesh extracted 2026-09-07 with voxel 0.001u (0.374 mm) and
  truncation band 0.005u (1.87 mm) stated in **millimetres**
- [x] Cross-view depth disagreement in **millimetres** for 2DGS on the same
      capture, on the same ruler (scale sidecars, per
      [M3](M3-is-the-mesh-at-true-scale.md)) — 2026-09-11, adjacent views median
      0.28–0.66 mm, p90 11–36 mm, 25–44% of pixels beyond 1 mm (n≈140k each,
      3 pairs; self-pair control 0.00 mm); deep clay median 0.22–0.31 mm
      (17–29% beyond), rim band median 0.35–1.54 mm (32–57% beyond), p90
      20–56 mm. Half the pixels outvote the 0.374 mm cube — the floor sits
      above the ~1 mm bar
- [x] Same-ruler comparison against OpenMVS on A03 — fraction of sherd surface within
      the M1 requirement (in **mm**) — 2026-09-08/11, login-node CPU raycast:
      2DGS→OpenMVS 13.2% within 1 mm, median 49 mm; reverse 42.9%, median
      2.2 mm; correct-K re-fusion 8.4%, median 71 mm (noise-only change —
      cameras exonerated, verdict doubly grounded). Formal `compare_meshes.py`
      refused (size gate 2.31× — content, not units). Keep (a) and (b) fail
- [x] Break-face close-up renders, 2DGS versus MILo, at a view that resolves ~0.2 mm
      ridges — 2026-09-07 conservator eye (CloudCompare boxed mm mesh: some
      sherds OK-ish, some never formed — first completeness failure);
      2026-09-10 probe eye (`artifacts/2dgs-a03/probe_A31_1100.png`: black
      frame, sherds translucent smears); 2026-09-12 dilated eye
      (`artifacts/2dgs-a03/dprobe_A31_1100.png`: identical ghosts); preview
      pair staged — `.scratch/visual-qa` ticket 07
      (`preview/manifest_a03.json`, previews at
      `MILo/artifacts/visual-qa/a03_2dgs_openmvs/`). Keep (c) fails: control
      held-out PSNR 21–22 dB, masked probes 11.6 dB — no viewing-only route
- [x] Rig check: `mask_content.py` steel-vs-clay split for the inputs actually used, and
      remaining steel surface area in the extracted mesh, stated in cm² —
      inputs 644 cm² steel vs 61 cm² clay per view; OpenMVS O01 rig 326 cm²,
      O02–O11 ten sherds 18–100 cm²; 2DGS S01–S20 all 25–254 cm² with no
      sherd-scale separation (sherd+steel webbing); masked fine mesh keeps
      steel sheets

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
  **Retired 2026-09-10 (ticket 07): NO — 94% drained by 7k iters (78,227→4,620),
  bg 0.00195, held-out PSNR 11.6 dB vs 21.2 control. Same trade as M4/M5 with
  nothing paired to the exclusion. Eye renders landed 2026-09-10/12 (black frame, translucent smears; dilated identical ghosts); numbers alone had retired it.
  This is a method-on-material failure (type 1), same-ruler numbers.**
- 2026-09-12/13, branch stays dead after two follow-ups (ticket 07): dilated
  masks 78,227->5,781 (92.6% drained, PSNR 11.59 vs 11.57 -- margin buys nothing);
  background weight 0.1 (job 30485175) 78,227->12,796 (~84% drained, PSNR
  11.58 dB -- counts scale with weight, collapse does not lift). No further
  masked variants without fresh justification.
- 2026-09-11: a calibration scare (fusion intrinsics) was raised and then
  retracted the same day — correct-K re-fusion changed the verdict numbers by
  noise only (8.4% vs 13% within 1 mm). Type-1 verdict stands, doubly grounded.
- **Verdict 2026-09-13: retired NO.** One capture (A03), eye verification at every
  step. Baseline masked fine mesh: 13.2% within 1 mm (median 49 mm) vs the ~1 mm
  bar and 0.186 mm OpenMVS ceiling — keep (a) mesh-of-record and (b) complementary
  coverage fail; masked probes hold 11.6 dB vs 21–22 dB control — keep (c)
  viewing-only fails. Depth floor (median 0.28–0.66 mm, p90 11–36 mm) sits above
  the bar with nothing complementary. This is failure type 1 — the method failed
  on this material — not a broken ruler (correct-K re-fusion agrees) and not a
  wrong reference (OpenMVS side is the M1 ceiling). Ticket 06 resolved here;
  ticket 07 retired the masked branch at probe weight; ticket 08 never started
  (probe never GO) and goes `wontfix`.
- Loop check 2026-09-13: close-out written back from tickets 06/07/08; M6 carries no checker errors (remaining errors on the board belong to M8, a separate open question).

## Source

User proposal 2026-09-06 (`hbb1/2d-gaussian-splatting`, official 2DGS implementation);
Rogge-style object-centric masked 2DGS (arXiv:2501.08174 — M5 does not retire this branch,
amended 2026-09-06 per user OK); [M1](M1-resolution-the-material-needs.md),
[M4](M4-can-rig-gaussians-be-pruned-after-training.md),
[M5](M5-can-masked-training-exclude-rig.md); MILo `AGENTS.md` domain notes (0.21 mm
photo support, block-cliff arithmetic, mask-content split).
