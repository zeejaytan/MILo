# 03: Full A/B pair

**What to build:** two full 30k-iteration A03 trainings (patched vs control, identical seed and config), run only if the probe pair in ticket 02 gives the go, with logs and checkpoints intact for scoring.

**Answers:** M5

**Blocked by:** 02 (needs the probe go verdict).

**Status:** ready-for-agent

- [ ] Both runs train to completion on the same seed, config, dataset and rasterizer, differing only in the patch flag
- [ ] Checkpoints and logs retained for both; held-out every-8th-view renders kept for scoring
- [ ] No gamma ladder, no second seed, no config drift: one variable moves
