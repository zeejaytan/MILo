# M1 — Can either route reach the resolution a break face needs?

**Status:** open — the authors' route is closed; the ceiling looks liftable
**Blocked by:** none. The second box was blocked on [M3](M3-is-the-mesh-at-true-scale.md)
— `compare_meshes.py` could report a millimetre figure that was not in millimetres, and
"the same ruler" is the whole point. **Lifted 2026-09-04**: the script now refuses a mesh
that cannot state its units, and A02 and A03 both carry a scale sidecar, so the OpenMVS
comparison can be run on the same ruler

## Why it matters

A break face is the surface a reassembly model reads. If the mesh smooths it below the
scale of its ridges, every downstream result is about a smoothed object, and the model
will be blamed for something the scanner did. This is failure mode 2 — **the measurement
was broken** — and it is the one that has already faked a finding here once.

The numbers as they stand: the finest voxel reached was **0.822 mm**; the photographs
support roughly **0.21 mm**. That is about a fourfold shortfall — on a wall of 5–12 mm, a
feature four times coarser than the photographs can see is a real loss, not a rounding
detail.

## What is already known

- The authors' DTU extraction route is closed on quality grounds (2026-09-01).
- The 32,768-block cliff is **per extraction call**, so per-sherd tiling should reach about
  **0.45 mm** — better, still not 0.21 mm.

## Done when

- [ ] **Cross-view depth disagreement measured in millimetres** on at least one capture.
      This is the honest resolution floor; the voxel size is only what we asked for
- [ ] **What OpenMVS already achieves on A03**, measured the same way, so the two routes
      are compared on the same ruler. **Scale is now established by the tool, not by
      hand**: `compare_meshes.py` refuses a mesh without a sidecar rather than measuring
      it, so this box can no longer be ticked against an unscaled mesh — see
      [M3](M3-is-the-mesh-at-true-scale.md)
- [ ] A stated requirement in millimetres: what a break face actually needs, argued from
      the ridge scale we can see in the photographs, not from what the tool can deliver
- [ ] Meshes rendered at a view that resolves ridges — a whole-sherd view looks fine at
      every resolution and has already misled here four times running

## Gate

If OpenMVS already meets the stated requirement, MILo tiling is **not worth doing for
this**, whatever its merits otherwise. Write that down and stop, rather than lifting a
ceiling nothing is pressing against.

## Source

`docs/notes/A03_DTU_EXTRACTION_RESULT.md` and its 2026-09-02 addendum;
`docs/notes/A02_MESH_METHOD_COMPARISON.md`.
