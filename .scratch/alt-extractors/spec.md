## Problem Statement

**Answers:** M7 (MILo project — this spec is the plan that settles whether TopoSurfel or VGGT + InstantSplat++ can separate sherd from rig at the resolution a break face needs).

**Status:** ready-for-agent

MILo's own DTU extraction route is closed on quality grounds, and two retired lines showed that removing the steel is easy but removing it without thinning the clay past use is the hard part. Two candidates stand outside the door: TopoSurfel, claimed for accuracy, and VGGT, claimed for speed, with InstantSplat++ named as VGGT's downstream viewable-splat route. Neither separates sherd from rig as shipped — TopoSurfel exposes no mask input and grows its starting surface from an unmasked init, VGGT predicts everything in frame including the rig — and neither has shown anything at the quarter-millimetre scale of a fracture ridge. The conservator needs a gated, same-ruler verdict on existing material, not a fresh build campaign on promise.

## Solution

Evaluate both tracks against the same bar on the same capture, in order: M1's two cheap boxes first (what OpenMVS already does on A03; cross-view depth disagreement in mm), then pinned one-capture A/Bs on the existing sherd-only dataset at full capture resolution. TopoSurfel is judged on masking at fusion time; VGGT is judged as a pose source first; the InstantSplat++ splat is judged on renders only, never in millimetres. If OpenMVS already clears the ~1 mm relief the break faces need, record it and stop rather than swapping. Either a candidate clears a bar MILo cannot and earns its keep, or it lands on the same ceiling and the question retires with numbers attached.

## User Stories

1. As a conservator, I want the ten sherds separated from the clamps, rods and jaws by any candidate route, so that no reassembly decision ever reads steel as clay.
2. As a conservator, I want break-face relief at ~1 mm preserved by any candidate mesh, so that the edge the matcher reads is photographed clay, not smoothed guesswork.
3. As a conservator, I want any mesh at true scale or refused, so that a millimetre figure I act on is a millimetre.
4. As a conservator, I want break-face close-ups at a view resolving ~0.2 mm ridges before any number, so that a wrong-scale picture cannot pass off a coarse mesh the way whole-tray views did before.
5. As a conservator, I want remaining steel stated in cm² on the mesh actually extracted, so that "clean" is a measurement and not an impression.
6. As a conservator, I want the clamp-contact faces written down as unobserved rather than filled in, so that no method invents clay nobody photographed.
7. As a conservator, I want a fast viewable splat judged as viewing-only, so that a good-looking render is never mistaken for a measurable surface.
8. As a researcher, I want M1's two boxes measured before any candidate builds, so that a swap that lands on the same ceiling is never funded.
9. As a researcher, I want TopoSurfel pinned by commit alongside its PGSR init before any job, so that the run is repeatable.
10. As a researcher, I want VGGT pinned by checkpoint with InstantSplat++ pinned alongside it, so that the pose-plus-splat route is repeatable.
11. As a researcher, I want TopoSurfel trained and extracted at full capture resolution with voxel size and truncation band stated in millimetres, so that the voxel is a claim about sampling, not a hidden coarsening.
12. As a researcher, I want VGGT cameras compared against the COLMAP solve on the same capture, so that the pose track is scored as poses.
13. As a researcher, I want cross-view depth disagreement in millimetres for each candidate versus MILo's DTU route on the same ruler, so that the honest resolution floor is measured, not assumed.
14. As a researcher, I want the same-ruler OpenMVS comparison reused from M1, not a second ruler, so that fraction-within-requirement means the same thing for every route.
15. As a researcher, I want the mask-content steel-versus-clay split recorded for the inputs actually used, so that a candidate fed the rig cannot be credited with removing it.
16. As a researcher, I want the 32,768-block cliff assumed to bind TopoSurfel's TSDF extraction until shown otherwise, so that a crash at the required voxel is read as the known ceiling, not a new mystery.
17. As a researcher, I want masked-training and post-training pruning stays retired and unrelitigated under either candidate without fresh justification, so that two settled NOs are not re-bought at GPU prices.
18. As a researcher, I want the result written back into intent M7 with a date either way, so that the question closes even when the answer is "uninformative".

## Implementation Decisions

- Scope is one capture and its existing sherd-only dataset; second captures and second seeds follow only if the verdict is releasable. No re-photography, no re-mount for this work; clamp-contact holes stay recorded as unobserved.
- Sequencing is fixed: M1's OpenMVS-on-A03 box and depth-disagreement box run first and gate everything; candidate tickets are charted but unbuilt until those land. If OpenMVS already meets the requirement, the spec stops there by its own gate.
- TopoSurfel track is judged on fusion-time masking only. Its first decision is a mask-path audit against the shipped arguments (no mask flag at HEAD): either a masked init plus fusion-time zeroing route is stated in the ticket, or the track does not build. Training resolution stays at full capture density with no silent downsample; the object-centric indoor metric applies as with MILo.
- VGGT pose track names its checkpoint up front and scores cameras against the COLMAP solve on the same capture, with scale anchored per the true-scale question — an unscaled result is refused, never measured.
- InstantSplat++ splat track runs the upstream prior-model path with the prior type stated, and its verdict rests on renders at ridge-resolving views plus the input mask-content split. It never clears a mesh box; any mesh claim behind it must be ticketed separately with voxel and band in mm.
- Pinned versions are recorded in the ticket before any submission: TopoSurfel plus PGSR commits, VGGT checkpoint, InstantSplat++ commit, dependency build notes where they affect repeatability. An unpinned run is not a result.
- Standing machine rules carry over unchanged: heavy data stays on the cluster, small renders and metrics land locally, no Slurm submission without explicit approval, full-resolution training throughout.
- The small-object literature half of the background research is still owed and is ticketed, not silently dropped.

## Testing Decisions

- A good test here compares routes against each other on the same capture and the same ruler, never against ground truth (none exists): candidate versus MILo's DTU route versus OpenMVS, all in millimetres with scale sidecars, fraction of sherd surface within the M1 requirement as the shared figure.
- Modules under test: the TopoSurfel mask path (rig absent from the fused grid with clay intact at the rim), the VGGT pose output (camera agreement with the COLMAP solve), the splat renders (ridge detail at resolving views), and the instrumentation itself (mask-content split on the inputs actually used; block counts and free-memory figures printed before any extraction).
- Prior art to follow: the every-8th-view holdout discipline for honest views; the thirteen-plate verification habit of pairing every claim with a figure; gate-style self-checks that prove the instrumentation can fail; the render-before-number rule — no scoring box ticks without close-ups at a scale that resolves the feature, and per-vertex unbinned views where a proxy picture keeps failing.
- Each verdict names which of the three it is — method failed on this material, measurement broken, or reference answer wrong — because those lead to opposite decisions.

## Out of Scope

- Re-animating masked training or post-training pruning under either candidate (retired under M4/M5; fresh justification required).
- Tiling or chunked-extraction builds before M1's boxes report; if a candidate hits the block cliff at the required voxel, the question is amended to the tiling question rather than built around silently.
- Poisson-based point-cloud meshing across occlusion holes (invents unphotographed surface; worse than a hole for a conservation record).
- COLMAP, OpenMVS or photogrammetry config changes; re-photography, remounting or lighting changes.
- Second seeds, second captures, or density-drain relitigation unless the base A/B passes.
- Any chapter-level method-list decision (that is U7's business; this spec only produces the numbers U7 will need).

## Further Notes

- Answers intent M7; M1's gate stands around this work — this spec is the branch where an outside route earns its GPU-h, and the stop condition is part of the spec, not an afterthought.
- Triage state for the coming tickets: ready-for-agent once cut via `to-tickets`.
- Vocabulary follows the project glossary: masking, pruning and culling are three different operations; a splat is judged on renders, never in millimetres.
