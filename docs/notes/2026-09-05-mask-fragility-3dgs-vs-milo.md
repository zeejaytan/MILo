# Is mask-fragility a 3DGS representation issue or a MILo wiring issue? — source-checked (2026-09-05)

Scope: answer one question from the conservator. In this workflow every mask application
hurts mesh quality at a different stage: the training-time mask painted 0.6–0.9 mm of
break face as background (removed at commit `770338f`); the fusion-time mask is blameless
for the 0.822 mm voxel; post-training pruning drops ~94% of Gaussians and the tet skin
goes slack. SfM/OpenMVS suffers none of this. Is that the representation or the
implementation? Read-only session: no code edits, no Slurm/Spartan, one new note.

Status words: **measured** = seen on our material; **parent-reported** = stated in the
research brief from Spartan runs, not found in-repo; **inferred** = follows from a
verified primary source, unrun here; **web-reported** = what the source states, untied to
our material. SAGA (Segment Any 3D Gaussians) is **not covered**: the guessed arXiv ID
resolved to an unrelated software-engineering paper, so no claim about it is made here —
Gaussian Grouping covers the segmentation family.

## Verdict up front (per mask point — they split)

1. **Training-time mask (one-sided ground-truth patch, removed at `770338f`):
   MILo-wiring.** Masking the ground truth but not the render told the model to paint
   background over everything outside the outline, including the 6 px erosion band that
   is 0.6–0.9 mm of real fracture edge on A03 (**measured** effect size, **inferred**
   mechanism — no masked-vs-unmasked MILo A/B has ever run). The literature-correct form
   masks *both* sides plus an alpha loss, and its measured cost is small (below).
2. **Fusion-time mask (DTU depth zeroing): blameless — neither representation nor
   wiring.** Zeroing masked depth before TSDF fusion is exactly the family convention
   (2DGS does the same at extraction). The 0.822 mm voxel comes from Open3D's signed-32-bit
   scratch at 32,768 blocks, which knows nothing about masks (**measured**).
3. **Post-training pruning (~94% of Gaussians dropped, tet skin slack): both — the
   architecture sets the trap, the wiring walks into it.** No method in the surveyed
   family deletes primitives after training without replacement capacity, because the
   Gaussians are the only scaffold the surface is built from. MILo's prune path deletes
   at the one stage that cannot regrow (refinement tunes occupancy values only; no pivot
   is ever spawned). **Parent-reported** drop size; **inferred** slack mechanism —
   M4's own gate (renders + break-face arc in mm + flat noise) is the measurement that
   settles it.

The one-sentence core, in plain words: **OpenMVS can skip masked pixels because its
surface (mesh vertices) is a separate thing from its supervision (photographs). In 3D
Gaussian Splatting the Gaussians are both at once — they are the surface scaffold *and*
the thing the photographs train. So every exclusion of Gaussians must be paired with
replacement: fresh densification, continued optimisation, or newly bound primitives.
The whole family does this *during* training. Nobody does it *after*.** MILo's three
mask points are exactly: a patch that excluded without pairing (training), a mask that
excludes nothing from the representation (fusion — hence blameless), and a deletion with
nothing paired (pruning).

## 1. Original 3DGS: the loss has no surface term, and upstream itself ships a one-sided mask

Source: Kerbl et al. 2023 (`https://arxiv.org/abs/2308.04079`, v1 — photometric
anisotropic objective, no surface term); code at
`graphdeco-inria/gaussian-splatting`, branch `main` (no tags published):
`train.py` loss block and `scene/gaussian_model.py` density control, fetched this
session (**web-reported**).

- Mechanism. Loss is L1 + D-SSIM on full frames. Mask support is three lines:
  `if viewpoint_cam.alpha_mask is not None: image *= alpha_mask` — the **render** is
  masked, the **ground truth is not**. That is one-sided masking in the opposite
  direction from MILo's removed patch (which masked the ground truth, not the render —
  `milo/train.py:218-236`, verified local read; removal verified `git show 770338f`).
  So one-sided mask application is not uniquely a MILo sin; upstream 3DGS does it too,
  and either direction leaves masked-out pixels contributing loss and gradients.
- What replaces removed capacity. `densify_and_prune`: clone/split driven by
  view-space position gradients, prune on opacity `< min_opacity` and screen/world size,
  interleaved every `densification_interval` until `densify_until_iter`, plus periodic
  `reset_opacity`. After training ends, `prune_points` only deletes — there is no
  post-training densification path in the file. Fixed primitive budget after training:
  whatever survives is all the surface scaffold there is.
- Flip. Masked-vs-unmasked MILo A/B on A03 (break-face arc in mm + flat-wall noise):
  gap ≫ §2's ~3% → our material punishes masks harder than DTU and the verdict flips
  toward representation.

## 2. Object-centric 2DGS: the correct way to mask training is published, and its cost is small

Source: Rogge & Stricker, "Object-Centric 2D Gaussian Splatting"
(`https://arxiv.org/html/2501.08174v2`, v2 — §§4.2–4.3, 5.1, 5.3–5.4, Tables 1/3/4,
Figs. 5–6, App. B), fetched this session (**web-reported**).

- Mechanism. Background loss on accumulated render alpha,
  `L_b = mean(A_i · (1 − M_i))` (eq. 1), **plus** photometric loss with *both* sides
  multiplied by the mask, `L_c^M = L_c(I_i·M_i, R_i·M_i)` (eq. 2, §4.2). The paper states
  the reason outright: the background loss "is at odds with" the photometric loss, which
  otherwise pushes Gaussians to match background colours where M = 0. Masking one side
  alone is the documented failure mode — this is the literature behind `770338f`. An
  occlusion-aware pruning step runs *inside* adaptive density control (every 100/600
  iterations, §5.1).
- What replaces removed capacity. Densification keeps running on 3DGS defaults (§5.1);
  Gaussians driven transparent by `L_b` (γ = 0.5) are auto-pruned by the same density
  control. Nothing is deleted post-hoc.
- Cost of masking, measured on DTU (not our material): chamfer 0.769 vs 0.748 (~3%
  worse), Gaussians 108,568 vs 198,820 (~45% fewer), training 6.46 vs 10.94 min
  (Table 3). Mask errors are tolerated by multi-view consensus: non-object pixels caught
  in a mask are *not* reconstructed, object pixels missed by a mask still are (Figs. 5–6).
- Flip. Their masks are tight outlines over 49–64 views; ours are 6 px-eroded outlines
  over 143 turntable views with clamp contact. Port their §5.4.3 background-loss
  ablation to A03: if the quality gap is an order of magnitude larger than ~3%, the
  "training masks are cheap" verdict flips for this material.

## 3. Segmentation family (Gaussian Grouping): labels, not exclusions — deletion is never followed by meshing

Source: Ye et al., "Gaussian Grouping" (`https://arxiv.org/html/2312.00732v2`, v2 —
§3.2, Alg. 1, §3.3, §4.2/Table 1/Figs. 5–7), fetched this session (**web-reported**).

- Mechanism. Each Gaussian gains an identity encoding supervised by rendered-feature
  classification (eq. 1) plus a k-NN 3D regularisation loss (eq. 3) that explicitly
  supervises occluded Gaussians the 2D loss cannot reach. Crucially, the photometric
  loss is **unmasked** (Alg. 1: `L_image` on the original rendering) — the full scene
  keeps training; grouping is a label, nothing is excluded from supervision. Joint
  training costs ~nothing: PSNR 28.43 vs 28.69 baseline (Table 1). Mask association
  errors self-correct through the shared 3D representation (Fig. 5).
- Deletion without re-densification exists here — and proves the point. Object removal
  deletes a Gaussian group directly with no regrow, but the result is *rendered or
  edited, never re-meshed*; the inpainting path adds **new** Gaussians and fine-tunes
  them (§3.3, Fig. 7). The "transparent bear" ablation (Fig. 7) shows what deletion
  without supervision leaves behind: unsupervised interior Gaussians the 2D loss never
  saw.
- Flip. If any segmentation paper meshes a post-deletion remainder and reports chamfer
  against the pre-deletion mesh, revisit. None surveyed does.

## 4. GaussianObject: masks from iteration zero, deletion interleaved with regrow, then repair

Source: Yang et al., "GaussianObject" (`https://arxiv.org/html/2402.10259v4`, v4 —
§§3.2–3.5, eqs. 2–6), fetched this session (**web-reported**).

- Mechanism. Masks are used three ways, all *during* optimisation: (a) visual-hull
  initialisation — rejection sampling keeping points inside the intersection of all
  image-space masks, colours averaged across views; (b) BCE mask loss on the rendered
  mask (eq. 3) alongside L1 + D-SSIM (eqs. 2, 6); (c) floater elimination — KNN mean
  neighbour distances, threshold τ = mean + λe·std, applied **periodically with λe
  decayed to 0** (§3.3).
- What replaces removed capacity. Optimisation and densification continue after every
  elimination round; then a diffusion repair model synthesises missing content and the
  Gaussians are refined further (`L_rep` + `L_ref`, §§3.4–3.5). Exclusion and regrow are
  interleaved by design — the closest published analogue to "prune and regrow," and it
  never deletes after the optimiser stops.
- Flip. Sparse 4-view regime, not dense turntable. Port only the floater-elimination
  schedule into MILo training on A03: if rig Gaussians clear without touching break
  faces, post-hoc pruning was the wrong stage, not the wrong idea.

## 5. 2DGS: no training mask at all — and density still follows texture, not geometry

Source: Huang et al., "2D Gaussian Splatting" (`https://arxiv.org/html/2403.17888v3`,
v3 — §3 "Challenges in Surface Reconstruction", §5 eq. 16, §6.1, Table 5, §7
Limitations), fetched this session (**web-reported**).

- Mechanism. No mask anywhere in training (final loss `L = L_c + αL_d + βL_n`, §5).
  Masks appear only at TSDF extraction (depth truncation where M = 0) — same stage and
  same spirit as MILo's blameless fusion mask. Pruning is opacity `< 0.05` every 3000
  steps with gradient threshold 0.0002 (§6.1): mid-training, with densification running.
- The representation verdict in the authors' own words (§7 Limitations, verbatim):
  "our current densification strategy favors texture-rich over geometry-rich areas,
  occasionally leading to less accurate representations of fine geometric structures…
  our regularization often involves a trade-off between image quality and geometry, and
  can potentially lead to over-smoothing in certain regions." On untextured fired clay,
  densification under-supplies break faces **whether or not a mask exists** — masking
  cannot be the whole story for thin-relief loss.
- Their ablations bound the extraction stage: median depth beats expected depth (0.83
  vs 0.94 avg, Table 5C — expected depth is outlier-sensitive), TSDF beats SPSR on
  Gaussian centres (Table 5D), because SPSR "cannot incorporate the opacity and the
  size" of the primitives.
- Flip. Gaussian-scale histogram on trained A03 (M1 gate): median support ≫ 0.2 mm
  with quiet depth → floor proven above the requirement regardless of masks.

## 6. GOF: the family's mask-free exclusion — min-over-views — still resolves at Gaussian scale

Source: Yu et al., "Gaussian Opacity Fields" (`https://arxiv.org/html/2404.10772v2`,
v2 — §§3.2–3.4, 4.1, 5), fetched this session (**web-reported**).

- Mechanism. Opacity of a point = **minimum over all training views** (eq. 10, §3.2) —
  "shares similarities to the visual hull or space carving" but with rendered opacity
  instead of binary silhouettes. No masks; exclusion happens at field-evaluation time
  and the Gaussians are untouched. Tets are built from 3σ Gaussian bounding boxes via
  CGAL Delaunay with a non-overlap edge filter (§3.4); level set found by 8-iteration
  binary search, not linear interpolation (Fig. 5). Densification is improved
  (per-pixel gradient norms, eq. 15) with opacity prune at 0.05; densification stops at
  15k of 30k iterations (§4.1).
- Limitations (§5, verbatim in substance): Delaunay is O(N log N) — "a bottleneck
  particularly when the number of points increases" (8 min for one Mip-NeRF360 scene);
  "spherical harmonics for view-dependent appearance… potentially inaccurately
  representing reflections as geometric features" — the mechanism behind chrome-rig
  depth that moves with viewpoint.
- Relevance. GOF is the existence proof that the family knows how to exclude (carve)
  without masks — and still resolves at Gaussian/tet scale, never finer. It never
  re-densifies after exclusion either; it doesn't need to, because it never deletes.
- Flip. None outstanding; supports the representation verdict. If GOF-style min-field
  extraction were ported to MILo's Gaussians, concavities narrower than the view cone
  would carve rather than round — different damage, same scale.

## 7. SuGaR: the family's prune-and-regrow — exclusion mid-schedule plus brand-new primitives

Source: Guédon & Lepetit, "SuGaR" (`https://arxiv.org/html/2311.12775v3`, v3 —
§1/Fig. 3, §§4.2–4.3, 5.1, Table 2), fetched this session (**web-reported**).

- Mechanism. Staged schedule (§5.1): 7k iterations free → 2k entropy pressure toward
  binary opacity → **delete** Gaussians under 0.5 → 6k regularised iterations. Mesh via
  level-set sampling + Poisson (depth 10, λ = 0.3). Then §4.3: instantiate **new, thin
  Gaussians bound to mesh triangles** (barycentric means, 2 scaling factors, 2D
  rotation) and jointly refine mesh + bound Gaussians.
- Why this matters for the verdict. SuGaR deletes mid-training with 6k regularised
  iterations after, then adds fresh capacity shaped by the extracted surface. That is
  the family's only "delete then recover" — and both halves are load-bearing. MILo's
  prune path has neither: deletion happens after the optimiser stops, and refinement
  tunes occupancy on the surviving pivots only. Fig. 3 also states the architectural
  floor plainly: millions of tiny Gaussians make the density "close to zero almost
  everywhere, and Marching Cubes fails to extract proper level sets even with a fine
  voxel grid."
- Flip. Bind new Gaussians to the pruned tet surface à la §4.3 + short refinement: if
  the skin re-tightens, the fragility was wiring (missing regrow), not representation.

## 8. MILo's three mask points, contrasted (locally verified this session)

| # | MILo mask point | What the code does (file:line) | 3DGS-arch or MILo-wiring? |
|---|---|---|---|
| T1 | Training loss unmasked by design; fork patch removed | `milo/train.py:218-236` comment records the removal; `milo/scene/cameras.py:43-48` loads alpha into `gt_mask`, multiply commented out; removal commit `770338f` verified via `git show` | **Wiring** (one-sided patch). Upstream 3DGS is one-sided the other way (`train.py`: `image *= alpha_mask`, GT untouched). Correct form (§2) is published and cheap |
| T2 | DTU fusion zeroes masked depth | `milo/eval/dtu/mesh_extract_dtu.py:133-135`: `depth[(gt_mask<0.5)]=0`, `depth[mask<alpha_thr]=0` before `vbg.integrate()` | **Neither** — matches 2DGS extraction masking (§5). 0.822 mm is Open3D's int32 scratch (**measured**, sphere reproducer 28,176 ok / 34,184 dump) |
| T3 | Native tet path masks dead; prune deletes post-hoc | `masks=None` at `milo/mesh_extract_sdf.py:176,191,341,550` (calls into `integration`/`depth_fusion`/`evaluate_mesh_occupancy`/`evaluate_mesh_colors_all_vertices`); `masks` threaded through `regularization/sdf/depth_fusion.py:403,468,507,570,642` but the fusing body (`_evaluate_sdf_values:443-457`) renders full frames and integrates unmasked depth — parameter documented, never read; prune votes in `scripts/prune_rig_gaussians.py:53-89` (`vote_keep`, no dilation, no off-frame excuse) and pivots drawn from survivors at `mesh_extract_sdf.py:92-105` | **Both.** Dead masks: wiring (upstream). Slack after 94% deletion: architecture (scaffold removal — §§3,6,7: nobody deletes-then-meshes) triggered by wiring (no regrow step; cf. SuGaR §4.3) |

Two caveats that survive this note. First, `770338f`'s message and the `train.py`
comment cite arXiv:2501.08174 as "explicit" that both sides must be masked — verified
this session (§4.2: background loss "at odds with" the unmasked photometric loss).
But the 0.6–0.9 mm damage figure is **measured** (mask erosion × 0.21 mm/px) while the
claim that the patch *caused* a lost A03 run's quality is **inferred** — no A/B ran
(`docs/notes/A03_DTU_EXTRACTION_RESULT.md:152` says "Untested"). Second, the "~94%"
prune drop appears nowhere in-repo (searched); it is **parent-reported** from Spartan
runs. The slack-skin mechanism is **inferred** from §§3/6/7, not rendered.

## Bottom line for M4 (and what would flip each line)

- **T1 — MILo-wiring.** Re-adding any training mask must mask both sides + add an
  alpha loss (§2, eqs. 1–2), not re-animate the one-sided patch. Flip: A03 A/B with
  gap ≫ 3% (§1).
- **T2 — blameless, toolchain.** No mask work needed; the ceiling is the block cliff.
  No flip available post-hoc.
- **T3 — architecture sets it, wiring triggers it.** Deleting 94% of the pivot
  scaffold with no replacement is outside everything the family demonstrates (§§3, 4,
  6, 7 delete-then-continue or never-delete; only SuGaR §4.3 adds capacity back, bound
  to the surface). M4's gate stands as the cheapest decider: pruned extraction + tight
  0.10 mm/px renders + break-face arc loss in mm + flat noise pruned/unpruned/OpenMVS.
  If the skin holds and arc loss is ≪ 1 mm, this note's T3 verdict is wrong and the
  correction is recorded in `intent/M4-*`. If it goes slack, the SuGaR-shaped fix
  (bind new Gaussians to the pruned surface + short refinement) is the only
  family-precedented recovery — plain re-densification has no precedent because
  post-training gradients no longer exist.
- **Why OpenMVS is immune, in one line each:** per-pixel depth skips masked pixels
  because depth maps are per-view images, not a shared primitive budget; per-vertex
  refinement moves existing vertices because the mesh topology survives masking. In
  3DGS the primitives are the budget, the scaffold, and the supervision carrier all at
  once — masking any one of the three starves the other two unless replacement is
  explicitly paired. That asymmetry is representation, and it is the whole answer to
  "why does every mask hurt here and none hurt there."

## Primary sources fetched (pinned, this session)

- 3DGS paper: `https://arxiv.org/abs/2308.04079` (v1; photometric objective).
- 3DGS code, `main` (no tags): `train.py` (`image *= alpha_mask`, unmasked
  `l1_loss(image, gt_image)`); `scene/gaussian_model.py` (`densify_and_prune`,
  `reset_opacity`, `prune_points` — no post-training densify). Raw URLs under
  `https://raw.githubusercontent.com/graphdeco-inria/gaussian-splatting/main/…`.
- Object-centric 2DGS: `https://arxiv.org/html/2501.08174v2` (§4.2 eqs. 1–3, §4.3,
  §5.1, Tables 1/3/4, Figs. 5–6, App. B).
- Gaussian Grouping: `https://arxiv.org/html/2312.00732v2` (§3.2 eqs. 1/3–4, Alg. 1,
  §3.3, Table 1, Figs. 5/7).
- GaussianObject: `https://arxiv.org/html/2402.10259v4` (§§3.2–3.5, eqs. 2–6).
- 2DGS: `https://arxiv.org/html/2403.17888v3` (§3 challenges, §5 eq. 16, §6.1 incl.
  Table 5, §7 Limitations).
- GOF: `https://arxiv.org/html/2404.10772v2` (§3.2 eq. 10, §3.3 eqs. 13–15, §3.4,
  §4.1, §5).
- SuGaR: `https://arxiv.org/html/2311.12775v3` (§1/Fig. 3, §4.1 eqs. 1–10, §4.2–4.3,
  §5.1/Table 2).
- Local: `milo/train.py:218-236`, `milo/scene/cameras.py:43-48`,
  `milo/mesh_extract_sdf.py:92-105,176,191,341,550`,
  `milo/regularization/sdf/depth_fusion.py:400-457`,
  `milo/eval/dtu/mesh_extract_dtu.py:133-135`, commit `770338f`.
- Sister note (context, not evidence): `docs/notes/2026-09-04-milo-vs-3dgs-limits.md`
  (R1/R2 representation floor); `docs/notes/A03_DTU_EXTRACTION_RESULT.md:152`.
