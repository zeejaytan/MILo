# 23: Rebuild the full repaint lossless (PNG), same masks, same fill

**What to build:** a bit-identical-content twin of the 13c composite with no JPEG in the chain, so the follow-up train isolates repaint content from compression.

**Answers:** M10

**Blocked by:** none (masks + fill recipe exist; this is compute, not research).

**Status:** resolved 2026-10-19 — DONE. `m10_ticket23/composite_png/` 164 PNG views, guarantees hold (outside-union diff 0, sherd px 0). All intermediates reused, zero LaMa rerun; jobs 33391405 + 33392084 COMPLETED (33391991 FAILED empty-heredoc, no output touched). Ring stats: new-PNG vs old-JPEG mean|d| 1.72 — content identical, JPEG ringing confirmed small. Verified on disk by lead.

- [ ] Source recipe: 13c composite = bg-fill (T10-dilated refined masks, big-lama + refinement) + contact paste. Reuse the EXACT saved masks (`masks_inpaint` / dilated set under m10_ticket13c) and the same pinned LaMa (advimman/lama@786f5936 + big-lama, env lama02, refinement on) — change NOTHING about mask content or fill settings; the only change is lossless PNG output throughout.
- [ ] If the bg-fill intermediate PNGs still exist on disk (T10 dilated `images_filled`), reuse them verbatim instead of re-running LaMa — verify by byte-compare against composite content modulo JPEG ringing (same pixels, no re-encode). Only re-run LaMa for views whose intermediates are missing.
- [ ] Contact paste onto the lossless bg-fill with the same contact stats/method as 13c; verify `union_outside_max_absdiff = 0` and `filled_sherd_total_px = 0` like verify13c.json.
- [ ] Output under `/data/gpfs/projects/punim2657/MILo/output/17062025/m10_ticket23/composite_png/` — 164 views, `.png` names, PIL-verified PNG RGB 3200x2133 — plus `m10_t23_note.json` (sources reused vs re-run per view, guarantees, jobs).
- [ ] `slurm_poll` on every sbatch with final `sacct` State/ExitCode.
- [ ] Evidence-only worker: no verdict. Report output dir + note JSON + every Slurm job ID with State/ExitCode. Leave Status/checkboxes for the lead; no commit or push.
