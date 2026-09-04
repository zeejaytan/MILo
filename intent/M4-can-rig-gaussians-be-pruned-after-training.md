# M4 — Can the rig Gaussians be pruned after training while keeping Gaussian-scale sharpness?

**Status:** answered NO on A03 (2026-09-06) — see verdict below · **Blocked by:** none

## Why it matters

Native MILo tet extraction looks sharp to the eye because it has no voxel grid, but it keeps the whole clamp rig (dead masks at `milo/mesh_extract_sdf.py:151,166,316,525`). DTU fusion removes the rig but smooths to 0.822 mm voxels — 4× coarser than the 0.21 mm ridges the photos hold. If rig Gaussians can be dropped post-training, we keep tet sharpness *and* lose the rig, with no retrain. If not, the choice is between a sharp mesh with steel in it and a clean mesh too coarse for reassembly.

## Done when

- [x] Pruned extraction on A03 renders with no rig steel above 5 mm — v1 (80% rule) and v2 (≥20 views) both carry zero steel-coloured solid; all solid pieces read as clay (redness +5 to +28). Conservator eye verification in CloudCompare 2026-09-06. Tight-crop renders were superseded by direct eye inspection at will.
- [ ] Break-face loss stated in millimetres of arc length versus the unpruned mesh — NOT measured; see verdict for why it cannot change the answer.
- [ ] Flat-wall noise on the same box for pruned vs unpruned vs OpenMVS (mm) — NOT measured; same reason.

## Verdict 2026-09-06: no — prune-plus-tet cannot carry break-face density on A03

Two mesh builds, one capture, both off the reassembly table on measured grounds that
arc-loss and noise numbers cannot rescue:

- v1 (fraction rule, 8,686 kept): 128k vertices, ~19x sparser than the 2.41M-vertex
  reference — density alone disqualifies it for 0.21 mm relief.
- v2 (count rule, 14,670 kept): 204k vertices but two components span 331 mm and
  218 mm — separate sherds webbed by tet sheets, and webbed sherds cannot seat.
- Kept-Gaussian footprint median 1.76 mm (p90 4.08 mm): the skin spans summed pivot
  scales, so sub-2 mm relief is attenuated before any grid or tet sees it — ~9x over
  the bar whatever threshold is picked. Fewer kept means slack skin, more kept means
  webbing; the count moves along that trade without leaving it.
- Conservator eye (CloudCompare, 2026-09-06): too coarse for any use in reassembly.

Unmeasured and stated as such: arc-loss mm and wall-noise mm. They would quantify a
failure the webbing plus footprint already establish — no number there re-seats a
webbed sherd. This is a claim about the method (type 1: it cannot do this task on this
material as assembled), not a broken ruler and not a wrong reference.

## Gate / stop condition

Fired. Per-sherd split extraction (one tet mesh per linkage cluster, webs impossible
by construction) was named but never built — it inherits the 1.76 mm film, so it is a
finer failure or a slower one, never a pass at 0.21 mm. Training-time masking stays
closed pending its own A/B (masked-training tickets 01–04, intent M2). Otherwise M1's
gate rules: depth-disagreement job, then OpenMVS on A03, code last.

## Source

Conversation 2026-09-04 (unmasked MILo looks on-par with OpenMVS to the eye; fusion-masked DTU reads coarse); `docs/notes/A03_DTU_EXTRACTION_RESULT.md`; `docs/notes/2026-09-04-milo-rig-extraction.md` routes 5–6; `docs/notes/2026-09-04-milo-vs-3dgs-limits.md` B2/R1; `.scratch/rig-pruning/` tickets 01–06; jobs 30056136 (v1 mesh) and 30086544 (v2 mesh); probe job 30090865 runs masked-training, not this question.
