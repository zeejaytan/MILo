# 20: SDF-script unmasked extraction of the LaMa field

**What to build:** the true August-route replica for `mesh_carved_mm.ply`: the SDF extraction script run UNMASKED on the LaMa field. No masked fusion, no cull — the room with the rig inside it, as the field holds it.

**Answers:** M10

**Blocked by:** none. Runs alongside 18 (different method, separate outdir, same read-only source field).

**Status:** resolved 2026-10-18 (lead review below)

## Result (lead review, 2026-10-18) — ACCEPTED, evidence verified on disk

Job 33369941 COMPLETED 0:0 (6:06, sacct-verified); mesh + note JSON on disk as reported. Key finding: the genuinely-never-masked SDF output is a 13.8-metre room (2.9M valid verts, 0 junk), NOT the 595mm studio of `mesh_carved_mm.ply`. Since the August job ran with the INIT default (integration = SDF hull cull), the admired file was mask-shaped at SDF level and partly regrown by refinement — the tight studio is itself a product of the mask. Implication: no-mask-anywhere cannot reproduce the 595mm studio on either field; the mask must enter at SDF init. Ticket 18 (tiled 0.82mm DTU fusion) still running.

- [ ] Source field (do NOT retrain): the ticket-14 train — newest LaMa field, trained on the T13-composite kept views — under `/data/gpfs/projects/punim2657/MILo/output/17062025/m10_ticket14/`. Locate its iteration cloud + trained model dir on disk; state exact paths used. (Ticket-07 rigfill train is the fallback if the 14 model dir is missing; state which was used.)
- [ ] Recipe = the August extraction verbatim, minus the mask: `python mesh_extract_sdf.py -s <DATA_DIR for 17062025/A03> -m <OUT_DIR = m10_ticket20> -i <same IMAGES_ARG the August job used> -r 1 --rasterizer radegs --init learnable --refine_iter 1000`. `--init learnable` is the default that silently discards the mask (mesh_extract_sdf.py:568) — that is the point: NO mask enters anywhere. Keep `-r 1`, radegs, refine 1000 identical; do NOT tune.
- [ ] Scale via `measurement.env` FACTOR + `scripts/apply_scale.py --force-factor` (`*_mm.ply`); `markers_usable false`; extent + vert count stated.
- [ ] Expectation, stated so nobody misreads the result: the August file built this way carries ~1M non-finite junk verts alongside ~343k valid ones over a 595mm studio (probed on the laptop 2026-10-18). Report valid vs non-finite counts for the new mesh the same way (finite = |xyz| < 1e10); do NOT clean or filter the mesh to hit a target — the dirt is data.
- [ ] Output under `/data/gpfs/projects/punim2657/MILo/output/17062025/m10_ticket20/` with `m10_t20_note.json` (source field, init, refine_iter, verts valid/junk, extent, jobs).
- [ ] `slurm_poll` on every sbatch with final `sacct` State/ExitCode; held allocation if iterating.
- [ ] Evidence-only worker: no verdict. Report mesh path + note JSON + every Slurm job ID with State/ExitCode. Leave Status/checkboxes for the lead; no commit or push.
