# 18: August-style extraction of the control train

**What to build:** re-extract the EXISTING ticket-03 control Gaussian field the August way, to isolate whether the LaMa route's coarseness is extraction settings or the retrained field. No new training.

**Answers:** M10

**Blocked by:** none (control train on disk). Informative to 08/14 interpretation; does not rewrite them.

**Status:** withdrawn 2026-10-18 — user corrected: no mask, no cull, LaMa field. Rewritten as 18-august-voxels-lama-field-no-carve.md.

- [ ] Source field (do NOT retrain): `/data/gpfs/projects/punim2657/MILo/output/17062025/m10_ticket03/A03_ctrl_unmasked/` iteration_18000 cloud (73 MB). Same cameras/config as ticket 03 Arm A.
- [ ] August recipe, both halves: (1) masked depth fusion per `scripts/mesh_extract_dtu.py:66-67` (background depths zeroed before entering the grid — training stays unmasked, per the 2026-08-24 ruling; only the extraction input is masked); (2) silhouette cull per `scripts/evaluate_dtu_mesh.py:89-145` cull_mesh() (all-views test, disk(6) dilation, outside-frame excusal). Reference the repo A03_DTU note for the exact August parameters.
- [ ] Voxel 0.0022u (= 0.822mm class). If the block count refuses over the 32,768 cliff, do NOT silently coarsen: stop, report the count, and await the lead (masked fusion should hold only sherds, as in August: 32,209 blocks).
- [ ] Scale via `measurement.env` FACTOR + `scripts/apply_scale.py --force-factor` (`*_mm.ply`); `markers_usable false`; base ruler stated.
- [ ] Score the mesh with the ticket-04/08 measure (verts, extent, pieces, relief Rq/Ra median+p90, wall means, sherd silhouette agreement) into `m10_t18_score.json` beside the mesh under `/data/gpfs/projects/punim2657/MILo/output/17062025/m10_ticket18/`.
- [ ] `check_turntable.py` exit code recorded; `slurm_poll` on every sbatch with final `sacct` State/ExitCode in the report; held allocation for iterative checks if needed.
- [ ] Evidence-only worker: no verdict. Report: mesh path + score JSON + block count + every Slurm job ID with sacct State/ExitCode. Leave Status/checkboxes for the lead; no commit or push.
