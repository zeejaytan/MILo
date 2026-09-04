# What we are trying to establish with MILo

**This project is about getting the sherds into the computer at all.** Everything in GARF,
TORA, PF++ and SfS++ assumes a mesh exists and is right. MILo (and the COLMAP → OpenMVS
route beside it) is where that assumption is made or broken — so a failure here does not
look like a reconstruction failure downstream, it looks like the *method* failing.

This folder is **state, not a log**. Edit a line when it turns out wrong; git holds the
history. The runs live in [`../docs/notes/`](../docs/notes/).

Prefix **`M`**, permanent. Numbers are never reused. **M4 is next.**

**M3's blocking half is done** (2026-09-04) — `compare_meshes.py` no longer reports
millimetres it cannot stand behind, so M1's route comparison can now be measured on the
same ruler, and every capture now states where its millimetres come from. What remains in
M3 is one bench measurement against a caliper and one section picture, neither of which
blocks anything.

**M1 is the one to do next.** Both its first two boxes are cheap and unblocked, and the
second one — what OpenMVS already achieves on A03 — decides whether lifting MILo's
extraction ceiling is worth doing *for this material*.

| # | Question | Status | Blocked by |
|---|---|---|---|
| [M1](M1-resolution-the-material-needs.md) | Can either route reach the resolution a break face needs? | open — the authors' DTU route is closed, the ceiling may be liftable | none (was M3; lifted 2026-09-04) |
| [M2](M2-does-masking-eat-the-break-face.md) | Does masking the clamps destroy the thing we are trying to measure? | open — at the limit | none |
| [M3](M3-is-the-mesh-at-true-scale.md) | How do we know a mesh is at true scale? | open — **118 of 118 captures state a scale source** (117 plate, 1 board); what is left is a caliper round-trip and a section picture | none |

## What is established

| Claim | Weight | Source |
|---|---|---|
| **The authors' DTU extraction route is closed** — the conservator judged the mesh quality unacceptable for this material, 2026-09-01. | 1 capture (A03), conservator's judgement | `docs/notes/A03_DTU_EXTRACTION_RESULT.md` |
| Masked depth fusion worked: ten sherds, correctly sized, rig gone — but the silhouette cull then deleted every vertex. | 1 capture | ibid. |
| Finest achievable voxel was **0.822 mm** against roughly **0.21 mm** the photographs support — about a 4× shortfall. | 1 capture | ibid. |
| The 32,768-block cliff is **per extraction call**, so per-sherd tiling should reach about **0.45 mm**. The ceiling is liftable. | analysis, not yet run | ibid., addendum 2026-09-02 |
| A 6-pixel mask shrink is **at the limit** on fracture ridges; the clamp-contact surface is still unobserved. | 1 tree (A03) | `docs/notes/A03_BENT_SOLVE_AND_CLAMP_ARTEFACTS.md` §3 |
| Horns on mid-size sherds came from `Densify` mixed pixels at the clamp edge (~0.6 mm strip), **not** from `RefineMesh`; horn points are low-view outliers. | 1 capture (03072025/N01) | `docs/notes/03072025-N01_TAIL_FIX.md` |
| The turntable marker is **unusable before 2025-07-03 N01** — **59 of 118 captures** have a usable marker (19 in 2025 from N01 onward, all 40 in 2026). This is a claim about **alignment**, not scale. | capture record, all captures | `docs/reference/scanning-record.json` |
| **A usable marker is not a scale source.** The board is the ruler for **one** capture (N01, the only derived reference); the base plate is the ruler for the other 117, declared once per season at the top of each sheet. **118 of 118 captures state a source — the corpus is not halved**, and the earlier "59 of 118 are metric" was a marker count wearing a scale count's name. | capture record, all captures; the record's own words (*"Use base as scale, marker on turntable for alignment"*) | `.scratch/scale-provenance/issues/02`, commits `92772e8`, `8ed9c29` |
| The metric route is **built and verified**: board pitch measured with a ruler on the physical sheet at 40 mm, 2026-08-23. The board is the tighter **instrument** (lattice rms 0.196 mm, pitch SD 0.0146 mm) but the **looser ruler** — its absolute size is one ruler reading, ±1.25%, against the plate's long edge at 0.42%. Deriving more board references buys repeatability, not accuracy. | 1 capture (N01) | `docs/notes/2026-08-22-turntable-markers.md` §8; corrected 2026-09-04 |
| The **N01 Metashape chunk is 1.2–1.4% too large** — 1.2–1.4 mm on a 100 mm sherd — from one misplaced click. Broken measurement, not broken method. | 1 capture (N01) | ibid. §8 |
| The blue plate is **190 × 130 mm as recorded**, confirmed by two routes that never touch Metashape, so **A01–A04 need no correction**. | 3 trees | ibid. §10 |
| **`compare_meshes.py` reported a millimetre figure that was not in millimetres** — `frac_within_0.5mm` compared distances against a raw 0.5 in whatever units the mesh held. A broken measurement, not a broken method; it never reached a published number. Fixed and gated 2026-09-03/04. | read from the file, then reproduced: the same sphere pair in metres claimed **100.0%** of its surface within 0.5 mm | `.scratch/scale-provenance/issues/01`, commits `41b96ce`, `7e7bdf8` |
| A mesh with no scale sidecar is now **refused rather than measured** — exit 2 unknown units, exit 3 units disagree, `--shape-only` for the unit-free half. Proved able to refuse, not only observed to pass. | 20 assertions on synthetic fixtures; verified against A02's real sidecars and against a real derived mesh (`milo_mm_cropped_to_rig.ply`) that has none | ibid. |

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
