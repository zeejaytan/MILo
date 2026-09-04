# 05: v2 pruned extraction job

**What to build:** `mesh_learnable_sdf_pruned_v2.ply` from the v2 keep set of ticket 04 through the unchanged tet flow (`--keep-idx` seam), plus millimetre copy and piece count on the GPU.

**Answers:** M4

**Blocked by:** 04 (needs the v2 keep set and its count sanity check).

**Status:** ready-for-agent

- [ ] Single GPU job on Spartan runs end to end and writes the v2 pruned mesh plus `_mm.ply`
- [ ] Mesh is non-empty with vertex colours like the unpruned reference
- [ ] No rig steel larger than 5 mm survives on coarse inspection, or the failure is reported with figures
- [ ] Training data, unpruned Gaussians and the v1 keep set are untouched; the log records the v2 keep-set source
