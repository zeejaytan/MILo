# 07: Rig-only fill train (paired against ticket-03 control)

**What to build:** one MILo train on rig-only-filled photos, identical to the ticket-03 control arm in everything but inputs — so the rig-only treatment gets the same honest comparison the complement fill got.

**Answers:** M10

**Blocked by:** 06-rig-only-fill (fill accepted by lead first).

**Status:** ready-for-agent

- [ ] Single train on A03 with rig-only-filled inputs (ticket-06 `images_filled`, PNG-bytes handling as ticket 03: verify don't convert); control arm is the ALREADY-TRAINED ticket-03 `A03_ctrl_unmasked` (do NOT retrain control — same seed-0 construction, same config, same 18k iters; state the equivalence explicitly)
- [ ] Identical config/CLI: `train.py -s -m -i -r 1 --eval --imp_metric indoor --rasterizer radegs --dense_gaussians --decoupled_appearance`, 18k iters (`configs/fast` + `cfg_args` merge); seed 0 by construction (`safe_state`, train.py:702 — same code, no action needed, state it)
- [ ] Native unmasked training; `check_turntable.py` exit code (shared sparse — already exit 0, re-state); poll via sacct directly (no slurm_poll helper); every job ID + final State/ExitCode; run dir + logs under new untracked `/data/gpfs/projects/punim2657/MILo/output/17062025/m10_ticket07/`; no tracked edits, no commit/push.
