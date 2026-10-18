# 15: Measure the jaw-exclusion mesh the same four ways

**What to build:** answer the conservator's quality question with numbers, not impressions — score the ticket-14 mesh exactly as the control/rigfill arms (ticket 08) and the full scene (ticket 09) were scored, on the sherds only.

**Answers:** M10

**Blocked by:** 14-exclude-jaw-views-train-extract.md.

**Status:** resolved 2026-10-18 — job 33362826 COMPLETED 0:0 (4:52). t14 within noise of ctrl/rigfill on density/roughness/walls; deficit is grip-localized (grip Rq 0.251 vs 0.149 global, 20.8% of samples); photo agreement t14 0.617 best of three CPU-800. Raw: m10_ticket15/m10_t15_score.json

## Inputs (read first)

- `14-exclude-jaw-views-train-extract.md` + `08-*.md` (four-way method: density, roughness, walls, photo agreement) + `09-*.md` (full-scene reference numbers) + `../spec.md`
- Mesh: `output/17062025/m10_ticket14/mesh_t14keep_v0.0028_mm.ply` (scale sidecar in same dir; mm_per_unit 373.7333)
- Kept/dropped lists in the same dir (123 kept / 41 dropped)

## Method (fixed)

- Same four metrics, same sherd-only scoring regions, same flags convention as 08/09. Graft/flag columns: mark the jaw-grip patches (jaw masks from `m10_ticket13d/jaw_masks/`) as a third region class — measured-but-unobserved — so thin grip patches read as a named region, not as noise in the sherd statistics.
- Compare against the 08 (control, rigfill) and 09 (full scene) numbers in one table: density pts/cm², roughness Rq mm, wall mm x2, photo agreement. State per metric whether t14 is within noise of rigfill or clearly worse, and where (grip patches vs everywhere).
- One Slurm CPU job max for the scoring; record job ID + sacct. No retraining, no re-extraction, no tracked edits, no commit/push.

## Deliver back (evidence only — the lead judges)

- Score table + the raw numbers file path; which region drives any deficit (grips vs global); job ID + sacct State/ExitCode.
