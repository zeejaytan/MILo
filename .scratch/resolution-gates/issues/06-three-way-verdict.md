# 06: Three-way verdict with renders

**What to build:** the answer M6 exists to get — MILo vs 2DGS vs OpenMVS on the one
ruler, with resolving-view break-face renders, written back into M6 win or lose.

**Answers:** M6

**Blocked by:** 05 (2DGS mesh); reads the M1 boxes (01–03) as its bar and baseline.

**Status:** claimed (2026-09-07 — verdict work started; renders before numbers)

- [ ] Same-ruler comparison of all three meshes (fraction of sherd surface within the
      requirement in **mm**); the average across runs is reported, never best-of-N alone
- [ ] Cross-view depth disagreement in **mm** for 2DGS on the same ruler (M6 box;
      port `scripts/depth_disagreement.py` to 2DGS `surf_depth` — GPU job)
- [ ] Break-face close-up renders, 2DGS versus MILo, at a view that resolves ~0.2 mm ridges —
      the render exists before any geometry box is ticked
- [ ] Rig check: remaining steel surface area in each extracted mesh, stated in cm²
- [ ] M6's boxes ticked with the date, or M6 amended/retired in place with the reason

## Comments

- 2026-09-07, shared reference built: `scripts/color_components.py` paints top-20
  components + legend PNG. OpenMVS side: 16 components — O01 is rig (326 cm²),
  O02–O11 are the ten sherds (18–100 cm²), O12+ specks. 2DGS side S01–S20 all
  large (25–254 cm², no sherd-scale separation — sherd+steel webbing suspected).
  Files in `2dgs/output/A03_sherds/numbered/`, pulled to `artifacts/2dgs-a03/`.

- 2026-09-07, conservator eye (CloudCompare, boxed mm mesh): some sherds read
  OK-ish, some never formed as sherds at all. First completeness failure of the
  trial — recorded before any number. Component inventory same day: 50
  components (post-filter cap), largest 415/353/343 cm² down through sherd-scale
  40–90 cm² pieces spread ±250 mm — size alone cannot separate clay from rig
  steel; cause (mask gaps vs clamp occlusion vs depth noise) goes to the depth
  probe + mask audit, not to this count.

- 2026-09-07, verdict work: 2DGS mesh scaled to mm (`fuse_post_mm.ply`
  ×373.73332518281325 + sidecar; same sparse frame as MILo so the plate factor
  transfers — reasoning recorded in the sidecar). Submitted render rerun 30207590
  (short, fixed PYTHONPATH) and compare 30207591 (2DGS-vs-OpenMVS `dense_fixed`
  refined, short 2h, roles: 2DGS as --milo). Second compare (2DGS-vs-MILo-boxed)
  follows after outputs are moved aside — the script hardcodes one out dir, so
  no parallel runs. Polls running on both.
