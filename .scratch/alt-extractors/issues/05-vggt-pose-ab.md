# 05: VGGT pose A/B vs COLMAP

**What to build:** VGGT judged as what it is — a pose source — with its cameras scored against the COLMAP solve on the same capture.

**Answers:** M7

**Blocked by:** 01 (OpenMVS on A03, same ruler), 02 (depth disagreement in mm).

**Status:** ready-for-agent

**Pinned (desk, 2026-09-06 — provisional until run time, no job submitted):** checkpoint `facebook/VGGT-1B-Commercial` (HF `https://huggingface.co/facebook/VGGT-1B-Commercial`; code fallback `facebook/VGGT-1B` `model.pt`). vggt code commit to be recorded at run time (main ~93 commits; Omega May 2026 noted). Path `demo_colmap.py --scene_dir=<DIR>/` (images in `<DIR>/images/`), outputs `<DIR>/sparse/{cameras,images,points3D}.bin` + `points.ply`; `--use_ba` adds pycolmap BA. Input fixed 518x518 — on A03 ≈1.3 mm/px vs 0.21 photographed, so depth maps cannot clear ~1 mm; pose-only by design. Blocker: Commercial checkpoint needs HF gated approval — confirm before any run.

- [ ] VGGT checkpoint pinned in this file before any run; poses estimated on the existing A03 views and compared against the COLMAP solve
- [ ] Scale anchored per the true-scale question — an unscaled result is refused, never measured
- [ ] Verdict states whether VGGT earns the pose-source role (fast COLMAP replacement) with the comparison figures attached; a coarse result retires only the mesher reading, not the pose track, and says which of the three it is

## Comments

- 2026-09-06 (trail start, both-in-order track 1/3): M1 boxes land (A02 0.186 mm flat wobble; A03 depth floor 4.1 mm; requirement ~1 mm), so this unblocks. Metrics: Sim(3)/Umeyama scale anchor then relative rotation (°), relative translation (mm), reprojection residual (px), registration rate (n/143), AUC@3/5/10° — mean, not best-of-N. No Slurm without approval.
