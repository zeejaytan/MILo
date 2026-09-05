# 05: VGGT pose A/B vs COLMAP

**What to build:** VGGT judged as what it is — a pose source — with its cameras scored against the COLMAP solve on the same capture.

**Answers:** M7

**Blocked by:** 01 (OpenMVS on A03, same ruler), 02 (depth disagreement in mm).

**Status:** ready-for-agent

- [ ] VGGT checkpoint pinned in this file before any run; poses estimated on the existing A03 views and compared against the COLMAP solve
- [ ] Scale anchored per the true-scale question — an unscaled result is refused, never measured
- [ ] Verdict states whether VGGT earns the pose-source role (fast COLMAP replacement) with the comparison figures attached; a coarse result retires only the mesher reading, not the pose track, and says which of the three it is
