# 05: Killer-view autopsy — what do the wedging views share?

**What to build:** a feature table comparing the 4 killer views against matched passing neighbours, and a verdict: one shared trigger feature, or none.

**Answers:** M9

**Blocked by:** 02 (killer list — satisfied: A31_1111, A32_1142, A33_1176 hang; A32_1151 illegal-access; outcomes flip run to run across two nodes).

**Status:** ready-for-agent

- [ ] Feature table for the 4 killers vs 4+ passing neighbours from the same trays: camera pose (angle/height neighbours), steel cm² share per view, dial/marble-rod presence, blur/exposure outliers, COLMAP sparse point counts and reprojection spread
- [ ] Verdict recorded: one shared feature (name it, with numbers) or no-common-feature (say so explicitly — a negative is an answer)
- [ ] Login-node work only (image stats + sparse queries); a GPU probe only if the table points at one and the probe is sized under 30 min
- [ ] No edits to the authors' tree; resume-wedge suspects from 32276629 stay in 06, not here

## Comments

- 2026-10-19 (lead): cut after control 33427213 acquitted the stack — the wedge is data-specific, so the data gets interrogated. Diagnose-only per conservator decision; bounded: one table, one verdict, then 07 builds subsets from it.
