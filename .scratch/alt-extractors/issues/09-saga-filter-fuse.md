# 09: SAGA post-hoc filter then fuse

**What to build:** freeze the full-scene MILo Gaussians, distil SAM masks to per-Gaussian features, filter to the sherd subset at full density, then reuse the live fusion-time masked-depth path — steel out without thinning clay.

**Answers:** M7

**Blocked by:** 01 (OpenMVS on A03, same ruler), 02 (depth disagreement in mm).

**Status:** ready-for-agent

**Pinned (desk, 2026-09-06 — provisional, no job submitted):** `Jumpat/SegAnyGAussians@v2@2d4c5d7` (HEAD 2026-08-02 — re-verify full SHA before any job).

- [ ] SAGA feature head trained on frozen full-scene `A03_sherds` Gaussians at full capture resolution (`train_scene.py` frozen → `extract_segment_everything_masks.py` + `get_scale.py` → `train_contrastive_feature.py` ~5–10 min default)
- [ ] Sherd subset retrieved by mask query (`saga_gui.py` / `prompt_segmenting.ipynb`), keep-index wired to live path `mesh_extract_dtu.py:133-135` + `integration.py:54-59`, voxel size and truncation band stated in mm
- [ ] Same-ruler scoring vs OpenMVS (fraction within ~1 mm), break-face close-ups resolving ~0.2 mm ridges, remaining steel in cm² (`mask_content.py` split — rig was 644 cm² vs 61 cm² clay per view)
- [ ] If filtering webs steel or drains clay like M4/M5: retire NO at one capture with eye verification (type-1 method failure), do not fund a second post-hoc architecture

## Comments

- 2026-09-06 (trail start, both-in-order track 2/3): M7 added this track 2026-09-06 but spec/issues 01–08 never ticketed it — this file closes the gap. Caution: SAGA paper notes weak regime on small targets absent from SAM masks (ours 2.28% of frame); masks must be consistent across all 143 views or the ID splits. Geometry untouched by construction (only affinity dim-32 attached). No Slurm without approval.
