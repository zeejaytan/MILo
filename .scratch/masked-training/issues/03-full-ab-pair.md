# 03: Full A/B pair

**What to build:** two full 30k-iteration A03 trainings (patched vs control, identical seed and config), run only if the probe pair in ticket 02 gives the go, with logs and checkpoints intact for scoring.

**Answers:** M5

**Blocked by:** 02 (needs the probe go verdict).

**Status:** claimed (masked full run resubmitted as job 30099987 with 14h limit; control reused from 30094277; log MILo/logs/milo_probe_30099987.log)

- [ ] Both runs train to completion on the same seed, config, dataset and rasterizer, differing only in the patch flag
- [ ] Checkpoints and logs retained for both; held-out every-8th-view renders kept for scoring
- [ ] No gamma ladder, no second seed, no config drift: one variable moves

## Comments — control already done (2026-09-06)

A03_probe_ctrl finished all 18k iterations in job 30094277. Remaining work is the
masked leg only: resubmit the probe script (per-leg skip reuses control) with a
14h limit for ~11h of training plus renders.
