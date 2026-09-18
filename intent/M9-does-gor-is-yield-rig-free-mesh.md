# M9 — Does GOR-IS give a rig-free sherd mesh at the resolution a break face needs?

**Status:** open · **Blocked by:** none (M1 requirement ~1 mm stated; OpenMVS baseline stands as ceiling) · **Effort:** roughly 1–2 weeks (pinned build, one-capture A/B on existing data)

## Why it matters

The rig-free MILo mesh is too coarse for seating sherds — 0.82 mm cubes against ~1 mm grain the break faces carry, and the depth feeding it wobbles 4.1 mm. GOR-IS removes an object plus its reflections and fills behind it in material/lighting space, then a TSDF fusion can mesh the result. If that mesh keeps ~1 mm relief with zero steel, it earns a record or complementary role. If it lands where 2DGS/PGSR did, it retires at the same weight.

Plain terms: OpenMVS error on flat ground is 0.19 mm, two sheets of paper. The test is whether GOR-IS mesh gets within about five such sheets (1 mm) on sherd clay, with no clamp steel, on the same ruler.

## Opinion before acting (workspace rule — researched, then stated)

Worth doing in general, not yet shown worth doing **for this**. GOR-IS is a legitimate remover (CVPR 2026 Highlight, `applezyh/GOR-IS@eb36acc` 2026-05-30) with a real mesh path (`render.py` → `GaussianExtractor.extract_mesh_bounded/_unbounded`, voxel/depth/sdf args, 50-cluster post pass). But its accuracy is shown on clean scenes at cm scale, none at 0.2 mm ridge scale, none with 644 cm² chrome steel against 61 cm² clay per view. Its default `run.sh` never meshes (`--skip_mesh` on both removal and render steps) — mesh-after is a manual third call. The inpainted jaw contact is invented clay by construction and must never score in mm.

## Done when

- [ ] Pinned build `applezyh/GOR-IS@eb36acc` in separate `envs/goris` (python 3.12, nvdiffrast, OptiX gtracer fork), A03_sherds converted (rig object_mask, chrome specular_mask, predicted normals, train/val/test lists), full resolution
- [ ] Recon → removal → 2D/3D inpaint → manual mesh-after with voxel size and truncation band stated in **millimetres** (mesh is REQUIRED, not optional)
- [ ] Cross-view depth disagreement in **millimetres** on the same capture, same ruler (scale sidecars, per M3)
- [ ] Same-ruler fraction within ~1 mm vs OpenMVS on A03; inpainted contact excluded from the score
- [ ] Break-face close-ups at ridge-resolving views, GOR-IS mesh vs OpenMVS, plus conservator eye sign-off
- [ ] Rig check: steel-vs-clay split of inputs actually used, remaining steel cm² in the mesh

## Gate / stop condition (OpenMVS is the ceiling, not a stop-baseline)

- "Earns its keep" means (a) matches/beats OpenMVS within ~1 mm with ridge renders — mesh of record; (b) clears ~1 mm with **complementary coverage** OpenMVS misses — combined record, inpainted contact excluded; (c) viewing-only — renders hold ridge detail, judged on renders never mm.
- Retire as mesh route if depth floor sits far above ~1 mm with nothing complementary (one capture, eye verification) — record which of the three it is (method failed / ruler broken / reference wrong), do not fund a second seed.
- If masked/inpaint training drains density the way M5/M6 did (~90%+), retire NO at the same weight.
- If extraction hits an Open3D ceiling at the required voxel, this becomes the tiling question — amend, do not build around it.
- Pinned builds, full resolution.

## Source

User request 2026-09-18 (mesh-after required); GOR-IS README + `run.sh` + `launcher.py` + `render.py` at `eb36acc`; [M1](M1-resolution-the-material-needs.md), [M3](M3-is-the-mesh-at-true-scale.md), [M4](M4-can-rig-gaussians-be-pruned-after-training.md), [M5](M5-can-masked-training-exclude-rig.md), [M6](M6-does-2dgs-reach-break-face-resolution.md), [M8](M8-does-pgsr-replace-milo.md); `docs/notes/A03_DTU_EXTRACTION_RESULT.md`.
