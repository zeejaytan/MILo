# Best mesh-extraction route for Rabati sherds — source-checked (2026-09-04)

Broader question: which extraction route best preserves break-surface geometry at the
~0.21 mm the photographs support, with clamp-rig removal? Prior version of this note
scoped only two cheap routes; this revision ranks all primary-source-backed candidates.
Code citations are `file:line` in `C:\PR\MILo` unless prefixed (`o3d:` = Open3D v0.19.0,
`pp:` = `C:\PR\pottery-photogrammetry`, `vdb:` = VDBFusion). Measured = observed on our
material; inferred = follows from source but unrun here.

Shared ground (measured, `docs/notes/A03_DTU_EXTRACTION_RESULT.md` + `MILo/AGENTS.md`):
A03 at voxel 0.002 units needs 34,129 blocks vs the 32,768 cliff (4% past); depth maps
sample the sherd at ~0.21 mm/px; 131 occlusion holes; 10 sherds/tray; SAM 3 sherd-only
`erode0` masks keep 2.28% of frame (16 cm² non-sherd vs 627 cm²). M1 gate order stands:
depth-disagreement measurement first, OpenMVS comparison second, new code last.

## 1. `extract_point_cloud` + screened Poisson (shortened, confirmed earlier)

Rig: inherited — mask zeroes depth at `milo/eval/dtu/mesh_extract_dtu.py:133-135`
before `vbg.integrate()` (`:282-290`); `depth <= 0` never fuses (`o3d:
VoxelBlockGridImpl.h`, `IntegrateCPU/CUDA`). Ceiling 524,288 blocks (no per-block
scratch; only `index_t n = n_blocks*resolution3`). Limit: Poisson (Kazhdan & Hoppe 2013)
outputs watertight surface, so 131 occlusion holes become invented sherd — needs
density trim + eye check, unmeasured. Per-sherd clustering pre-Poissson verified
(1.5–8 mm eps → 10/10 sherds). Disqualifier: trim check shows invented surface that
can't be separated from sherd.

## 2. MILo's own `mesh_extract_sdf.py` (shortened, confirmed earlier)

Rig: no working path — `masks` dead in `milo/regularization/sdf/depth_fusion.py`
(signatures `:403,:468,:507,:570,:642`, zero reads), `masks=None` hard-coded
(`mesh_extract_sdf.py:151,166,316,525`); only live mask rule is
`integration.py:54-59,:94` (any-view, never-seen = −100 solid) already measured to keep
the rig. Inferred (unmeasured): `AdaptiveTSDF` unobserved = `initial_sdf_value=-1.0` =
solid (`depth_fusion.py:224,256,353`; negative = behind surface = inside), consistent
with `convert_occupancy_to_sdf` (`learnable.py:238-241`) — so porting depth-zeroing is
necessary but plausibly insufficient. Upstream offers `--rasterizer {radegs,gof}`
(`mesh_extract_sdf.py:556`); GOF = Gaussian Opacity Fields tet-meshing, still no voxel
grid but same dead-mask problem. Disqualifier: rendered mask-patch test keeps rig-like
solid (sign convention confirmed adversarial).

## 3. Per-sherd tiled TSDF + small-component filter

Rig: same inherited masking as route 1 (identical upstream lines). Tiling uses public
API: `vbg.compute_unique_block_coordinates(...)` per view, intersect with per-sherd
block set, then `vbg.integrate(filtered_coords, ...)` (`o3d: VoxelBlockGrid.cpp`,
`Integrate(block_coords,...)` activates only listed blocks) — one grid per sherd (or
one grid, one extraction call per block subset, since the 32,768 cliff is per
*extraction call*, `mesh_structure = Zeros({n_blocks,16,16,16,4},Int32)`).
Seams: none in principle — sherds are physically separate, share no zero-crossings, so
per-sherd grids never cut a surface (inferred from geometry; the A03 note's "seam-free"
claim). Holes: TSDF leaves occlusion holes open (good — honest gaps, unlike Poisson).
Cull: replace `evaluate_dtu_mesh.py:89-140` all-views silhouette rule (measured: deletes
entire A03 mesh, best vertex passes 139/143) with keep-components-above-area rule
(measured design: drops 589 specks, keeps 10 sherds). Resolution arithmetic (A03,
373.7 mm/unit): voxel 0.002 → 0.75 mm; halving voxel ×4 blocks: full tray at 0.37 mm ≈
136k blocks, but per-sherd ≈ 13.6k each — every tile clears 32,768 with margin; 0.22 mm
rung ≈ 130k/sherd ÷ 10 ≈ ditto per tile. So tiling reaches ~0.37–0.45 mm seam-free
today. Disqualifier: cross-view depth disagreement ≥ voxel (then finer grid fuses noise).

## 4. COLMAP → OpenMVS at pixel level (the baseline — currently winning)

Rig: removed by masks before densification (`pp: pipeline/config/pipeline_config.yaml`
mask/dense stages; SAM 3 sherd-only set reused). Measured on A02 (same tree, shared
frame, `MILo/docs/notes/A02_MESH_METHOD_COMPARISON.md`): OpenMVS-refined flat-surface
noise **0.186 mm** vs MILo 0.485 mm, debris 0 vs 17/sherd, interior holes 0 vs 10 mm —
wins by factors, not percents. Resolution: photometric refinement moves vertices to
minimise reprojection error at full image resolution (no voxel quantisation at all);
vertices 0.461 mm apart with 0.186 mm noise floor. Knobs that matter
(`pp: pipeline_config.yaml:94-102`, OpenMVS defaults): `refine.regularity_weight`
(default 0.2, lower trusts photos more) dominates, `reconstruct.smooth` (default 2)
secondary — but measured 2×2 on SH5 (job 29892523): coherent edge runs >10 mm stayed
**0 mm in all four cells**; loosening both gave 14× more steep fold as wall speckle,
not break line. Conclusion recorded in `pp: AGENTS.md`: limit is what SH5's photos
contain, not smoothing — needs re-photography, not parameters. Disqualifier (already
nearly tested): per-sherd edge audit shows break faces systematically missing
(current status: 1/7 sherds smooth; median 141 mm healthy).

## 5. VDBFusion / OpenVDB backend as Open3D drop-in

Primary source: VDBFusion README + Vizzo et al., "VDBFusion: Flexible and Efficient TSDF
Integration" (Sensors 2022): `VDBVolume(voxel_size, sdf_trunc, space_carving)`,
`integrate(scan, origin)` over **point clouds + sensor origins** (not depth images),
`extract_triangle_mesh()` adapted from Open3D's marching cubes onto the VDB tree —
sparse by construction, no pre-reserved block grid, and the `{n_blocks,16³,4}` scratch
tensor that overflows does not exist on this path (inferred from VDB traversal design;
not run here). Rig: mask handling is manual — drop masked pixels when unprojecting
rendered depth to scans before `integrate()`; `space_carving=true` then clears
never-observed space (opposite default to `AdaptiveTSDF`'s solid-initial, favourable
here). Cost: new dependency + glue code (depth→scan unprojection per view, per-sherd
split for the component filter); buys freedom from *both* the cliff and the
reservation arithmetic, at the same TSDF smoothing limit (~band-scale edge rounding).
Disqualifier: prototype fusion shows thicker edge rounding than route 3 at equal voxel
(no reason to pay integration cost for identical math).

## 6. Other sharp-edge routes (2DGS, direct tet-meshing)

- **2DGS** (Huang et al. 2024, surfel-aligned Gaussians): collapse of each Gaussian onto
  its tangent plane gives crisper depth discontinuities in principle. Against: not in
  MILo upstream (`mesh_extract_sdf.py:556` offers only radegs/gof), so it is a new
  training pipeline + new extraction path, unmeasured on any sherd here. Worth-doing in
  general; not for this material now.
- **GOF direct tet-meshing at Gaussian scale** (already in-repo, route 2's `--rasterizer
  gof`): avoids voxel quantisation, but inherits route 2's dead masks and the A02
  measurement (MILo-family noise 0.485 mm). Disqualifier shared with route 2.
- **COLMAP Delaunay / Poisson at depth 11** (measured A02): Delaunay totals 26
  perimeters of fold (faceting, not sharpness); Poisson prints its octree grid on walls
  and balloons 113 mm into the turntable. Both disqualified by measurement already.

## Ranking — worth-doing-for-this-material

1. **Route 4 (OpenMVS as-is).** Measured best on every surface figure; no work needed
   beyond the per-sherd edge audit already flagged. The M1 gate says stop here if the
   audit passes.
2. **Route 3 (per-sherd tiled TSDF).** Only route that provably clears the cliff with
   honest holes and working rig removal; reaches ~0.4 mm. Build iff OpenMVS audit fails
   AND depth-disagreement measurement says the band is quiet.
3. **Route 1 (point cloud + Poisson).** Cheapest code, but watertight prior is the most
   dangerous failure on conservation material. Only if holes can be masked-out downstream.
4. **Route 5 (VDBFusion).** Sound library, wrong amount of machinery while route 3 fits
   in Open3D's public API.
5. **Routes 2/6 (MILo-family / 2DGS).** Blocked (masks) or unowned (new pipeline); revisit
   only if Gaussian rendering is shown to beat 0.186 mm depth first.

## Open checks (unchanged carriers)

Cross-view depth disagreement in mm (one GPU job); OpenMVS per-sherd edge audit;
Route 3 tile prototype on one sherd; Route 1 trim separation proof. First failing
measurement stops its route — that is what each "disqualifier" above is for.

---

# v2 — web verification appendix (2026-09-04, background research)

`websearch` was unavailable in this session, so every item below was verified by
`webfetch` straight against the primary source (official docs, repo at tag/branch,
author-hosted paper page). Status words: **measured** = observed on our material;
**inferred** = follows from a verified source but unrun here; **web-reported** =
what the source states, not yet tied to our material.

## W1. Open3D VoxelBlockGrid cliff — confirmed upstream, still open

- **isl-org/Open3D#4824** (open, unassigned, labels `question`+`reconstruction`,
  opened 2022-03-01, no fix in thread):
  `https://github.com/isl-org/Open3D/issues/4824` — reporter runs
  `VoxelBlockGrid(..., block_count=50000, device=CUDA:0)`, integrates fine, then
  `extract_triangle_mesh()` dies with `illegal memory access` while only 8/16 GiB
  VRAM is used. Web-reported match for our diagnosis (free memory irrelevant).
- **v0.19.0 source** (tag `v0.19.0`, web-reported):
  `https://raw.githubusercontent.com/isl-org/Open3D/v0.19.0/cpp/open3d/t/geometry/kernel/VoxelBlockGridImpl.h`
  — `using index_t = int;` (32-bit); `ExtractTriangleMeshCPU/CUDA` allocates the
  `mesh_structure` scratch as `{n_blocks,16,16,16,4}` Int32 in a `try/catch`
  whose failure message is the "consider using a larger voxel size" text; past
  32,768 blocks the byte count wraps and no message is produced. The same file's
  `IntegrateCPU/CUDA` returns early on `depth <= 0`, i.e. masked-out depth never
  fuses (web-reported backing for the route 1/3 rig claim).
- **Public tiling API** (web-reported, 0.19.0 docs):
  `https://www.open3d.org/docs/release/python_api/open3d.t.geometry.VoxelBlockGrid.html`
  and tutorial `.../tutorial/t_reconstruction_system/voxel_block_grid.html` —
  `integrate()` accepts an explicit block-coordinate list, which is the API route 3
  relies on. No upstream chunked-`extract_triangle_mesh` found in the v0.19.0 docs.
- **Legacy CPU path, unverified pointer:** `open3d.pipelines.integration`
  still ships `ScalableTSDFVolume` in 0.19.0 (seen in the API index above). Whether
  its per-subvolume extraction avoids the single int32 scratch allocation needs a
  source read (`cpp/open3d/pipelines/integration/ScalableTSDFVolume.cpp`) — recorded
  here as an unchecked alternative, not a claim.

## W2. Poisson fills holes by design — author sources

- **Kazhdan & Hoppe 2013 abstract** (author-hosted, primary):
  `https://hhoppe.com/proj/screenedpoisson/` — "Poisson surface reconstruction
  creates **watertight** surfaces from oriented point sets." Watertight output is
  the method's stated property, not an implementation accident (web-reported
  backing for route 1's disqualifier).
- **Kazhdan reference implementation, v18.76** (author-hosted, primary):
  `http://www.cs.jhu.edu/~misha/Code/PoissonRecon/Version18.76/` (+ GitHub
  `mkazhdan/PoissonRecon`) — ships a `SurfaceTrimmer` executable documented as
  "Trims off parts of a triangle mesh … **used for removing parts of a
  reconstructed surface that are generated in low-sampling-density regions**."
  So the reference workflow itself expects invented surface where samples are
  sparse, and answers it with density-based trimming — the exact mitigation route 1
  needs, still unmeasured here. SuGaR inherits this: see W3.

## W3. Gaussian-splatting meshers beyond MILo — code availability + hole behavior

- **2DGS (Huang et al., SIGGRAPH 2024)**: official repo `hbb1/2d-gaussian-splatting`
  (`https://github.com/hbb1/2d-gaussian-splatting`, paper `arXiv:2403.17888`,
  project `https://surfsplatting.github.io/`). Mesh extraction is **Open3D TSDF
  fusion** (`render.py --voxel_size --depth_trunc --depth_ratio`; unbounded mode
  via space contraction + adaptive truncation). Two caveats from their README/FAQ:
  (a) masks ride in the **alpha channel** of the DTU inputs
  (`scene/cameras.py`), i.e. mask support exists but is a training-data
  convention, not a fusion flag; (b) the rasterizer assumes an **ideal pinhole**
  camera — off-centre principal points break convergence (favourable here: ours
  is exactly centred, measured). Verdict for this material: same TSDF smoothing
  and same Open3D cliff as routes 1/3, plus a whole new training pipeline —
  correctly ranked below route 3. No sharp-edge preservation claim found in the
  repo docs; "crisper discontinuities" stays an inference, not a source claim.
- **GOF / Gaussian Opacity Fields (Yu et al., SIGGRAPH Asia 2024 journal)**:
  official repo `autonomousvision/gaussian-opacity-fields`
  (`https://github.com/autonomousvision/gaussian-opacity-fields`, paper
  `arXiv:2404.10772`). Extracts the mesh **directly from the Gaussians** via an
  opacity level set + **marching tetrahedra** (`extract_mesh.py`; also ships
  `extract_mesh_tsdf.py`) — adaptive/compact, no voxel grid, so no 32-bit block
  cliff by construction (inferred from the tet-meshing design). Cost, from their
  README install section: tetra-triangulation needs a CGAL/GMP source build. Mask
  handling: same 3DGS data convention as 2DGS (no fusion-time mask flag found) —
  inherits route 2's dead-mask problem on rig material. Already in-repo as MILo's
  `--rasterizer gof`; ranking unchanged.
- **SuGaR (Guédon & Lepetit, CVPR 2024)**: official repo `Anttwo/SuGaR`
  (`https://github.com/Anttwo/SuGaR`, paper `arXiv:2311.12775`). Pipeline:
  7k-iter vanilla 3DGS → surface-alignment regularisation → sample surface points
  → mesh via **Poisson reconstruction** ("fast, scalable, and preserves details,
  in contrast to … Marching Cubes" — README abstract). Because the final step is
  Poisson, SuGaR inherits route 1's watertight disqualifier on the 131 occlusion
  holes (inferred from their stated pipeline). No mask convention found in the
  fetched README.
- **Not verified this session:** RaDe-GS and 3DGSR were not fetched (no primary
  citation to offer). No claim is made about them; they stay below 2DGS/GOF/SuGaR
  in evidence order until read from source.

## W4. OpenMVS knobs from upstream source (develop branch, 2026-09-04)

Fetched raw (web-reported; confirm against the pinned build before acting —
the fetched `develop` text differs in places from older remembered defaults):

- `apps/RefineMesh/RefineMesh.cpp`
  (`https://raw.githubusercontent.com/cdcseacave/openMVS/develop/apps/RefineMesh/RefineMesh.cpp`):
  `regularity-weight` **0.2**, `rigidity-elasticity-ratio` **0.9**,
  `gradient-step` **45.05**, `scales` **2**, `scale-step` **0.5**,
  `max-face-area` **16**, `ensure-edge-size` **1**, `resolution-level` **0**,
  `min-resolution` **640**, `max-views` **8**, `alternate-pair` **0**,
  `planar-vertex-ratio` **0** (disabled), `reduce-memory` **1** — and
  **`close-holes` 30**: refinement closes every hole spanned by ≤30 boundary
  edges unless disabled.
- `apps/ReconstructMesh/ReconstructMesh.cpp`
  (`https://raw.githubusercontent.com/cdcseacave/openMVS/develop/apps/ReconstructMesh/ReconstructMesh.cpp`):
  `Clean` options `close-holes` **30**, `remove-spurious` **20**,
  `remove-spikes` **true**, `decimate` **1** (= disabled); reconstruction
  `min-point-distance` **1.5**, `thickness-factor`/`quality-factor` **1**,
  `free-space-support` **false**. **Flag:** the fetched source states
  `smooth` default **10** (Taubin band-pass, "wants tens of [iterations], not the
  two a plain Laplacian needed") — against this note's §4 "`reconstruct.smooth`
  (default 2)". The §4 value cites `pp: pipeline_config.yaml:94-102`, i.e. the
  pipeline's own config, so there is no contradiction yet — but whichever value
  the pinned OpenMVS build actually compiles must be read from that build before
  the SH5-style parameter argument is reused.
- **Actionable for "honest holes": both OpenMVS stages close small holes by
  default** (`close-holes 30` in ReconstructMesh *and* RefineMesh). If occlusion
  holes must stay open as gaps, the pipeline config must set both to 0 and the
  edge audit re-run — otherwise the audit scores the closer, not the data.
  (Whether `pp` already does this is a config read, not done here.)
- **COLMAP author guidance** (primary, `colmap/colmap` `main`,
  `doc/tutorial.rst`):
  `https://raw.githubusercontent.com/colmap/colmap/main/doc/tutorial.rst` —
  capture guidelines: good texture, **similar illumination, "avoid specularities
  on shiny surfaces"**, high overlap (every object in ≥3 images), moved-camera
  viewpoints; dense chain undistort → `patch_match_stereo` → `stereo_fusion` →
  Poisson *or* Delaunay meshing (`poisson_mesher` / `delaunay_mesher`). Directly
  relevant: the clamp rig is chrome/steel (specular → violates the guideline) and
  the turntable violates the moved-camera assumption wherever the background is
  unmasked — both are why the SAM sherd-only masks exist, not new work.

## W5. VDBFusion as Open3D replacement — verified API, same smoothing

- Repo `PRBonn/vdbfusion` (`https://github.com/PRBonn/vdbfusion`, MIT):
  `VDBVolume(voxel_size, sdf_trunc, space_carving)` +
  `integrate(scan, origin)` over **point clouds and sensor origins** (not depth
  images) + `extract_triangle_mesh()`; credits Open3D and OpenVDB implementations.
- Paper: Vizzo et al., "VDBFusion: Flexible and Efficient TSDF Integration of
  Range Sensor Data", *Sensors* 2022, 22(3):1296, `doi:10.3390/s22031296`
  (`https://www.mdpi.com/1424-8220/22/3/1296`).
- Consequences (inferred): no pre-reserved block grid, so the `{n,16³,4}` scratch
  tensor that overflows does not exist on this path — but the input convention
  forces a depth→scan unprojection glue layer per view, and the fused field is
  the same TSDF math with the same band-scale edge rounding. Ranking unchanged:
  machinery without a resolution payoff while route 3 fits the public API.

## W6. Turntable / clamp-occlusion practice — gap recorded, not filled

No museum digitisation spec or turntable guide was fetched to a primary source
this session (web search was down; no URL is cited rather than a guessed one).
What the fetched primaries do establish: COLMAP's pipeline assumes a static
scene with a moving camera (tutorial.rst above), so a fixed-camera turntable
with visible rig/background needs masking before densification — which is
exactly what `pp`'s SAM sherd-only masks already do (measured). The remaining
occlusion problem (clamp jaws hide the sherd; 131 holes) is a **capture** deficit
— re-photography with flipped/rested sherds — not a parameter deficit; no web
source is needed for that and none is claimed.

## Web-session ranking deltas (v1 order stands, reasons strengthened)

1. **Route 4 (OpenMVS) — still first**, with one new condition: verify both
   `close-holes` settings are 0 in the pinned config before trusting the edge
   audit's holes, else the audit scores the hole-closer (W4).
2. **Route 3 (tiled TSDF) — still second.** W1 confirms no upstream fix exists
   (#4824 open since 2022), so tiling is the supported path, not a workaround.
3. **Route 1 (Poisson) — still third.** W2 upgrades the disqualifier from
   inference to author-stated property (watertight by design) with the
   author-shipped remedy (SurfaceTrimmer-style density trim, unmeasured here).
4. **Route 5 (VDBFusion) — still fourth.** API verified (W5); cost/benefit unchanged.
5. **Routes 2/6 (MILo-family incl. GOF rasterizer / 2DGS / SuGaR) — still last.**
   2DGS = same TSDF+Open3D limits via a new pipeline; SuGaR = Poisson at the end
   (same hole problem); GOF tet-meshing dodges the cliff but keeps the dead masks.
   2DGS's pinhole-only caveat is satisfied by our centred principal point, so it
   is the least-blocked Gaussian route *if* one is ever needed — still behind
   routes 4 and 3 on evidence.
