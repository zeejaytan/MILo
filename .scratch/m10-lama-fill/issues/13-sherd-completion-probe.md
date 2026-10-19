# 13: Sherd-completion probe (fill clamp notches with sherd, not background)

**What to build:** every sherd whole and floating — clamp-occluded sherd pixels inpainted from surrounding sherd texture instead of background, so fragments have no jaw notches.

**Answers:** M10

**Blocked by:** 10-refined-masks-refill (uses its v12/dilated masks + refined fork recipe).

**Status:** ready-for-agent

**User scope (2026-10-18):** remove the clamp itself; inpaint in the clamp's place ON the sherds so sherds float with no holes. Eye-gated probe first, full rollout only if the fill reads as continuous wall.

- [ ] Quantify per view: clamp-over-sherd pixels = dilated rig mask INTERSECT dilated sherd mask (sherd dilated ~8px for context ring); report mean/range/px counts — if tiny everywhere this is easy, if wide anywhere say so
- [ ] Fill ONLY the contact zones with the refined fork (same recipe as 10/dilated), masks = contact zones, context = surrounding sherd; all other pixels byte-identical
- [ ] Stage worst ~10 views as triptychs (photo | background-filled sherd with notch | sherd-completed) for LEAD eye-check; eye gate: ticket 11 trains NOTHING until the conservator approves the completion
- [ ] Honest failure line: where the contact zone is wide and the fill goes soft/smudge, list those views — those train with holes and multi-view consistency instead
- [ ] Outputs under new untracked `/data/gpfs/projects/punim2657/MILo/output/17062025/m10_ticket13/`; `sacct` State/ExitCode recorded; heavy work on compute nodes only; no tracked edits, no commit/push
