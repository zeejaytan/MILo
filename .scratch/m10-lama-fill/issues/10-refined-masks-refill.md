# 10: Refined rig masks + refill (author-intended path, no SAM)

**What to build:** rig masks that catch the steel ticket 06 missed — blue knobs, smooth mid-gray clamp faces, lit-rubber jaw interiors — then refill with the unchanged pinned LaMa. LaMa's authors ship no mask tool (masks are inputs; their demos use hand/refined masks, big-lama trained on narrow masks), so the author-intended path is better masks + big-lama as-is. (SAM researched 2026-10-17 and set aside by user decision; rule-extension it is.)

**Answers:** M10

**Blocked by:** 05-eye-qa-writeback (M10 closed-keep; this is the refinement the verdict left room for).

**Status:** ready-for-agent

- [ ] Mask refinement, incremental on 06's pipeline (smooth-bg deviation + lum rules, CC filter, dilate, sherd re-subtracted): add (a) blue-chroma knob rule, (b) morphological close on enclosed smooth zones for clamp faces, (c) jaw-interior rule for lit rubber; rod stays UNMASKED (user scope). Every rule + threshold stated in-ticket; per-view rig-frac mean/range reported vs 06's 0.194.
- [ ] Hand touch-up the worst ~12 views (most missed steel by pixel count) after the rules; list which views + what was added.
- [ ] Refill with the same pins as 06 (no rebuild): pinned `advimman/lama@786f5936` + big-lama in env `lama02`; per-view 3200x2133 NEAREST, no cross-view propagation.
- [ ] Same guarantees as 06: background + sherd byte-identical (`max|Δ| = 0.0` outside mask, every view); filled∩sherd = 0 px; per-view flag in 02 flag form; jaw-contact exclusion recompute-or-reference.
- [ ] Stage mask-overlay + filled renders for the 10 worst views for LEAD eye-check (eye gate: ticket 11 trains NOTHING until the conservator approves the fill); `sacct` State/ExitCode recorded; heavy work on compute nodes only; outputs under new untracked `/data/gpfs/projects/punim2657/MILo/output/17062025/m10_ticket10/`; no tracked edits, no commit/push.
