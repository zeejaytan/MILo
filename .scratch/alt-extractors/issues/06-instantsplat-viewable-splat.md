# 06: InstantSplat++ viewable splat via VGGT prior

**What to build:** the named downstream of the VGGT track — a viewable splat on A03 through the upstream prior-model path, judged on renders only and never in millimetres.

**Answers:** M7

**Blocked by:** 01 (OpenMVS on A03, same ruler), 02 (depth disagreement in mm), 05 (VGGT pose A/B).

**Status:** wontfix

**Reason, 2026-09-06:** 05 retired the pose track NO (type-1, both input modes + BA refusal) — the VGGT prior this splat is built on is known-garbage on A03, so a VGGT-prior splat cannot be an honest test of anything. An unposed splat would be a different ticket (voxel/band in mm + scale anchoring per M7), not this one. No GPU spent here by design.

**Pinned (desk, 2026-09-06 — provisional, still blocked by 05, no job submitted):** `phai-lab/InstantSplatPP@0d5f8f5` (HEAD 2026-02-27, 2 commits — re-verify before any job). Path `scripts/run_all_prior_model.bash` with `PRIOR_MODEL_TYPE=vggt` (`init_geo.py --model_type vggt`, default ckpt `./vggt/checkpoints/VGGT_model.pth`, fallback HF `facebook/VGGT-1B`). Supports 3D-GS / 2D-GS / Mip-Splatting. No mask flag documented; no scaled-mesh export. Viewing-only by design.

- [ ] InstantSplat++ commit pinned alongside the VGGT checkpoint; prior-model type stated; run follows the upstream prior path on the existing A03 views
- [ ] Verdict rests on renders at views resolving ~0.2 mm ridges plus the input mask-content split — rig riding along in frame is recorded as expected unmasked-renderer behaviour, not a mesh failure
- [ ] Any mesh claim behind this track is refused here and ticketed separately with voxel and band in mm; a splat that holds ridge detail earns a look-but-don't-measure role, nothing more

## Comments

- 2026-09-06 (trail start, both-in-order track 3/3): waits on 05. Design target is sparse-view large scenes (opposite of 143 dense views of 20–80 mm sherds), so judge on break-face close-ups only, never mm. No Slurm without approval.
