# 14: Exclude jawed views, train + extract from the rest

**What to build:** the exclusion branch of the jaw decision (user, 2026-10-18): drop the views where the jaw eats the sherd face, train MILo on what remains, extract the sherd mesh — no fill, no graft, measured pixels only.

**Answers:** M10

**Blocked by:** 13d-jaw-fingertip-cleanup.md (jaw masks + negative fill result).

**Status:** resolved 2026-10-18 — train 33352041 COMPLETED 2:03:25, extract 33358077 COMPLETED, mesh 55,708 verts; render recovered by job 33359804 after first worker died silent (side-by-side glob bug, old render.py output was fine)

## Inputs (read first)

- `13d-jaw-fingertip-cleanup.md` + this ticket + `../spec.md` (pins, guarantees, no-tracked-edits rule)
- Ticket 07 (train config: seed/config/18k that produced the rigfill arm) and ticket 11 if present — reuse the exact train invocation
- Jaw masks: the R5 masks on Spartan under `m10_ticket13d/` (3.27M px over 161 views); per-view counts from the 13d report (worst: A33_1177 = 29,727 px)
- Photos: the T13c composite set (13b deliverable — completed sherds, jaw pixels still as-shot). Do NOT use 13d dark-filled copies as training input (13d paste ≈ identity, but composites are the canonical set)

## Exclusion rule (fixed — do not renegotiate)

- Rank all 164 views by jaw-mask pixel count. Drop every view at or above the 75th percentile (the worst ~41 views); train on the remaining ~123 views UNMASKED (2026-08-24 rule: full photos in training, masks only at extraction).
- Rationale for the file: the jaw rides with the sherd, so per-view jaw pixels hide different face patches as the assembly turns (fence-post-and-merry-go-round) — the kept views still observe every patch, thinly in the worst case. Whole-view exclusion keeps the unmasked-training convention M5 depends on.
- Write the kept/dropped view list + counts to the output dir. If the P75 cut lands awkwardly (e.g. a cliff mid-distribution), use the nearest natural break and record why.

## Train + extract

- Train MILo on the kept views, exact ticket-07 invocation (same config/seed/iterations), one Slurm job; record job ID + sacct State/ExitCode.
- Extract with the ticket-04/08 matched settings (voxel 0.0028u, same band/scale); record job ID + sacct.
- Verify: mesh non-empty, vertex count + bbox sanity vs the rigfill arm (64k verts); render one representative sherd crop (photo vs render side by side) as a debugging aid, not the verdict.

## Deliver back (evidence only — the lead judges)

- Output dir path (new untracked dir, e.g. `m10_ticket14/`); kept/dropped lists; both Slurm job IDs + sacct State/ExitCode; fused mesh path + size; vertex count; render path(s).
- The jaw-grip patches will likely come out thin or holed (no view ever saw beneath the jaw) — report where, with a render, plainly. That is an expected result, not a failure.
- No tracked edits, no commit/push.
