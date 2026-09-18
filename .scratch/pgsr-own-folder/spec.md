## Problem Statement

**Answers:** M8

**Status:** ready-for-agent

Photographs of Rabati sherds become meshes today by two routes: the existing photogrammetry route beside MILo, and the Gaussian-splatting route inside the MILo fork. The candidate that could replace the splatting side — PGSR, a planar-based splatting route with its own training plus its own TSDF fusion — currently has nowhere of its own to live. Its evaluation is ticketed inside MILo, its future checkout would sit inside a fork of a different method, and its question (M8: does PGSR replace MILo at the resolution a break face needs?) is asked from inside the thing it is meant to replace.

That placement causes three concrete problems. First, the MILo fork tracks an upstream method with a kept-current list of fork changes that a rebase must survive; unrelated PGSR checkouts, environments, job scripts and outputs inside it blur what belongs to the fork and what does not. Second, the workspace rule is that code, job scripts and parameters live in the nested project they belong to, and tickets live where the code they change lives — PGSR work kept under MILo breaks both. Third, the renderer file vendored inside MILo is not standalone PGSR; the standalone method (stock upstream plus the community masked-fusion construction) is a separate build with its own pins, and judging it from inside MILo invites reusing MILo's masks, scales and verdicts without stating them.

## Solution

Give PGSR its own top-level project folder, separate from the MILo fork, and start M8's verdict there: a pinned one-capture A/B on the existing sherd-only dataset at full capture resolution, judged on the same ruler as MILo and the photogrammetry route, with break-face close-ups before any number.

The new folder carries the standing project shape (own remote pair, own job-script area, heavy data gitignored and staying on the cluster, small renders and metrics as the local landing zone, own project working notes, own intent folder with a fresh single-letter prefix since P is taken). MILo keeps its fork, its closed DTU verdict, and its retired pruning and masked-training lines untouched. M8 stays the question being answered; the new folder holds the work that answers it. If the trial shows PGSR lands on the same ceiling MILo hit, the question retires with numbers attached instead of gaining a second home for motion without progress.

## User Stories

1. As a conservator, I want PGSR's meshes judged as meshes from a separate method, so that no reassembly decision ever inherits trust from MILo by folder proximity.
2. As a conservator, I want the ten sherds separated from clamps, rods and jaws by each PGSR variant, so that steel is never read as clay.
3. As a conservator, I want break-face relief at about one millimetre preserved in any PGSR mesh put forward, so that the edge the matcher reads is photographed clay, not smoothed guesswork.
4. As a conservator, I want any PGSR mesh at true scale or refused, so that a millimetre figure I act on is a millimetre.
5. As a conservator, I want break-face close-ups at a view resolving roughly two-tenths-of-a-millimetre ridges before any score, so that a whole-tray view cannot pass off a coarse mesh the way it has before.
6. As a conservator, I want remaining steel stated in square centimetres on each extracted mesh, so that clean is a measurement and not an impression.
7. As a conservator, I want clamp-contact faces written down as unobserved rather than filled in, so that no method invents clay nobody photographed.
8. As a conservator, I want a fast viewable splat judged as viewing-only where one exists, so that a good-looking render is never mistaken for a measurable surface.
9. As a researcher, I want the standalone PGSR build pinned by commit for both stock upstream and the community masked-fusion construction before any job, so that the run is repeatable.
10. As a researcher, I want training at full capture resolution with no silent downsample, so that the trial answers the resolution question actually asked.
11. As a researcher, I want the voxel size and truncation band stated in millimetres for every extraction, so that the grid is a claim about sampling, not a hidden coarsening.
12. As a researcher, I want both extraction variants from the same training (fusion-masked via the community alpha path, and cull-after on stock), so that the mask construction is the variable, not the seed.
13. As a researcher, I want cross-view depth disagreement in millimetres for PGSR versus the MILo route on the same capture and the same ruler, so that the honest resolution floor is measured, not assumed.
14. As a researcher, I want the same-ruler photogrammetry comparison reused from the resolution question, not a second ruler, so that fraction-within-requirement means the same thing for every route.
15. As a researcher, I want the steel-versus-clay split recorded for the inputs actually used, so that a variant fed the rig cannot be credited with removing it.
16. As a researcher, I want the known extraction block ceiling assumed to bind the TSDF step until shown otherwise, so that a crash at the required voxel is read as the known ceiling, not a new mystery.
17. As a researcher, I want retired lines to stay retired (post-training pruning, training-time masking) without fresh justification, so that two settled NOs are not re-bought at GPU prices.
18. As a researcher, I want the MILo fork's change list untouched by PGSR files, so that a future rebase onto upstream has only the documented fork changes to survive.
19. As a researcher, I want the result written back into M8 with a date either way, so that the question closes even when the answer is uninformative.
20. As a researcher, I want the new folder to follow the standing new-project shape (remote pair, job area, ignored heavy paths, project working notes), so that the next agent inherits layout, not archaeology.

## Implementation Decisions

- Scope is separation plus one-capture verdict, in that order: first the new project shell exists and MILo stops being its home; then the pinned A/B runs once on the existing sherd-only dataset. No re-photography, no re-mount; clamp-contact holes stay recorded as unobserved.
- The new project is a sibling of the existing reconstruction projects, not a subdirectory of the MILo fork and not a file at the workspace root. The MILo fork's tracked change list gains nothing from this work.
- Remote pairing follows the standing shape: a personal fork as the writable remote, the canonical PGSR source as the read-only upstream, with the cluster checkout pulling read-only. No direct pushes to canonical sources.
- The two PGSR sources are treated as distinct builds with separate pins recorded before any submission: stock upstream for the cull-after variant, the community masked-fusion construction for the fusion-masked variant. An unpinned run is not a result.
- Masking here means fusion-time outlines deciding what counts as clay when depth enters the grid, plus a small-component filter after fusion for the stock variant. Training-time masking and post-training pruning of the splat stay retired and are not relitigated without fresh justification.
- Resolution discipline carries over unchanged: full capture density throughout, object-centric indoor metric, every held-out view discipline kept for honest views, scale anchored per the true-scale question with unscaled results refused rather than measured.
- Sequencing inside the trial is fixed: the two cheap boxes first (what the photogrammetry route already does on the capture; depth disagreement in millimetres), then the PGSR A/B. If the photogrammetry route already clears the roughly-one-millimetre relief the break faces need, that is recorded and the swap case must clear parity-plus or complementary coverage, not merely run.
- The verdict distinguishes the three failure kinds because they lead to opposite decisions: the method failed on this material, the measurement was broken, or there was never valid material to score against.
- Standing machine rules carry over unchanged: heavy data stays on the cluster, small renders and metrics land locally.
- Cluster env is reused where its imports resolve (the MILo env already carries the plane rasterizer the vendored renderer imports); no fresh env build unless an import probe fails, then only the additive delta.
- Intent prefix for the new folder is **R** (reserved 2026-09-09; U/C/G/M/O/P/S taken, R free and mnemonic). New PGSR questions become R1, R2… M8 remains the question this first work answers until a new-folder question supersedes it by amendment, never by duplication.

## Testing Decisions

- A good test here compares routes against each other on the same capture and the same ruler, never against ground truth (none exists for a Rabati sherd): PGSR both variants versus the MILo route versus the photogrammetry route, all in millimetres with scale provenance, fraction of sherd surface within the resolution requirement as the shared figure.
- Seams, as agreed (repo-boundary plus live run): the boundary half checks the new folder exists as a sibling with the standing shape, the writable and canonical remotes resolve, no PGSR build imports from the MILo fork, heavy paths are ignored, project notes and the link gate pass. The live half trains the pinned PGSR build once on the existing dataset at full resolution and extracts both variants with voxel and band stated in millimetres.
- Modules under test: the separation itself (nothing PGSR-side reaches into MILo at build, train or fuse time); the masked-fusion path (rig absent from the fused grid with clay intact at the rim); the stock path plus post-fusion component filter (steel area in square centimetres on the mesh actually extracted); the instrumentation itself (input steel-versus-clay split; block counts and free-memory figures printed before any extraction).
- Prior art to follow: the every-Nth-view holdout discipline for honest views; pairing every claim with a figure; gate-style self-checks that prove the instrumentation can fail; the render-before-number rule — no scoring box ticks without close-ups at a scale that resolves the ridge, and per-vertex unbinned views where a proxy picture keeps failing.
- Each verdict names which of the three it is — method failed on this material, measurement broken, or reference answer wrong.
- The loop gate runs after ticketing and after close: the link checker must report zero errors, and any resolved ticket must have moved its question.

## Out of Scope

- Re-animating training-time masking or post-training pruning under PGSR (retired under prior verdicts; fresh justification required).
- Tiling or chunked-extraction builds before the cheap boxes report; if PGSR hits the block ceiling at the required voxel, the question is amended to the tiling question rather than built around silently.
- Point-cloud meshing across occlusion holes that invents unphotographed surface; worse than a hole for a conservation record.
- Photogrammetry or capture config changes; re-photography, remounting or lighting changes.
- Second seeds, second captures, or density-drain relitigation unless the base A/B passes.
- Any chapter-level method-list decision (that belongs to the cross-project comparison question; this spec only produces the numbers it will need).
- Moving or rewriting historical MILo notes and verdicts; history stays where it was written.

## Further Notes

- Answers M8; triage state for the coming tickets is ready-for-agent once cut via to-tickets. Vocabulary follows the project glossary: masking, pruning and culling are three different operations; a splat is judged on renders, never in millimetres.
- M8 is currently open with no ticket behind it; this spec is the first work behind it. TopoSurfel stays under its own question (it needs a PGSR starting mesh first, so this trial gates it, not the reverse).
- Next step is to-tickets slicing the boundary half and the live half into single-context tickets, each carrying its Answers line, then the link gate.
