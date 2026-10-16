# 08: Rig-only extraction + measure vs control

**What to build:** surface the rig-only train with ticket-04's identical millimetre settings and judge it the same three ways — with the same honesty rule (measure, don't rescue).

**Answers:** M10

**Blocked by:** 07-rig-only-train.

**Status:** ready-for-agent

- [ ] Extraction with ticket-04's matched settings (`mesh_extract_dtu.py`, voxel 0.0028u = 1.047mm, band ±8.37mm, block_count 40000, radegs; masks only at visual-hull cull); same scale path (`mm_per_unit 373.7333`, `--force-factor`, `markers_usable false`); outputs under new untracked `/data/gpfs/projects/punim2657/MILo/output/17062025/m10_ticket08/`
- [ ] Density counts AND relief mm stated separately (same tools/hooks as 04); ticket-06 flag demonstrated honoured (filled regions excluded from mm scoring — counts, not claims); break-arc hook as 04 (no `break_arc` — nearest hook + contamination honesty)
- [ ] Control side reuses ticket-04's `mesh_ctrl_v0.0028_mm.ply` (same settings already — state the equivalence, do NOT re-extract control); renders both sides at ridge-resolving views + viewpoint-proof numbers; `sacct` discipline throughout; no tracked edits, no commit/push.
