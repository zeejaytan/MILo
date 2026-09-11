# Fork changes against upstream

Moved from `AGENTS.md` on 2026-09-11 so it loads only when needed; text unchanged except
cross-references. Code sites carry a `[SHERD FORK]` marker.

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
     photographs actually carry. See the TSDF resolution entry in `traps.md`.
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
5. **`milo/mesh_extract_sdf.py` — post-training prune hook (intent M4).** New flags
   `--keep-idx` (numpy index array from `scripts/prune_rig_gaussians.py`) and `--out-name`;
   both default to upstream behaviour. With a keep set, pivots are drawn from kept
   Gaussians only at the existing downsample-index seam, and pivot spread stays at trained
   scale (no downsample compensation — a pruned set keeps full clay density, unlike a
   thinned one). Empty or out-of-range keep sets refuse loudly. Search `[SHERD FORK]`.
