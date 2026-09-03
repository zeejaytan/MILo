# What we are trying to establish with MILo

**This project is about getting the sherds into the computer at all.** Everything in GARF,
TORA, PF++ and SfS++ assumes a mesh exists and is right. MILo (and the COLMAP → OpenMVS
route beside it) is where that assumption is made or broken — so a failure here does not
look like a reconstruction failure downstream, it looks like the *method* failing.

This folder is **state, not a log**. Edit a line when it turns out wrong; git holds the
history. The runs live in [`../docs/notes/`](../docs/notes/).

Prefix **`M`**, permanent. Numbers are never reused. **M4 is next.**

| # | Question | Status | Blocked by |
|---|---|---|---|
| [M1](M1-resolution-the-material-needs.md) | Can either route reach the resolution a break face needs? | open — the authors' DTU route is closed, the ceiling may be liftable | none |
| [M2](M2-does-masking-eat-the-break-face.md) | Does masking the clamps destroy the thing we are trying to measure? | open — at the limit | none |
| [M3](M3-is-the-mesh-at-true-scale.md) | How do we know a mesh is at true scale? | open | none |

## What is established

| Claim | Weight | Source |
|---|---|---|
| **The authors' DTU extraction route is closed** — the conservator judged the mesh quality unacceptable for this material, 2026-09-01. | 1 capture (A03), conservator's judgement | `docs/notes/A03_DTU_EXTRACTION_RESULT.md` |
| Masked depth fusion worked: ten sherds, correctly sized, rig gone — but the silhouette cull then deleted every vertex. | 1 capture | ibid. |
| Finest achievable voxel was **0.822 mm** against roughly **0.21 mm** the photographs support — about a 4× shortfall. | 1 capture | ibid. |
| The 32,768-block cliff is **per extraction call**, so per-sherd tiling should reach about **0.45 mm**. The ceiling is liftable. | analysis, not yet run | ibid., addendum 2026-09-02 |
| A 6-pixel mask shrink is **at the limit** on fracture ridges; the clamp-contact surface is still unobserved. | 1 tree (A03) | `docs/notes/A03_BENT_SOLVE_AND_CLAMP_ARTEFACTS.md` §3 |
| Horns on mid-size sherds came from `Densify` mixed pixels at the clamp edge (~0.6 mm strip), **not** from `RefineMesh`; horn points are low-view outliers. | 1 capture (03072025/N01) | `docs/notes/03072025-N01_TAIL_FIX.md` |
| The turntable marker is **unusable before 2025-07-03 N01**. | capture record | `docs/notes/2026-08-22-turntable-markers.md` |

## Before writing any more extraction code

Two measurements come first, and both are cheap:

1. **Cross-view depth disagreement in millimetres** — the real resolution floor, as opposed
   to the voxel size we happen to be asking for.
2. **What OpenMVS already achieves on A03** — if the route beside this one already clears
   the bar, lifting MILo's ceiling is worth doing but not worth doing *for this*.

That distinction — worth doing, versus worth doing for this — is the standing workspace
rule, and this is the case it applies to most directly right now.

## Related

`U1` (judging without an answer key) and `U6` (Rabati access) in
[`../../intent/`](../../intent/). Sister repo for the photogrammetry route:
`zeejaytan/pottery-photogrammetry`.
