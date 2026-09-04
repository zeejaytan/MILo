# 04: Count-rule flag plus v2 vote rerun

**What to build:** the vote script speaks absolute counts (`--min-inside`, v2 rule: inside in >=20 views), the self-test covers the absolute rule beside the fraction rule, and a fresh A03 keep set from the v2 rule whose count is sanity-checked (clay-scale, order of 100k, not 8k and not the full cloud) before anything builds.

**Answers:** M4

**Blocked by:** None (can start immediately).

**Status:** resolved (v2 rerun in progress on Spartan login node)

- [ ] `--min-inside N` keeps Gaussians inside the raw outline in >=N front-facing views; fraction rule stays as fallback when the flag is absent
- [ ] Self-test extended and green locally: absolute keeps/drops plus the existing 7 assertions
- [ ] A03 rerun on the login node CPU prints kept/dropped counts with the vote histogram; counts land at clay scale or the ticket reports the miss with figures
- [ ] v2 keep set written beside v1 with the rule recorded; v1 set untouched

## Answer

v2 rule (>=20 views) keeps 14,670 with full-tray coverage; rim regained vs v1 but footprint floor stands. Counts toward the M4 no. Recorded in intent/M4-can-rig-gaussians-be-pruned-after-training.md (2026-09-06).
