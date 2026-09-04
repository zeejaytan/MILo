## Problem Statement

**Answers:** M4 (MILo project — this spec is the plan that tickets 01–03 execute).

Unmasked native MILo extraction looks as sharp as OpenMVS to the eye on sherd clay, but it keeps the entire clamp rig, so the mesh cannot go to reassembly. Masked DTU fusion removes the rig cleanly (10 pieces for 10 sherds on A03) but smooths to 0.822 mm voxels — about 4x coarser than the 0.21 mm ridges the photographs hold — so the break face it produces cannot be matched. Training-time masking is closed: the old patch painted background over 0.6–0.9 mm of real edge and was removed. The conservator needs one MILo path that keeps tet-level sharpness and drops the rig.

## Solution

Prune rig Gaussians after training instead of masking during training or voxelising during fusion. Vote every Gaussian centre against the existing sherd-only outlines across all training views, keep clay, drop steel, then run the unchanged tet extraction from the survivors and drop sub-sherd specks with a component-size rule. Proof is a tight zoom on one break face plus millimetre numbers, never a full-tray view.

## User Stories

1. As a conservator, I want a MILo mesh with no rig steel in it, so that reassembly never matches against clamp geometry.
2. As a conservator, I want the break face preserved to the ridges the photos show (~0.21 mm), so that joins seat on real relief, not smoothed guesses.
3. As a conservator, I want occlusion gaps left open where the jaws hid clay, so that I see missing evidence instead of invented surface.
4. As a conservator, I want edge loss stated in millimetres of arc per sherd, so that I know what pruning cost the join.
5. As a conservator, I want flat-wall noise in mm for pruned vs unpruned vs OpenMVS on the same box, so that sharpness is a number, not an eye read.
6. As a conservator, I want the proof render at 0.10 mm/px on the break face itself, so that a full-sherd view cannot hide smoothing again.
7. As a researcher, I want training untouched (reuse the unmasked Gaussians as-is), so that no background gets painted over the fracture rim.
8. As a researcher, I want the vote rule stated as keeps and drops with counts, so that a later run can reproduce the keep set.
9. As a researcher, I want specks removed by component size with the kept count reported, so that cleaning never eats a small sherd silently.
10. As a researcher, I want a stop rule with numbers (rig solid above 5 mm fails; break-face loss above ~1 mm of arc fails), so that a bad outcome stops the route instead of drifting into tuning.
11. As a researcher, I want the result written back into intent M4 with a date, so that the question closes whatever the outcome.

## Implementation Decisions

- Single seam: filter the Gaussian set after loading and before pivot building, inside the existing tet extraction flow. Everything downstream — pivots, triangulation, refinement, marching tetrahedra, colours — runs unchanged.
- Vote source is the existing sherd-only outline set already proven on A03 (erode0, on the clay edge), read through the train cameras the way the DTU path reads them. No new mask production, no undistortion work, no retraining.
- Keep rule: a Gaussian survives only if its centre lands inside the outline in at least 80% of the views where it is in front of the camera. Depth-ordering uses the rendered median depth already available at extraction time.
- No change to the refinement losses, edge-collapse flags, or out-of-frustum handling for this ticket; they are measured later, not tuned now.
- Speck cleaning reuses the existing largest-components shape already present for the regular volume path (keep N largest, report kept vs dropped faces), applied to the tet mesh, never to the Gaussian set.
- Prototype decision encoded from discussion: projection vote at centres (not scales, not opacities) is the v1 rule; scale-aware voting is explicitly deferred until v1 renders.
- No dilation on the outline: the vote samples the erode0 alpha raw. Dilating would vote the clamp rim back in; the cull's disk(6) generosity is the opposite choice for the opposite job.
- Never-seen Gaussians are dropped, not kept. A Gaussian in front of no training camera was photographed by nothing, so it cannot be clay. This is decided here, not inherited from the integration path's never-seen-means-solid convention.
- Known limitation, v1: the vote has no occlusion term. A rig Gaussian sitting directly behind clay from every angle that sees it would project inside the outline and survive. Rods encircle the tray so most segments stand beside clay from most angles, but if the pruned mesh keeps rig-like solid behind sherd faces, v2 compares projected depth against rendered median depth per view (GPU) before voting.
- Scope is one capture (A03): the vote runs over the whole cloud, and proof crops to one sherd (piece 1, the large 33 x 79 x 74 mm body) for renders and numbers; the tray-wide verdict is a separate ticket gated on this one passing.

## Testing Decisions

- A good test here checks outside behaviour, not code shape: rig absent above 5 mm, break-face arc loss in mm, flat-wall noise in mm, all on named boxes and named renders. Anything asserting internal tensor shapes is out.
- Modules under test: the Gaussian vote filter (kept/dropped counts, determinism on seed), the tet extraction from a filtered set (runs end to end, mesh non-empty), and the component filter (589-speck behaviour: drops specks, keeps all 10 sherd-sized pieces on the A03 fusion reference).
- Prior art to follow: the CPU login-node diagnostic that reprojects the mesh into all training views in ~2 min; the silhouette-compare held-out-view discipline (21 views, sherds-only second pass); the A02 thirteen-plate verification habit (every claim paired with a figure); gate-style self-tests that prove the check can fail (a synthetic rig blob must be dropped, a synthetic sherd edge must survive).
- The render is part of the test, not decoration: no acceptance box ticks without the 0.10 mm/px break-face crop from the same window for pruned, unpruned, and OpenMVS side by side.

## Out of Scope

- Retraining with masks; any change to the training loss.
- DTU voxel path changes, tiling, block-limit work, or the Open3D version.
- VDBFusion, new dependencies, or any new training pipeline (2DGS and friends).
- OpenMVS, COLMAP, or pottery-photogrammetry config changes.
- Re-photography, cross-polarisation, or remounting to recover jaw contact.
- Full-tray production runs or Slurm automation beyond the single proof job.

## Further Notes

- Answers intent M4 (MILo project). M1's gate still stands around this work: the depth-disagreement measurement and OpenMVS-on-A03 comparison decide whether any extraction code is worth building for this material; this spec is the code-last branch, scoped to one sherd so the cost stays small if the gate later says stop.
- Seams proposed at the highest point available (filter the set, reuse everything below). Confirm they match expectations before tickets are cut; `to-tickets` follows this spec.
- Triage state for the coming tickets: ready-for-agent once cut.
