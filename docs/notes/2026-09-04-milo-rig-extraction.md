# MILo-only rig extraction routes — source-checked (2026-09-04)

Scope: **MILo workflow only.** No OpenMVS, no separate COLMAP pipeline, no new
dependencies outside this repo. Every candidate below runs from the trained
Gaussians in `output/` with code that is in `C:\PR\MILo` (or upstream
`Anttwo/MILo`) plus the pinned Open3D 0.19.0 wheel already in `envs/milo`.

Shared ground (**measured** on A03, `docs/notes/A03_DTU_EXTRACTION_RESULT.md`):
10 sherds per tray; SAM 3 sherd-only `erode0` masks keep 2.28% of frame;
depth maps sample the sherd at ~0.21 mm/px; the fusion mesh carries 131
occlusion holes (mount contact + clamp jaws — no mask creates or removes
them); the 32,768-block cliff is per extraction *call*.
373.7 mm/unit on A03. Status words: **measured** = seen on our material;
**inferred** = follows from a read source, unrun here; **web-reported** =
what the source states, untied to our material.

Upstream intent, read from source (not memory): MILo's method is
"differentiably extract a mesh … at every iteration directly from the
parameters of the Gaussians" (abstract, `https://arxiv.org/abs/2506.24096`,
v2 29 Oct 2025). Post-training extraction offers three documented paths
(`https://github.com/Anttwo/MILo`, README §3, master):
§3.1 learned-SDF + marching tetrahedra over Gaussian pivots
(`mesh_extract_sdf.py`, default); §3.2 integrated opacity field or scalable
TSDF on the same pivots (`mesh_extract_integration.py`, GOF recommended);
§3.3 traditional TSDF on a regular voxel grid, "heavily inspired from 2DGS",
which "does not scale to unbounded real scenes with background geometry"
(`mesh_extract_regular_tsdf.py`). The DTU harness (`milo/eval/dtu/`) is the
benchmark scorer, not the method — but on rig material it is the only path
with a working mask.

## 1. DTU masked depth fusion + `extract_triangle_mesh` — works, cliff-limited

Rig removal (**measured**): `milo/eval/dtu/mesh_extract_dtu.py:133-135`
zeroes rendered depth where `gt_mask < 0.5` (and `:135` where alpha < 0.5)
*before* `vbg.integrate()` (`:282-290`). Background never enters the grid —
not a crop of a finished mesh, so there is no rig-shaped hole to leave
behind. Open3D skips zeroed pixels inside the kernel:
`if (depth <= 0 || depth > depth_max || ...) return;` (**web-reported**,
`https://raw.githubusercontent.com/isl-org/Open3D/v0.19.0/cpp/open3d/t/geometry/kernel/VoxelBlockGridImpl.h`,
`IntegrateCPU/CUDA`). A03 result: 10 pieces >1,000 triangles vs 10 sherds,
20–80 mm across, 97.2% of faces, rig absent.
Resolution (**measured**): finest voxel clearing the cliff is 0.0022 units =
**0.822 mm** (32,209 blocks); paper default 0.002 = 0.75 mm needs 34,129
blocks, 4% past the cliff. Floor below that is depth sampling ~0.21 mm/px
(**measured**), so ~4× headroom exists but is unreached on this call.
Holes/seams: TSDF leaves the 131 occlusion holes open — honest gaps
(**measured**). No tiling, no seams.
Disqualifier: none on rig removal — this is the reference. Its limit is
resolution (0.822 mm vs ~0.21 mm break surface), not inclusion.

## 2. Same fusion + `extract_point_cloud` — higher ceiling, mesh step unmeasured

Rig removal: identical to route 1 (same `:133-135`, upstream of either
extraction call) — inherits the working removal untouched (**inferred** from
code order; the call swap itself is unrun).
Ceiling (**inferred** from the fetched v0.19.0 source above):
`ExtractPointCloudCPU/CUDA` allocates no per-block scratch, only outputs
sized by `valid_size`; its only 32-bit exposure is
`index_t n = n_blocks * resolution3`, overflowing at ~**524,288 blocks, 16×
the mesh cliff**. A 0.37 mm whole-tray cloud (~136k blocks) extracts in one
call, no tiling.
Holes: the cloud itself invents nothing — but it is points, not a mesh.
Meshing it with screened Poisson makes the output **watertight by design**
(**web-reported**, author abstract: "Poisson surface reconstruction creates
watertight surfaces from oriented point sets",
`https://hhoppe.com/proj/screenedpoisson/`; code
`https://www.cs.jhu.edu/~misha/Code/PoissonRecon/`), i.e. spans the 131
occlusion holes with sherd nobody photographed. The reference kit's answer
is density trimming (`SurfaceTrimmer`, "removing parts … generated in
low-sampling-density regions" — **web-reported**, same page), unmeasured
here and eye-checked at trim-resolving scale or not at all.
Per-sherd clustering before Poisson is safe (**measured** on A03 fused
points with connectivity discarded: eps 1.5–8 mm all give 10/10 sherds, no
splits, no merges).
Disqualifier: a trim check showing invented surface that cannot be separated
from sherd — on conservation material worse than a hole.

## 3. Per-sherd tiled `VoxelBlockGrid` extraction — seam-free to ~0.45 mm

Rig removal: same as route 1 (identical lines). Mechanism for the cliff:
`compute_unique_block_coordinates()` returns the (3, M) blocks a depth map
would touch *without* activating them; `integrate()` accepts an explicit
block-coordinate list (**web-reported**,
`https://www.open3d.org/docs/release/python_api/open3d.t.geometry.VoxelBlockGrid.html`).
Filter per view to one sherd's block set, integrate only those; the 32,768
cliff counts blocks per *extraction call*
(`mesh_structure = Zeros({n_blocks,16,16,16,4}, Int32)` in the fetched
`VoxelBlockGridImpl.h`), so one grid per sherd clears it.
Resolution (**inferred** arithmetic from measured 32,209 blocks at 0.822 mm,
band held at fixed physical width): 0.60 mm → ~9,100 blocks/sherd; 0.45 mm
→ ~19,700/sherd (fits); 0.37 mm → ~35,000/sherd (needs sub-tiles + halo).
Holes/seams: holes stay honest (same TSDF math); seams none *in principle* —
sherds share no zero-crossings, one tile per sherd cuts no surface
(**inferred** from tray geometry, unrun).
Disqualifier: cross-view depth disagreement ≥ voxel (one short GPU job:
render depth from a handful of views, project to a common frame, measure in
mm). If the band is noisier than the voxel, a finer grid fuses noise.

## 4. `mesh_extract_regular_tsdf.py` + `ScalableTSDFVolume` — live masks, no cliff, unmeasured

Rig removal (**inferred** from code, unrun on sherds):
`milo/utils/regular_tsdf_utils.py:167-168` zeroes depth where
`gt_mask < 0.5` when `mask_backgrond=True` (the default), inside
`GaussianExtractor.extract_mesh_bounded()` (`:140-180`), which fuses into
`o3d.pipelines.integration.ScalableTSDFVolume` (`:156-160`). This is the
legacy CPU volume (**web-reported**,
`https://www.open3d.org/docs/release/python_api/open3d.pipelines.integration.ScalableTSDFVolume.html`):
subdivided sub-volumes, no pre-reserved block grid, no `{n,16³,4}` scratch
tensor — the cliff does not exist on this path. Cleanup is built in:
`post_process_mesh()` keeps the largest `--num_cluster` components
(`:28-49`, default 50) — the small-component filter route 7 wants, already
wired.
Resolution (**inferred**, needs one log line to settle):
`voxel_size = depth_trunc / mesh_res`
(`mesh_extract_regular_tsdf.py:67`), `depth_trunc = radius ×
radius_factor` (`:66`, default 2.0) with radius estimated from the camera
ring (`regular_tsdf_utils.py:126-136`). If radius ≈ 1.4 m as on A03,
mesh_res 1024 gives ≈ 2.7 mm voxels — *coarser* than route 1 — and reaching
0.22 mm needs mesh_res ≈ 13,000 on a CPU volume. That arithmetic is
unverified here; the radius print (`:134-136`) decides it in one run.
Holes: TSDF, honest gaps expected (**inferred**); carving (empty space from
camera to surface) is part of this integrator's design (**web-reported**,
Zhou & Koltun 2013, same docs page) and favours outlier rejection.
Disqualifier: the radius/voxel print shows ≥ route-1 voxel at affordable
mesh_res, or the run's renders show band-scale edge rounding worse than
route 1 at equal voxel (same TSDF math, no reason to expect better).

## 5. `mesh_extract_sdf.py --init learnable` (the default) — no mask hook

Rig removal: none exists. The default `--init learnable` refines SDF values
learned in training over Delaunay pivots drawn from *all* Gaussians
(`mesh_extract_sdf.py:82-120`); there is no `masks` argument anywhere on
this path, and the colour pass also takes `masks=None` (`:522-526`). Gaussians
trained on unmasked views model the rig, pivots cover the rig, the tet mesh
covers the rig (**inferred** from code structure; unrun — no learnable
extraction has been run on any A03 output here).
Resolution: adaptive tet-meshing at Gaussian scale — no voxel, no cliff
(**web-reported** design, arXiv abstract above). Edge behaviour rests on the
`filter_large_edges` / `collapse_large_edges` flags plus `remove_oof_vertices`
(`:479-518`); what they do to 0.21 mm fracture relief on clay is unmeasured.
Disqualifier: run it on the existing `A03_nomask` Gaussians — if the clamp
rig survives (expected), this route needs masked retraining before anything
else about it matters. Note `identify_out_of_field_points` only removes
never-frustumed vertices; the rig is *in* every frustum, so
`--remove_oof_vertices` is not a rig remedy on turntable material.

## 6. Pivot-SDF paths with dead masks — `mesh_extract_sdf.py --init
integration|depth_fusion`, `mesh_extract_integration.py` both modes

Dead masks confirmed upstream, not a fork regression (**web-reported**,
`https://raw.githubusercontent.com/Anttwo/MILo/master/milo/mesh_extract_sdf.py`:
`masks=None` hard-coded at the same four sites, local `:151, :166, :316,
:525`; `mesh_extract_integration.py:74, :81, :116, :131` sets `mask = None`
and threads it through). Live-mask inventory, local files:
`regularization/sdf/integration.py:54-59` consumes `rendered_mask ×
view.gt_mask × masks[cam_id]` — the only live consumer — with rule
*inside a mask in ≥1 view*; `:94` labels never-seen points −100 (deeply
solid). `regularization/sdf/depth_fusion.py` takes `masks` at
`:403, :468, :507, :570, :642`, documents it, never reads it.
Measured consequence: `--init integration` kept the whole clamp rig as one
500 mm object (any-view rule passes the rig trivially; `-100` fills the rest).
Inferred hazard for a depth-zeroing patch: `AdaptiveTSDF` starts unobserved
points at `initial_sdf_value=-1.0` (`depth_fusion.py:224, :256`) / `-1.1`
(`:601`), and `convert_occupancy_to_sdf` maps occupancy < 0.5 to negative
SDF (`learnable.py:238-241`, local) — negative = behind surface = inside.
Masked-out points become never-observed points, i.e. plausibly *solid*: the
same sign convention that kept the rig. GOF rasterizer (`--rasterizer gof`,
local `:556` / `mesh_extract_integration.py:212`) changes opacity precision,
not the mask flow — inherits all of this.
Disqualifier: a rendered mask-patch test that keeps rig-like solid (sign
convention confirmed adversarial) — do not build on these paths before that
test.

## 7. Cull replacement — component filter for the DTU mesh (measured design, unwritten)

The all-views silhouette cull (`eval/dtu/evaluate_dtu_mesh.py:89-140`,
`(sampled_masks > 0.).all(dim=-1)`, 6-px dilation `:129`) deletes all 91,463
A03 vertices while each view alone accepts median 82% (**measured**;
reprojected with `scripts/cull_diag.py`). Likely cause: clamp rods occlude
sherd in some views, each view vetoes different ~18% — fits the evidence,
unconfirmed (contiguity test never run). Its *ranking* is sound (rejected
vertices are the streaks/spikes), so replace, don't tune: keep connected
components above a face count — drops all 589 specks, keeps all 10 sherds
(**measured** design; `regular_tsdf_utils.py:28-49` already implements this
shape for route 4). Disqualifier: none — cheapest change on the only working
route; but it cleans specks, it does not refine break surface.

## Ranking — worth-doing-for-this-material

Break surface needs ~0.21 mm; honest holes outrank invented surface.

1. **Route 1 + route 7 (DTU fusion as-run + component filter).** Only
   measured working rig removal with honest holes. Coarse (0.822 mm) but
   honest; unblocks everything downstream today.
2. **Route 3 (per-sherd tiling to ~0.45 mm).** Same rig removal and honest
   holes, seam-free by tray geometry. Build iff the depth-disagreement job
   says the band is quieter than the voxel.
3. **Route 4 (regular TSDF with live masks).** One run settles it: radius
   print → real voxel, renders → edge rounding. Promising only if its voxel
   at affordable mesh_res beats route 1; same TSDF smoothing either way.
4. **Route 2 without Poisson (point cloud as instrument).** Honest dense
   points under a high ceiling; useful for measurement, not a conservation
   mesh. With Poisson: disqualified unless the trim check separates invented
   from photographed surface.
5. **Routes 5–6 (native tet/SDF family, either rasterizer).** Blocked on
   masks (dead upstream, adversarial sign default). Revisit only after a
   mask patch *plus* a render proving unobserved space extracts as empty.

Open checks, in gate order: (a) cross-view depth disagreement in mm (decides
routes 2–3); (b) route 4 single-sherd run with radius/voxel log + tight-crop
renders at fracture-resolving scale; (c) route 6 mask-patch render test
(solid-vs-empty); (d) route 2 trim separation proof. First failing
measurement stops its route.
