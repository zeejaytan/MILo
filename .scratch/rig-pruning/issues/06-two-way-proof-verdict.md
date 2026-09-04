# 06: Two-way piece-1 proof plus verdict

**What to build:** the verdict package for M4 on the v2 mesh — piece-1 crops (pruned v2 vs unpruned A03 learnable) fetched for conservator CloudCompare, same-window 0.10 mm/px renders, edge-arc loss and flat-wall noise in mm on the same box, component-clean counts via the largest-components shape, the stop-rule verdict, and the one-line write-back into intent M4 with a date. (Two-way, not three-way: verified 2026-09-05 that no OpenMVS mesh exists for A03; A02 OpenMVS numbers stand as reference.)

**Answers:** M4

**Blocked by:** 05 (needs the v2 pruned mesh).

**Status:** resolved (M4 answered NO 2026-09-06 — see intent write-back; arc/noise mm deliberately unmeasured, webs + footprint disqualify regardless)

- [ ] Piece-1 crops of both meshes exist under `artifacts/` at millimetre scale for hand-checking
- [ ] Same-window 0.10 mm/px renders resolve the ridge scale for both meshes
- [ ] Edge-arc loss vs unpruned in mm of arc, flat-wall noise in mm for both on the same box
- [ ] Human in the loop: conservator eye verification in CloudCompare beside the numbers; no geometry box ticks without it
- [ ] Stop rule applied on numbers and M4 updated with the date whatever the outcome (paste exactly one draft below).

## Comments

Close-out drafts for the M4 write-back. Neither is true until the renders exist:
an unchecked geometry box is how the wear bug survived three rounds of numeric
validation.

- PASS: "Pruned v2 tet mesh holds break-face arc within ~1 mm of unpruned on piece 1
  at 0.10 mm/px, no rig solid above 5 mm, flat-wall noise within [x] mm of unpruned.
  Post-training pruning separates steel from clay on A03 (1 capture). M4 answered yes
  for this tree; density ([n]/sherd) and footprint ([x] mm median) bound the generality."
- FAIL: "Pruned v2 mesh [webs sherds across gaps|loses [x] mm of break-face arc|keeps
  rig solid above 5 mm] on piece 1 at 0.10 mm/px. Post-training pruning without
  replacement cannot carry break-face density on A03 (1 capture). M4 answered no for
  this tree; per-sherd split or SuGaR-shaped regrow is the next branch, or the M1 gate
  closes extraction work."

## Answer

v1 mesh (job 30056136): 128k verts, zero steel, too sparse for 0.21 mm relief. v2 mesh (job 30086544): 204k verts, zero steel, two components webbed across 331/218 mm. Kept footprint median 1.76 mm. Conservator eye 2026-09-06: too coarse for any reassembly use. Verdict and weight recorded in intent/M4-can-rig-gaussians-be-pruned-after-training.md; close-out drafts above retired with the ticket.
