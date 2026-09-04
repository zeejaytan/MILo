# 01: Vote filter with counts on piece 1

**What to build:** a rerunnable script that loads the A03 unmasked Gaussians plus the erode0 sherd-only outlines through the train cameras, applies the 80% front-facing vote (centre inside the raw, undilated outline in >=80% of views where the Gaussian is in front of the camera; never-seen is dropped), and prints kept/dropped counts with a determinism check on seed. The vote runs over the whole cloud; piece 1 scoping happens at proof time in ticket 03.

**Answers:** M4

**Blocked by:** None (can start immediately).

**Status:** resolved (A03 run in progress on Spartan login node)

- [ ] Script runs on the login node CPU with no GPU and finishes in minutes on A03 (143 views)
- [ ] Prints kept/dropped Gaussian counts plus the vote histogram, deterministic across reruns
- [ ] Self-test on synthetic fixtures proves the check can fail: a synthetic rig blob is dropped, an in-frame-but-outside rim is dropped, a point 1 px inside the outline survives
- [ ] Keep set is written beside the source Gaussians with the rule and counts recorded, reproducible from the log alone

## Comments

2026-09-04, Spartan login node, CPU, no GPU: 222,678 Gaussians in
`output/17062025/A03_nomask/point_cloud/iteration_18000/point_cloud.ply`,
143 training views voting at keep-ratio 0.8. Kept 8,686 (3.90%); 41 never seen
in front of any view; median seen 83 views, median inside 1. Keep set at
`output/17062025/A03_prune/kept_idx.npy`, histogram at `.../votes.png` (fetched
to laptop temp and viewed): clean bimodal split — ~140k Gaussians at ~0
inside-fraction, kept population at 0.8–1.0, so the threshold separates two
populations rather than slicing a continuum. 3.90% kept sits beside the masks'
2.28% of frame, consistent. One RuntimeWarning (behind-camera cast) fixed in
the script after this run; self-test re-greened (7 assertions).

## Answer

v1 8,686 kept (3.90%), v2 14,670 (6.59%) at >=20 views; tray span 491x356x328 mm with 10/10 sherd clusters. Vote separates cleanly; density shortfall feeds the M4 verdict. Recorded in intent/M4-can-rig-gaussians-be-pruned-after-training.md (2026-09-06).
