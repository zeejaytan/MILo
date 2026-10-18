# 24: Train on the lossless repaint (compression separation)

**What to build:** the twin of T21 that differs in exactly one thing — no JPEG anywhere — so M10 can say whether T22 softness came from the repaint or the compression.

**Answers:** M10

**Blocked by:** 23-lossless-repaint-rebuild (resolved 2026-10-19).

**Status:** ready-for-agent

- [ ] Source images: `/data/gpfs/projects/punim2657/MILo/output/17062025/m10_ticket23/composite_png/` (164 PNG views, PIL-verified PNG RGB 3200x2133).
- [ ] View set: same 123 kept views as T14/T21 (reuse the roster; drop the same 41). Dataset layout mirrors T21 (filtered sparse copy + symlinks into composite_png).
- [ ] Train: exact T07/T14/T21 invocation (same config/seed/18k, fresh, no warm start).
- [ ] Output under `/data/gpfs/projects/punim2657/MILo/output/17062025/m10_ticket24/` with `m10_t24_note.json` (source, roster, config/seed/iters, jobs).
- [ ] `slurm_poll` on the sbatch with final `sacct` State/ExitCode.
- [ ] Evidence-only worker: no verdict. Report train dir + iteration cloud path + every Slurm job ID with State/ExitCode. Leave Status/checkboxes for the lead; no commit or push.
