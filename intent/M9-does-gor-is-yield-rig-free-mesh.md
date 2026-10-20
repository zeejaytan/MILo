# M9 — Does GOR-IS give a rig-free sherd mesh at the resolution a break face needs?

**Status:** retired 2026-10-20 (method failed on this material — bounded probe series closed, no second seed)

## Why it matters

The rig-free MILo mesh is too coarse for seating sherds — 0.82 mm cubes against ~1 mm grain the break faces carry, and the depth feeding it wobbles 4.1 mm. GOR-IS removes an object plus its reflections and fills behind it in material/lighting space, then a TSDF fusion can mesh the result. If that mesh keeps ~1 mm relief with zero steel, it earns a record or complementary role. If it lands where 2DGS/PGSR did, it retires at the same weight.

Plain terms: OpenMVS error on flat ground is 0.19 mm, two sheets of paper. The test is whether GOR-IS mesh gets within about five such sheets (1 mm) on sherd clay, with no clamp steel, on the same ruler.

Resolution, amended 2026-09-21 (user decision, ticket 02): full 3200px trains at ~10s/iter — 30k iters ≈ 80 GPU-hours, out of reach. Half resolution (1600px, 0.42 mm/px) still oversamples the ~1 mm grain 2.4× and is what the trial runs at. This weakens the resolution box openly rather than silently.

## Opinion before acting (workspace rule — researched, then stated)

Worth doing in general, not yet shown worth doing **for this**. GOR-IS is a legitimate remover (CVPR 2026 Highlight, `applezyh/GOR-IS@eb36acc` 2026-05-30) with a real mesh path (`render.py` → `GaussianExtractor.extract_mesh_bounded/_unbounded`, voxel/depth/sdf args, 50-cluster post pass). But its accuracy is shown on clean scenes at cm scale, none at 0.2 mm ridge scale, none with 644 cm² chrome steel against 61 cm² clay per view. Its default `run.sh` never meshes (`--skip_mesh` on both removal and render steps) — mesh-after is a manual third call. The inpainted jaw contact is invented clay by construction and must never score in mm.

## Done when

- [x] Pinned build `applezyh/GOR-IS@eb36acc` in reused `envs/milo` + `goris_pkgs` sidecar (2026-09-19, ticket 01: full import smoke green on GPU), A03_sherds converted (rig object_mask eye-verified, base+dial kept; specular/normal via loader None-path; 143/21/21 lists), full resolution (`--resolution 1` explicit)
- [ ] Recon → removal → 2D/3D inpaint → manual mesh-after — RETIRED UNEXECUTED 2026-10-20 (ticket 08): recon wedges at iter ~4000 on A03, no mesh ever existed
- [ ] Cross-view depth disagreement in mm — RETIRED UNMEASURED (never reached measurement)
- [ ] Same-ruler fraction within ~1 mm vs OpenMVS — RETIRED UNMEASURED (inpainted-contact exclusion never engaged)
- [ ] Break-face close-ups + conservator eye sign-off — RETIRED UNSTAGED (no renders to judge)
- [ ] Rig check — PARTIAL: killers excluded 143→139 under 8-stop rule (4 of 8 spent, remainder unspent); steel cm² in mesh unmeasured (no mesh)

## Gate / stop condition (OpenMVS is the ceiling, not a stop-baseline)

- "Earns its keep" means (a) matches/beats OpenMVS within ~1 mm with ridge renders — mesh of record; (b) clears ~1 mm with **complementary coverage** OpenMVS misses — combined record, inpainted contact excluded; (c) viewing-only — renders hold ridge detail, judged on renders never mm.
- Retire as mesh route if depth floor sits far above ~1 mm with nothing complementary (one capture, eye verification) — record which of the three it is (method failed / ruler broken / reference wrong), do not fund a second seed.
- If masked/inpaint training drains density the way M5/M6 did (~90%+), retire NO at the same weight.
- If extraction hits an Open3D ceiling at the required voxel, this becomes the tiling question — amend, do not build around it.
- Pinned builds, full resolution.

## Source

User request 2026-09-18 (mesh-after required); GOR-IS README + `run.sh` + `launcher.py` + `render.py` at `eb36acc`; [M1](M1-resolution-the-material-needs.md), [M3](M3-is-the-mesh-at-true-scale.md), [M4](M4-can-rig-gaussians-be-pruned-after-training.md), [M5](M5-can-masked-training-exclude-rig.md), [M6](M6-does-2dgs-reach-break-face-resolution.md), [M8](M8-does-pgsr-replace-milo.md); `docs/notes/A03_DTU_EXTRACTION_RESULT.md`.

## Where it stands

GOR-IS recon cannot train A03 past iter ~4000 — the sample-scene control ran 0–30000 clean (job 33427213) and its resume ran clean (job 33449819), so the stack is acquitted; killer views are acquitted (05 found no shared feature, 07's killer-free clean set wedged too, jobs 33449900/33449901); the trigger is unidentified at probe weight (iter 4000 is a routine densify step per code read, not a unique event). Cause: the method failed on this material — not the ruler, not the reference. Tickets 02/05/06/07 results in, 03/04 retired unexecuted.

Weight: one capture (A03), probe weight (control + bounded 2-leg series, no second seed).
Next: none — route retired.
Picture: none (no mesh or renders to judge).
Viewer: none.
