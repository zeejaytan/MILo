# 06: Resume-wedge isolation — does the resume path wedge on clean data?

**What to build:** one short resume of the SAMPLE control from chkpnt15000, to separate a checkpoint/resume-path fault from A03-data fault.

**Answers:** M9

**Blocked by:** None (control 33427213 COMPLETED; chkpnt15000.pth on Spartan).

**Status:** resolved (M9 retired 2026-10-20 on this evidence)

- [x] One short GPU job: resume sample control from chkpnt15000, run to ~15500 (or the next save point), then stop — sized in minutes, not hours
- [x] Final sacct State/ExitCode recorded in the ticket; faulthandler tail kept if it wedges
- [x] Verdict recorded: wedges on clean data ⇒ resume-path suspect (record the mechanism hypothesis, no patch — diagnose-only); runs clean ⇒ resume-wedge is A03-data-specific and the killer count may exceed 4
- [x] No edits to the authors' tree; sample data and scripts untouched (resume via --start_checkpoint only)

## Comments

- 2026-10-19 (lead): cut after control 33427213 acquitted the stack. Resume 32085160 wedged within ~20 iters from chkpnt4000 on A03 (double-densify withdrawn on code read) — this ticket asks whether ANY resume wedges, using data known to train clean.
- 2026-10-20 (worker): resume job `33449819` SUBMITTED (`slurm/goris_sample_resume15000.slurm`, new file modelled on `slurm/goris_sample.slurm`: chkpnt15000→16000, THEIR settings RES=512, faulthandler diag wrapper, 1h limit). PENDING (Priority), est. start 07:42 AEDT — verdict pending, ticket to be updated on completion.
- 2026-10-20 (worker): VERDICT — RUNS CLEAN. Job `33449819` COMPLETED 0:0 (sacct `33449819|COMPLETED|0:0`, batch + extern also COMPLETED). Resume chkpnt15000→16000 on the sample control ran the full 1000/1000 iters at steady ~4.9 it/s (Loss ~0.008, Points stable 57550, no pace decay), saved Gaussians + checkpoint at ITER 16000 (`[ITER 16000] Saving Gaussians/Checkpoint`, `Training complete.`), log `logs/goris_sample_resume_33449819.log`. No wedge, no stall, no faulthandler dump. Per the ticket rule this means the resume-wedge is A03-data-specific and the killer count may exceed 4 — resume path itself NOT suspect. Diagnose-only: nothing patched. New script: `slurm/goris_sample_resume15000.slurm` (also uploaded to Spartan `repo/slurm/` for the run; lead to commit).
