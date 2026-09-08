# M7 — Can TopoSurfel or VGGT + InstantSplat++ get sherds out of the rig at the resolution a break face needs?

**Status:** open · **Blocked by:** the OpenMVS baseline only (requirement ~1 mm
stated; MILo-specific boxes do not gate a different method — each candidate carries
its own depth probe as part of its evaluation) · **Effort:** roughly 2–4 days for the VGGT pose track, 1–2 weeks for a pinned
TopoSurfel build plus one-capture A/B, 2–3 days for a pinned SAGA filter plus fusion reuse

**Settled scope, 2026-09-06 (grilling rounds 1–2, accepted; user change; amended 2026-09-06
per user OK):** TopoSurfel is judged on
**masking** (fusion-time sherd outlines — the only route that worked on A03); VGGT is
judged as a **pose source** first, with **`phai-lab/InstantSplatPP` (InstantSplat++) as
its named downstream viewable-splat route** (VGGT prior → splat optimisation → free-view
rendering, per upstream `scripts/run_all_prior_model.bash`). **SAGA (`Jumpat/SegAnyGAussians`,
AAAI'25) is judged as a post-hoc filter first:** freeze full-scene MILo Gaussians, distil
SAM masks to per-Gaussian features, filter to sherd subset at full density, then reuse the
live fusion-time masked-depth path (`mesh_extract_dtu.py:133-135`, `integration.py:54-59`).
A viewable splat is for
looking, not measuring — it does not clear the mesh bar below until a mesh route with
voxel/band in mm plus scale anchoring is named. The bar is the M7 bar as written (steel
cm² left, fraction within M1 ~1 mm on the same ruler, ridge-resolving renders). All
tracks wait for M1's boxes. Pinned builds, full resolution, no Slurm without approval.
"Extract" alone is vague — `CONTEXT.md` now says to name masking, pruning, or culling;
a splat is not a mesh.

## Why it matters

MILo's own DTU extraction route is closed on quality grounds, and two retired lines
([M4](M4-can-rig-gaussians-be-pruned-after-training.md),
[M5](M5-can-masked-training-exclude-rig.md)) showed that removing the steel is easy but
removing it *without thinning the clay past use* is the hard part. Any replacement has to
clear the same bar on the same capture: the ten sherds separated from the clamps, rods
and jaws, the break-face relief (~1 mm per M1) preserved, and the mesh at true scale.
A swap that lands on the same ceiling is motion without progress. If nothing reaches the
bar, say which of the three it is — the method failed on this material (1), the ruler was
wrong (2), or there was never valid material to score against (3) — because those lead
to opposite decisions.

## Opinion before acting (workspace rule — researched, then stated)

Worth doing in general; **not yet shown worth doing for this**, and the three candidates
are not the same kind of thing.

- **SAGA** (`Jumpat/SegAnyGAussians`, AAAI'25, arXiv:2312.00860) is the closest fit for
  the stated condition — sherd out with no quality loss. **Post-hoc:** freeze the full
  MILo scene, distil SAM masks to per-Gaussian affinity features, retrieve the sherd
  subset by point/scribble/mask query in ms. Pure filter — geometry untouched, object at
  full density — then feed the survivors to the live masked-depth TSDF or GOF tetrahedra
  path. Unlike M4 vote-pruning (19x sparse, 1.76 mm skin) and M5 masked training (91%
  drained), exclusion is paired with retention by construction. Needs pinned commit,
  full-resolution `A03_sherds` masks, and the same mm bar; masks must be consistent
  across the 143 dense views or the ID splits.

- **TopoSurfel** (SIGGRAPH Asia 2026, `Fan-Treasure/TopoSurfel`, arXiv:2608.20687) is the
  closer fit: Gaussian surfels co-evolved with a proxy mesh to suppress floaters and fill
  holes, and it names MILo among the codebases it builds on. But as shipped it has **no
  mask input** — `arguments/__init__.py` at HEAD exposes `images`, `resolution`,
  `white_background`, multi-view and mesh-guidance weights, and no mask flag; custom data
  is `images/` + COLMAP `sparse/` + a required `mesh_init.ply` grown by PGSR first. Run
  that init on an unmasked turntable and the rig enters on day one, baked into the
  surface the surfels start from. Final extraction is `render.py` with `--voxel_size` /
  `--max_depth` TSDF fusion, i.e. the same Open3D family that binds MILo — assume the
  measured 32,768-block cliff binds here too until shown otherwise. Accuracy is shown on
  DTU, Tanks and Temples, Mip-NeRF 360 and synthetic scenes, none of them at 0.2 mm
  fracture-ridge scale. So the accuracy claim does not transfer until the mask path and
  the millimetre figures are demonstrated on A03.
  **Audit verdict, 2026-09-06 (ticket 04, HEAD `1525ce3`): NO-BUILD as a masked
  extractor without new code** — rig enters via the required `mesh_init.ply` at
  three points (surfel init, proxy-mesh box, surface prior); the only
  training-time mask consumer is one-sided GT compositing, the removed-fork
  construction; `cam.mask` is populated and never read. Reopening needs a
  scoped mask patch amended here first; ticket 07 stays closed-unbuilt.
- **VGGT** (CVPR 2025 Best Paper, `facebookresearch/vggt`, arXiv:2503.11651) is a
  **different category**: a feed-forward transformer that infers cameras, depth maps and
  point maps from views in seconds and exports COLMAP `sparse/` for a downstream
  splatting/meshing step. Its speed claim is about that inference, not about a finished
  break-face mesh. It predicts everything in frame including the rig, carries no mask,
  and its scale is ambiguous until anchored — so "extract the sherd cleanly" as shipped
  is not something it does at all. **Measured cap, 2026-09-06 (ticket 03): VGGT
  resizes every input to 518×518** (ISPRS Ann. 2026 DTU analysis) — ≈1.3 mm/px at
  our object against 0.21 mm/px photographed, so its maps cannot resolve ~1 mm
  relief regardless of later filtering (confidence threshold 2.0 recommended
  start; uncertainty aleatoric only). Its honest role here is **fast poses** (a possible
  COLMAP replacement), not a break-face mesher, and it should be judged as one.
- **InstantSplat++** (`phai-lab/InstantSplatPP`, extension of `NVlabs/InstantSplat`,
  arXiv:2403.20309) is the named downstream of the VGGT track: sparse-view SfM-free
  Gaussian splatting with explicit prior-model support including VGGT
  (`scripts/run_all_prior_model.bash`), optimised for **free-view rendering** in seconds
  and supporting 3D-GS / 2D-GS / Mip-Splatting. That pairing is upstream-supported, so
  the route is coherent — but it is a **viewing** route, not a measuring one: no mask
  input is documented, the design target is sparse views of large scenes (the opposite
  of 143 dense views of 20–80 mm sherds), and the output is splats for rendering, not a
  scaled mesh scored in millimetres. Sound as a fast look at the tray; not shown to
  preserve ~1 mm break-face relief or to remove steel. Judge it on renders, never on
  vertex counts.

Neither candidate meets the user's condition — sherd out of the rig with no quality
loss — without extra work that is currently unscoped (a mask path for TopoSurfel, a
mesh route with scale anchoring behind VGGT + InstantSplat++, a pinned SAGA filter wired
to the live fusion path). Measure M1's boxes first; they are
cheap and they gate all tracks either way. Small-object literature search now partly done
2026-09-06 (SAGA, Gaussian Grouping, Feature3DGS, object-centric 2DGS, GOF surveyed from
primary sources); A03-scale demonstration still owed before building.

## Done when

- [x] SAGA commit pinned in this file before any job is submitted, trained feature head
  on frozen full-scene `A03_sherds` Gaussians at full capture resolution, sherd subset
  retrieved by mask query, mesh extracted via the live fusion-time masked-depth path
  with voxel size and truncation band stated in **millimetres** — DONE 2026-09-08
  (ticket 09, verdict EARNS): `Jumpat/SegAnyGAussians@v2@2d4c5d7`; 222,678 frozen
  Gaussians → 24,292 kept at sim>0.1 (footprint 1.35 mm); voxel 0.0022 units =
  0.822 mm, band ±6.58 mm; outlines 73.7% (OpenMVS 42.2%, unfiltered MILo 8.6%,
  21 sherd-only held-out views); surface 67.2% within 1 mm of OpenMVS, median
  0.53 mm (p90 is OpenMVS's base-plate content); zero steel; one capture —
  speck filter, ridge close-ups and a second capture owed before mesh-of-record.
  Conservator eye 2026-09-09: best Gaussian-splat mesh so far, but coarse/rugged
  (1.35 mm footprint, 4.1 mm depth floor), clamp residue in places, clamp holes
  elsewhere (unobserved, stay open) — earns the filter role, not the record
- [ ] TopoSurfel **and** its PGSR init pinned by commit hash in this file before any job
      is submitted — an unpinned build is unrepeatable. Trained on the existing
      `A03_sherds` dataset at full capture resolution (`-r 1` equivalent — no silent
      downsample), mesh extracted with voxel size and truncation band stated in
      **millimetres**
- [x] VGGT pose track RETIRED NO 2026-09-06 (ticket 05): checkpoint `facebook/VGGT-1B` open (Commercial application-gated), code `facebookresearch/vggt@a288dd0`. Feed-forward collapsed in both input modes on A03 (unmasked: median rot 92°, trans 1385 mm; masked sherd-on-white: 111°, 1072 mm; AUC@10° 0.0 both; rings plots eye-verified) and `--use_ba` refused (`No reconstruction can be built with BA`, too few inliers). Type-1 on this material, one capture. Pose-source role not earned; mesher reading was already closed by the 518px cap
- [x] InstantSplat++ viewable-splat RETIRED pose-dependent 2026-09-06 (ticket 06 `wontfix`): its VGGT prior is known-garbage on A03, so no honest splat test exists behind this track. An unposed splat would be a new ticket with voxel/band in mm + scale anchoring, not this one
- [ ] Cross-view depth disagreement in **millimetres** for each candidate versus MILo's
      DTU route on the same capture, on the same ruler (scale sidecars)
- [ ] Same-ruler comparison against OpenMVS on A03 — fraction of sherd surface within
      the M1 requirement (~1 mm relief); reuses M1's second box, not a second ruler
- [ ] Break-face close-up renders, each candidate versus MILo, at a view that resolves
      ~0.2 mm ridges — a whole-sherd view looks fine at every resolution and has misled
      here repeatedly
- [ ] Rig check for the inputs actually used: `mask_content.py` steel-vs-clay split, and
      remaining steel surface area in each extracted mesh, stated in **cm²**

## Gate / stop condition

- If OpenMVS already meets the M1 requirement: **stop** — record it and do not swap,
  whatever any candidate's merits elsewhere.
- If SAGA filtering leaves steel webbed or drops clay density the way M4/M5 did: retire
  NO at one capture with eye verification (type-1 method failure on this material); do
  not fund a second post-hoc architecture to re-learn it.
- If TopoSurfel needs a mask patch (fusion-time zeroing or masked init): that is new
  extraction code — amend this question with the patch stated, do not build around it
  silently. If its extraction hits the 32,768-block cliff at the required voxel, this
  becomes the tiling question — amend, do not build around it.
- If VGGT depth/point maps land coarser than the M1 requirement: retire the mesher
  track at one capture with eye verification (type-1 method failure on this material);
  the pose-only track stays open only with fresh justification, not by default.
- The InstantSplat++ splat is judged as viewing-only: if its renders hold ridge detail
  at ~0.2 mm-resolving views it earns a look-but-don't-measure role; if the rig rides
  along in frame, that is expected behaviour for an unmasked renderer, not a mesh
  failure — record which of the three it is and do not score it in mm.
- If masked training under either candidate drains density the way M5 did (~91% on
  MILo): retire NO at the same weight, do not fund a second architecture to re-learn it.

## Source

User proposal 2026-09-06 (TopoSurfel for accuracy, VGGT for speed, condition: clean
sherd-from-rig separation without quality loss; amended 2026-09-06 per user OK to add
SAGA post-hoc filter track); SAGA paper (arXiv:2312.00860) + `Jumpat/SegAnyGAussians`
README (freeze + distil + millisecond retrieval; geometry untouched); TopoSurfel README + paper
(arXiv:2608.20687) + `arguments/__init__.py` at HEAD (no mask flag); VGGT README +
paper (arXiv:2503.11651: cameras/depth/point-maps in seconds, COLMAP export,
downstream splatting); InstantSplat++ README (upstream VGGT-prior path,
`run_all_prior_model.bash`; free-view rendering; 3D-GS/2D-GS/Mip-Splatting; no mask
input documented); [M1](M1-resolution-the-material-needs.md),
[M4](M4-can-rig-gaussians-be-pruned-after-training.md),
[M5](M5-can-masked-training-exclude-rig.md),
[M6](M6-does-2dgs-reach-break-face-resolution.md); MILo `AGENTS.md` domain notes
(0.21 mm photo support, block-cliff arithmetic, mask-content split);
`docs/notes/A03_DTU_EXTRACTION_RESULT.md`.
