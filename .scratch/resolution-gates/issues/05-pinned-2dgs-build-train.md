# 05: Pinned 2DGS build and train on A03_sherds

**What to build:** 2DGS at a commit pinned in M6 before anything runs, trained on the
existing `A03_sherds` dataset at full capture resolution, mesh extracted with voxel size
and truncation band stated in **millimetres**. This ticket exists only if 04 says go.

**Answers:** M6

**Blocked by:** 04 (gate verdict — do not start on any other basis).

**Status:** claimed (2026-09-06 — M6 trial start; build-prep only, no sbatch without explicit approval)

- [ ] Commit pinned in M6's file before the first job; build from that commit only
- [ ] Training reuses `A03_sherds` (existing fusion-time masks — no new masking, no
      relitigation of retired M4/M5)
- [ ] Voxel size and truncation band reported in **mm**; block count checked against the
      32,768 cliff before extraction is attempted (refuse-before-call, per the
      established gate)
- [ ] Job submission approved explicitly before sbatch (standing rule)

## Comments

- 2026-09-06, trial start (build-prep only): pin is `hbb1/2d-gaussian-splatting@f3e3b9f`
  + `diff-surfel-rasterization@e0ed020`, recorded in M6. Source audit at that commit:
  vanilla training is unmasked (full-frame L1+SSIM, `train.py`; mask-multiply in
  `scene/cameras.py` commented out); fusion-time mask depth-zeroing is shipped
  (`extract_mesh_bounded(mask_backgrond=True)`), same construction as MILo's DTU path —
  so the settled scope (fusion-time sherd masks, no retrain) needs no patch.
  Bounded extraction uses `ScalableTSDFVolume`, NOT `VoxelBlockGrid`: the 32,768-block
  refuse-before-call gate in the box above does not directly apply — restate the budget
  for this class before extraction (voxel + sdf_trunc in mm, subvolume count, free RAM).
  Dataset checks on Spartan: `data/17062025/A03_sherds` holds 164 images + masked set +
  `sparse/0` COLMAP bins; mask coverage mean 2.28% (`capture.json`); scale sidecar not
  under the dataset dir — locate before any mm claim (known factor 373.733 mm/unit from
  the A03 masked-training work; re-derive, don't inherit).
- 2026-09-06, correction: the first clone attempt landed on the laptop
  (`C:\data\...`, missing ssh wrapper) — removed; the Spartan clone above is the real
  one, verified at both hashes with clean status.
- 2026-09-06, gate amended per user: OpenMVS is the ceiling to beat (0.186 mm), not
  a stop-baseline — trial runs to a measured verdict either way; keep means
  match/beat, complementary coverage, or viewing-only (see M6). Retire bar unchanged.
- 2026-09-06, loader audit at pin (Spartan clone): `-r 1` is mandatory here too —
  default `-1` rescales anything wider than 1600 px (`utils/camera_utils.py:loadCam`),
  ours are 3200. Fusion-time masks need NO patch: `loadCam` splits image band 4 into
  `gt_alpha_mask`, and `A03_sherds/images_masked` already carries the sherd outline as
  alpha (colmap_to_milo convention) — train 2DGS on that dir and
  `extract_mesh_bounded(mask_backgrond=True)` zeroes rig depth as shipped. Still to
  verify at train time: masked filenames match `images.bin` basenames exactly (MILo
  kept `.JPG` names over PNG bytes — same join), and the alpha band survives `-r 1`.
