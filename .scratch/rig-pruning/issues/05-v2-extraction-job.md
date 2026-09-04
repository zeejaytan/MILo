# 05: v2 pruned extraction job

**What to build:** `mesh_learnable_sdf_pruned_v2.ply` from the v2 keep set of ticket 04 through the unchanged tet flow (`--keep-idx` seam), plus millimetre copy and piece count on the GPU.

**Answers:** M4

**Blocked by:** 04 (needs the v2 keep set and its count sanity check).

**Status:** resolved (job 30086544 submitted 2026-09-05: v2 keep set kept_idx_v2.npy → mesh_learnable_sdf_pruned_v2.ply; log MILo/logs/milo_prune_30086544.log)

- [ ] Single GPU job on Spartan runs end to end and writes the v2 pruned mesh plus `_mm.ply`
- [ ] Mesh is non-empty with vertex colours like the unpruned reference
- [ ] No rig steel larger than 5 mm survives on coarse inspection, or the failure is reported with figures
- [ ] Training data, unpruned Gaussians and the v1 keep set are untouched; the log records the v2 keep-set source

## Answer

v2 mesh built by job 30086544: 204k verts, zero steel, webbed 331/218 mm, footprint median 1.76 mm. Counts toward the M4 no. Recorded in intent/M4-can-rig-gaussians-be-pruned-after-training.md (2026-09-06).
