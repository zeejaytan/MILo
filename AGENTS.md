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
2. **`milo/train.py` — a comment only; the patch was REMOVED (commit `770338f`).** This
   fork used to composite the background colour into the ground truth outside the mask.
   It masked the ground truth but *not* the render, so the loss instructed the model to
   paint background over every pixel outside the outline — including the 6 px the masks
   are eroded by, which on A03 is 0.6–0.9 mm of real sherd and is the fracture edge. The
   object-centric splatting literature is explicit that both sides must be masked or the
   two losses fight (arXiv:2501.08174). Upstream's design already reaches the same goal at
   a better stage: the alpha becomes `gt_mask` and is consumed once, in
   `regularization/sdf/integration.py`, to cull the SDF field to the visual hull — the
   mask decides what is *solid*, not what the pixels should look like. What remains at
   `train.py:218` is a `[SHERD FORK]` comment recording why the line is deliberately
   absent, so nobody re-adds it. **Caveat: this is reasoning plus literature, not a
   measurement on our material — no masked-vs-unmasked MILo A/B has been run.**
3. **`.gitignore`** — upstream ignores `*.sh`, `*.slurm`, `*.ply` and `*.png` outright,
   which would silently swallow this fork's own tooling. Re-included by name at the end
   of the file.
4. **`milo/eval/dtu/mesh_extract_dtu.py` — TSDF resolution made adjustable and legible.**
   New flags `--voxel_size`, `--block_count`, `--trunc_voxel_multiplier`, `--ply_name`,
   `--mm_per_unit`; all default to the author's effective values, so passing none of them
   reproduces upstream exactly. Why each exists:
   - `--voxel_size` was hard-coded at `0.002`. DTU normalises every scan to a fixed size,
     so one voxel size fits that benchmark; our captures are in COLMAP units that differ
     per capture. 0.002 units is **0.75 mm on A03**, and the depth maps it fuses are
     rendered at 0.21 mm/px — so the author's setting discards a factor of 3.6 that the
     photographs actually carry. See the resolution note under *Domain notes* below.
   - `--trunc_voxel_multiplier` is the one that matters if you touch the voxel size.
     Open3D's truncation band is `trunc_voxel_multiplier * voxel_size`, upstream passes it
     to **neither** `compute_unique_block_coordinates` nor `integrate`, so it sits at 8 —
     one block wide, which is why 8 pairs with `block_resolution=16`. Refining the voxel
     alone shrinks the band with it (≈6 mm → ≈1.5 mm at 4×), and where Gaussian-rendered
     depth disagrees between views by more than the band, surfaces stop reinforcing and
     the mesh fragments. Raise it in step with any refinement. It must be passed to both
     calls or block allocation will not cover the band integration writes into.
   - `--ply_name` so a ladder of voxel sizes does not overwrite `recon_tsdf.ply`.
   - `--mm_per_unit` is reporting-only: the log then states voxel size and band in
     millimetres, which makes a wrong scale obvious instead of plausible.
   Three checks were added on the same principle: how many views carried a mask (zero
   would fuse the whole room and still exit 0), how many blocks the grid actually used
   (Open3D **silently drops** geometry past `block_count`, which looks like a slightly
   incomplete mesh rather than an error), and a hard failure on an empty output mesh.
   Search `[SHERD FORK]`.

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
- **What actually limits TSDF resolution here — measured on A03, not assumed.** Three
  separate ceilings, and only the first is a setting:
  1. *Voxel size*, the author's `0.002` units × 373.7 mm/unit = **0.75 mm**. Adjustable.
  2. *Depth-map sampling*, the real floor: images are 3200 × 2133, `fx` 6829.8 px, camera
     ring 3.77 units ≈ **1.41 m** from the turntable centre, giving 1408/6830 = **0.21 mm
     per pixel** at the object. (Cross-check: 3200 px × 0.21 = 660 mm field of view against
     a ~500 mm tray — consistent.) Refining below ~0.2 mm samples nothing new.
  3. *Truncation band*, `trunc_voxel_multiplier × voxel_size` = **±6.0 mm** at the
     defaults. This is what fails first when you refine, and it is separately controllable
     — see fork change 4.
  So the author's voxel is **3.6× coarser than the photographs support**, and refining it
  to ~0.0006 units (0.22 mm) is justified by the data. That is a claim about *sampling*
  only: a finer grid resolves whatever the rendered depth maps contain, which at a quarter
  of a millimetre may be fracture relief or may be Gaussian depth noise. Renders decide
  that, never the vertex count.
- **Open3D's CPU/CUDA choice is made at import, on whatever node you are sitting on — do
  not diagnose it from the login node.** `envs/milo` has open3d **0.19.0 with the CUDA
  build present** (`open3d/cuda/pybind*.so`, 802 MB, alongside the 225 MB CPU one).
  `open3d/__init__.py` calls `open3d_core_cuda_device_count()` and only imports the CUDA
  module if that is `> 0`; on the login node it is 0, so `o3d.core.cuda.is_available()`
  reports `False` there and looks exactly like a CPU-only wheel. It is not. No rebuild is
  needed — run it on a GPU node.
  What still forces CPU is MILo's own hard-coded `o3d.core.Device("CPU:0")`, now
  overridable with `--o3d_device` (see fork change 4). Fusion cost grows as 1/voxel², so
  GPU is worth a lot; the ceiling is that `block_count` reserves **80 KiB per block**
  (4096 voxels × 20 bytes) on whichever device — 1.5 M blocks is 114 GiB and will not fit
  an A100. Coarse voxels on the GPU, fine voxels in host RAM.
- **MILo has two different mask-culls and they do opposite things on a turntable.**
  `--init integration` (`regularization/sdf/integration.py`) keeps anything that falls
  inside a mask in **at least one** view, and — the line that actually bites, `:94` —
  labels never-seen points `-100`, i.e. *deeply solid*, rather than deleting them. A
  mounting rig sits behind the sherds from many angles, so it passes that test trivially:
  this is why the A03 mask-cull run kept the whole rig fused into one 500 mm object.
  `eval/dtu/evaluate_dtu_mesh.py:cull_mesh` keeps a vertex only if it is inside a 6-px
  dilated outline in **every** view (`(sampled_masks > 0.).all(dim=-1)`), excusing views
  where the vertex falls off-frame. `eval/dtu/mesh_extract_dtu.py:66-67` is a third thing
  again — it zeroes masked *depth pixels* before TSDF fusion, so background never enters
  the voxel grid at all. Any-view, all-views, never-fused: do not call these "the mask".
- **There is no ground truth.** No correct mesh exists for a Rabati sherd. Nothing in
  `scripts/compare_meshes.py` scores against one, and no result from it should be phrased
  as if one existed.
