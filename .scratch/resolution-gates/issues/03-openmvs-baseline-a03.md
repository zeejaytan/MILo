# 03: OpenMVS baseline on A03, same ruler

**What to build:** M1's second box — what the route beside MILo already achieves on A03,
measured through `compare_meshes.py` (which refuses unscaled meshes per ADR-0001) plus
break-face close-up renders at a resolving view.

**Answers:** M1

**Blocked by:** None (can start immediately).

**Status:** ready-for-agent

- [ ] OpenMVS mesh and MILo mesh compared on the same ruler (scale sidecars checked,
      units agree before measuring — never compare before checking)
- [ ] Flat-surface noise in **mm** for both routes on A03, stated beside the A02 figures
      (OpenMVS 0.186 mm vs MILo-family 0.485 mm) for continuity
- [ ] Break-face close-up renders for both routes at a view resolving ~0.2 mm ridges
      (whole-sherd views do not count — they have misled repeatedly)
- [ ] M1's second box ticked with the date

## Comments

- 2026-09-06: both routes scaled on the node with sidecars at the same factor
  (373.733 mm/unit, blue plate): `output/17062025/A03/mesh_mm.ply` (MILo native,
  1.4M verts) and `dense_masked/scene_refined_mm.ply` (OpenMVS refined, 464k
  verts). Follows the A02 method (`dense_masked` refined, learnable-SDF MILo).
  Compare itself needs a GPU (nvdiffrast) → Slurm `milo_compare.slurm`, awaiting
  submission approval.
- 2026-09-06: approved, submitted as job 30131757 (partition auto-bumped to
  gpu-a100: 128G exceeds the short partition). Boxes stay open until numbers +
  renders land and are read against the ~1 mm bar in 04.
- 2026-09-06: job 30131757 FAILED in 1:50 — compare refused, correctly, but for
  the wrong stated reason. Node measurement (`.scratch/alt-extractors` ticket
  01): MILo `mesh_mm.ply` spans ~983 mm, OpenMVS refined spans ~643 mm, boxes
  barely overlap — different content in different frames, not a units mismatch
  (both sidecars claim the same factor). Next step is a common-box crop, not a
  resubmit; parked for user confirm.
