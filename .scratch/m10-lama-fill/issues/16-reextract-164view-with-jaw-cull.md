# 16: Re-extract the 164-view rigfill train with jaw masks in the extraction cull

**What to build:** the cheap answer to the conservator's quality question (2026-10-18): keep ALL 164 views and the unmasked-training rule, and cull the jaw pixels only at extraction — no retraining, one short CPU job.

**Answers:** M10

**Blocked by:** 08-rig-only-extract-measure.md (matched settings + rigfill train) and 13d-jaw-fingertip-cleanup.md (jaw masks).

**Status:** resolved 2026-10-18 — job 33363828 COMPLETED 0:0 (24:55). HEADLINE: jaw-cull is a no-op (jaw ∩ sherd-keep = 0 px over 164 views, verified numerically); fused mesh reproduces ticket-08 exactly, 64,018 verts / 118,119 faces / 24,505 blocks. Jaw pixels never entered SDF initialisation in any arm — they were already culled as non-sherd.

## Inputs (read first)

- `08-*.md` (exact extraction invocation, voxel 0.0028u, band, block count, scale 373.7333) + `13d-*.md` (jaw masks `m10_ticket13d/jaw_masks/`, R5 rule) + `../spec.md`
- Train to extract from: the ticket-07 rigfill train (164 views, 18k iters — the same train ticket 08 extracted). Do NOT retrain.

## Method (fixed)

- Re-run the ticket-08 extraction verbatim except the cull mask set: sherd masks (as in 08) PLUS jaw masks. Confirm the extractor's cull semantics first (mask = keep vs mask = drop — read the script, do not guess); the intent is jaw pixels excluded from SDF initialisation, everything else identical.
- If the extractor takes a single mask input, union sherd-keep with jaw-drop correctly (jaw ∩ sherd excluded; jaw pixels were already sherd-subtracted last in R5, verify).
- One Slurm CPU job; record job ID + sacct State/ExitCode. New untracked output dir (e.g. `m10_ticket16/`); no tracked edits, no commit/push.

## Verify (numbers, then a look)

- Mesh non-empty; vertex count vs rigfill 64,018 and t14 55,708; scale gate (same factor) before anything else.
- One representative sherd-crop render, photo vs render; view it downscaled and say whether the sherd reads as clean clay.
- Jaw-grip patches will still be thin/holed (visible nowhere) — report where, plainly.

## Deliver back (evidence only — the lead judges)

- Mesh path + size + vertex count; scale json path; render path; job ID + sacct; the cull-union rule used (exact command/flag); grip-patch report.
