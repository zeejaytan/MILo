# 07: Rig-only fill train (paired against ticket-03 control)

**What to build:** one MILo train on rig-only-filled photos, identical to the ticket-03 control arm in everything but inputs — so the rig-only treatment gets the same honest comparison the complement fill got.

**Answers:** M10

**Blocked by:** 06-rig-only-fill (fill accepted by lead first).

**Status:** resolved

- [x] Single train on A03 with rig-only-filled inputs (ticket-06 `images_filled`, PNG-bytes handling as ticket 03: verify don't convert); control arm is the ALREADY-TRAINED ticket-03 `A03_ctrl_unmasked` (do NOT retrain control — same seed-0 construction, same config, same 18k iters; state the equivalence explicitly)
- [x] Identical config/CLI: `train.py -s -m -i -r 1 --eval --imp_metric indoor --rasterizer radegs --dense_gaussians --decoupled_appearance`, 18k iters (`configs/fast` + `cfg_args` merge); seed 0 by construction (`safe_state`, train.py:702 — same code, no action needed, state it)
- [x] Native unmasked training; `check_turntable.py` exit code (shared sparse — already exit 0, re-state); poll via sacct directly (no slurm_poll helper); every job ID + final State/ExitCode; run dir + logs under new untracked `/data/gpfs/projects/punim2657/MILo/output/17062025/m10_ticket07/`; no tracked edits, no commit/push.

## Result (lead review, 2026-10-17) — ACCEPTED, ticket 08 unlocked

NOTE: the worker's closing message was a leaked tool-call markup (atem leak), not a result — it finished without reporting. Lead recovered all evidence from disk and verified directly: job 33216618 COMPLETED 0:0 (2:06:50); `.../m10_ticket07/A03_rigfill/` holds iteration_18000, chkpnt8000.pth (125MB), cameras.json, cfg_args, time.txt (7560s); log shows "Training complete" + final N_Gauss=158,312, Loss=0.0477. cfg_args diff vs ticket-03 control is ONLY model_path + images lines (lead-verified). Staging symlink `data/.../A03_sherds/images_rigfill` absolute → ticket-06 images_filled, 164 files. Control equivalence: same seed-0 construction, same flags, same 18k, same sparse. Health read (outcome, not verdict): 158k Gaussians at loss 0.0477 ≈ control's 0.047 — the rig-only arm did NOT collapse like the complement arm (8.3k/0.081). Ticket 08 judges what that means.
