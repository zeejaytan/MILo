# 05: Pinned 2DGS build and train on A03_sherds

**What to build:** 2DGS at a commit pinned in M6 before anything runs, trained on the
existing `A03_sherds` dataset at full capture resolution, mesh extracted with voxel size
and truncation band stated in **millimetres**. This ticket exists only if 04 says go.

**Answers:** M6

**Blocked by:** 04 (gate verdict — do not start on any other basis).

**Status:** claimed (2026-09-06 — M6 trial start; build-prep only, no sbatch without explicit approval)

- [x] Commit pinned in M6's file before the first job; build from that commit only
  (2026-09-06: `f3e3b9f` + rasterizer `e0ed020`; Spartan clone verified, clean)
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
- 2026-09-06, layout (no mixing): 2DGS lives in its own area
  `/data/gpfs/projects/punim2657/2dgs/` (`repo/` = pin, `envs/surfel`, `.conda-pkgs`,
  `output/`+`logs/` to follow) — sibling of `MILo/`, nothing 2DGS inside it. The
  earlier `MILo/2dgs` clone + `MILo/envs/surfel` partial env + `MILo/.conda-pkgs`
  were moved/cleared accordingly; env rebuild from scratch at the new prefix.
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
- 2026-09-06, build-prep COMPLETE (no sbatch): extensions compiled inplace against
  the shared env (`TORCH_CUDA_ARCH_LIST=8.0` was needed — login nodes have no GPU
  for torch's auto-detect) and import clean (`EXT_OK`) via `PYTHONPATH`, env
  untouched. Filename check: 164/164 solve names present in `images_masked`, all
  RGBA 3200×2133. Remaining: GPU smoke (torch sees card — job pre-flight) and the
  train+extract job itself, which needs explicit approval.
- 2026-09-06, job script ready (NOT submitted): `2dgs/slurm/2dgs_train.slurm` —
  1×A100/8cpu/128G/12h; `train.py -i images_masked -r 1 --eval` (30k iters,
  vanilla unmasked) then bounded extract voxel 0.001u (0.374 mm) / band 0.005u
  (1.87 mm), `--num_cluster 50`; GPU pre-flight refuses without a card;
  refuses to overwrite a finished mesh. `sbatch --test-only` estimates start
  2026-09-14 (queue ~8 days). Awaiting explicit submit approval.
- 2026-09-06, env decision per user: REUSE the MILo env
  (`MILo/envs/milo`: py3.9, torch 2.3.1+cu118, o3d 0.19.0) — no separate `surfel`
  env, no `conda env create` (attempts 1–2 failed: home quota, then a corrupt
  torch tarball plus a cuda-cupti/nvtx LICENSE clobber; both cleaned up).
  Deviations from 2DGS's pinned `environment.yml` (py3.8/torch2.0.0/o3d0.18.0)
  recorded here; code stays separate: the two CUDA extensions
  (`diff-surfel-rasterization`, `simple-knn`) build inplace inside `2dgs/repo/`
  and are exposed via `PYTHONPATH` in 2DGS job scripts only — nothing installed
  into the shared env (both repos import `simple_knn`, so an env-level install
  would mix them). `lpips`/`mediapy` not on the train/mesh path — skipped.
