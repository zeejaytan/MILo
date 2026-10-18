# 25: Extract + measure the lossless-repaint train

**What to build:** the twin of T22 with compression removed — the number that says whether T22 softness came from the repaint or the JPEG.

**Answers:** M10

**Blocked by:** 24-train-lossless-repaint (resolved 2026-10-19).

**Status:** resolved 2026-10-19 — DONE. All 3 jobs COMPLETED. T25 vs T22 vs ctrl: density 152.2/154.8/146.3 per-cm2; Rq 0.156/0.181/0.144 (grip 0.198/0.236); disagreement 0.576/0.618; silhouette 0.510/0.482/0.606 (= rigfill 0.511). Compression caused ~2/3 of excess roughness; repaint itself costs silhouette + residual relief. Verified on disk by lead.

- [ ] Source field: `/data/gpfs/projects/punim2657/MILo/output/17062025/m10_ticket24/A03_t24lossless/` iteration_18000 cloud.
- [ ] Extract with the T08/T22-matched settings (voxel 0.0028u, band mult 8, masked DTU fusion + same scale FACTOR via apply_scale --force-factor). Expect the inherited broken render tail (T14/T22 precedent: fusion+scale+report succeed; run renders/scores as separate jobs, do not re-derive).
- [ ] Measure the same four-way panel as T22 (density, Rq global + grip, disagreement-vs-ctrl, wall hooks, silhouette CPU800 IoU) vs control `mesh_ctrl_v0.0028_mm.ply`. State T22 numbers alongside for the twin comparison.
- [ ] Output under `/data/gpfs/projects/punim2657/MILo/output/17062025/m10_ticket25/` with `m10_t25_note.json` + `m10_t25_score.json`.
- [ ] `slurm_poll` on every sbatch with final `sacct` State/ExitCode.
- [ ] Evidence-only worker: no verdict. Report mesh path + note/score JSONs + every Slurm job ID with State/ExitCode. Leave Status/checkboxes for the lead; no commit or push.
