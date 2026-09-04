# 03: Proof renders plus millimetre verdict

**What to build:** the verdict package for M4 — side-by-side break-face crops at 0.10 mm/px (pruned vs unpruned vs OpenMVS, same window on piece 1, the large 33 x 79 x 74 mm body), edge-arc loss in mm of arc, flat-wall noise in mm on the same box, component-clean counts via the largest-components shape (keep N largest, report kept vs dropped faces, applied to the tet mesh never the Gaussian set), the stop-rule verdict, and the one-line write-back into intent M4 with a date.

**Answers:** M4

**Blocked by:** 02 (needs the pruned mesh).

**Status:** ready-for-agent

- [ ] Break-face crops at 0.10 mm/px from the same window for all three meshes exist under `artifacts/` and resolve the ridge scale
- [ ] Edge-arc loss vs unpruned reported in mm of arc, flat-wall noise in mm for all three on the same box
- [ ] Component clean reported as kept vs dropped faces; occlusion gaps stay open, no invented surface, or the failure is stated plainly
- [ ] Stop rule applied on numbers (rig solid above 5 mm fails; break-face loss above ~1 mm of arc fails) and M4 is updated with the date whatever the outcome
