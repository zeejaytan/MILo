# 05: VGGT pose A/B vs COLMAP

**What to build:** VGGT judged as what it is — a pose source — with its cameras scored against the COLMAP solve on the same capture.

**Answers:** M7

**Blocked by:** 01 (OpenMVS on A03, same ruler), 02 (depth disagreement in mm).

**Status:** ready-for-agent

**Pinned (desk, 2026-09-06 — code + checkpoint, no job submitted):** code `facebookresearch/vggt@a288dd0` (HEAD 2026-09-06, cloned to `/data/gpfs/projects/punim2657/vggt/`); checkpoint `facebook/VGGT-1B` open (model.pt public, pre-cached to torch hub on the login node — compute nodes have no outbound internet). `-Commercial` is application-gated (`gated: manual`) — unavailable without an approved HF application, so the open checkpoint is the trial pin. VGGT commit recorded in `slurm/vggt_pose.slurm`; job asserts it at run time. Input fixed 518x518 — on A03 ≈1.3 mm/px vs 0.21 photographed, so depth maps cannot clear ~1 mm; pose-only by design. Env `/data/gpfs/projects/punim2657/MILo/envs/vggt` (login-node build, background 2026-09-06).

- [ ] VGGT checkpoint pinned in this file before any run; poses estimated on the existing A03 views and compared against the COLMAP solve
- [ ] Scale anchored per the true-scale question — an unscaled result is refused, never measured
- [ ] Verdict states whether VGGT earns the pose-source role (fast COLMAP replacement) with the comparison figures attached; a coarse result retires only the mesher reading, not the pose track, and says which of the three it is

## Comments

- 2026-09-06 (trail start, both-in-order track 1/3): M1 boxes land (A02 0.186 mm flat wobble; A03 depth floor 4.1 mm; requirement ~1 mm), so this unblocks. Metrics: Sim(3)/Umeyama scale anchor then relative rotation (°), relative translation (mm), reprojection residual (px), registration rate (n/143), AUC@3/5/10° — mean, not best-of-N. No Slurm without approval.
- 2026-09-06 (approved): env `envs/vggt` built on login node (torch 2.3.1+cu118, pycolmap 3.10.0, trimesh); VGGT-1B model.pt (4.5 GB) pre-cached to torch hub (compute nodes offline). Feed-forward only, no BA; unmasked `images/` (COLMAP's own views — masking would change the question). Submitted as job 30167538 (`slurm/vggt_pose.slurm 17062025/A03_sherds`), laptop poll running; final State/ExitCode to follow here.
- 2026-09-06, 30167538 FAILED 1:0 in seconds — broken setup, not a result: `demo_colmap.py` imports the LightGlue tracking stack at top level even for non-BA runs and the env lacked it. Fixed on login node (LightGlue + hydra-core/omegaconf installed; numpy re-pinned 1.26.1 after LightGlue dragged 2.x; opencv rebuilt headless-only after a mixed cv2 broke `cv2.Feature2D`; `import demo_colmap` verified clean on CPU). Resubmitted as job 30167756, poll running.
- 2026-09-06, 30167756 FAILED 1:0 — setup again, still no measurement: the cached model.pt was a truncated 4.2 GB curl download (`PytorchStreamReader failed finding central directory`). Causes: HOME nearly full (47.5/51.2 GB) plus offline compute nodes. Fix: caches moved to project disk (`vggt_cache/{hf,torch}`); checkpoint re-downloaded checksummed (5,026,874,952 B, `torch.load` ok, 1797 tensors); job exports the same paths. Resubmitted as job 30167893, poll running.
