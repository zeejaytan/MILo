# 21: Train on the full repaint (bg-fill + contact composite)

**What to build:** the train the chain has been missing. Ticket 14 trained on contact-only originals (full sharp rig); the bg-fill branch was only ever looked at. Train on the actual full repaint so the mesh answers whether the repaint removes the rig.

**Answers:** M10

**Blocked by:** none. Source data exists on disk; no fill work needed.

**Status:** resolved 2026-10-19 — DONE. Job 33387133 COMPLETED 0:0 (2:20), 151k Gaussians, cloud `A03_t21full/point_cloud/iteration_18000/point_cloud.ply` + note JSON on disk, verified by lead. Same 123 kept views + config as T14. OBSERVED CONFOUND (worker): composite files are real JPEG ~210KB, not PNG-bytes — so T21 differs from T14 in repaint content AND JPEG compression; inherent to the delivered set.

- [ ] Source images: `/data/gpfs/projects/punim2657/MILo/output/17062025/m10_ticket13c/composite/` (164 views, PNG bytes under .JPG names; verify13c.json: bg-fill + contact paste, outside rig-UNION-contact byte-identical to photo). NOTE: files are PNG-data — symlink/copy handling must not re-encode; train reads pixels, extension is cosmetic but verify the loader accepts it (T14 read images_completed/ PNG-bytes fine — same pattern).
- [ ] View set: same 123 kept views as T14 (drop the same 41 jaw-heavy views T14 dropped; list the drop list source — reuse T14 images_kept roster exactly for comparability).
- [ ] Train: same config/seed/18k-iter as T07/T11/T14 (state config + seed + iters in the note; `configs/fast`, decoupled appearance, same eval flags). Fresh train from scratch, no warm start.
- [ ] Output under `/data/gpfs/projects/punim2657/MILo/output/17062025/m10_ticket21/` with `m10_t21_note.json` (source dir, view roster + drop list, config/seed/iters, jobs).
- [ ] `slurm_poll` on the sbatch with final `sacct` State/ExitCode.
- [ ] Evidence-only worker: no verdict. Report train dir + iteration cloud path + every Slurm job ID with State/ExitCode. Leave Status/checkboxes for the lead; no commit or push.
