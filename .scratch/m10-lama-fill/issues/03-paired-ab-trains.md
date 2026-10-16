# 03: Paired A/B trains — filled vs unmasked control

**What to build:** two MILo trains differing only in the fill, with determinism pinned so the comparison is honest.

**Answers:** M10

**Blocked by:** 02-pinned-lama-fill.

**Status:** resolved

- [x] Fresh paired trains on A03 (do NOT exact-resume `output/17062025/A03_nomask/` — its seed is unrecorded): filled inputs vs unmasked control, identical config/iterations: `train.py -s -m -i -r 1 --eval --imp_metric indoor --rasterizer radegs --dense_gaussians --decoupled_appearance`, 18k iters (see correction below — ticket premise said 30k; `configs/fast` sets `iterations=18_000`, verified on disk), `configs/fast` + `cfg_args` merge
- [x] Determinism pinned in the ticket body: state exactly how "identical seed" is achieved given MILo train exposes no seed arg (what was set, where, log lines proving it); if bit-identical resume is impossible, state the closest honest control and why
- [x] Native unmasked training (masking patch removed by design — `milo/train.py:218` fork note); mask flows only via `--init integration|depth_fusion` visual-hull cull at extract time, never at train time
- [x] `check_turntable.py` exit code recorded; `../scripts/slurm_poll.sh <JOBID>` (or `.ps1`) on every sbatch with final `sacct` State/ExitCode in the ticket; held allocation for iterative checks
- [x] Both Gaussian sets + logs kept under `/data/gpfs/projects/punim2657/MILo/output/` with config/seed/iteration provenance stated

## Result (lead review, 2026-10-17) — ACCEPTED, ticket 04 unlocked

Both arms completed 18k/18k with "Training complete" in-log; sacct COMPLETED 0:0 (lead-verified): A=33192555 (2:07), B=33192982 (2:34). Run dirs `.../m10_ticket03/A03_ctrl_unmasked/` and `.../A03_filled/` hold iteration_18000 clouds (73 MB vs 2.7 MB), chkpnt8000, cameras.json, cfg_args, time.txt. cfg_args diff is ONLY model_path + images lines (lead-verified). Determinism: closest honest control — hardcoded `random/np/torch.seed(0)` in `safe_state()` (general_utils.py:130-132), called unconditionally at train.py:702 (both lead-verified on disk); PYTHONHASHSEED=0 both arms; no cudnn-deterministic flags exist and radegs kernels use atomics, so bit-identical is NOT guaranteed — same seed + same flags + same A100-80GB class (gpgpu126 vs 127). Same init (N_Gauss=78227, 2,185,832 params). PNG-bytes handling byte-correct (PIL magic-sniff; per-job verify 164 RGB 3200x2133, bad=0; nothing renamed). check_turntable exit 0 both arms (shared sparse, 349.0°, ORDER OK). Cancelled pendings on the way (33173307/33191862 queue ~14h; 33192533/34 mem-cap partition forcing; 33192556 failed on a relative symlink, guard refused cleanly, fixed to absolute) — no outputs touched by failures. Staging symlink `data/.../A03_sherds/images_m10fill` (absolute, untracked data area) kept for ticket 04.

DIVERGENCE NOTE (observed outcome, not a breach — ticket 04 judges it): final N_Gauss 225,486 (A, loss 0.047) vs 8,287 (B, loss 0.081); chkpnt8000 183 MB vs 11 MB. Same seed/config — divergence is pixel-driven simplification. If extraction shows B collapsed, that is data (likely NO-GO), not a rerun trigger; no protocol error found.
