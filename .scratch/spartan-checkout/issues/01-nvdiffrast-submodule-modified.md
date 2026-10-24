# 01: Spartan's MILo checkout shows the nvdiffrast submodule as modified

**What to build:** find out why `submodules/nvdiffrast` reads as modified in the Spartan
canonical checkout (`/data/gpfs/projects/punim2657/MILo/repo`, at c29386b on 2026-10-24),
and make that checkout read clean without editing a tracked file on Spartan.

**Answers:** none

**Blocked by:** None

**Status:** ready-for-agent

Found by pr-workspace `scripts/check_spartan_checkouts.sh` (workbench-enforcement ticket 05,
first run 2026-10-24, `/mnt/project-files/spartan_check_05_run1.txt`): MILo FAIL
modified-tracked, ` M submodules/nvdiffrast`. Porcelain v1 reports a submodule as `M` for
three different things, which lead to different fixes:

- the submodule is checked out at a commit other than the one MILo records (someone
  checked out or pulled inside it) -> put it back with `git submodule update`, with the
  user's OK, after saving anything unpushed there;
- tracked files inside it were edited -> save them as a patch to the MILo attic first
  (rule 13), then restore;
- only untracked build output inside it (a compiled extension) -> the build writes into
  the source tree; set `ignore = untracked` for that submodule in `.gitmodules`, or move the
  build out, so a build never reads as an edit.

- [ ] Read-only on Spartan, through the relay: `git -C <repo> submodule status`,
      `git -C <repo>/submodules/nvdiffrast status --short | head -40`, `log -1 --oneline`
- [ ] Fix by the case above; any Spartan change has the user's OK first
- [ ] Re-run `check_spartan_checkouts.sh`: MILo row `ok`
