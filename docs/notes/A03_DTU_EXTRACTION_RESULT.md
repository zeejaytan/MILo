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

## If this is ever picked up again

- The cull step needs **replacing, not tuning**. For this material, dropping small connected
  components would remove all 589 specks and keep all ten sherds; a silhouette vote will not.
- `mesh_extract_dtu.py`'s block-limit gate and `scripts/cull_diag.py` stay useful whatever
  route is chosen; the diagnostic runs on CPU on the login node in about two minutes.
- Judging break-surface quality requires renders at a scale that resolves a fracture ridge —
  tight crops, not whole-tray views. That was never done here and would be the first thing
  to do.

See also `A03_BENT_SOLVE_AND_CLAMP_ARTEFACTS.md` (the masks and the clamp rig) and
`A02_MESH_METHOD_COMPARISON.md` (the COLMAP → OpenMVS route this was to be compared against).
