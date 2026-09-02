# A03 — MILo's own DTU extraction route: result and verdict

**Verdict (conservator's decision, 2026-09-01): the mesh quality is not acceptable for this
material. The route is not pursued further.**

This note records what was actually run, what came out, and — as precisely as the evidence
allows — what that verdict does and does not cover. It is written so a later reader can tell
which parts are measured and which parts were never tested.

Job **29798496** (`gpu-h100`, 3 min 35 s). Dataset `data/17062025/A03_sherds` (SAM 3
sherd-only masks, `A03_erode0`), Gaussians reused unchanged from `output/17062025/A03_nomask`
— masking here is a fusion-time operation, so no retrain was involved. 164 photographs, 143
training views after `--eval` holds out every 8th.

Meshes and pictures: `output/17062025/A03_dtusherds/` on Spartan; renders copied to
`MILo/artifacts/A03_dtu/` (gitignored).

---

## What the two steps are

The authors' DTU route is two separate operations and they were run separately on purpose,
because the question was what each one does.

1. **Masked depth fusion** (`eval/dtu/mesh_extract_dtu.py`) — render a depth map from the
   trained Gaussians for every training view, zero the pixels outside the sherd mask, and
   fuse what remains into a voxel grid. Background never enters the grid at all.
2. **Silhouette cull** (`eval/dtu/evaluate_dtu_mesh.py:cull_mesh`, driven by
   `scripts/cull_dtu_mesh.py`) — project every vertex of that mesh into every training
   camera and keep it only if it lands inside the sherd outline, dilated by 6 pixels, in
   **every** view. A vertex that falls outside the picture frame in a view is excused for
   that view.

## Step 1 — masked depth fusion: it works

Voxel **0.822 mm**, truncation band **±6.6 mm**, 32,209 active blocks, 2.5 GiB of grid.
Output `recon_tsdf_v0.0022.ply`: 91,463 vertices, 173,567 faces, overall extent
**481 × 337 × 327 mm** — the spread of the sherds across the tray, not the size of any one
of them. Millimetre copy: `mesh_dtufusion_v0.0022_mm.ply`.

The fusion separates the fragments correctly:

- **Exactly 10 solid pieces have more than 1,000 triangles, and A03 holds 10 sherds.**
- Their individual sizes run **20–80 mm** across, which is right for these fragments.
- Those ten pieces carry **97.2%** of all the geometry (168,738 of 173,567 faces).
- The remaining **589 pieces average 8 triangles each** — floating specks, not sherds.

The mounting rig is absent, which is what the `A03_erode0` sherd-only masks were for. On
that count the step does what it claims.

Render: `artifacts/A03_dtu/recon_tsdf_v0.0022_render.png`.

## Step 2 — the silhouette cull: it deletes the entire mesh

All 91,463 vertices. Not a subset.

Two obvious explanations were checked and **both are wrong**:

- **The masks are not empty or missing.** All 164 masked images carry alpha; kept area runs
  **1.49% to 3.06% per view, median 2.17%**, no view keeps nothing. `cull_dtu_mesh.py` had
  only checked that a mask *exists*, which an empty mask would have passed — it isn't that.
- **The principal point is not the problem.** `cull_mesh` forces the principal point to the
  image centre and ignores COLMAP's. A03's undistorted camera is PINHOLE with
  `cx = 1600.0`, `cy = 1066.5` — *exactly* W/2 and H/2. That shortcut costs nothing here.

What is actually happening, measured by reprojecting the mesh into all 143 views with
COLMAP's own poses (`scripts/cull_diag.py`):

| Quantity | Value |
|---|---|
| Vertices in frame, per view | 91,463 — **all of them, in every view**, so nothing is ever excused |
| Share of vertices each view accepts | 67.7% – 90.0%, **median 82.1%** |
| Vertices passing all 143 views | **0** |
| Best-surviving vertex | passes **139** of 143 |
| Median vertex | passes 124 of 143 |
| Passing ≥ 95% of views (136) | 4,627 (5.1%) |
| Passing ≥ 90% of views (129) | 31,335 (34.3%) |

Every view individually accepts most of the mesh — but a *different* ~18% each time, and the
intersection of 143 such votes is empty.

**The cull's judgement is sound; its threshold is not.** Colouring each vertex by how many
views accepted it (`artifacts/A03_dtu/cull_passed_render.png`, red = nearly all, blue =
rejected often) shows the blue concentrated exactly on the thin streaks and spikes hanging
off the sherds — the junk that ought to go. The sherd bodies are red. But relaxing the
threshold does not rescue it: at 90% only a third of the mesh survives and the sherds are
already chewed down to slivers (`cull_p90_render.png`).

**Why, most likely.** The all-views rule assumes the masked object is the only thing in the
scene that can occlude it — true on the DTU benchmark, where one object sits alone. Here ten
fragments sit in clamps, so from many angles a rod or a jaw crosses in front of a sherd. The
sherd surface behind that rod is genuinely absent from that view's outline, and the cull
votes to delete it: correct by its own rule, wrong for our purpose. **This explanation fits
the evidence but was not confirmed** — the test that would settle it is whether each vertex's
rejecting views form a contiguous band of viewing angles (a fixed obstruction) rather than a
scatter (noise). That test was not run.

## What the verdict rests on, and what it does not cover

Honest limits, so this is not read as more than it is:

- **One capture (A03), one run.** A lead about the method, not a result about sherds in
  general.
- **The voxel actually achieved was 0.822 mm** — 10% coarser than the paper's own 0.747 mm,
  and about **four times coarser than the photographs support** (depth sampling is
  0.206 mm/px at the object). The finer settings were never reached: see the ceiling below.
  So this is a verdict on the route *as it could actually be run*, not proof that MILo's
  extraction cannot do better at a quarter of a millimetre.
- **The renders behind the verdict are whole-tray views at roughly 0.5 mm per pixel.** That
  resolution cannot resolve a fracture ridge, so nothing in this note is a measurement of
  break-surface fidelity. What it does show is the fragment count, their sizes, the streaks
  and the specks.
- **Every millimetre figure carries at least 1.4%**, because A03's two scale bars disagree by
  that much.

## The ceiling that stopped the finer settings

`extract_triangle_mesh()` in Open3D 0.19.0 allocates a scratch tensor of **64 KiB per active
block** and sizes that allocation with a **signed 32-bit byte count**. At 32,768 blocks that
is exactly 2^31 bytes; at or past it the size wraps negative and the process dies with no
message — a segfault on CPU, "illegal memory access" on CUDA. It is device-independent and
free memory is irrelevant: job 29771412 died with 73.9 GiB free.

Confirmed on clean synthetic geometry (a sphere, no Gaussians, no masks), with the boundary
predicted from the arithmetic *before* the confirming runs:

| Active blocks | Scratch | Result |
|---|---|---|
| 28,176 | 1.72 GiB | 5,086,918 vertices |
| *32,768* | *2.00 GiB* | *predicted cliff* |
| 34,184 | 2.09 GiB | core dumped |

A03 at the paper's 0.002 units needs **34,129 blocks — 4% past the cliff**, which is why four
earlier jobs failed and were misread as memory problems. `mesh_extract_dtu.py` now refuses
before the call (`MC_BLOCK_LIMIT`, overridable with `--allow_mc_overflow`) and prints the
coarser voxel that would fit. Rung 0 (0.0022 units, 32,209 blocks) is the finest setting that
clears it.

The rest of the resolution ladder is therefore **untested, not failed**: rung 2 (0.37 mm)
needs roughly 136,000 blocks and rung 3 (0.22 mm) roughly 1,300,000, both far past 32,768.
Reaching them needs the extraction split into spatial tiles each under the limit, or an
independent marching cubes over the dense TSDF. Neither is written, and per the verdict above
neither is being written.

## The four places MILo touches a mask, and what each one does

Written down because they were being collapsed into one question — "do masks help?" — and
they have four different answers that lead to four different decisions.

| Where | What it does | Result on this material |
|---|---|---|
| `milo/train.py`, the training loss | Upstream applies **no** mask at all. Our fork's patch was removed at `770338f`. | **Untested.** The patch masked the ground truth but not the render, which instructs the model to paint background over the 6 px the masks are eroded by — 0.6–0.9 mm of real sherd on A03, i.e. the fracture edge. Removing it was reasoning plus literature (arXiv:2501.08174), **never A/B tested here**. |
| `regularization/sdf/integration.py`, `--init integration` | Keeps a point inside a mask in **at least one** view; `:94` labels never-seen points −100 (deeply solid) instead of deleting them. | **Actively harmful.** Measured: kept the whole clamp rig as a single 500 mm object. |
| `eval/dtu/mesh_extract_dtu.py:66-67`, masked depth fusion | Zeroes masked depth **pixels** before TSDF fusion, so background never enters the voxel grid at all. | **Works.** Ten pieces above 1,000 triangles against the ten sherds A03 holds, 20–80 mm across, 97.2% of the geometry, rig absent. |
| `eval/dtu/evaluate_dtu_mesh.py:cull_mesh`, the all-views silhouette cull | Deletes any vertex outside the outline in **any** training view, applied after the mesh exists. | **Deletes everything.** All 91,463 vertices. |

Two consequences that were being missed:

**Masking at fusion time is not a post-hoc crop and cannot leave a rig-shaped hole.** The
masked pixels are discarded before any surface is built, so there is nothing for the rig to
be cut out of. Cropping a finished mesh is not the only route, and it is not what the
authors' own DTU code does.

**The fusion mesh nevertheless has holes, and they have nothing to do with masking.** On the
ten sherds of `recon_tsdf_v0.0022.ply`:

```
piece   faces           size mm   holes   open edge mm   biggest hole mm   watertight
    1   38508      33 x 79 x 74      10          237.7             135.8        False
    2   30526      58 x 60 x 78      12          470.8             427.3        False
    3   23357      28 x 53 x 71      25          453.0             282.3        False
    4   15869      36 x 52 x 41      15          301.1             131.1        False
    5   14409      30 x 70 x 31       7          189.8              69.7        False
    6   12749      27 x 50 x 37       9          207.7              68.4        False
    7    9722      27 x 38 x 37       8          277.8             184.9        False
    8    9544      20 x 34 x 37       7          172.3              75.6        False
    9    7413      16 x 31 x 37      22          342.3             177.3        False
   10    6641      20 x 23 x 32      16          197.3              68.4        False
                                    131 holes, no sherd watertight
```

Rendered at 0.115 mm/px from four sides (`artifacts/A03_dtu/sherd2_holes.png`), the hole
rims sit on the thin flared edges and along the underside — the face resting on the mount and
the patches the clamp jaws physically cover. These are **occlusion** holes. No choice of mask
creates them and no choice of mask removes them; only more viewpoints, or turning the sherd
over, would.

**Where masks cannot help at all:** surface detail. Resolution is set by the voxel size
reached (0.822 mm), the depth-map sampling (0.206 mm/px) and the noise in the Gaussians'
depth. Masks decide what is *included*, never how finely it is *resolved*.

## Getting past the block cliff: is chunked extraction viable?

Researched 2026-09-02 against Open3D 0.19.0's own source at the pinned tag, not from memory.
**Answer: yes, and it is less work than expected — but it is the second-best of three
options, and none of them should be built before one short measurement.**

**The cliff is per-call, not per-scene.** `ExtractTriangleMesh` in
`cpp/open3d/t/geometry/kernel/VoxelBlockGridImpl.h` allocates exactly one scratch tensor:

```cpp
index_t n_blocks = static_cast<index_t>(block_indices.GetLength());
mesh_structure = core::Tensor::Zeros(
        {n_blocks, resolution, resolution, resolution, 4}, core::Int32, device);
```

with `using index_t = int`. That is 16³ × 4 × 4 = 65,536 bytes per block, sized by a signed
32-bit count, so 32,768 blocks is exactly 2³¹ bytes. `n_blocks` is the length of the block
list handed to *that call* — so splitting the grid genuinely fixes it. Nothing about the
scene's total size matters.

**The public API already supports tiling.** `integrate()` takes an explicit block-coordinate
tensor ("Integrate an RGB-D frame in the selected block coordinates"), and
`compute_unique_block_coordinates()` returns the (3, M) coordinates a depth map would touch
*without* activating them. Filter that tensor to a tile's coordinate range and integrate only
those. No hashmap surgery, no patched Open3D.

**The expensive half is already cached.** `mesh_extract_dtu.py` renders all 143 depth and
colour maps from the Gaussians into `depth_list` / `color_list` in host memory before fusion
begins. A tile loop reuses them. **Chunking costs extra integration passes, not extra
renders** — and the rendering is what needs the GPU.

**A03 removes the hard part.** Seams are what makes chunked TSDF unpleasant: marching cubes
needs a block's 27-neighbourhood, so a tile boundary produces a crack. Here the ten sherds are
physically separate objects, so **one tile per sherd** contains a whole sherd and cuts nothing.
No halo, no clipping, no seam merging.

**How far that actually gets you.** Blocks scale as (1/voxel²) × (band thickness in blocks),
and the band is `trunc_voxel_multiplier × voxel`. The file's own comment is right that
refining the voxel while leaving the multiplier at 8 shrinks the truncation band in
millimetres, which is what makes noisy Gaussian depth stop reinforcing and the mesh fragment.
Holding the band at a **fixed physical width** means raising the multiplier in step, and that
makes blocks grow as 1/voxel³, not 1/voxel². From the measured 32,209 blocks at 0.822 mm:

| voxel | multiplier for a constant band | whole scene | per sherd | under the 32,768 cliff? |
|---|---|---|---|---|
| 0.822 mm (current) | 8 | 32,209 | ~3,200 | already fits whole |
| 0.60 mm | 11 | ~91,000 | ~9,100 | yes, per sherd |
| 0.45 mm | 15 | ~197,000 | ~19,700 | yes, per sherd |
| 0.37 mm | 18 | ~353,000 | ~35,000 | **no** — needs sub-tiles |
| 0.22 mm | 30 | ~1,680,000 | ~168,000 | no — ~8 sub-tiles per sherd |

(The earlier figures in this note — 136,000 at 0.37 mm, 1,300,000 at 0.22 mm — assumed the
multiplier stays at 8, i.e. a band that shrinks with the voxel. Both conventions are shown
because they give different tile counts and the choice is a real one.)

So **per-sherd tiling alone reaches about 0.45 mm** — a 1.8× refinement on the current mesh,
seam-free, roughly eighty lines of change. Going finer reintroduces seams and needs a
one-block halo plus clipping to the tile core.

### Two cheaper routes found while checking this

**`extract_point_cloud` has no block cliff worth the name.** Reading the same header: it
allocates *no* per-block scratch — only output tensors sized by `valid_size`. Its only 32-bit
exposure is `index_t n = n_blocks * resolution3`, which overflows at about **524,288 blocks,
sixteen times higher**. A dense oriented point cloud at 0.37 mm therefore extracts in a
single call today, with no chunking at all, and can be meshed with screened Poisson. The
catch is real and matters here: **Poisson invents surface across the 131 occlusion holes
above.** For a conservator that is worse than a hole — it produces sherd geometry nobody
photographed. Density trimming controls it, but it has to be done and checked by eye.

**The block cliff is not MILo's.** `milo/eval/dtu/` is the *benchmark harness*, written to
score against DTU. MILo's own method, `milo/mesh_extract_sdf.py`, extracts by marching
tetrahedra over the Gaussian structure (`utils/tetmesh.marching_tetrahedra`) and never builds
a voxel grid. There is no block limit on that path and none of this applies to it.

**Upstream will not fix it.** [isl-org/Open3D#4824](https://github.com/isl-org/Open3D/issues/4824)
reports the same crash at `block_count=50000` and has been open and unlabelled since March
2022. [VDBFusion](https://github.com/PRBonn/vdbfusion) is what people move to when they hit
this repeatedly: an OpenVDB backend with no size assumption, which adapted Open3D's own
marching cubes to the VDB structure. It is a sound library and the wrong amount of machinery
for ten sherds on a table.

### Is a finer voxel worth it for *this* material?

The gate is whether the depth feeding the grid is quieter than the voxel. If it is not, a
finer grid spends its resolution on noise. Measured on the three largest sherds of the
existing mesh — how far the surface departs from a plane fitted to every vertex's neighbours
within 3 mm:

```
sherd 1: 19,422 vertices   p10 0.034  median 0.072  p90 0.457 mm
sherd 2: 15,622 vertices   p10 0.037  median 0.144  p90 0.426 mm
sherd 3: 12,011 vertices   p10 0.038  median 0.153  p90 0.439 mm

only 0.3% of the surface departs by more than the 0.822 mm voxel that produced it
```

Rendered per-vertex and unbinned (`artifacts/A03_dtu/sherd1_roughness.png`), the departure is
**not** scattered like static: it is low across the broad wall and concentrated in a band
along the sherd's edges, where the fracture surface meets the wall. It is reading real
geometry, and the geometry a finer voxel would buy is exactly the fracture edge — the feature
this project cares about.

**The limit of that measurement, stated plainly:** marching cubes interpolates within a
voxel, so this cannot see anything happening below 0.822 mm. It bounds the depth noise from
above — the surface is not 2–3 mm noisy, or it would show — and it does not measure it. The
direct test is one short GPU job: render depth from a handful of views, project into a common
frame and measure the cross-view disagreement in millimetres. **That measurement, not the
chunking code, is what should be run first**, because it decides whether any of the above is
worth writing.

### The comparison that should settle it before any of this is built

The ceiling after all this work is ~0.45 mm seam-free, ~0.37 mm with sub-tiles, against
depth maps that sample the sherd at 0.206 mm/px. That is one to two useful rungs, not an order
of magnitude. The COLMAP → OpenMVS route works at pixel level and may already deliver finer
surfaces on the same sherds. **Check what OpenMVS actually achieves on A03 first**
(`A02_MESH_METHOD_COMPARISON.md` is the nearest existing measurement). If it is already at or
below 0.45 mm, chunking a benchmark harness to reach 0.45 mm is a day spent to arrive where
the other route already is.

## If this is ever picked up again

- The cull step needs **replacing, not tuning**. For this material, dropping small connected
  components would remove all 589 specks and keep all ten sherds; a silhouette vote will not.
- `mesh_extract_dtu.py`'s block-limit gate and `scripts/cull_diag.py` stay useful whatever
  route is chosen; the diagnostic runs on CPU on the login node in about two minutes.
- Judging break-surface quality requires renders at a scale that resolves a fracture ridge —
  tight crops, not whole-tray views. That was never done here and would be the first thing
  to do.
- **Order of work, if the resolution ceiling is the reason for picking it up.** (1) Measure
  the cross-view depth disagreement in millimetres — one short GPU job, and it decides
  everything after it. (2) Check what COLMAP → OpenMVS already achieves on A03; if it is
  already at or below 0.45 mm there is nothing to gain here. (3) Only then write the tiling.
  Per-sherd tiles are seam-free and reach ~0.45 mm; `extract_point_cloud` plus trimmed
  Poisson reaches further with no tiling at all but invents surface across occlusion holes,
  which on this material is the more dangerous failure. Details and the block arithmetic are
  in "Getting past the block cliff" above.

See also `A03_BENT_SOLVE_AND_CLAMP_ARTEFACTS.md` (the masks and the clamp rig) and
`A02_MESH_METHOD_COMPARISON.md` (the COLMAP → OpenMVS route this was to be compared against).
