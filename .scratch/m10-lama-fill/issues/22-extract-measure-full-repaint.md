# 22: Extract + measure the full-repaint train

**What to build:** does the full repaint keep sherd density through crop — the M10 question asked of the train that actually had the rig repainted.

**Answers:** M10

**Blocked by:** 21-train-full-repaint-composite (resolved 2026-10-19).

**Status:** resolved 2026-10-19 — DONE. Mesh 61,578 verts (154.8/cm2), Rq 0.181mm global / 0.236mm grip (29% grip-class), disagreement-vs-ctrl median 0.618mm, silhouette IoU 0.4824 (ctrl 0.6056, rigfill 0.5106). Extract fused fine (16,749 blocks); FAILED flag is the inherited broken render tail only; render + score jobs COMPLETED. Verified on disk by lead.

- [ ] Source field: `/data/gpfs/projects/punim2657/MILo/output/17062025/m10_ticket21/A03_t21full/` iteration_18000 cloud.
- [ ] Extract with the T08-matched settings (voxel 0.0028u, band mult 8, masked DTU fusion + same scale FACTOR via apply_scale --force-factor) so the number compares directly against control and rigfill arms. State blocks + verts + extent.
- [ ] Measure the same four-way panel as T08/T12/T15 (density, Rq relief, wall thickness x2, photo agreement, silhouette agreement) vs control: `mesh_ctrl_v0.0028_mm.ply`. No new control work — reuse T08 numbers, state them alongside.
- [ ] Output under `/data/gpfs/projects/punim2657/MILo/output/17062025/m10_ticket22/` with `m10_t22_note.json` (source, settings, blocks/verts/extent, all measures, jobs).
- [ ] `slurm_poll` on every sbatch with final `sacct` State/ExitCode.
- [ ] Evidence-only worker: no verdict. Report mesh path + note JSON + every Slurm job ID with State/ExitCode. Leave Status/checkboxes for the lead; no commit or push.
