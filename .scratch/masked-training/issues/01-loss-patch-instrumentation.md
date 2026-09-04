# 01: Loss patch plus probe instrumentation

**What to build:** the both-sides masked loss plus background loss behind a flag in the training script (production radegs path only, background term gated on the regulariser kick around iteration 3000), the L1 fallback behind its own flag, per-view eroded-band alpha logging plus rim renders, and self-checks green without a GPU.

**Answers:** M2

**Blocked by:** None (can start immediately).

**Status:** ready-for-agent

- [ ] Masked photometric loss (photo times mask vs render times mask) matches control exactly where the mask is one
- [ ] Background term (mean rendered alpha outside mask, weight 0.5) reads zero where the mask is one; never touches depth or normal terms
- [ ] L1 fallback switchable by flag with no rebuild; GOF path untouched
- [ ] Self-checks prove the instrumentation can fail: a fully-masked view reads zero alpha mass
