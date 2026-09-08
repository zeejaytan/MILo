# 06: Three-way verdict with renders

**What to build:** the answer M6 exists to get — MILo vs 2DGS vs OpenMVS on the one
ruler, with resolving-view break-face renders, written back into M6 win or lose.

**Answers:** M6

**Blocked by:** 05 (2DGS mesh); reads the M1 boxes (01–03) as its bar and baseline.

**Status:** claimed (2026-09-07 — verdict work started; renders before numbers)

- [ ] Same-ruler comparison of all three meshes (fraction of sherd surface within the
      requirement in **mm**); the average across runs is reported, never best-of-N alone
- [ ] Cross-view depth disagreement in **mm** for 2DGS on the same ruler (M6 box;
      port `scripts/depth_disagreement.py` to 2DGS `surf_depth` — GPU job)
- [ ] Break-face close-up renders, 2DGS versus MILo, at a view that resolves ~0.2 mm ridges —
      the render exists before any geometry box is ticked
- [ ] Rig check: remaining steel surface area in each extracted mesh, stated in cm²
- [ ] M6's boxes ticked with the date, or M6 amended/retired in place with the reason

## Comments

- 2026-09-09, fair-recipe run (user challenge): our verdict fused mean-depth maps;
  upstream's recipe uses median. Fine voxels (0.001u) + median maps (dr1) =
  job 30260891 — the apples-to-apples run owed before any retire. Poll running.

- 2026-09-09, common-setup masked result: 1.92M verts in 328,925 fragments,
  largest ~4k tris — at 2.6 mm cubes nothing coheres (predicted: cubes 2.6× the
  ~1 mm bar). Negative control only; fine-voxel choice stands vindicated.
- 2026-09-09, unmasked OOM root cause corrected: NOT view-1 blowup — steady
  ~1.5 GB/view accumulation over ~90 views to the 134 GB cap (log buffering hid
  progress). Depths verified sane (no inf/nan). Full-room fusion simply costs
  hundreds of GB; masked fits because 2.3% of pixels fuse. Baseline properly
  attempted on idle 3 TB nodes: job 30260854 (1 TB, bigmem), poll running.

- 2026-09-09, common-setup pass per user (match upstream practice): depth-median
  maps (`--depth_ratio 1`, DTU recipe) + auto cubes (cutoff/1024 ≈ 0.0069u ≈
  2.6 mm) + band 5×, via `--tag dr1` maps and auto-voxel support added to the
  trial scripts (depth mode recorded in `_meta`). At 2.6 mm the unmasked
  baseline should fit (~330× fewer cubes), so masked + unmasked fuse from the
  same maps: render 30259403 (short GPU), fuse 30259404 masked /
  30259405 unmasked (`afterok` chain, CPU). `num_cluster` stays 50 (DTU's 1
  assumes a single object; deviation recorded). Polls running.

- 2026-09-09, baseline closed WITHOUT a mesh, and that is the answer: unmasked
  fusion died of OOM at 128 GB AND at 512 GB (this time at MILo's own 0.75 mm
  voxels, job 30259250, dead on view 1 at ~60 GB/view). Mechanism, with numbers:
  an unmasked view is mostly empty room out to the 7.1u truncation, and the
  grid must cover that whole frustum volume at 0.374 mm cubes; masked views
  cover 2.3% of pixels, so the same code fits easily. Upstream never fuses
  unmasked rooms either (DTU eval is masked; large scenes go unbounded), and
  the issue tracker shows others OOMing on fewer pixels than ours. MILo's room
  mesh came from tet-meshing, which never allocates volumes. Parameters stand
  proven by the masked run; no further baseline spends.

- 2026-09-09, correction (user challenge upheld on the fact): MILo DID mesh the
  whole room unmasked — `A03_nomask/mesh_learnable_sdf.ply` (111 MB). But by
  tet-meshing, which has no voxel grid and never pays volume×voxel. Nobody has
  TSDF-fused this room at 0.374 mm voxels; MILo's own TSDF ran at 0.75 mm
  (8× cheaper) and masked, and still hit 22 GiB reserved with the rig in.
  Fair test of the challenge: unmasked 2DGS baseline at MILo's voxel
  (0.002u/0.75 mm, job 30259250) — same pipeline, comparable density. If it
  fits 128G, the OOM was voxel scale, not a broken pipeline; if it dies too,
  something else is wrong and I say so.

- 2026-09-09, baseline closed WITHOUT a mesh, and that is the answer: unmasked
  fusion at 0.374 mm died of OOM at 128 GB (134 GB RSS) AND at 512 GB (535 GB
  RSS, 8 min in, job 30233740). The parameters are proven by the masked run
  (15 min, mesh on disk); unmasked at this voxel is unaffordable, same disease
  as MILo's rig-in grid. No 1 TB retry — a control mesh nobody will use is not
  worth terabytes. Verdict reads off the masked mesh.

- 2026-09-08, same-ruler verdict numbers (login-node CPU raycast, mm):
  2DGS-boxed→OpenMVS-refined: 13.2% within 1 mm, median 49 mm — most 2DGS
  surface lies nowhere near a real surface. Reverse: 42.9% within 1 mm,
  median 2.2 mm — under half the reference surface has 2DGS nearby. Against
  the ~1 mm bar and 0.186 mm ceiling, keep-options (a) and (b) fail as a mesh
  route; formal retire waits on the owed close-ups + depth probe + O-number
  read-in. Formal `compare_meshes.py` refused (size gate 2.31× — content, not
  units: 2DGS spans ~2× the tray in two axes).
- 2026-09-08, jobs: masked re-fuse guard-refused as designed; nomask baseline
  OOM'd at 128G (134 GB RSS on view 1 — unmasked fusion at 0.374 mm is itself
  unaffordable, same disease as MILo's rig-in grid); retried 30233740 at 512G
  sapphire, poll running. Render maps (30207590) carry the `mask` band —
  loader audit hole closed: masks reach fusion, so surviving steel is fused
  THROUGH outlines (streaks/sheets), not around them.

- 2026-09-07, baseline control per user (parameters must prove out unmasked
  first): render leg 30207590 COMPLETED in 6 min — 143 train maps + test PNGs,
  radius 3.552u matches the monolith's 3.55. Same maps feed both fusions, so
  masked-vs-unmasked is a pure ablation, no retrain. Submitted masked
  re-fuse 30208817 (guard will refuse — monolith output exists, identical
  params) and unmasked baseline 30208818 (`--ignore-mask`, new flag in
  `scripts/fuse_maps.py`), both CPU-only. Polls running.

- 2026-09-07, shared reference built: `scripts/color_components.py` paints top-20
  components + legend PNG. OpenMVS side: 16 components — O01 is rig (326 cm²),
  O02–O11 are the ten sherds (18–100 cm²), O12+ specks. 2DGS side S01–S20 all
  large (25–254 cm², no sherd-scale separation — sherd+steel webbing suspected).
  Files in `2dgs/output/A03_sherds/numbered/`, pulled to `artifacts/2dgs-a03/`.

- 2026-09-07, conservator eye (CloudCompare, boxed mm mesh): some sherds read
  OK-ish, some never formed as sherds at all. First completeness failure of the
  trial — recorded before any number. Component inventory same day: 50
  components (post-filter cap), largest 415/353/343 cm² down through sherd-scale
  40–90 cm² pieces spread ±250 mm — size alone cannot separate clay from rig
  steel; cause (mask gaps vs clamp occlusion vs depth noise) goes to the depth
  probe + mask audit, not to this count.

- 2026-09-07, verdict work: 2DGS mesh scaled to mm (`fuse_post_mm.ply`
  ×373.73332518281325 + sidecar; same sparse frame as MILo so the plate factor
  transfers — reasoning recorded in the sidecar). Submitted render rerun 30207590
  (short, fixed PYTHONPATH) and compare 30207591 (2DGS-vs-OpenMVS `dense_fixed`
  refined, short 2h, roles: 2DGS as --milo). Second compare (2DGS-vs-MILo-boxed)
  follows after outputs are moved aside — the script hardcodes one out dir, so
  no parallel runs. Polls running on both.
