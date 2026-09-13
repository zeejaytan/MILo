# M8 — Does PGSR replace MILo as the sherd mesh route at the resolution a break face needs?

**Status:** answered NO as mesh route 2026-09-13 · **Blocked by:** the OpenMVS baseline only (requirement ~1 mm stated and concurred; MILo-specific boxes do not gate a different method — it carries its own depth probe as part of its evaluation below) · **Effort:** roughly 1–2 weeks (pinned build, one-capture A/B on existing data, no Slurm campaign)

**Settled scope:** end-to-end swap (PGSR training + its TSDF extraction) on the existing `A03_sherds` dataset, compared same-ruler against MILo's DTU route and OpenMVS; bar is parity-plus (match MILo with voxel size and truncation band stated in mm; the M1 ~1 mm ridge requirement is the real bar). Two extraction variants on the same training, as requested:
- **(A) fusion-masked:** community fork path (`GhostLate/PGSR_MeshReconstruction` §2.4 construction) — masks baked to alpha, background depth zeroed during TSDF fusion, the same construction as MILo's live DTU path. No training-time masking.
- **(B) cull-after:** stock upstream (`zju3dv/PGSR`) unmasked training, rig removed after fusion by small-component filter only.
Pruning/training-time masking stays retired per M4/M5 and is not relitigated here without fresh justification. TopoSurfel stays under M7 (it requires a PGSR `mesh_init.ply` first, so this trial gates it, not the reverse).

## Why it matters

MILo's own DTU extraction route is closed on quality grounds, and M4/M5 showed removing steel is easy but removing it *without thinning the clay past use* is the hard part. PGSR is the planar-based GS route with the best published geometry on the benchmarks (DTU ~0.52 mm chamfer, TNT ~0.51 F1, unbiased depth + single/multi-view regularization), and it is the required init for any TopoSurfel build. A swap that clears a bar MILo cannot is worth doing; a swap that lands on the same ceiling is motion without progress. If nothing reaches the bar, say which of the three it is — the method failed on this material (1), the ruler was wrong (2), or there was never valid material to score against (3) — because those lead to opposite decisions.

Opinion before acting (workspace rule — researched, then stated): worth doing in general, not yet shown worth doing **for this**. PGSR's accuracy is shown on clean benchmark objects at cm scale with no clamp rig and no 0.2 mm ridge bar; as shipped it has no training-time mask, and its fusion mask is a community construction, not upstream. Small-object accuracy at sherd scale is unmeasured — the trial's own depth check decides.

## Done when

- [ ] Stock upstream + community fork both **pinned by commit hash in this file before any job** is submitted — an unpinned build is unrepeatable. Trained on the existing `A03_sherds` dataset at full capture resolution (no silent downsample), mesh extracted with voxel size and truncation band stated in **millimetres**, both variants (A fusion-masked, B cull-after) from the same training
- [ ] Cross-view depth disagreement in **millimetres** for PGSR versus MILo's DTU route on the same capture, on the same ruler (scale sidecars, per [M3](M3-is-the-mesh-at-true-scale.md))
- [ ] Same-ruler comparison against OpenMVS on A03 — fraction of sherd surface within the M1 requirement (~1 mm relief); reuses M1's second box, not a second ruler
- [ ] Break-face close-up renders, PGSR (both variants) versus MILo, at a view that resolves ~0.2 mm ridges — a whole-sherd view looks fine at every resolution and has misled here repeatedly
- [ ] Rig check: `mask_content.py` steel-vs-clay split for the inputs actually used, and remaining steel surface area in each extracted mesh, stated in cm²

## Gate / stop condition (OpenMVS is the ceiling, not a stop-baseline — per M6 amendment)

- OpenMVS (0.186 mm wobble on A02 + the A03 outline direction) is the **ceiling to beat**, not a bar that stops this trial. The trial runs to a measured verdict whatever OpenMVS meets — a different method with its own failure modes is worth measuring, and two independent routes agreeing is evidence neither gives alone.
- "Earns its keep" means one of three measured outcomes: (a) it matches or beats OpenMVS on sherd surface within the ~1 mm requirement with ridge-resolving renders — mesh of record; (b) it clears ~1 mm with **complementary coverage** OpenMVS misses (different honest holes, clamp-shadowed faces) — combined record; (c) viewing-only — fast high-quality novel views for inspection, judged on renders, never in millimetres.
- Retire as a mesh route if its depth-disagreement floor sits far above ~1 mm with nothing complementary (one capture, eye verification) — record which of the three it is (method failed / ruler broken / reference wrong), do not fund a second seed.
- If the fusion-masked variant (A) thins clay the way M5 did (~91% drain on MILo): retire that variant NO at the same weight (one capture, eye verification), keep variant B's verdict independent — do not let one variant's failure close the other.
- If PGSR hits an extraction ceiling at the required voxel (whichever Open3D class): this question becomes the tiling question — amend, do not build around it.
- Pinned builds, full resolution, no Slurm without approval.

## Verdict 2026-09-13: no — PGSR does not replace MILo as the sherd mesh route

One capture (A03, `A03_sherds`, 164 views), one seed, pinned stock `de24f1a` (+ community alpha construction `8777d4b` for variant A). Frame-correct masked mesh rendered (whole-mesh overviews in `PGSR/artifacts/review_A_stock/`); no ridge-resolving close-ups taken, depth-disagreement and same-ruler fraction boxes unrun — stated as gaps, not hidden.

- Regs catch-22 (causal, one variable): full-regs 30k smears the scene 4–5× (15.5 dB held-out); regs-off finds it crisply (22.9 dB, identical at the 7k pre-reg checkpoint). The planar/NCC losses fight chrome highlights + textureless black; without them Gaussians stay unflattened and `plane_depth` is unreliable.
- Frame-correct variant A (upstream W2C pass-through; a 09-11 C2W invert was tried, displaced every mesh ~5 units, and withdrawn) is lumpy and partial: 10 forced pieces, 96,719 verts at a 0.75 mm grid (0.002 units × 373.73 mm/unit route sidecar) — 1 mm relief is ~1.3 voxels, 0.2 mm ridges unresolvable by construction.
- Variant B (unmasked full-room fusion at that voxel) OOMs twice (134 GB, 268 GB): content×voxel ceiling, not bad luck.
- Kind: **(1) the method failed on this material as configured** — not a broken ruler (sidecar + bounds checks agree) and not a wrong reference (OpenMVS same capture). Training-time masking / pruning stay retired per M4/M5, unrelitigated.
- Not judged: viewing-only outcome (c) — 22.9 dB renders exist but were never scored as views. A future R question if wanted; this question closes on the mesh route.

## Source

User proposal (PGSR as MILo replacement + A/B: community alpha zero-background vs stock cull-after); PGSR paper (TVCG2024, arXiv:2406.06521 — planar flattening, unbiased depth, single/multi-view regularization, TSDF fusion) + `zju3dv/PGSR` README (train 30k iters, `render.py --voxel_size/--max_depth/--use_depth_filter`) + `GhostLate/PGSR_MeshReconstruction` §§2.4/3.2 (masks via alpha to zero background depth at fusion); TopoSurfel dependency (`Fan-Treasure/TopoSurfel` step 1: PGSR `mesh_init.ply` required); [M1](M1-resolution-the-material-needs.md), [M3](M3-is-the-mesh-at-true-scale.md), [M4](M4-can-rig-gaussians-be-pruned-after-training.md), [M5](M5-can-masked-training-exclude-rig.md); MILo `AGENTS.md` domain notes (0.21 mm photo support, block-cliff arithmetic, mask-content split).
