# 26: Unmasked 0.82mm fusion OF THE REPAINT field (no mask, no cull)

**What to build:** what T18 did for the wrong field, done for the right one — full-volume 0.0022u tiled fusion of the lossless-repaint train (T24), nothing masked, nothing culled, cut to the rig box.

**Answers:** M10

**Blocked by:** 24-train-lossless-repaint (resolved 2026-10-19). T18 recipe precedent: `output/17062025/m10_ticket18/` (4x4x4 tiles, 28-byte vertex rows, header-offset memmap, uchar-count faces — do NOT re-derive the format, copy the working parse).

**Status:** resolved

- [ ] Source field: `/data/gpfs/projects/punim2657/MILo/output/17062025/m10_ticket24/A03_t24lossless/` iteration_18000 cloud.
- [ ] Full-volume fusion at voxel 0.0022u (= 0.822mm), band mult 8, UNMASKED (all depths enter the grid) — tile the scene bbox so every tile fits the 32,768-block cliff (T18 used 4x4x4 with ~16mm overlap halo, keep overlap geometry, report max boundary step).
- [ ] NO silhouette / visual-hull cull of any kind. Scale via FACTOR + apply_scale --force-factor (`*_mm.ply`).
- [ ] Cut the rig-box crop with the T18/T20 box (lo [-422.60,-167.30,-208.30], hi [272.50,268.50,243.80]) to `mesh_t26_rigcrop_mm.ply` alongside the full-volume mesh.
- [ ] Output under `/data/gpfs/projects/punim2657/MILo/output/17062025/m10_ticket26/` with `m10_t26_note.json` (source, voxel, tiles/blocks, verts/extent of full + crop, jobs). LEAVE THE CROP ON SPARTAN — the lead pulls it to the laptop.
- [ ] `slurm_poll` on every sbatch with final `sacct` State/ExitCode.
- [ ] Evidence-only worker: no verdict. Report full mesh + crop paths + note JSON + every Slurm job ID with State/ExitCode. Leave Status/checkboxes for the lead; no commit or push.
