# 04: TopoSurfel mask-path audit (desk, no GPU)

**What to build:** the paper answer to whether TopoSurfel can exclude the rig on this material — a stated mask route or a documented no-build, decided on the laptop before any GPU burns.

**Answers:** M7

**Blocked by:** None (can start immediately).

**Status:** ready-for-agent

- [x] Audit reads the shipped arguments and extraction path at the pinned commit and states where a mask would enter (masked PGSR init, fusion-time depth zeroing, or neither exists)
- [x] Either the mask route is written down precisely enough to build, or the track is declared a no-build with the reason — "assume it works" is not an outcome
- [x] TopoSurfel and PGSR commits pinned in this file; the 32,768-block assumption for its TSDF extraction recorded as binding-until-shown-otherwise

## Comments

- 2026-09-06: audit run against TopoSurfel main HEAD `1525ce3` (2026-09-01),
  files read in full: `train.py`, `arguments/__init__.py`, `scene/__init__.py`,
  `scene/cameras.py`, `scene/dataset_readers.py`, `utils/camera_utils.py`.
  PGSR stage not code-audited (vendored dir, init scripts only) — its commit
  pins at build time if the track ever reopens.
- Verdict: **NO-BUILD as a masked extractor without new code.** Findings:
  1. `mesh_init.ply` is REQUIRED (unguarded read); surfels are created FROM it,
     the in-loop proxy-mesh box is padded 10% around it, and the surface prior
     is built from it. Run the PGSR stage on an unmasked turntable and the rig
     enters at all three points on day one. No masked-init path is documented.
  2. The only training-time mask consumer is one-sided GT compositing
     (`gt_image * gt_alpha_mask + bg * (1 - mask)`, render unmasked) — the same
     construction as the removed MILo fork patch: it instructs the model to
     paint background over masked-out pixels, including the eroded fracture
     rim. Feeding our `A03_erode0` RGBA set would repeat that failure, not
     inherit MILo's working fusion-time masking.
  3. `cam.mask` (RGBA 4th band) is populated and never read anywhere in
     training. No mask in any loss, densifier, pruner, or the TSDF extraction
     call. The 32,768-block assumption stands (same Open3D TSDF family).
  4. Latent traps for any future build: `-r -1` default downsamples past
     1600 px (same trap as MILo — sherds need `-r 1`); the virtual-cam path
     passes `image_width` into the `gt_alpha_mask` slot (arg-order bug, dead
     by default since virtual cams default off).
- Consequence for 07: reopening TopoSurfel needs a scoped mask patch (masked
  init + fusion-time depth zeroing instead of GT compositing), stated and
  amended into M7 first per its gate. Until then 07 stays closed-unbuilt.
