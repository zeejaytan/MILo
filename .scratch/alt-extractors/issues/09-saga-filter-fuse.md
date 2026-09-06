# 09: SAGA post-hoc filter then fuse

**What to build:** freeze the full-scene MILo Gaussians, distil SAM masks to per-Gaussian features, filter to the sherd subset at full density, then reuse the live fusion-time masked-depth path — steel out without thinning clay.

**Answers:** M7

**Blocked by:** 01 (OpenMVS on A03, same ruler), 02 (depth disagreement in mm).

**Status:** ready-for-agent

**Pinned (2026-09-06 — code audited at pin, laptop clone):** `Jumpat/SegAnyGAussians@v2@2d4c5d7` (verified HEAD on clone; full SHA `2d4c5d77c857c956d747e4775d3d72c4ec5dfe16`). Cloning to `/data/gpfs/projects/punim2657/saga/` + env `envs/saga` build running on login node (background 2026-09-06).

**Audit verdict, 2026-09-06 (desk, no GPU) — GO with one known risk:**
1. Geometry compatible: `GaussianModel.load_ply` reads by attribute NAME (`x,y,z,opacity,f_dc_0..2,f_rest_*` with count asserted `3*(sh+1)^2-3`); MILo's 19 extra props (`filter_3D`, `base_occupancy_*`, `occupancy_shift_*`) are ignored, f_rest 45 = sh3 asserts clean. Frozen source: `output/17062025/A03_nomask/point_cloud/iteration_18000/point_cloud.ply` (222,678 Gaussians — the M5 control run).
2. SAM extraction SKIPPED by design: SAGA's `extract_segment_everything_masks` + `get_scale` replaced by OUR adapter-verified masks — `sam_masks/<stem>.pt` converted from `images_masked` alpha (164/164 views, sherd-only erode0). Single binary mask/view is sufficient: contrastive loss then learns sherd-vs-background, exactly the filter wanted. Scales via SAGA's own `get_scale.py` on the staged scene.
3. Query headless: notebook path (`render features → query pixels → cosine sim → segment(>0.75) → .pt`) scriptable with our masks as the prompt — no GUI/notebook needed.
4. KNOWN RISK, update 2026-09-07: confirmed — no pytorch3d wheel for (py311, torch 2.3, cu118) at either per-combo page; login-node compile of simple-knn + all three rasterizer forks clean. pytorch3d v0.7.6 (torch-2.3 era) building from source on a GPU node via `slurm/saga_pytorch3d.slurm`, knn smoke-tested on GPU in-job.

- [ ] SAGA feature head trained on frozen full-scene `A03_nomask` Gaussians (222,678) at full capture resolution with OUR masks as the stack (`sam_masks/*.pt` from `images_masked` alpha; scales via `get_scale.py`; `train_contrastive_feature.py`)
- [ ] Sherd subset retrieved by headless mask-prompt query, keep-index → filtered ply → live path `mesh_extract_dtu.py:133-135` + `integration.py:54-59`, voxel size and truncation band stated in mm
- [ ] Same-ruler scoring vs OpenMVS (fraction within ~1 mm), break-face close-ups resolving ~0.2 mm ridges, remaining steel in cm² (`mask_content.py` split — rig was 644 cm² vs 61 cm² clay per view)
- [ ] If filtering webs steel or drains clay like M4/M5: retire NO at one capture with eye verification (type-1 method failure), do not fund a second post-hoc architecture

## Comments

- 2026-09-06 (trail start, both-in-order track 2/3): M7 added this track 2026-09-06 but spec/issues 01–08 never ticketed it — this file closes the gap. Caution: SAGA paper notes weak regime on small targets absent from SAM masks (ours 2.28% of frame); masks must be consistent across all 143 views or the ID splits. Geometry untouched by construction (only affinity dim-32 attached). Standing approval for Slurm submits noted 2026-09-06.
- 2026-09-07: env complete (torch 2.3.1+cu118; simple-knn + 3 rasterizers compiled login-node; pytorch3d 0.7.6 source-built on GPU, knn GPU-tested). Submitted job 30169355 (`slurm/saga_train.slurm`): stage our 164 masks to `sam_masks/*.pt`, `get_scale.py`, then feature-head-only 10k iters on frozen A03_nomask scene. Query + fusion in a second job after looking. Poll running.
