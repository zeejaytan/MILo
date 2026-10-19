# 06: Resume-wedge isolation — does the resume path wedge on clean data?

**What to build:** one short resume of the SAMPLE control from chkpnt15000, to separate a checkpoint/resume-path fault from A03-data fault.

**Answers:** M9

**Blocked by:** None (control 33427213 COMPLETED; chkpnt15000.pth on Spartan).

**Status:** ready-for-agent

- [ ] One short GPU job: resume sample control from chkpnt15000, run to ~15500 (or the next save point), then stop — sized in minutes, not hours
- [ ] Final sacct State/ExitCode recorded in the ticket; faulthandler tail kept if it wedges
- [ ] Verdict recorded: wedges on clean data ⇒ resume-path suspect (record the mechanism hypothesis, no patch — diagnose-only); runs clean ⇒ resume-wedge is A03-data-specific and the killer count may exceed 4
- [ ] No edits to the authors' tree; sample data and scripts untouched (resume via --start_checkpoint only)

## Comments

- 2026-10-19 (lead): cut after control 33427213 acquitted the stack. Resume 32085160 wedged within ~20 iters from chkpnt4000 on A03 (double-densify withdrawn on code read) — this ticket asks whether ANY resume wedges, using data known to train clean.
