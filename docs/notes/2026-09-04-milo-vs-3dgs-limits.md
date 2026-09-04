# Is the 0.21 mm fracture edge unreachable a MILo limit or a 3DGS limit? — source-checked (2026-09-04)

Scope: answer one question — Method 1 (DTU masked fusion, 0.822 mm voxel) is out as too
coarse, and no route has been found to extract sherds at pixel-level refinement with sharp
~0.21 mm fracture edges, honest holes and rig removal. Is that MILo's fault or 3D Gaussian
Splatting's? No OpenMVS build work, no code edits, no Slurm/Spartan this session.

Shared ground (**measured** on A03/A02): 373.7 mm/unit; finest voxel clearing the Open3D
cliff 0.0022 units = **0.822 mm** (32,209 blocks vs 32,768 cliff; paper default 0.002 =
0.747 mm needs 34,129); depth maps sample the sherd at **~0.21 mm/px**; OpenMVS flat-surface
noise **0.186 mm** vs MILo-family **0.485 mm** on A02; 131 occlusion holes, none watertight.
Status words: **measured** = seen on our material; **inferred** = follows from a verified
primary source, unrun here; **web-reported** = what the source states, untied to our material.

## Verdict up front

**Both — at different scales, and they must not be conflated.**

- The **0.822 mm cap, the dead masks, and the mesh-deleting cull are MILo-implementation**
  (benchmark-harness choices, fixable in the fork, costed in prior notes). Fixing all of
  them buys at most ~0.45 mm seam-free, ~0.37 mm with sub-tiles — still ~2× coarser than
  the photographs support.
- The reason **no Gaussian route reaches 0.21 mm fracture edges "like OpenMVS" is
  3DGS-representation**: the surface every Gaussian mesher extracts is a level set of
  overlapping smooth kernels optimised for *photometric* error, and its sharpness floor is
  the Gaussian footprint plus the regularisation that keeps depth quiet — not the voxel or
  tet size. Finer extraction grids sample noise more finely; they do not recover sub-Gaussian
  relief. That last rung needs a different representation (vertex-level photometric
  refinement, which is what OpenMVS already is) or re-photography — not a finer MILo voxel.

Plain reading: **about 0.07 mm of the shortfall is MILo's code, about 0.4–0.6 mm of it is
the representation.** The paper setting (0.747 mm) vs achieved (0.822 mm) is the
implementation gap; the gap from 0.747 mm to 0.21 mm is almost entirely representation.

## What "like OpenMVS" means in mm (contrast only)

OpenMVS `RefineMesh` moves **vertices** to minimise reprojection error at full image
resolution — `resolution-level` default **0**, `min-resolution` 640 (**web-reported**,
`apps/RefineMesh/RefineMesh.cpp`, option defaults block: `regularity-weight` 0.2,
`rigidity-elasticity-ratio` 0.9, `gradient-step` 45.05, `scales` 2, `scale-step` 0.5,
`max-views` 8, `max-face-area` 16, `ensure-edge-size` 1, `close-holes` 30). There is **no
voxel quantisation anywhere on this path** — a vertex can stop halfway between pixels where
the photos tell it to, and `max-face-area 16` subdivides faces projected large in any image
pair so vertex spacing follows image content, not a grid. The smoothing knob is
`regularity-weight` (0.2 trusts photos strongly). That is why the A02 figure is a **noise
floor (0.186 mm)** rather than a grid step: resolution ≈ pixel sampling 0.21 mm/px, floor =
depth noise. (**measured** 0.186 mm A02; mechanism **web-reported** from fetched source.)

Gaussian extraction works the other way round: render depth from smooth kernels, then
isosurface the fused field. Resolution ≈ kernel footprint, floor = cross-view depth
disagreement. The two numbers coincide only if Gaussians are sub-pixel and agree — which is
exactly what the papers below say they are not without regularisation that itself smooths.

## Bottlenecks — MILo-implementation (fixable in fork)

### B1. The 32,768-block cliff — Open3D's int32 scratch, not MILo's math

`extract_triangle_mesh()` allocates `{n_blocks,16,16,16,4}` Int32 scratch
(**web-reported**, `cpp/open3d/t/geometry/kernel/VoxelBlockGridImpl.h` at v0.19.0;
`using index_t = int`), so 32,768 blocks = exactly 2³¹ bytes and the count wraps negative.
Per *extraction call*, device-independent, free memory irrelevant (**measured**: sphere
reproducer 28,176 → ok / 34,184 → core dump; A03 34,129 = 4% past). mm impact: forces
0.0022 units (**0.822 mm**) instead of the paper's 0.002 (**0.747 mm**) — a **0.075 mm**
implementation tax — and blocks the 0.37/0.22 mm rungs without tiling. Escapes exist
(per-sherd tiles via public `integrate(block_coords,…)`, `extract_point_cloud` ceiling
~524,288, `mesh_extract_regular_tsdf.py` CPU volume) — all verified in prior notes.
*Flip measurement:* none needed — already measured. This verdict stands.

### B2. Dead masks on every native MILo path — upstream wiring, not representation

`milo/mesh_extract_sdf.py:151,166,316,525` hard-codes `masks=None` (**verified** local grep,
4 hits); `regularization/sdf/depth_fusion.py` takes `masks` at `:403,:468,:507,:570,:642`,
documents it, never reads it (**verified** local grep); only live consumer is
`regularization/sdf/integration.py:54-59` (any-view rule, `:94` never-seen = −100 solid —
**measured** keeps the whole 500 mm rig). The working rig removal is three lines in the DTU
harness (`milo/eval/dtu/mesh_extract_dtu.py`, upstream: `depth[(gt_mask<0.5)]=0`,
`depth[(mask<0.5)]=0` before `vbg.integrate()` — **web-reported** from fetched upstream
source). mm impact: **zero on sharpness** — inclusion, not resolution. Fixable by porting
the zeroing, *subject to* the sign-convention check (`AdaptiveTSDF` starts unobserved at
`initial_sdf_value=-1.0`, `depth_fusion.py` constructor; negative = inside — **web-reported**
from fetched source — so masked-out points may extract as *solid*).
*Flip measurement:* rendered mask-patch test — port the 3 lines on one sherd, extract, render:
rig gone + empty stays empty → fixable; rig-shaped solid → adversarial, route stays shut.

### B3. The all-views silhouette cull — benchmark rule, wrong for ten sherds in clamps

`evaluate_dtu_mesh.py:cull_mesh` keeps a vertex only inside the dilated outline in **every**
view. **Measured** on A03: deletes all 91,463 vertices while each view alone accepts median
82% (best vertex 139/143) — clamp rods occlude sherd in different views each time
(**inferred** cause, contiguity test never run). Replace with connected-component filter
(589 specks dropped, 10 sherds kept — **measured** design). mm impact: none on edges.
*Flip measurement:* none needed — already measured. Replace, don't tune.

### B4. `mesh_extract_regular_tsdf.py` voxel parameterisation — setting, not ceiling

`voxel_size = depth_trunc / mesh_res` with `depth_trunc = radius × radius_factor`
(**web-reported** prior read; needs one log line to settle the radius ≈ 1.4 m → mesh_res
1024 ≈ 2.7 mm claim). Live masks (`regular_tsdf_utils.py:167-168`, default
`mask_backgrond=True`) + built-in component filter (`:28-49`) make this the cheapest live-mask
native path — but same TSDF smoothing as B1 once voxel is equal.
*Flip measurement:* single-sherd run printing radius/voxel + tight-crop renders: voxel ≤
0.45 mm with honest holes → promote; else stays behind tiling.

## Bottlenecks — 3DGS-representation (new representation or re-photography needed)

### R1. Photometric objective, geometric cheating — depth is noisy because nothing asks it to be quiet

3DGS (Kerbl et al. 2023, arXiv:2308.04079) optimises anisotropic covariance **for
novel-view photometric error**; opacity and view-dependent (spherical-harmonic) colour are
free parameters per Gaussian. MILo's own paper states the consequence plainly: Gaussians
"adjust their opacity and view-dependent colors independently of the geometry… to fit the
training images more precisely, but often at the expense of geometric consistency.
'Cheating' leads to hallucinated structures such as floaters or cavities, which are
particularly hard to resolve during mesh extraction" (§1, **web-reported**,
arXiv:2506.24096v2 HTML). Rendered depth is an alpha-blended expectation over these
kernels — photometrically excellent, geometrically compromised. **Measured** consequence on
our material: MILo-family flat-surface noise 0.485 mm vs OpenMVS 0.186 mm (A02) — the
Gaussian depth is ~2.6× noisier than the vertex-refined surface *before any voxel exists*.
mm impact: the honest resolution floor is the **cross-view depth disagreement**, not the
voxel; every prior note's gate stands. If disagreement is ~0.5 mm, a 0.22 mm voxel fuses
noise at 2× oversampling.
*Flip measurement:* the one GPU job — render depth from a handful of views, project to a
common frame, disagreement in mm. Quiet (< 0.3 mm) → tiling worth building; noisy (≥ voxel)
→ no extraction grid helps, retrain with stronger regularisation (which triggers R2).

### R2. The footprint floor — sub-Gaussian relief cannot survive any isosurface

A Gaussian is a smooth kernel; the extracted surface is a level set of their sum. Detail
smaller than the kernel support is attenuated before any grid or tet sees it, and every
Gaussian mesher then *explicitly* deletes sub-footprint triangles:

- MILo samples 9 Delaunay vertices per Gaussian (centre + 8 axis-aligned corners,
  `pₖ,ᵢ = μₖ + Rₖ(sₖ⊙bᵢ)`, §4.1 eq.1) and filters tet edges with `dmtet_distance <= scale
  sum` (`filter_large_edges`/`collapse_large_edges`, `mesh_extract_sdf.py` refinement loop
  — **web-reported** from fetched upstream source). A 0.21 mm fracture ridge carried by
  mm-scale Gaussians is below the pivot spacing and gets collapsed by design.
- MILo §5.3 erosion loss forces sampled Gaussian *centres* inside the surface
  (`L_erosion = Σ max(0,f_μ)`, §5.3 eq.8) — thin fracture relief near a centre is filled,
  not preserved (**web-reported**). The interior loss (§5.3 eq.9) fills occluded volume the
  same way.
- GOF builds tet vertices from Gaussian bounding boxes at **3× scales**, drops cells
  spanning non-overlapping Gaussians (edge > summed max scales), then marching-tetrahedra
  + 8-iteration binary search (§3.4, **web-reported**, arXiv:2404.10772v2 HTML). The binary
  search locates the level set precisely — but the field being located is still Gaussian-
  wide. Adaptive to Gaussian scale ≠ sharper than Gaussian scale.
- 2DGS collapses kernels to tangent-plane disks with ray-splat intersection for
  view-consistent depth (§4, **web-reported**, arXiv:2403.17888v3 HTML) — crisper
  discontinuities than 3DGS in principle — yet still fuses **rendered depth via Open3D TSDF
  at voxel 0.004 / trunc 0.02** (§6.1). Same band-averaging as B1, plus its own limits
  section: "densification favors texture-rich over geometry-rich areas… regularization…
  can lead to over-smoothing" (§7 Limitations, **web-reported**). Sharper kernels, same
  smoothing end-step.
- SuGaR is explicit about why grids fail on Gaussians at all: millions of tiny Gaussians
  make the density "close to zero almost everywhere, and Marching Cubes fails to extract
  proper level sets even with a fine voxel grid" (Fig.3 caption, §4.2 samples the level set
  from depth maps + **Poisson reconstruction at depth 10**, **web-reported**,
  arXiv:2311.12775v3 HTML). Poisson is watertight by design — it spans our 131 occlusion
  holes with invented sherd.

mm impact: fracture ridges at ~0.21 mm need Gaussians ≤ ~0.1–0.2 mm support to even reach
the isosurface step; nothing in any fetched paper shows Gaussians converging that small on
clay without texture to anchor them, and the regularisers that keep depth quiet (R1) push
the other way. This is the core representation verdict: **voxel/tet size is the sampling of
an already-smoothed field**.
*Flip measurement:* Gaussian-scale histogram on the trained A03 scene (mean/minimum scale
in mm near break faces) + the depth-disagreement job from R1. Median support ≫ 0.2 mm with
quiet depth → floor proven above the requirement; support ≤ 0.2 mm with quiet depth → the
verdict flips and tiling is back on.

### R3. Band averaging across views rounds every edge — even with a perfect grid

TSDF fuses disagreeing per-view depths into a weighted mean inside
`trunc_voxel_multiplier × voxel` (±6.0 mm at defaults on A03 — **measured** arithmetic).
A sharp fracture corner photographed from 143 angles becomes 143 slightly different depths;
the zero-crossing sits at their average, rounded over the band. GOF's min-over-views opacity
(eq.10, §3.2 — "shares similarities to the visual hull / space carving") mitigates this by
construction, but trades it for silhouette-style filling of concavities — break-face hollows
narrower than the view cone get carved away rather than rounded. Either way the edge loses
at band/Gaussian scale, never at voxel scale.
*Flip measurement:* same depth-disagreement job — disagreement ≪ voxel → band harmless;
disagreement ≥ voxel → rounding dominates and finer voxels only resolve the rounding.

### R4. Chrome rig + turntable is a capture deficit no representation fixes

COLMAP's pipeline assumes a static scene with a moving camera; fixed-camera turntable with
visible rig needs masking before densification (standard guidance, prior note W4). Worse,
the rig is chrome/steel: specular, so Gaussian depth for it moves with viewpoint and shells
never reinforce (290,640 blocks / ~41.6 m² fused vs ~0.1 m² of sherd — **measured** A03).
GOF's limitations section names the mechanism generally: "spherical harmonics for
view-dependent appearance… potentially inaccurately representing reflections as geometric
features" (§5 Limitations, **web-reported**). Masking removes the rig from the grid (B2);
it cannot remove the reflection baked into nearby sherd Gaussians, nor photograph the clay
under the clamp jaws (131 holes — **measured**, occlusion not masking).
*Flip measurement:* none available post-hoc — needs re-photography (flipped/rested sherds,
cross-polarised or matte rig). Until then, honest holes outrank invented surface.

## Per-bottleneck table (A03 mm, 373.7 mm/unit)

| # | Bottleneck | MILo or 3DGS? | mm impact on A03 | What flips it |
|---|---|---|---|---|
| B1 | 32,768-block cliff | MILo toolchain (Open3D impl) | 0.747 → 0.822 forced (+0.075); ladder locked | already measured; tiling design exists |
| B2 | Dead masks / `masks=None` ×4 | MILo wiring (upstream) | 0 on sharpness (inclusion only) | mask-patch render test (empty stays empty) |
| B3 | All-views cull deletes mesh | MILo harness rule | 0 on sharpness | already measured; component filter |
| B4 | regular_tsdf voxel parameterisation | MILo setting | unknown until radius print (suspect coarser) | one run: radius/voxel log + tight crops |
| R1 | Opacity/SH cheating → depth noise 0.485 vs 0.186 | 3DGS representation | floor ≈ disagreement, not voxel | depth-disagreement job (mm) |
| R2 | Footprint + tet-collapse + erosion fill | 3DGS representation | sub-~0.5 mm relief attenuated pre-grid | Gaussian-scale histogram + R1 job |
| R3 | Band/view averaging rounds edges | 3DGS + TSDF math | rounding ≈ band scale (±6 mm phys.) | R1 job: disagreement ≪ voxel? |
| R4 | Specular rig, jaw occlusions | Capture, via representation | 131 holes; reflection baked near edges | re-photography only |

## Bottom line for M1 (M1-resolution-the-material-needs.md)

Method 1 is out at 0.822 mm (**measured**, conservator's verdict 2026-09-01 stands). The
research question here was whether anything in the Gaussian family recovers the ~0.21 mm
break face honestly. Against the pinned primaries: **no** — 2DGS sharpens kernels but keeps
TSDF fusion and over-smooths (§6.1, §7); GOF dodges voxels but resolves at Gaussian/tet
scale with view-dependent-reflection caveats (§3.4, §5); SuGaR ends in watertight Poisson
(§4.2, §5.1); MILo's native path adds learnable SDF decoupling (§4.2) and anti-erosion fill
(§5.3) that work *against* thin relief. The single cheapest evidence remains the ordered
gate: **(1) depth-disagreement in mm, (2) OpenMVS on A03 on the same ruler, (3) code last.**
If (1) is noisy or (2) already passes, no fork work in B1–B4 changes the answer.

## Primary sources fetched (pinned, this session)

- MILo paper v2: `https://arxiv.org/html/2506.24096v2` (§1 cheating/floaters; §4.1 eq.1
  pivots; §4.2 decoupled SDF; §5.1–5.3 losses incl. eq.8 erosion, eq.9 interior; §6.7
  limitations; related-work TSDF/Poisson survey). Abstract page `https://arxiv.org/abs/2506.24096`.
- MILo upstream master: `https://github.com/Anttwo/MILo` README §3 (three extraction paths;
  §3.3 regular-grid TSDF "does not scale to unbounded real scenes"); raw
  `milo/eval/dtu/mesh_extract_dtu.py` (masked depth zeroing before `vbg.integrate`,
  voxel 0.002, block_count 50000); raw `milo/mesh_extract_sdf.py` (`masks=None` ×4,
  tet edge filter, `remove_oof_vertices` only removes never-frustumed); raw
  `milo/regularization/sdf/integration.py` (live any-view mask + `:94` −100 solid); raw
  `milo/regularization/sdf/depth_fusion.py` (`masks` threaded never read,
  `AdaptiveTSDF initial_sdf_value=-1.0/-1.1`).
- 3DGS: `https://arxiv.org/abs/2308.04079` (Kerbl et al. 2023; photometric anisotropic
  objective, no surface term).
- 2DGS: `https://arxiv.org/html/2403.17888v3` (§3 multi-view inconsistency of 3DGS; §4
  disks + ray-splat intersection; §5 depth-distortion + normal-consistency; §6.1 TSDF
  voxel 0.004/trunc 0.02; §7 Limitations: texture-biased densification, over-smoothing).
- GOF: `https://arxiv.org/html/2404.10772v2` (§1 TSDF "struggles with thin structures";
  §3.2 min-over-views opacity eq.10; §3.3 normal-as-intersection-plane + SH limitation
  foreshadow; §3.4 3σ tet grid + binary search; §5 Limitations: Delaunay O(N log N),
  SH reflections-as-geometry).
- SuGaR: `https://arxiv.org/html/2311.12775v3` (§4.1 alignment regulariser; §4.2 level-set
  sampling + Poisson depth 10; Fig.3 Marching Cubes failure on Gaussian density; §5.1
  λ=0.3, 5–10 min extraction).
- OpenMVS develop: raw `apps/RefineMesh/RefineMesh.cpp` (defaults as listed above;
  `RefineMesh(resolution-level 0, … regularity-weight 0.2 …)` — vertex-level
  photometric refinement, no voxel).
- Local verification: `milo/mesh_extract_sdf.py` 4× `masks=None`; `sdf/depth_fusion.py`
  vs `sdf/integration.py` mask reads — cited `file:line` above.
- Not fetched (no claim made): RaDe-GS, 3DGSR — stay below the verified routes in evidence
  order until read from source.
