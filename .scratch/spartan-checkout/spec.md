# Spartan checkout: MILo's canonical checkout reads clean

**Prior work searched:** git's own manuals on how a submodule shows as modified and how to
quiet build output inside one. Found: https://git-scm.com/docs/git-status (porcelain v1
reports a submodule as `M` for a new commit, modified content, or untracked content alike;
`--porcelain=v2` and `git submodule status` tell them apart) and
https://git-scm.com/docs/gitmodules (`submodule.<name>.ignore = untracked|dirty|all`). GitHub NVlabs/nvdiffrast at the
commit MILo pins (729261d) and at its tip: https://github.com/NVlabs/nvdiffrast has a
`setup.py` but no `.gitignore` (404 on both, checked 2026-10-24), so a `pip install` in the
source tree leaves `build/` and `*.egg-info` there as untracked content, which porcelain v1
shows as `M`; the leading suspect, to be confirmed by ticket 01's read-only step. A web
search for the symptom found only Hugging Face Spaces vendoring nvdiffrast, nothing on this
behaviour. No method or paper is involved: this is checkout housekeeping.

**Answers:** none (routine workbench work).

## Why

pr-workspace's Spartan check (workbench-enforcement ticket 05) fails any modified tracked
file in a canonical checkout. Its first run (2026-10-24) failed MILo on
`submodules/nvdiffrast`. Ticket 01 finds which of the three causes it is and fixes that one,
with the user's OK before anything on Spartan changes.
