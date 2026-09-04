# M4 — Can the rig Gaussians be pruned after training while keeping Gaussian-scale sharpness?

**Status:** open · **Blocked by:** none · **Effort:** ~half a day (one sherd, CPU vote + one tet extraction + renders)

## Why it matters

Native MILo tet extraction looks sharp to the eye because it has no voxel grid, but it keeps the whole clamp rig (dead masks at `milo/mesh_extract_sdf.py:151,166,316,525`). DTU fusion removes the rig but smooths to 0.822 mm voxels — 4× coarser than the 0.21 mm ridges the photos hold. If rig Gaussians can be dropped post-training, we keep tet sharpness *and* lose the rig, with no retrain. If not, the choice is between a sharp mesh with steel in it and a clean mesh too coarse for reassembly.

## Done when

- [ ] Pruned extraction on A03 (Gaussians from `output/17062025/A03_nomask`, erode0 masks) renders with no rig above 5 mm and no rig-shaped solid at the clamp contact, checked at 0.10 mm/px tight crops on one break face
- [ ] Break-face loss stated in millimetres of arc length versus the unpruned mesh on the same sherd — not in pixels or vertex counts
- [ ] Flat-wall noise on the same box reported for pruned vs unpruned vs OpenMVS (mm), so sharpness is a number, not an eye read

## Gate / stop condition

If the pruned mesh keeps rig-like solid (unobserved = solid sign convention wins) or cuts more than ~1 mm of break-face arc to clear the rig, stop: keep training-time masking closed (removed at `770338f` for painting 0.6–0.9 mm of edge) and fall back to M1's gate — depth-disagreement job, then OpenMVS on A03, code last. This is a claim about the method (it cannot separate steel from clay post-hoc), not a broken ruler.

## Source

Conversation 2026-09-04 (unmasked MILo looks on-par with OpenMVS to the eye; fusion-masked DTU reads coarse); `docs/notes/A03_DTU_EXTRACTION_RESULT.md`; `docs/notes/2026-09-04-milo-rig-extraction.md` routes 5–6; `docs/notes/2026-09-04-milo-vs-3dgs-limits.md` B2/R1.
