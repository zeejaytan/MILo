# 18: 0.82mm-voxel DTU fusion of the LaMa field — no mask, no cull

**What to build:** genuine 0.82mm cubes over the whole LaMa-field scene, with nothing masked and nothing culled. One mesh: the whole scene as the field holds it, at DTU-experiment fineness.

**Ancestry correction (2026-10-18, lead):** the 0.0022u = 0.822mm voxel belongs to the *September DTU experiment* (job 29798496, `docs/notes/A03_DTU_EXTRACTION_RESULT.md`), NOT to `artifacts/A03/mesh_carved_mm.ply` — that file came from the SDF route (`mesh_extract_sdf.py`), which has no voxel knob in these units, and carries ~1M non-finite junk verts (probed on the laptop 2026-10-18). This ticket does not replicate the August route; ticket 20 does that. It answers the literal requirement: 0.82mm cubes, LaMa field, no mask, no cull.

**Answers:** M10

**Blocked by:** none. Supersedes 19 (coarse full-volume — moot once tiled-fine works).

**Status:** resolved 2026-10-19 — DONE as specified. Full-volume 0.0022u (0.822mm) tiled fusion of the T14 LaMa field, no mask, no cull: `mesh_lamafield_v0.0022_mm.ply` (1.74GB, 33,870,687 verts / 61,103,874 faces, extent 1003.1x3360.6x3281.7mm — whole capture volume) + `m10_t18_note.json` under `output/17062025/m10_ticket18/`. 4x4x4 tiles (41 with surface), 552,919 unique blocks, max tile 29,412 blocks (89.8% of cliff). Jobs: 33369926 render COMPLETED, 33370515 array 61/64 COMPLETED + 3 transient Lustre FAILs rerun as 33371164 all COMPLETED, 33384840 merge COMPLETED. Verified on disk by lead (sizes + sacct). Method note: compute_unique_block_coordinates returns (M,3) row-major here despite upstream (3,M) comment.

- [ ] Source field (do NOT retrain): the ticket-14 train — newest LaMa field, trained on the T13-composite kept views — under `/data/gpfs/projects/punim2657/MILo/output/17062025/m10_ticket14/`. Locate its iteration cloud on disk; state the exact path used. (Ticket-07 rigfill train is the fallback if the 14 cloud is missing; state which was used.)
- [ ] Voxel 0.0022u (= 0.822mm class), band per the August DTU route. NO masked fusion (`mesh_extract_dtu.py` fusion unmasked — all depths enter the grid) and NO silhouette / visual-hull cull of any kind.
- [ ] Full volume at 0.0022u will NOT fit the 32,768 block cliff in one grid (ticket 17 proved even 0.0028u OOMs unmasked). Tile it: split the scene bbox into tiles that each fit the cliff with margin (e.g. 2x2x2), fuse each tile at 0.0022u, merge the tile meshes into one PLY. State tile count + per-tile blocks; if a tile still refuses, split finer, never coarsen. NOTE (differs from August): the August mesh fused in ONE grid with no tiling and no seams — it fit only because masked fusion kept sherds alone in the grid. Tiling is forced here by the no-mask/no-cull requirement, and tile boundaries can cut surfaces (unlike per-sherd tiles, which share no zero-crossings). Use a ~16mm overlap halo between adjacent tiles, keep the overlap geometry from both sides (no boolean), and report the max boundary step so the lead can eye-check seams in the viewer.
- [ ] Scale via `measurement.env` FACTOR + `scripts/apply_scale.py --force-factor` (`*_mm.ply`); `markers_usable false`; extent + vert count + tile/blocks stated.
- [ ] Output under `/data/gpfs/projects/punim2657/MILo/output/17062025/m10_ticket18/` with `m10_t18_note.json` (source field, voxel mm, tiles, blocks per tile, verts, extent, jobs).
- [ ] `slurm_poll` on every sbatch with final `sacct` State/ExitCode; held allocation for the tile sweep.
- [ ] Evidence-only worker: no verdict. Report mesh path + note JSON + every Slurm job ID with State/ExitCode. Leave Status/checkboxes for the lead; no commit or push.
