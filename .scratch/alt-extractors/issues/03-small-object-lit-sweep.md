# 03: Small-object literature sweep

**What to build:** the owed half of the background research — how experienced people use TopoSurfel, VGGT and InstantSplat++ (or their close kin) on small dense-view objects, from primary sources at pinned versions.

**Answers:** M7

**Blocked by:** None (can start immediately).

**Status:** resolved

- [x] Sources are the guides at pinned versions plus papers, issue trackers and forums for the *task* (dense turntable / small-object / sub-mm detail), not the tools in general
- [x] Findings captured as cited notes stating for each candidate whether the evidence supports, contradicts, or says nothing about sherd-scale masked extraction
- [x] Gaps stated plainly where no independent experience exists — absence of evidence is not evidence either way

## Comments

- 2026-09-06: web search was unavailable in this session (tool cancelled on
  every attempt, twice), so the independent-experience half cannot run here.
  Partial substitute completed: primary-source code audit of TopoSurfel at
  pinned HEAD (see ticket 04) plus the VGGT/InstantSplat++ README+paper reads
  already in M7. Ticket stays open until search is available and the sweep runs.
- 2026-09-06 (later same day): search restored, sweep run. Findings:
  1. **VGGT resizes every input image to 518×518** (ISPRS Ann. 2026 DTU
     uncertainty analysis, VGGT-1B checkpoint): ~6× downsample of our 3200 px
     captures, ≈1.3 mm/px at the object against 0.21 mm/px photographed. Its
     depth/point maps cannot resolve ~1 mm break-face relief — hard number
     behind M7's pose-source-only framing. Same study: point-map branch is
     weaker than depth-plus-camera unprojection; confidence threshold 2.0 is
     the recommended filter start; uncertainty is aleatoric only, no metric
     per-point figure — so no metrology-grade output without downstream work.
  2. **InstantSplat is sparse-view (2–3 images), large-scale, photometric**
     (paper arXiv:2403.20309: 7.5 s, SSIM 0.3755→0.7624 in 3-view; MASt3R
     priors; co-visibility init; confidence-aware GauBA). The opposite corner
     from 143 dense views of 20–80 mm sherds. The PyPI `instantsplat` variant
     documents COLMAP keypoint masking (`input_mask/` folder) and a
     VGGT+COLMAP-BA path — helps SfM ignore rig features, says nothing about
     mesh extraction. Viewing-only verdict in M7 stands.
  3. **Community masked-training experience matches M4/M5**
     (`graphdeco-inria/gaussian-splatting` issue #127): alpha-channel masking
     merely blacks pixels rather than excluding them; masked training leaves
     floater ellipsoids in masked areas; the init point cloud must also be
     masked. Same exclusion-without-replacement trade, third architecture.
  4. **Gap:** no independent TopoSurfel small-object or masked-turntable
     experience found anywhere — the audit in 04 is the only evidence, and it
     is code reading, not a run.
