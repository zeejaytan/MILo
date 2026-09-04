# 02: Pruned tet extraction end to end

**What to build:** one pruned mesh of A03 piece 1, produced by running the unchanged tet extraction flow from the filtered Gaussian set of ticket 01 — the keep indices feed the flow's existing downsample-index seam before pivots are built, and pivots, triangulation, refinement, marching tetrahedra and colours all run as before, mesh non-empty, with a coarse rig-absent check.

**Answers:** M4

**Blocked by:** 01 (needs the keep set and its counts).

**Status:** claimed (wiring done, job submitting)

- [ ] Single GPU job on Spartan runs end to end from the filtered set and writes `mesh_learnable_sdf_pruned.ply` for piece 1
- [ ] Mesh is non-empty and carries vertex colours like the unpruned reference
- [ ] No rig steel larger than 5 mm survives in the pruned mesh on coarse inspection, or the ticket reports the failure with figures (including rig surviving behind clay faces — the recorded v1 occlusion limitation)
- [ ] Training data and unpruned Gaussians are untouched; the job log records the keep-set source from ticket 01
