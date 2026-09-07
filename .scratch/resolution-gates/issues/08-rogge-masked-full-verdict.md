# 08: Full Rogge masked build + verdict (probe-gated)

**What to build:** the full masked-training A/B the M6 gate demands — 30k masked
build against the unmasked control on the same capture, extracted and compared
on the same ruler, verdict written into M6.

**Answers:** M6

**Blocked by:** 07 (probe GO — do not start on any other basis).

**Status:** ready-for-agent

- [ ] Full 30k masked train on `A03_sherds` (`-r 1`, `--eval`); deltas vs control:
      Gaussian counts, agreement mm, masked-PSNR, rim renders — same instruments
      as M5's A/B so the comparison is like-for-like
- [ ] Mesh extracted (same voxel 0.001u/band 0.005u) and compared same-ruler;
      density-drain check first: if the set collapses the way M5's did (~91%),
      retire NO at one capture with eye verification (M6 gate) — no second
      architecture, no occlusion-pruning rescue without fresh justification
- [ ] M6 amended with the branch verdict either way (keep means match/beat,
      complement, or viewing-only — same three as the baseline)
