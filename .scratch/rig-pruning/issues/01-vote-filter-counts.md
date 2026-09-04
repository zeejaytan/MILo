# 01: Vote filter with counts on piece 1

**What to build:** a rerunnable script that loads the A03 unmasked Gaussians plus the erode0 sherd-only outlines through the train cameras, applies the 80% front-facing vote (centre inside the raw, undilated outline in >=80% of views where the Gaussian is in front of the camera; never-seen is dropped), and prints kept/dropped counts with a determinism check on seed. The vote runs over the whole cloud; piece 1 scoping happens at proof time in ticket 03.

**Answers:** M4

**Blocked by:** None (can start immediately).

**Status:** ready-for-agent

- [ ] Script runs on the login node CPU with no GPU and finishes in minutes on A03 (143 views)
- [ ] Prints kept/dropped Gaussian counts plus the vote histogram, deterministic across reruns
- [ ] Self-test on synthetic fixtures proves the check can fail: a synthetic rig blob is dropped, an in-frame-but-outside rim is dropped, a point 1 px inside the outline survives
- [ ] Keep set is written beside the source Gaussians with the rule and counts recorded, reproducible from the log alone
