# 06: Two-way piece-1 proof plus verdict

**What to build:** the verdict package for M4 on the v2 mesh — piece-1 crops (pruned v2 vs unpruned A03 learnable) fetched for conservator CloudCompare, same-window 0.10 mm/px renders, edge-arc loss and flat-wall noise in mm on the same box, component-clean counts via the largest-components shape, the stop-rule verdict, and the one-line write-back into intent M4 with a date. (Two-way, not three-way: verified 2026-09-05 that no OpenMVS mesh exists for A03; A02 OpenMVS numbers stand as reference.)

**Answers:** M4

**Blocked by:** 05 (needs the v2 pruned mesh).

**Status:** ready-for-agent

- [ ] Piece-1 crops of both meshes exist under `artifacts/` at millimetre scale for hand-checking
- [ ] Same-window 0.10 mm/px renders resolve the ridge scale for both meshes
- [ ] Edge-arc loss vs unpruned in mm of arc, flat-wall noise in mm for both on the same box
- [ ] Human in the loop: conservator eye verification in CloudCompare beside the numbers; no geometry box ticks without it
- [ ] Stop rule applied on numbers and M4 updated with the date whatever the outcome
