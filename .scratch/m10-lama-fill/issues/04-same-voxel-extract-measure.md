# 04: Same-voxel extraction + density / relief / break measures

**What to build:** both arms surfaced identically in millimetres, then judged as counts, relief, and break stability — with invented clay fenced out of every score.

**Answers:** M10

**Blocked by:** 03-paired-ab-trains.

**Status:** ready-for-agent

- [ ] Same-voxel extraction both arms, voxel + band stated in mm (prior ceiling 0.0022u = 0.822mm / ±6.58mm / 32,209 blocks; 0.002u overflows the 32,768 cliff — stay clear and state what was used); scale `mm_per_unit 373.7333` via `measurement.env` FACTOR + `scripts/apply_scale.py --force-factor` (`*_mm.ply`); `markers_usable false`, base 190x130mm ~1%
- [ ] Density as counts (`mesh_report.py --expect-pieces 10`, `render_mesh.py` verts/faces/extent/per-cm2) AND relief in mm (`compare_meshes.py surface_disagreement` median/p90/p99/max + frac-within-0.5/1mm; `raking_render` + 10mm bar; glossary Ra/Rq with λc) stated separately — smooth fake must not pass
- [ ] Break-face arc agreement in mm; pin the hook in-ticket (candidates: `section_overlay.py wall_chords` / `compare_meshes wall_thickness` / `surface_disagreement` — no `break_arc` function exists); any break move = contamination, trial stops
- [ ] Ticket-02 filled-area flag demonstrated honoured (filled regions excluded from all mm scoring — show the exclusion, not a claim); units/scale gate first (`compare_meshes scale_decision`); no ground-truth phrasing (DTU result + traps)
- [ ] Representative renders before/after at ridge-resolving views + viewpoint-proof numbers; `sacct` + poll discipline as tickets 01–03
