# 03: Paired A/B trains — filled vs unmasked control

**What to build:** two MILo trains differing only in the fill, with determinism pinned so the comparison is honest.

**Answers:** M10

**Blocked by:** 02-pinned-lama-fill.

**Status:** ready-for-agent

- [ ] Fresh paired trains on A03 (do NOT exact-resume `output/17062025/A03_nomask/` — its seed is unrecorded): filled inputs vs unmasked control, identical config/iterations: `train.py -s -m -i -r 1 --eval --imp_metric indoor --rasterizer radegs --dense_gaussians --decoupled_appearance`, 30k iters (`milo/arguments/__init__.py:76`), `configs/fast` + `cfg_args` merge
- [ ] Determinism pinned in the ticket body: state exactly how "identical seed" is achieved given MILo train exposes no seed arg (what was set, where, log lines proving it); if bit-identical resume is impossible, state the closest honest control and why
- [ ] Native unmasked training (masking patch removed by design — `milo/train.py:218` fork note); mask flows only via `--init integration|depth_fusion` visual-hull cull at extract time, never at train time
- [ ] `check_turntable.py` exit code recorded; `../scripts/slurm_poll.sh <JOBID>` (or `.ps1`) on every sbatch with final `sacct` State/ExitCode in the ticket; held allocation for iterative checks
- [ ] Both Gaussian sets + logs kept under `/data/gpfs/projects/punim2657/MILo/output/` with config/seed/iteration provenance stated
