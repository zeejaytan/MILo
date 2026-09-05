# 06: InstantSplat++ viewable splat via VGGT prior

**What to build:** the named downstream of the VGGT track — a viewable splat on A03 through the upstream prior-model path, judged on renders only and never in millimetres.

**Answers:** M7

**Blocked by:** 01 (OpenMVS on A03, same ruler), 02 (depth disagreement in mm), 05 (VGGT pose A/B).

**Status:** ready-for-agent

- [ ] InstantSplat++ commit pinned alongside the VGGT checkpoint; prior-model type stated; run follows the upstream prior path on the existing A03 views
- [ ] Verdict rests on renders at views resolving ~0.2 mm ridges plus the input mask-content split — rig riding along in frame is recorded as expected unmasked-renderer behaviour, not a mesh failure
- [ ] Any mesh claim behind this track is refused here and ticketed separately with voxel and band in mm; a splat that holds ridge detail earns a look-but-don't-measure role, nothing more
