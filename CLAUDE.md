# CLAUDE.md — MILo / sherd 3DGS (project)

Follow the workspace root **`../AGENTS.md`** / **`../CLAUDE.md`** (laptop ↔ GitHub ↔ Spartan)
for all shared rules, including the plain-language communication rules and the mandatory
visual confirmation for anything that moves or reconstructs geometry.

Same overlay as **`AGENTS.md`** in this folder — the fork-change list, the paths table, the
Slurm conventions and the domain traps live there. Read it before touching this repo.

Edit and commit on the laptop; Spartan is pull-only (`git pull --ff-only`) and runs Slurm
via `scripts/remote/*`. Photographs, COLMAP datasets, trained scenes and meshes stay on
Spartan; `artifacts/` is the local, gitignored landing zone for comparison renders,
metrics and logs only.
