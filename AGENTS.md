# AGENTS.md — MILo / sherd 3DGS (project)

Follow the workspace root **`../AGENTS.md`** (laptop ↔ GitHub ↔ Spartan) for all shared
rules. This file only adds MILo-specific paths and domain notes.

## What this repo is for

Turning turntable photographs of Rabati pottery sherds into 3D meshes by a **second route**:
optimise a 3D Gaussian Splatting scene and extract the mesh from it with MILo, then compare
against the meshes the existing COLMAP → OpenMVS pipeline produces for the same sherds.
Neither route is retired; the point is to find out which gives better break-surface geometry.

The photographs and every reconstruction live **only on Spartan**. Nothing heavy is
committed, and nothing heavy is copied to the laptop.

> **Status — the authors' DTU extraction route is closed** (conservator's verdict on mesh
> quality for this material, 2026-09-01). Masked depth fusion worked (ten sherds, correctly
> sized, rig gone); the silhouette cull deleted every vertex, and the finest voxel reached was
> 0.822 mm against the ~0.21 mm the photographs support. Full record, including what the
> verdict does *not* cover: **`docs/notes/A03_DTU_EXTRACTION_RESULT.md`** — read it before
> restarting this route. The 0.822 mm ceiling is liftable, and MILo's own
> `mesh_extract_sdf.py` is not a free alternative (its mask parameter is dead) — first section
> of **`docs/reference/traps.md`**.

## Paths

| Role | Value |
|------|--------|
| GitHub fork (`origin`) | `zeejaytan/MILo` |
| Upstream | `Anttwo/MILo` (SIGGRAPH Asia 2025) |
| Spartan checkout (`REMOTE_ROOT`) | `/data/gpfs/projects/punim2657/MILo/repo` |
| Spartan working area (untracked) | `/data/gpfs/projects/punim2657/MILo/` — holds `envs/milo` (conda), `data/`, `output/`, `logs/` |
| Photographs on Spartan | `/data/gpfs/projects/punim2657/Rabati2025/<date>/<tree>/` |
| Photographs of record | Mediaflux (see `slurm/mediaflux_fetch.slurm`) |
| Sister pipeline (COLMAP/OpenMVS) | `/data/gpfs/projects/punim2657/Photogrammetry` — repo `zeejaytan/pottery-photogrammetry` |
| SSH | `Host spartan`, user `zhuojiat` |
| Remote helpers | `scripts/remote/pull_and_sbatch.sh`, `job_status.sh`, `fetch_artifacts.sh` |

Default branch is **`master`** (upstream's name). Local rsync landing zone: `artifacts/`
— comparison renders, metrics and logs only.

## Fork changes against upstream

Five, each with its reason, in **`docs/reference/fork-changes.md`**: `.gitmodules` SSH → HTTPS;
a comment in `milo/train.py` recording a removed masking patch; `.gitignore` re-includes;
adjustable TSDF resolution in `milo/eval/dtu/mesh_extract_dtu.py`; a prune hook in
`milo/mesh_extract_sdf.py`. Keep that file current — it is what a rebase onto upstream has to
survive. In code, search `[SHERD FORK]`.

Everything else this fork adds lives in `scripts/` and `slurm/` and touches no upstream file.

## Slurm conventions

Job scripts are versioned in `slurm/` and sbatch'd **from the repo checkout** on Spartan
(unlike TORA, where operational copies live outside the repo). Use:

```bash
./scripts/remote/pull_and_sbatch.sh slurm/milo_train.slurm 16062025
./scripts/remote/job_status.sh
```

Logs go to `/data/gpfs/projects/punim2657/MILo/logs/`.

Submit without asking (workspace rule 3), and start `../scripts/slurm_poll.sh <JOBID>` on every submit.

## Domain notes / traps

Each line is a trap that has already cost a job or a false finding. The measured detail, job
IDs and withdrawn claims are in **`docs/reference/traps.md`** — read the matching entry
before working in that area.

- **Train with `-r 1`, `--imp_metric indoor` and `--eval`.** The default silently downsamples
  past 1600 px; the turntable is an object-centric scene; `--eval` holds out every 8th view,
  the honest check.
- **Masked images keep COLMAP's exact filenames** (`.JPG` names holding PNG bytes). Renaming
  them breaks the dataset silently.
- **Check units before comparing any two meshes** — scale may or may not already be applied.
- **The turntable marker is unusable on every capture before 2025-07-03 N01** (M01–M04 that
  day included). Per capture: `markers_usable` in `docs/reference/scanning-record.json`. Key
  captures by `capture_id` — 2026 tree IDs restart per day.
- **TSDF resolution has three ceilings** — voxel size (0.75 mm), depth sampling (~0.21 mm/px),
  truncation band (±6 mm). Only the first is a setting; the band fails first when you refine.
- **Open3D mesh extraction dies with no message at 32,768 active blocks** (a 32-bit overflow,
  not memory). Its CPU/CUDA binary is chosen at import, its CUDA out-of-memory kills the
  process, and a fallback under `set -e` never fires. Several earlier explanations were
  withdrawn — read the entry before diagnosing a crash.
- **"The mask" is three different things in MILo** (kept if in any view, kept only if in every
  view, never fused), and the every-view cull deletes the whole A03 mesh.
- **The old A03 masks keep the clamp rig** — run `scripts/mask_content.py` before spending a
  GPU. Use the SAM 3 sherd masks: `A03_erode0`, dataset `data/17062025/A03_sherds`.
- **There is no ground truth** for a Rabati sherd; never phrase a `compare_meshes.py` result
  as if there were.

## Agent skills

Configured here so this repo works when opened on its own, not only from the `C:\PR`
umbrella. The full text of each convention lives at the workspace root; these are the
parts an agent needs before it can act.

- **Issue tracker — local markdown.** One feature per directory: the spec at
  `.scratch/<feature>/spec.md`, tickets one per file at
  `.scratch/<feature>/issues/<NN>-<slug>.md`, numbered from `01` in dependency order.
  Every ticket carries an **`Answers:`** line naming the question in `intent/` it exists
  to settle -- `M1` for this project, `U6` for the workspace, or `none` for routine
  work. Conventions and the ticket template: `../docs/agents/issue-tracker.md`.
- **Triage labels.** `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`,
  `wontfix`, recorded as a `Status:` line near the top of the ticket. Details:
  `../docs/agents/triage-labels.md`.
- **Domain docs — single-context.** Three different things, kept apart: **this file** is
  how to work here, with the traps indexed (detail in `docs/reference/traps.md`); **`CONTEXT.md`** at the repo root is the glossary, and
  `/domain-modeling` creates it lazily when the first term is actually resolved — do not
  create it empty; **`../docs/glossary.md`** is the cross-project measurement vocabulary
  (`part_acc`, chamfer distance, best-of-N) and outranks any local redefinition. ADRs go
  under `docs/adr/`. Details: `../docs/agents/domain.md`.
- **Intent.** [`intent/`](intent/) holds what we are trying to establish and what would
  settle it -- prefix **`M`**, permanent, numbers never reused. `/to-intent` opens a
  question or writes a finished ticket's result back into one. Check the loop is wired
  with `python ../scripts/check_intent_links.py`.

**Do not run `/setup-matt-pocock-skills` in this repo.** It would replace the above with
its own defaults, and its ticket template has no `Answers:` line -- tickets would stop
being connected to the question they exist to answer, silently.
