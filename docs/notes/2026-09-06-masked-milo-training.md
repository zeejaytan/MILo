# Can MILo be trained with masks? Both-sides construction, rim analysis, cheapest test (2026-09-06)

Status words: **measured** = seen on our material or in a cited table; **inferred** = follows from a
verified primary source, unrun here; **web-reported** = what the source states, untied to our material.
This is a background-research note: no code was changed, no job was run.

Question: can MILo exclude the clamp rig at *training* time — masking both render and ground truth plus
an alpha/background loss — without repeating the failure that got the old one-sided patch removed at
commit `770338f` (painting background over the 0.6–0.9 mm break-face rim)?

## Verdict up front

**Buildable: yes, in ~15 lines at one site** (`milo/train.py:238-244`), on the `radegs` rasterizer the
sluice already uses. **Rim-safe: not proven — the literature's safety case does not cover our erosion**,
and the exact failure class it warns about (systematic mask error + large background weight) is what a
6 px erosion on every view is. **Cheapest test: two A03 training runs** (masked vs unmasked, same seed),
scored on millimetres of break-face arc plus flat-wall noise on held-out views — about 12 GPU-hours plus
scoring, with a cheaper 8k-iteration probe available first. Details below.

Plain words: the published recipe for masked training exists and fits MILo's code with a small patch.
Its measured cost on the benchmark is small (~3% worse shape). But the benchmark's masks are tight
outlines with occasional mistakes, while ours are shrunk by 6 pixels on *every* view along exactly the
edge a reassembly matcher reads. The paper says occasional mistakes are tolerated and systematic ones
are not. So the patch is worth building, but the rim question can only be settled by running it on A03,
not by citing the paper.

## 1. Proposed loss construction for MILo

Source for the construction: Rogge & Stricker, "Object-Centric 2D Gaussian Splatting",
`https://arxiv.org/html/2501.08174v2`, §§4.2–4.3, 5.1, 5.4.3, 5.5, Tables 1/3, Figs. 5–6, App. B
(**web-reported** throughout §1; the arXiv record states "Implementation details (no code)", so this is
a port from the equations, not a patch import).

Total loss (paper eq. 3):

```
L = L_c^M  +  α·L_d  +  β·L_n  +  γ·L_b
```

- **Masked photometric loss** (paper eq. 2): `L_c^M(I,R,M) = L_c(I·M, R·M)` — *both* the photograph and
  the render multiplied by the mask before the colour loss. The paper states the reason outright: the
  background loss "is at odds with" an unmasked photometric loss, which pushes Gaussians to match
  background colours where M = 0 (§4.2). Masking one side alone is the documented failure mode — this is
  the literature behind `770338f`.
- **Background loss** (paper eq. 1): `L_b = mean(A·(1−M))`, where A is the accumulated render alpha.
  Penalises any opacity outside the mask; Gaussians driven transparent are auto-pruned by the standard
  density control. Weight γ = 0.5 in all paper experiments (§5.1).
- Depth-distortion and normal-consistency terms need no masking ("they do not influence the opacity of
  Gaussians", §4.2) — convenient, because MILo's depth-normal and mesh regularisers stay untouched.

Where each term hooks into MILo (all locally verified this session):

| Term | Hook |
|---|---|
| `M` (mask) | `viewpoint_cam.gt_mask`, already loaded per view at `milo/scene/cameras.py:43-48` and already at training resolution (`milo/utils/camera_utils.py:51-53` resamples the alpha channel with the same `resolution` as RGB). No plumbing needed. |
| `L_c^M` | `milo/train.py:238-244`: replace `l1_loss(image, gt_image)` with `l1_loss(image·M, gt_image·M)` and likewise inside `fused_ssim(...)`. λ_dssim default 0.2 (`milo/arguments/__init__.py:87`). |
| `L_b` | Same block: `γ · (rendered_alpha·(1−M)).mean()` with γ = 0.5 starting value. Alpha source depends on path (next row). |
| `A` (render alpha) | **Only on some render paths.** `radegs` returns it as `render_pkg["mask"]` (`milo/gaussian_renderer/radegs.py:76-91`). `render_full` returns gradient-capable `expected_alpha` when `compute_expected_depth=True` (`milo/gaussian_renderer/__init__.py:525-543,586`) and no-gradient `accum_alpha` (`:568,579`). **The `gof` path returns `"mask": None`** (`milo/gaussian_renderer/gof.py:124-125`) — the alpha hook does not exist there. The default no-regularisation path `render_imp` returns **no alpha at all** (`milo/gaussian_renderer/__init__.py:197-202`). |
| Pruning of killed Gaussians | Existing `densify_and_prune_mask` prunes on opacity `< min_opacity` (`milo/scene/gaussian_model.py:967-981`) — transparent rim/rig Gaussians drain through it with no new code. |

Two wiring catches, both **inferred** from the reads above:

1. **Gate `L_b` on alpha availability.** MILo's production sluice (`slurm/milo_train.slurm:94-103`) trains
   with `--rasterizer radegs`, and past iteration 3000 the depth-normal regulariser (`--regularization_from_iter`,
   default 3000) and mesh loop route rendering through `render` = `render_radegs` (`milo/train.py:187-192`),
   where `render_pkg["mask"]` exists. But iterations 0–3000 use `render_imp`, which has no alpha key —
   reading it unconditionally crashes the first 3000 steps. Start `L_b` with the regulariser kick
   (`reg_kick_on`), or force the `render` path throughout. (Side benefit: holding `L_b` until ~3000 also
   spares rim seed points from transparency pressure before densification, which runs 500–15,000 per
   `milo/arguments/__init__.py:88-92`, and before depth re-init at 2000.)
2. **Do not build this on `--rasterizer gof`.** Its render dict drops alpha; porting means threading
   `rendering[7:8]` through as `"mask"`. `radegs` needs nothing.

What is deliberately *not* ported: the paper's occlusion-aware pruning (§4.3 — CUDA-kernel tracking of
which Gaussians actually contribute to alpha blending, pruning inside density control every 100/600 iters
per §5.1). That is a kernel change, not a loss change. MILo's prune rule (opacity + screen/world size,
`gaussian_model.py:974-978`) plus its frustum `factor_culling` is coarser: never-contributing interior
floaters survive. Accept them for the A/B; they cost memory, not rim geometry.

## 2. Rim-pixel analysis on A03 (in mm)

Measured inputs: masks eroded 6 px; on A03 that band is **0.6–0.9 mm of real sherd at the fracture edge**
(**measured**, AGENTS.md fork change 2; depth sampling 0.21 mm/px at the object). Erosion is at the limit
on fracture ridges and the clamp-contact face is permanently unobserved (**measured**, `intent/M2-*`).

What each loss term does at an eroded-rim pixel (M = 0, real clay present) — **inferred** from §4.2:

- `L_c^M`: contributes nothing (both sides are zero). The rim pixel is *unsupervised* by colour.
- `L_b`: actively pushes accumulated alpha toward 0 along that ray — i.e. it tells the optimiser no
  surface exists there. Surviving rim Gaussians go transparent and drain through opacity pruning.
- Who constrains the rim, then? **Only multi-view consensus.** The paper's Figs. 5–6 show object pixels
  missed by one mask still reconstructed because other views supervise them (**web-reported**).

Whether consensus saves *our* rim turns on one distinction the paper draws explicitly:

- Tolerated: errors in *individual* masks (§5.3.2: "robust to minor errors in individual masks").
- Not tolerated: *systematic* errors — "systematic errors will result in bad reconstructions" (§5.5), and
  the §5.4.3 ablation shows raising the background weight to clear stubborn background penalises
  correctly-placed Gaussians at occluded/erroneously-masked pixels until geometry suffers.

Our erosion is the second kind: 6 px on **every** view, always biased inward. Mitigating nuance, also
**inferred**: image-space erosion does not erase the same physical points in all views. A fracture ridge
seen from above falls mid-mask (M = 1, supervised); it is only at silhouette in profile views. So the
ridge keeps colour supervision from near-nadir views, while exactly the *profile* constraint — the one
that locates the edge in depth — is unsupervised everywhere. Expected failure signature if this bites:
rims that recede or round by roughly the erosion width (order 0.6–0.9 mm), not catastrophic collapse.
One structural point in our favour vs the paper's data: DTU is a front-hemisphere capture (49–64 views),
while the turntable rings the object (143 views), so each rim point is seen interiorly from more angles
than any DTU point — consensus has more to work with here (**inferred** from §5.2 view counts).

## 3. DTU cost evidence vs our-material differences

Paper Tables 1/3 (§5.3.1, **web-reported**, RTX 3090, 30k iterations, 800×600, tight SAM-style masks):

- Shape cost of full masking: chamfer 0.769 vs 0.748, ~3% worse; ~45% fewer Gaussians (108,568 vs
  198,820); ~41% faster training (6.46 vs 10.94 min).
- Pruning alone (no masks): chamfer 0.750 vs 0.748 — effectively free (§5.4.1, Table 6).
- Masking alone without the background loss (photometric masking only): "geometry breaks and Gaussians
  remain in the background" (§5.4.3, Fig. 8) — the both-sides-plus-alpha construction is load-bearing,
  not optional garnish.

What changes on our material (**inferred** deltas, all against the DTU conditions above):

| Factor | DTU | A03 | Direction |
|---|---|---|---|
| Views / resolution | 49–64 @ 800×600 | 143 @ 3200×2133 | Ours carries ~35× the pixel-throughput; a run is ~6 GPU-h (`slurm/milo_train.slurm`). Absolute A/B cost ~12 GPU-h + scoring. `L_b` itself is normalised by pixel count (mean over h·w, eq. 1), so γ = 0.5 transfers without rescaling. |
| Mask error type | Tight, sporadic | 6 px systematic inward erosion + permanently unobserved clamp contact | Against us (§5.5). The contact face deserves emphasis: mask = 0 there in *all* views, so `L_b` carves a hole. That is correct behaviour (no data exists), but it must be scored as missing surface, never as wrong surface. |
| View coverage | Front hemisphere | Full ring | For us (consensus per §2). |
| Surface texture | Varied objects | Untextured fired clay | Against us if anything: 2DGS's own limitations note densification favours texture over geometry (sister note §5). Masked colour supervision is thinner on clay, so `L_b` meets less resistance at the rim. |
| Subject of interest | Whole object | 0.6–0.9 mm rim band | Whole-object chamfer cannot see our failure mode even if it occurs — hence §4's scoring. |

## 4. Cheapest A/B design (no whole-object chamfer)

Dataset `data/17062025/A03_sherds` (sherd-only masks) already exists — no new masking work. Two training
runs, identical seed/config (`-r 1 --eval --imp_metric indoor --rasterizer radegs --dense_gaussians`,
per `slurm/milo_train.slurm:94-103`): **(A)** patched loss from §1 with γ = 0.5; **(B)** unpatched control.
`--eval` holds out every 8th view as the honest instrument.

Score, in order (all deltas A−B, never absolute-vs-GT — there is no ground truth):

1. **Break-face arc in mm** (primary): pick 2–3 fracture edges, trace arc length of seated break face on
   A vs B vs the OpenMVS mesh. OpenMVS is a *reference*, not truth — report agreement deltas.
2. **Flat-wall noise** (secondary): RMS residual to a local plane on flat sherd faces, A vs B. Detects
   whether `L_b`/masking roughens quiet surfaces.
3. **Held-out masked rendering**: masked PSNR/SSIM on the `--eval` views (paper eqs. 4–5, §5.3.2). Detects
   gross damage cheaply before any meshing.
4. **Renders first**: rim close-ups at ≤0.10 mm/px on the same edges before trusting any number
   (workspace look-before-reporting rule; a picture at the wrong scale has already hidden a wear effect
   once — `docs/lessons.md`).

Even cheaper pre-gate (optional, **inferred** to be informative): an ~8k-iteration probe pair — past
depth re-init (2000) and into densification, before the 15k densify cutoff — logging per-view alpha mass
inside the eroded band plus rim renders. If band alpha is draining and nadir views cannot hold the edge,
stop before spending the full 12 GPU-h.

Why not whole-object chamfer: it averages a sub-millimetre, rim-localised effect over ~0.1 m² of sherd,
launders OpenMVS error into "truth", and — with no ground-truth mesh existing — cannot be phrased as a
score against one. It is the ruler most likely to report "no difference" while the matcher-relevant edge
recedes.

## 5. Flip conditions

- **Buildable flips to wrong-for-this-material** if the A/B gap on arc-loss/flat-noise is an order of
  magnitude beyond DTU's ~3%: e.g. arc recession approaching the 0.6–0.9 mm erosion width, or flat noise
  clearly above control. Then training-time masking is representation-hostile on clay rims and rig
  exclusion stays a fusion/extraction-time operation.
- **Rim-safe is confirmed** (not merely not-refuted) if arc agreement A−B is ≪ erosion width *and* rim
  renders hold the edge at profile views, across the 2–3 sampled edges. One sherd is a lead, not a
  conclusion — say so in the read-out.
- **M2's gate still rules the fieldwork**: if arc loss is a material fraction of a typical break face
  either way, the mount has to change (second mount per sherd) and no loss recovers it.

## 6. Risks (ordered by likelihood of biting)

1. **Systematic-erosion carve (§5.5 class).** The paper's stated non-covered case. Mitigation is the γ
   ladder (0.25 / 0.5 / 1.0) only if 0.5 damages rims — not upfront.
2. **DSSIM window bleed at the mask edge.** `fused_ssim` on zero-masked frames straddles a black,
   sharp mask boundary in every 11×11 window crossing the rim; rim gradients get driven by the mask edge,
   not clay. The paper's own masked-SSIM discussion admits window contamination (§5.3.2). If rims look
   etched, shift weight to L1 on the masked term or compute SSIM over valid pixels only (**inferred**).
3. **Clamp-contact holes read as damage.** Permanent, per M2 — pre-register contact faces and exclude
   them from arc scoring, or the A/B punishes the masked run for honesty.
4. **Masked-out views impoverish view-dependent colour.** SH degree ramps 0→3 during training
   (`milo/train.py:63,165-166,438`); rim Gaussians never supervised from clamp-side directions fit their
   higher lobes on fewer views. Low risk for near-Lambertian clay; note-and-move-on unless rims render
   with directional blotches (**inferred**).
5. **`--decoupled_appearance` interaction.** Per-view appearance embeddings now fit on masked pixels only;
   held-out masked PSNR stays the apples-to-apples check. Low risk, watched by metric 3 (**inferred**).
6. **GOF rasterizer has no alpha hook** (`gof.py:125`). Not a risk if the sluice stays on `radegs`; a hard
   build step if anyone switches.
7. **Re-animating the one-sided patch.** Any experiment that composites background into GT without also
   masking the render (or vice versa) re-runs `770338f`. The §1 construction masks both sides *and* adds
   `L_b` — all three, or none.

## Primary sources

- Loss construction, weights, ablations, cost tables, limitations: Rogge & Stricker,
  `https://arxiv.org/html/2501.08174v2` (§§4.2 eqs. 1–3, 4.3, 5.1, 5.2, 5.3.1 Tables 1/3, 5.3.2 eqs. 4–5
  + Figs. 5–6, 5.4.1 Tables 6–7, 5.4.3 Fig. 8, 5.5, App. B). Record page `https://arxiv.org/abs/2501.08174`
  (v2, 3 Apr 2025; "Implementation details (no code)" — no public implementation to pin).
- MILo hooks (local, this session): `milo/train.py:187-244,438`; `milo/scene/cameras.py:43-48`;
  `milo/utils/camera_utils.py:51-53`; `milo/gaussian_renderer/radegs.py:76-91`;
  `milo/gaussian_renderer/gof.py:97-134`; `milo/gaussian_renderer/__init__.py:110-202,387-590`;
  `milo/scene/gaussian_model.py:967-981`; `milo/arguments/__init__.py:76-92`;
  `slurm/milo_train.slurm:94-103`.
- Measured context: `MILo/AGENTS.md` (fork change 2; 0.21 mm/px; `A03_sherds` dataset);
  `intent/M2-does-masking-eat-the-break-face.md` (6 px at the limit, unobserved contact);
  `docs/notes/2026-09-05-mask-fragility-3dgs-vs-milo.md` §§1–2.
