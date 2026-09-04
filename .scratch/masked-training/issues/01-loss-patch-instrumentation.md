# 01: Loss patch plus probe instrumentation

**What to build:** the both-sides masked loss plus background loss behind a flag in the training script (production radegs path only, background term gated on the regulariser kick around iteration 3000), the L1 fallback behind its own flag, per-view eroded-band alpha logging plus rim renders, and self-checks green without a GPU.

**Answers:** M5

**Blocked by:** None (can start immediately).

**Status:** claimed (patch + self-checks green locally; Spartan probe is ticket 02)

## Comments

2026-09-06: `milo/train.py` carries the both-sides loss + background term behind
`--masked-training` (default off), `--mask-bg-weight 0.5`, `--mask-l1-only`
fallback flag; background pressure gated on the regulariser kick where alpha
exists; eroded-band alpha logging every 1000 iters. `scripts/masked_loss_selftest.py`
green on the laptop (5 assertions incl. the one-sided-tripwire that fails any
re-animation of 770338f). Unpatched runs behave exactly as upstream.

- [ ] Masked photometric loss (photo times mask vs render times mask) matches control exactly where the mask is one
- [ ] Background term (mean rendered alpha outside mask, weight 0.5) reads zero where the mask is one; never touches depth or normal terms
- [ ] L1 fallback switchable by flag with no rebuild; GOF path untouched
- [ ] Self-checks prove the instrumentation can fail: a fully-masked view reads zero alpha mass
