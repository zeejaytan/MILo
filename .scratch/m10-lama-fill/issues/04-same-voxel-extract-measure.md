# 04: Same-voxel extraction + density / relief / break measures

**What to build:** both arms surfaced identically in millimetres, then judged as counts, relief, and break stability — with invented clay fenced out of every score.

**Answers:** M10

**Blocked by:** 03-paired-ab-trains.

**Status:** resolved

- [x] Same-voxel extraction both arms, voxel + band stated in mm (used 0.0028u = 1.047mm / ±8.37mm / 29,857 blocks, ~9% under the 32,768 cliff; 0.0022u gave 35,366 and 0.0024u 33,292 — both refused cleanly. Prior ceiling noted in-ticket superseded); scale `mm_per_unit 373.7333` via `measurement.env` FACTOR + `scripts/apply_scale.py --force-factor` (`*_mm.ply`); `markers_usable false`, base ruler (scale edges disagree 1.38%, mean taken)
- [x] Density as counts (`mesh_report.py --expect-pieces 10`, `render_mesh.py` verts/faces/extent/per-cm2) AND relief in mm (`compare_meshes.py surface_disagreement` + local-plane Ra/Rq λc=5mm stated non-ISO; `raking_render` + 10mm bar) stated separately — B unmeasurable (empty), recorded as UNMEASURABLE_EMPTY_MESH, not skipped
- [x] Break-face arc agreement in mm; hook pinned: NO `break_arc` function exists (verified) → nearest hook normal-ray wall thickness on A only, stated CONTAMINATED (room-scale 29.9mm median — mesh includes turntable surroundings via unmasked test views), NOT a sherd-wall value; cross-arm break verdict UNMEASURABLE (needs B surface)
- [x] Ticket-02 filled-area flag demonstrated honoured (164/164 views audited: flag-white frac mean 0.977, filled∩sherd = 0 px every view; 199,991/200,000 A-samples project to sherd); units/scale gate first; no ground-truth phrasing
- [x] Representative renders before/after at ridge-resolving views + viewpoint-proof numbers (probe triplets both arms, shared views; B mesh-render/compare/silhouette/closeup recorded NOT RUN — no B surface)

## Result (lead review, 2026-10-17) — ACCEPTED, headline NO-GO for the fill

Arm A: `mesh_ctrl_v0.0028_mm.ply`, 57,632 verts / 108,518 faces, extent 481mm (includes surroundings — contaminated, stated); 464 pieces, 11 over 200 verts (expected 10 sherds; top pieces 70-80mm span at ~135-148 verts/cm²); relief Rq median 0.144 / p90 0.430mm, Ra median 0.116 / p90 0.349mm. Arm B: NO MESH — 0 verts at matched settings on CPU:0 and CUDA:0, still 0 at 4x band (mult16/32 diags, lead-confirmed in log). Renders lead-viewed: A resolves the full rig crisply; B is a near-blank dark field with faint smudges (RGB std ~3 vs ~38). B's depths are flat mutually-contradicting walls → fusion carves everything away. Photo-metrics fine (PSNR 28.39) but no geometry: looks fine, measures nothing. Verdict class: the method genuinely failed on this input (claim 1), NOT a broken ruler — refutation (wider band ×4, both devices, identical emptiness) already run. Scope: single object, single run — a lead, not a conclusion. Precision: this retires the COMPLEMENT-mask repaint construction; a rig-only fill is a different, untested treatment. Evidence: `.../m10_ticket04/` (mesh + sidecar, m10_t04_score.json — lead-verified on disk, mesh_report, probe/, renders_ctrl/); extract 33201755 FAILED 1:0 exiting on B's empty fusion (A mesh valid), probe/diag/finals COMPLETED (33203222/33203722/33204982/33205443).
