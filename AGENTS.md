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

Keep this list current; it is what a rebase onto upstream has to survive.

1. **`.gitmodules` — SSH → HTTPS.** Upstream uses `git@github.com:` URLs for
   `Depth-Anything-V2` and `nvdiffrast`. Spartan cannot reach GitHub over SSH, so a
   recursive clone there fails outright. (The other six directories under `submodules/`
   are vendored in-tree, not git submodules.)
2. **`milo/train.py` — object masking.** Upstream loads a PNG alpha channel into
   `viewpoint_cam.gt_mask` (`milo/scene/cameras.py`) but never applies it: the multiply is
   commented out and the loss uses the raw image. On a turntable the backdrop is the one
   thing that does *not* move with the sherd, so unmasked training spends Gaussians on an
   inconsistent background and softens the sherd's silhouette. The patch composites the
   ground truth against the render background outside the mask. Search `[SHERD FORK]`.
3. **`.gitignore`** — upstream ignores `*.sh`, `*.slurm`, `*.ply` and `*.png` outright,
   which would silently swallow this fork's own tooling. Re-included by name at the end
   of the file.

Everything else this fork adds lives in `scripts/` and `slurm/` and touches no upstream file.

## Slurm conventions

Job scripts are versioned in `slurm/` and sbatch'd **from the repo checkout** on Spartan
(unlike TORA, where operational copies live outside the repo). Use:

```bash
./scripts/remote/pull_and_sbatch.sh slurm/milo_train.slurm 16062025
./scripts/remote/job_status.sh
```

Logs go to `/data/gpfs/projects/punim2657/MILo/logs/`.

Ask before submitting any job, per the workspace rules.

## Domain notes / traps

- **`-r 1` is not optional for sherds.** MILo's default `-r -1` silently downsamples any
  image wider than 1600 px (`milo/utils/camera_utils.py`). The captures are several
  thousand pixels wide and a fracture ridge is a fraction of a millimetre. Training at
  1600 px answers a coarser question than the one being asked — the same failure the
  workspace scale rule was written about.
- **`--imp_metric indoor`** — a turntable rig is a bounded object-centric scene, not a
  landscape.
- **`--eval` holds out every 8th view** (`llffhold=8` in `milo/scene/dataset_readers.py`).
  Those held-out views are the honest instrument in Phase 6; always train with it.
- **Filenames must match COLMAP exactly.** `readColmapCameras` joins the images directory
  with `os.path.basename(extr.name)`, extension included. The masked RGBA images therefore
  keep the original `.JPG` names while holding PNG bytes — PIL sniffs content, not
  extension. Renaming them to `.png` breaks the dataset silently.
- **Scale.** If `pipeline/bin/scale_apply.py` has already run for a capture, the COLMAP
  sparse model is *already* metric and so is the MILo mesh — nothing further to do. If it
  has not, `<work>/scale/SCALE.txt` holds the factor and `scripts/apply_scale.py` applies it.
  Never compare two meshes before checking they are in the same units.
- **The turntable marker is unusable before 2025-07-03 N01.** On every capture up to and
  including M04 that day the marker was placed incorrectly; using it for feature
  recognition or alignment pulls the solve off while still looking plausible. Align and
  scale those from the 13x19 cm base. From N01 onwards (and all of 2026) the marker is on
  the turntable and is the intended reference. The cutoff is a position in the record,
  not a date — M01-M04 share the date and carry the bad marker. Per-capture answer:
  `markers_usable` in `docs/reference/scanning-record.json`.
- **The scanning record is a file, not a memory.** `docs/reference/scanning-record.json`
  (and `.md`) is generated from the conservator's spreadsheets by
  `scripts/build_scanning_record.py`. In 2026 tree IDs restart per day, so key a capture
  by `capture_id` (`<date>/<set>`) — `2026-06-15/A01` and `2026-06-16/A01` are different
  trees with **swapped** bags. See `docs/reference/capture-layout.md`.
- **There is no ground truth.** No correct mesh exists for a Rabati sherd. Nothing in
  `scripts/compare_meshes.py` scores against one, and no result from it should be phrased
  as if one existed.
