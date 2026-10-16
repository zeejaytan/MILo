# 08: Rig-only extraction + measure vs control

**What to build:** surface the rig-only train with ticket-04's identical millimetre settings and judge it the same three ways — with the same honesty rule (measure, don't rescue).

**Answers:** M10

**Blocked by:** 07-rig-only-train.

**Status:** resolved

- [x] Extraction with ticket-04's matched settings (`mesh_extract_dtu.py`, voxel 0.0028u = 1.047mm, band ±8.37mm, block_count 40000, radegs; masks only at visual-hull cull); same scale path (`mm_per_unit 373.7333`, `--force-factor`, `markers_usable false`); outputs under new untracked `/data/gpfs/projects/punim2657/MILo/output/17062025/m10_ticket08/`
- [x] Density counts AND relief mm stated separately (same tools/hooks as 04); ticket-06 flag demonstrated honoured (filled regions excluded from mm scoring — counts, not claims); break-arc hook as 04 (no `break_arc` — nearest hook + contamination honesty)
- [x] Control side reuses ticket-04's `mesh_ctrl_v0.0028_mm.ply` (same settings already — state the equivalence, do NOT re-extract control); renders both sides at ridge-resolving views + viewpoint-proof numbers; `sacct` discipline throughout; no tracked edits, no commit/push.

## Result (lead review, 2026-10-17) — ACCEPTED: rigfill WIN, keep per gate

Jobs lead-verified COMPLETED 0:0 (extract 33220031, probe 33236202, measure 33236411, gates 33236486, section 33236577; one measure CANCELLED while pending, no work lost). Numbers lead-verified in m10_t08_score.json on disk — all match the report: rigfill `mesh_rigfill_v0.0028_mm.ply` 64,018 verts / 118,119 faces (+11% vs control 57,632/108,518), 14 vs 11 pieces over 200 verts, same ~137-150 verts/cm²; relief Rq median 0.155 vs 0.144mm (8% rougher, sub-mm both); cross-surface median 0.30/0.31mm, 71-76% within 0.5mm; section z=-76.4 median 0.099mm (550/601 outline points); wall hooks 7.80 (chords) / 8.30 vs 8.34mm (compare) — sherd-wall scale both arms. Flag honoured: 164/164 views, filled∩sherd = 0 px, scores sherd-projected only. Lead eye-check (mesh renders both arms, section overlay, laptop copies in artifacts/m10_t08/): same 10-piece layout, rigfill slightly fuller; section outlines nearly coincident — NO break move visible. Honest debit (stated, not hidden): held-out silhouette 73% (ctrl) vs 59% (rigfill) — extra surface somewhere in rigfill, expected direction. Hygiene note: score.json's `break_arc_mm` string is a stale leftover from 04's script ("without filled surface") — the section/thickness numbers beneath it are real rigfill-vs-ctrl values. Binding framing applied: NOT a null → INCONCLUSIVE clause does not trigger; per gate (clay + break untouched + flag honoured) this is KEEP. Single object, single run — a lead, not a conclusion. Evidence: `.../m10_ticket08/` (mesh + sidecars, score json, probe/, renders/, compare/, section overlay).
