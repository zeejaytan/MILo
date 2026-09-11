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

- 2026-09-11, calibration break found digging the common failure (user: why did
  common fail?): 2DGS's own camera conversion (`to_cam_open3d`) recovers
  fx=6689/fy=6292/cx=1734/cy=-2857 from our solve vs COLMAP's
  6829.8/6829.4/1600/1066.5 — reprojection off by thousands of px median.
  Formula verified correct on synthetic input; dataset inputs verified
  correct; saved matrices exactly as computed — so the math mis-handles
  turntable-scale translations. Training cameras (FoV-only, centered —
  truly centered here) were fine; only FUSION cameras broke. Fix:
  `--sparse` in trial `fuse_maps.py` builds intrinsics straight from
  cameras.bin. All fused meshes to date are suspect; verdict numbers under
  review (type-2, broken construction — method NOT yet failed). Re-fuse with
  correct cameras: job 30424870 (fine voxels, masked). Poll running.

- 2026-09-11, deconfounded (job 30419585): mean maps × coarse auto cubes =
  kilometre-scale garbage too. Cause is the auto (voxel, band) pair
  (0.0069u/0.0347u), NOT median mode — dr1 maps exonerated. Wide band +
  noisy turntable depths lets marching cubes interpolate giant sheets;
  fine cubes constrain the field. Common-setup line fully dead; mean-fine
  masked mesh stands alone.

- 2026-09-11, deconfounding the common-setup failure (user: why did common
  fail?): two variables changed at once (median depth AND 0.0069u cubes), so
  neither can be blamed yet. Cross run 30419585: proven mean maps × coarse
  auto cubes, masked, CPU. Garbage → cube size is the cause; clean →
  median mode is the cause. Poll running.

- 2026-09-11, common mesh is NOT viewable (user found empty view): extent
  3.2M mm, median vertex 3.5 m off-box, 0.0% inside the shared box — not a
  coarse sherd mesh but a failed fusion (median-depth maps + coarse grid →
  spurious giant sheets; dr1 maps themselves verified sane and near-identical
  to mean maps, same cameras). Local copies removed to avoid confusion.
  Median-depth line now dead at both voxels (fine=OOM, coarse=garbage);
  mean-depth masked mesh stands alone as the only correct fusion.

- 2026-09-09, fuse018 + package cache removed per user (8.8 GB freed); served
  its purpose (versions exonerated). Shared env untouched throughout.

- 2026-09-09, versions exonerated: 0.18.0 blows identically (267 GB, 5 views).
  Revised mechanism: floater-filled background depths (274k Gaussians through
  room air) make the grid fill frustum VOLUME, not surfaces — consistent with
  masked fitting (coherent sherd depths), median dying (noisier), and the
  50 GB/view rate. Remedy under test: clip the room with depth_trunc 4.0
  (30287517, 5 views); cameras sit ~3.7u out, so sherds+rig survive the clip.

- 2026-09-09, fuse018 ready (o3d 0.18.0 + numpy pinned 1.26.4 — also dodges the
  Numpy<2 segfault report) and 5-view probe submitted there (30280601, CPU,
  peak-RSS print). Same maps, same voxel, only the library changed: fits →
  versions were the story; blows → allocator exonerated, volume stands final.

- 2026-09-09, 0.18 fusion env per user (author's own pin, not forum lore):
  `2dgs/envs/fuse018` (py3.9 + open3d==0.18.0 + CPU torch), separate area,
  shared env untouched. Build running; 5-view probe reruns there first, then
  the dead fusions only if the probe fits.

- 2026-09-09, extraction-route options beyond Open3D TSDF (user question):
  (a) 2DGS unbounded mode (same repo, contraction+marching-cubes, GPU-heavy,
  experimental); (b) per-sherd tiled fusion (M1 route 3 — same math, 10×
  smaller volumes, honest holes; needs per-sherd mask split); (c) VDBFusion
  backend (M1 route 5 — no Open3D allocator, needs depth→scan glue);
  (d) tet/Poisson routes (GOF needs 3D Gaussians not surfels; Poisson fills
  the 131 holes — both out of scope). M1's stop applies to (b) too: tiling
  past the ~1 mm depth floor samples noise, not relief.

- 2026-09-09, version check (user: is the pin latest / fixed upstream?): 2DGS
  pin `f3e3b9f` is still HEAD today. Open3D 0.19.0 (Jan 2025) is the latest
  RELEASE on PyPI — nothing newer to upgrade to; dev exists but unreleased,
  and the legacy TSDF class source is unchanged 0.19→latest docs. So "fixed
  upstream" is not an option that exists; remaining moves are OMP-probe
  result, 0.17 fusion env, or accept masked-only.

- 2026-09-09, OMP probe dead (30269160): OOM at 267 GB on FIVE views,
  single-threaded. ~50 GB/view against ~1 GB estimated from surface area —
  two orders over, threading ruled out. Version pathology now the lead
  hypothesis by elimination (volume arithmetic says single-digit GB).
  Next: fusion-only env (py3.8 + o3d0.17 + CPU torch, all confirmed
  installable) — awaiting user go since it revisits the env-reuse decision.

- 2026-09-09, workaround+forum sweep: 2DGS#189 (large-set OOM/segfault; one fix
  was Numpy<2 — N/A, ours is 1.26.4; another was CPU cap), #212 (bounded=small
  scenes, unbounded=big is community norm), #82 (author: CPU TSDF <2 min for
  m360 when installed right; OMP thread cap suggested), #97/#40 (GPU-side OOMs,
  N/A). NVIDIA fVDB room-scale guidance: voxels coarser than the noise floor
  (0.01–0.03 m), truncation 3–4× voxel, min_weight≥3, prune_opacity 0.1 —
  independent support that sub-noise voxels carve per-splat bubbles. Non-TSDF
  routes (GOF/SOF marching-tets) dodge grids entirely but don't take 2DGS
  surfels — out of M6 scope, noted for MILo-family. OMP probe running.

- 2026-09-09, env-issue research (primary sources only): Open3D#4824 (VBG CUDA
  illegal-access with free VRAM, open since 2022), #6712 (0.18/0.19 TSDF
  segfault from an OpenMP race — workaround `OMP_NUM_THREADS=1`), #2107
  (`ScalableTSDFVolume.integrate` filling 256 GB+swap; "wrong poses activate
  new blocks in unobserved space", also fixed by downgrade). gs2mesh
  prescribes py3.8+o3d0.17 (their pipeline, Ubuntu confounded). NO smoking gun
  for our exact call — version story suggestive, not proven; stated as such.
  Installability confirmed: conda-forge has py3.8; PyPI has o3d 0.17.0 cp38/39
  Linux wheels. Free test first: 5-view probe with OMP single-threaded
  (30269160). If it still blows, build the fusion env; if it fits, versions
  were never the story and volume stands.

- 2026-09-09, memory verdict (user vindicated): unmasked fusion died at 1 TB
  (1046 GB RSS, job 30260854) — no legitimate grid costs that; and masked
  MEDIAN-depth fusion died at 134 GB where masked MEAN-depth fit (30260891).
  Pattern: only one configuration ever fused (masked + mean + 0.374 mm).
  Prime suspect is version pathology (community: TSDF kills on py3.9, ours is
  py3.9+o3d0.19; theirs works on py3.8+o3d0.17) — not volume, not settings.
  Probe resubmitted with _DONE fixed (30269072) for the per-view number; then
  the call is new-fusion-env vs close-the-lines, user's call.

- 2026-09-09, memory burden-of-proof (user: 1 TB is ridiculous vs MILo — and
  my 1.5 GB/view was crude division off a dying log): 5-view unmasked probe
  30261001 with peak-RSS print (`/usr/bin/time -v`), verdict voxel. ≤~10 GB
  → steady-growth story, bigmem stands. Tens of GB → version pathology
  (community reports TSDF kills on py3.9, ours is py3.9+o3d0.19), fix is env
  not memory, bigmem gets cancelled. Poll running.

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
