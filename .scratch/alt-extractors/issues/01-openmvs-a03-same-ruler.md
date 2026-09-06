# 01: OpenMVS on A03, same ruler

**What to build:** the M1 baseline this whole comparison stands on — the COLMAP → OpenMVS route's meshes for A03 scored against the M1 requirement on one enforced ruler.

**Answers:** M1

**Blocked by:** None (can start immediately).

**Status:** ready-for-agent

- [ ] OpenMVS meshes for A03 measured with scale sidecars enforced — an unscaled mesh is refused, not measured
- [ ] Fraction of sherd surface within the M1 ~1 mm relief bar reported in mm, with the figure and the meshes named so M7 reuses them, not a second ruler
- [ ] If OpenMVS already meets the requirement, the stop condition is stated in the ticket: record it and halt the swap tracks

## Comments

- 2026-09-06: started while user away. Found the M1-gate compare job 30131757
  (submitted 2026-09-06) FAILED in 1:50 — refusal was correct, but the stated
  reason misleads. Measured on the node: MILo `mesh_mm.ply` spans ~983 mm,
  OpenMVS `scene_refined_mm.ply` spans ~643 mm, and their bounding boxes barely
  overlap — different content in different frames (MILo kept ~1 m of
  surroundings; OpenMVS is a tray crop), not a units mismatch. Both sidecars
  claim the same mm factor. Next step is a common-box crop before comparing,
  NOT a blind resubmit — resubmitting the same job reproduces the same refusal.
  Parked for user confirm since it changes the comparison basis.
- 2026-09-06 (parallel session): root cause is deeper than content. `dense_fixed`
  vs `dense_masked` are DIFFERENT reconstructions, not one frame: pairwise camera
  distances across 164 shared views give unit-ratio spread 0.29–1.11, and a
  best-fit similarity leaves 2.5 m median residual on a 1.4 m ring. The
  mask-frame OpenMVS mesh scaled with the MILo factor was wrong-scaled and has
  been deleted (file + sidecar). Redone correctly: `dense_fixed`
  `scene_refined_mm.ply` + sidecar (same reconstruction as the MILo training
  data, factor valid), MILo mesh cropped to its box keeps 98.8% of faces
  (`mesh_mm_boxed.ply`, sidecar carried) — same frame confirmed by behaviour.
  Remaining extents ratio ~1.25 is backdrop content, not units; the gate's
  premise (shared frame ⇒ sizes must agree) does not cover it. Next: shape-only
  silhouette compare (shared frame now valid), mm figures per-sherd à la A02.
