# 12: Extract + full four-way measure vs control

**What to build:** surface ticket-11's train with ticket-04/08's identical millimetre settings and judge it the same four ways.

**Answers:** M10

**Blocked by:** 11-retrain-refined-fill.

**Status:** ready-for-agent

- [ ] Extraction with ticket-04's matched settings (`mesh_extract_dtu.py`, voxel 0.0028u = 1.047mm, band ±8.37mm, block_count 40000, radegs; masks only at visual-hull cull); same scale path (`mm_per_unit 373.7333`, `--force-factor`, `markers_usable false`); outputs under new untracked `/data/gpfs/projects/punim2657/MILo/output/17062025/m10_ticket12/`
- [ ] Full four-way vs control (same tools/hooks as 04/08/09): density counts AND relief mm stated separately; ticket-06 flag form demonstrated honoured (refined-fill regions excluded from mm scoring); break-arc hook as before (no `break_arc` — nearest hook + contamination honesty); held-out silhouette on the same 21 views.
- [ ] Control side reuses ticket-04's `mesh_ctrl_v0.0028_mm.ply` (state the equivalence, do NOT re-extract control); renders both sides at ridge-resolving views + viewpoint-proof numbers; `sacct` discipline throughout; no tracked edits, no commit/push.
