# 02: Pinned PGSR source record

**What to build:** the repeatability record both PGSR variants build from, written on the laptop before any GPU burns.

**Answers:** M8

**Blocked by:** 01 new sibling shell.

**Status:** resolved

- [x] Stock upstream commit and community masked-fusion construction commit both pinned in the ticket before any submission; an unpinned run counts as no result
- [x] States where a sherd outline enters each variant (fusion-time depth zeroing for the masked variant, post-fusion component filter only for stock) or declares the variant unbuildable with the reason
- [x] Records the known TSDF extraction block ceiling as binding-until-shown-otherwise for the required voxel, plus full-resolution and indoor object-centric settings carried over
- [x] Training-time masking and post-training pruning stay retired with no new code path unless fresh justification is amended into M8 first
- [x] Env probe recorded (existing env name plus import check for the plane rasterizer and torch); rebuild only on probe failure

## Comments

- 2026-09-09: pins recorded before any job. **Stock:** `zju3dv/PGSR` at `de24f1a38b350387e8d8fe381b2cd70c1ae946e7` (fork HEAD at creation; == upstream HEAD that minute). Lives in this repo as `origin/main^2` under merge `2e03931`; merge commit itself is shell, never a result pin.
- **Community (variant A):** `GhostLate/PGSR_MeshReconstruction` at `8777d4be79613992f951b469adde577b22db6b21` (main HEAD, 2026-05-26, "added new eval results"). Shallow-cloned to OS temp and read at that commit — no code change, clone deleted after.
- **Mask entry verified at the pin, not trusted from memory:** `scripts/preprocess/crop_and_mask.py` bakes the mask into RGBA alpha → `scene/cameras.py` reads alpha as `view.mask` → `render.py:120-121` zeroes background depth (`ref_depth[view.mask.squeeze() < 0.5] = 0`) before TSDF fusion. README §2.4 documents the same construction. Variant B (stock + post-fusion small-component filter) needs no mask path.
- **Watch-item for 04, not a blocker:** the community path bakes a *feathered, dilated* mask and crops to one global bounding box — built for a single foreground object, not ten separate sherds. Ticket 04 measures whether that costs rim clay; erode0-style tight masks stay an option there.
- **Env probe (Spartan login node, seconds, read-only):** existing `envs/milo` (torch 2.3.1+cu118, open3d 0.19.0, nvdiffrast editable) imports `torch`, `simple_knn`, `fused_ssim`, `plyfile` cleanly. **One additive delta:** `diff_plane_rasterization` is not installed and exists in neither tree (MILo vendors only the standard-rasterizer family) — build it once into the same env at 04 time (CUDA compile belongs on a GPU node, not the login node). No fresh env.
- 32,768-block ceiling assumed binding for PGSR's Open3D TSDF step until 04 shows otherwise.

## Answer 2026-09-13

Pins held for the whole trial: every train/extract/probe ran at stock `de24f1a` (+ community `8777d4b` construction for A); Spartan checkout stayed detached there, tooling entering via `fetch + checkout -- slurm scripts`. Retired lines stayed retired. One amendment owed to the record: the mask-entry verification missed that training never reads `view.mask` (bake keeps full RGB; `train.py`/renderer mask-free) — variant A's mask acts at fusion only. M8 answered NO as mesh route.
