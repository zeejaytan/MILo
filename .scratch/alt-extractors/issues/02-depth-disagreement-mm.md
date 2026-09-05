# 02: Cross-view depth disagreement in mm

**What to build:** the honest resolution floor — how far apart the Gaussian-rendered depths for A03 land when projected into a common frame, in millimetres.

**Answers:** M1

**Blocked by:** None (can start immediately).

**Status:** ready-for-agent

- [ ] Depth rendered from a handful of training views of the existing sherd-only dataset, projected into a common frame, disagreement reported in mm (not voxels, not pixels)
- [ ] Figure pairs the number with renders at a view resolving ~0.2 mm ridges — the number alone never stands
- [ ] Result written back into M1's first box with a date; if disagreement exceeds the voxel being asked for, finer grids are declared noise-sampling before any are built

## Comments

- 2026-09-06: started while user away. Found the probe job 30131641 (submitted
  2026-09-06) FAILED in 25 s at the first view: render outputs carry singleton
  dims, so `mask & (depth > 0)` broadcast to 3D and `np.nonzero` returned 3
  arrays for 2 names (`depth_disagreement.py:66`). Fixed by squeezing all three
  arrays to 2D at the seam plus a loud shape refusal inside `unproject`;
  reproduced the exact crash with the old lines and verified the new lines on a
  synthetic case on the laptop. Committed and resubmitted below.
- 2026-09-06: fix committed (`1ae8a7f`, pushed) and resubmitted as job 30132793
  via pull-then-sbatch with the same args. Next: read
  `depth_disagreement.json` + log against the ~1 mm bar when the job completes.
- 2026-09-06: job 30132793 COMPLETED but reported 1–2.6 m disagreement on a
  half-metre tray — a broken ruler (type 2), not a result. Cause found on the
  laptop: `world_view_transform` is stored transposed for CUDA, and inverting
  the stored matrix yields C^T, so no view's cloud ever left camera space
  (synthetic proof in ticket: old (0,0,5), fixed (1,2,8)). Fixed with
  un-transpose-before-invert plus a comment recording the trap. Resubmitting
  as a new job after commit+push.
