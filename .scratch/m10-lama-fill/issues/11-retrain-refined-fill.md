# 11: Retrain from scratch on refined fill

**What to build:** fresh A03 train on ticket-10's refined-filled photos, identical to ticket-07's rigfill train except the input photos.

**Answers:** M10

**Blocked by:** 10-refined-masks-refill (eye gate: trains NOTHING until the conservator approves the fill).

**Status:** ready-for-agent

- [ ] Train from scratch: same seed-0-by-construction, same config, 18k iters (configs/fast), same held-out every-8th views as 03/07; only the input photo set differs (ticket-10 refined fill).
- [ ] Report final Gaussian count + loss vs 07's 158,312 / 0.048 and control's 225k / 0.047; `sacct` State/ExitCode recorded; outputs under new untracked `/data/gpfs/projects/punim2657/MILo/output/17062025/m10_ticket11/`; no tracked edits, no commit/push.
