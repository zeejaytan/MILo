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
   Checks were added on the same principle: how many views carried a mask (zero would fuse
   the whole room and still exit 0); how many blocks the grid actually used; whether the
   marching-cubes scratch tensor will fit before it is attempted; and a hard failure on an
   empty output mesh. Search `[SHERD FORK]`.
   **Correction, measured:** an earlier version of this list said Open3D *silently drops*
   geometry past `block_count`. It does not, on CUDA — the hashmap rehashes and grows, and
   job 29694649 ran to 581% of its reservation with nothing lost. The real cost of
   under-reserving is that the old buffers stay alive through the growth, so the card holds
   far more than the grid's nominal size and the *extraction* then fails.

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
  **An Open3D CUDA OOM is not a recoverable exception**: it raises, then aborts the
  process while unwinding (`Block of ... should have been recorded`) and takes the job
  with it — job 29626640 died that way in 1:45. Never catch it; pre-flight the free VRAM
  and downgrade to host RAM instead, and retry in a *fresh process* if it still happens.
  The cause there was upstream's bare `torch.cuda.empty_cache()`, which frees PyTorch's
  cache but not its live tensors — and `cameraList_from_camInfos` keeps **every training
  image and its alpha on the GPU** (143 × 3200 × 2133 × 4 ch × 4 B ≈ **15.6 GiB**), with
  the Gaussians on top. Open3D allocates outside PyTorch's pool, so it got nothing.
  Release the camera pixels before fusing; the fusion needs only intrinsics, extrinsics
  and image size.
  What still forces CPU is MILo's own hard-coded `o3d.core.Device("CPU:0")`, now
  overridable with `--o3d_device` (see fork change 4). Fusion cost grows as 1/voxel², so
  GPU is worth a lot; the ceiling is that `block_count` reserves **80 KiB per block**
  (4096 voxels × 20 bytes) on whichever device.
  ~~**CPU:0 is not a fallback at sherd-capture grid sizes.**~~ **Withdrawn — this was an
  over-generalisation and it is worth keeping visible.** CPU:0 segfaulted in job 29694649
  (while over its reservation) *and* in job 29695830 (at 72.7% **of** it), and `vbg.cpu()`
  segfaulted on a healthy grid too — but **every one of those grids was 290,640 blocks
  (22 GiB), because the clamp rig was still in the mask.** "It failed at 22 GiB" was
  written up as "Open3D has no host path", which is a claim about the library drawn from a
  measurement about our masks. With the rig removed the grid is 34,129 blocks / 2.6 GiB and
  the host path has simply never been tried. `slurm/milo_extract_dtu.slurm` now tries
  **CPU:0 first and CUDA:0 as the retry**, in a fresh process each time — an illegal memory
  access poisons the CUDA context, so anything attempted after one in the same interpreter
  fails for an unrelated reason.
  **The CUDA *binary* is the bug, and `--o3d_device CPU:0` did not escape it.** Open3D
  chooses its binary at **import**, from whether a GPU is visible — not from the device you
  hand it. So on a compute node `CPU:0` was the CPU *device of the CUDA build*, and
  `extract_triangle_mesh()` died there too: illegal memory access on CUDA:0 (job 29771412),
  segfault on CPU:0 (job 29774524), both at 34,129 blocks / 2.6 GiB with 73.9 GiB free.
  Two failures, one cause, and neither is memory.
  **The cheap test that separated them, after four Slurm jobs could not:** 20 synthetic
  views of a sphere, 256 blocks, run on the login node in seconds. The identical call
  succeeds in the CPU binary. That is the whole diagnosis, and it cost nothing — the login
  node had been quietly exercising the good binary all along, which is exactly why "do not
  diagnose Open3D from the login node" (above) was true and also why the login node was
  where the answer was.
  `mesh_extract_dtu.py` now blanks `CUDA_VISIBLE_DEVICES` across the `import open3d` and
  restores it immediately, so `CPU:0` means the CPU binary while PyTorch keeps the GPU
  (importing torch does not create a context; torch's device view is pinned right after the
  restore so the blanking cannot leak into rendering). **The log line to check is
  `binary: cpu`.** `binary: cuda` means the extraction is going to fail.
  **A fallback guarded by `set -e` is not a fallback.** The CUDA retry added to
  `milo_extract_dtu.slurm` never fired in job 29774524: `set -euo pipefail` turned the
  segfaulting pipeline into a fatal error and killed the script before the "did it produce a
  mesh" test could run. `run_fuse ... || true`.
  **Fitting on the card is necessary but NOT sufficient.** Job 29771412: 34,129 blocks,
  2.1 GiB of scratch wanted, **73.9 GiB free**, and CUDA `extract_triangle_mesh()` still
  died with *"illegal memory access"* inside Open3D's own `MemoryManagerCUDA`. That is
  [isl-org/Open3D#4824](https://github.com/isl-org/Open3D/issues/4824) — the identical
  crash, also at `block_count=50000`, reported in 2022 and neither diagnosed nor fixed. Do
  not read a CUDA extraction failure as a memory problem without checking the free figure
  the script prints.
  Budget on the card anyway, and the budget has **two** terms, which is the trap:
  the grid is 80 KiB × `block_count` reserved up front, and `extract_triangle_mesh()` then
  allocates a scratch tensor of **64 KiB × *active* blocks** on top of it
  (`{n_blocks,16,16,16,4}` int32, `VoxelBlockGridImpl.h`). Its failure reads *"Unable to
  allocate assistance mesh structure for Marching Cubes with N active voxel blocks…
  consider using a larger voxel size"*, which sounds like a hard ceiling on N and is not —
  it is an ordinary allocation failure. Reserve the blocks properly and 290,640 of them
  extract fine in 19.1 GiB of scratch.
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
- **The A03 masks keep the clamp rig, and that is what makes TSDF fusion unaffordable.**
  `data/17062025/A03/images_masked` keeps **24.4% of every frame**; by the redness test
  that separates fired clay from steel (`R − (G+B)/2`, sherds +7…+27, rig ≈ −5) only
  **8.7% of that is sherd** — 61 cm² of clay against **644 cm² of mounting hardware** per
  view. The masks are not broken at what they were built for: the backdrop is gone and the
  outlines are tight. Nobody asked them to remove the stand holding the sherds up.
  The cost is not cosmetic. Thin chromed rods carry enormous surface area for their volume
  and are specular, so the depth the Gaussians render for them **moves with the
  viewpoint** and the 143 per-view shells never reinforce each other. The A03 voxel grid
  therefore used **290,640 blocks** — an implied ~41.6 m² of fused surface against ~0.1 m²
  of actual sherd — and every extraction failure in jobs 29626640 / 29694649 / 29695830
  traces back to it. It also kills the resolution ladder: rung 2 needs ~2.3 M blocks
  (178 GiB) with the rig in, and ~200 k (15 GiB) with it out.
  Run **`scripts/mask_content.py --images <dir> --out <dir>`** before spending a GPU. It
  reports the split and writes *photo | kept by mask | reads as sherd* panels — look at
  those, because the redness test misreads a warm-lit rig and a shadowed sherd.
  The OpenMVS route's `masks_milo/` and `masks_user/` are built the same way and should be
  assumed to share this until checked.
- **Fixed, and the fix was already on disk — look before building.** SAM 3 sherd-only masks
  existed for A03 the whole time at `masks/17062025/A03_erode0/masks_sherds`, written by
  `scripts/sam3_masks.py` (job 29448323). They had simply never been wired in, because they
  are drawn on the **original 5568×3712 photographs** while MILo trains on COLMAP's
  **undistorted 3200×2133** views, and `build_masked_images` refused the size mismatch — a
  correct refusal, since resampling a mask that is misaligned only hides the misalignment.
  What resolves it is measuring rather than asserting: A03's camera is `SIMPLE_RADIAL`
  k1 = −0.0081, so undistortion moves a **corner** pixel 1.23 px and a pixel where the
  sherds actually sit **0.2 px**, in the undistorted frame. A NEAREST resize is therefore
  honest here. `colmap_to_milo.py --masks <dir>` now does exactly that, gated on the solved
  camera: a *cropping* undistorter (aspect ratio changed), an unreadable camera, or a shift
  past `--max-mask-shift-px` (default 2) is still refused outright.
  Three SAM 3 variants exist; **`A03_erode0` is the one to use.** Rendered at full
  resolution over the photograph, the default (eroded) outline sits visibly *inside* the
  clay and drops 7.1 cm² of it, `dilated` climbs onto the black clamp jaw, and `erode0`
  sits on the edge. Measured per view, kept area: 23.84% → **2.28%**; non-sherd area
  **627 cm² → 16 cm²**; 8–10 separate sherds resolved per view against the 10 that exist.
  Dataset: **`data/17062025/A03_sherds`** — use it in place of `data/17062025/A03`.
  Masking here is a **fusion-time** operation, so this needs no retrain: the same
  `A03_nomask` Gaussians are reused and the mask is the only thing that changes.
- **There is no ground truth.** No correct mesh exists for a Rabati sherd. Nothing in
  `scripts/compare_meshes.py` scores against one, and no result from it should be phrased
  as if one existed.
