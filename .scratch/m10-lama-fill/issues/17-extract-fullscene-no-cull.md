# 17: Extract the full-scene train with no cull at all

**What to build:** the conservator's direct instruction (2026-10-18) — extract whatever the train holds, no carving, no cull, no masks anywhere in the path. Tests whether the 33mm fullscene-vs-rigfill gap (staging flag 2026-10-18) comes from the carve/cull step or the train itself.

**Answers:** M10

**Blocked by:** 09 (full-scene reference) — mesh path only.

**Status:** ready-for-agent

## Inputs (read first)

- `08-*.md` (extractor invocation + scale path) + `../spec.md` (pins)
- Train: the A03_nomask full-scene train (same train ticket 09 measured as mesh_carved_mm). Do NOT retrain.

## Method (fixed)

- Run the ticket-08 extractor verbatim EXCEPT: no mask input, no visual-hull cull, no cropping — full-volume output, whatever is there (rig, scatter, floor, all of it).
- Same voxel 0.0028u / band / block count / scale 373.7333 so the result compares directly; scale-gate before anything else.
- One Slurm CPU job; record job ID + sacct State/ExitCode. New untracked output dir (e.g. `m10_ticket17/`); no tracked edits, no commit/push.

## Verify

- Mesh non-empty; vertex count vs carved 1.37M sherd-projected verts; scale gate.
- Coincidence check vs rigfill mesh (same script the stager uses): report median/p90. If the gap collapses toward zero, the carve was the 33mm — say so plainly. If it persists, the trains disagree and the carve is exonerated.
- No render needed; the eye pair comes after.

## Deliver back (evidence only — the lead judges)

- Mesh path + size + vertex count; scale json path; coincidence median/p90 vs rigfill; job ID + sacct; exact command (proving the cull was off).
