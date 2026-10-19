# 19: Raw full-volume extract — no mask, no cull

**What to build:** the field's whole scene as it is, carved by nothing. Completeness over fineness: this mesh is the honest counterpart to the carved outputs, showing everything the reconstruction holds including rig, backdrop, and floaters.

**Answers:** M10

**Blocked by:** none. Runs alongside 18 (read-only shared source, separate outdir).

**Status:** superseded by 18-august-voxels-lama-field-no-carve.md 2026-10-18 (tiled-fine replaces coarse-full).

- [ ] Source field, in this order of preference: (1) the ORIGINAL August A03_nomask train's iteration cloud on Spartan, if it still exists — this is the truest "original output"; (2) fallback: the ticket-03 control field `.../m10_ticket03/A03_ctrl_unmasked/` iteration_18000. State which was used and why.
- [ ] Extraction with NO masked fusion and NO silhouette/visual-hull cull of any kind: every depth the field renders enters the grid. Only the August recipe's geometry path (same scripts, same scale chain) minus the two carving steps.
- [ ] Voxel: full volume will NOT fit fine (ticket 17: OOM/segfault at 0.0028u). Probe downward from 0.004u until the block count fits the 32,768 cliff with margin; state the voxel used in mm and never present this mesh at a fineness it was not extracted at.
- [ ] Scale via `measurement.env` FACTOR + `scripts/apply_scale.py --force-factor` (`*_mm.ply`); `markers_usable false`; extent + vert count + block count stated.
- [ ] Output under `/data/gpfs/projects/punim2657/MILo/output/17062025/m10_ticket19/` with a `m10_t19_note.json` (source field, voxel mm, blocks, verts, extent, jobs).
- [ ] `slurm_poll` on every sbatch with final `sacct` State/ExitCode; held allocation if iterating on voxel size.
- [ ] Evidence-only worker: no verdict. Report mesh path + note JSON + every Slurm job ID with State/ExitCode. Leave Status/checkboxes for the lead; no commit or push.
