# Does shrinking the mask eat the fracture?

Design note, 2026-08-20. Status: **run on A03.** Result recorded in
`A03_BENT_SOLVE_AND_CLAMP_ARTEFACTS.md` §3 “How far shrinking actually goes”.
Companion: that note.

## What this answers

Surface masks are shrunk by 6 pixels before the mesh is built, so clamp-straddling pixels never get a depth. Vertex counts and overall size said the sherds survived that. Those numbers cannot say whether the **break face** kept its ridges — a 6-pixel rim taken off a fracture edge is exactly the geometry a reassembly matcher reads.

This test looks at the photographs, at a scale where 6 pixels are obvious, and asks where the shrinking outline sits.

## Verdict, written before looking

On each crop:

- **Still on the clamp** → that amount is not enough *there*
- **On the outer wall, short of the break ridges** → that amount is usable
- **Across the break face, ridges inside the discarded rim** → that amount has gone too far *there*

6 pixels can be too little at the clamp and too much on a free break. If the pictures say that, the finding is “one number cannot serve both,” not a new default.

One tree is a lead, not a rule for every capture.

## Method

1. **Unshrunk masks, new folder.** One SAM 3 run with `--erode-surface 0`, written to `masks/17062025/A03_erode0`. Production `masks/17062025/A03` is not touched. Growing the current 6-pixel masks back does not restore eaten pixels, so they cannot be the source.
2. **Outlines, not tints.** From `masks_sherds`, shrink copies by 0, 2, 4, 6, 8, 12 pixels and draw them as coloured contours on the photograph. A filled overlay would hide the ridges.
3. **Crops that resolve 6 pixels.** Tight crop around one sherd, nearest-neighbour zoom so a 6-pixel step is many pixels on the picture. Whole-tree views are forbidden: they would hide the effect.
4. **Four crops, all A03:**
   - smallest piece, break facing the camera
   - smallest piece, clamp on it
   - larger piece, break facing the camera
   - that same larger piece at a clamp
5. **Scale.** A bar of 6 pixels (the current default) on every crop, plus millimetres when the camera solve gives a depth in that crop. 6 pixels is claimed ~1 mm; measure it on the crop, because a small sherd occupies fewer pixels and the same step is a larger bite.

## Out of scope

Other trees. OpenMVS rebuilds. Changing the production 6-pixel setting. Scoring by vertex count, extent, or chamfer distance.

## Result (A03, 2026-08-20)

Job **29448323**. Unshrunk masks in `masks/17062025/A03_erode0`. Pictures in
`artifacts/A03_metric/erode_overlay/` and Spartan
`MILo/output/17062025/A03_erode_overlay/overlays/`.

**Six pixels is already on the fracture, not a safety margin.** On these crops it is
**0.60–0.86 mm**, not ~1 mm.

| crop | 6 px | call |
|---|---|---|
| `large_break.png` (A35_1240) | 0.60 mm | 0–2 follow the ridge; 4 rounds the finest peaks; 6 bridges small crevices; 8–12 are a cartoon of the break |
| `small_piece.png` (A34_1222, ~30 mm) | 0.74 mm | same pattern |
| `pin_clamp.png` (A32_1140) | 0.86 mm | unshrunk outline already at the pottery; 6 px then eats pottery, not clamp |
| `small_prong.png` (A31_1115) | 0.75 mm | same millimetre bite as `small_piece` |
| `large_clamp.png` (A35_1239) | 0.61 mm | same as `large_break`; clamp jaws less clear than `pin_clamp` |

Discarded: `small_break.png` (A31_1102) — a sliver beside a knob, not a complete sherd.

Applied: 0–2 px usable; 4 px borderline; **6 px is the last amount that still resembles the
break**; 8 and 12 too far. Do not raise the default. If it changes, try 4, not 8.

This is a photograph-outline result on one tree. Not a rebuilt mesh. Not a rule for every
capture. The method is taking fracture-ridge pixels; the size numbers were the wrong
instrument.

## Where things go

| | |
|---|---|
| unshrunk masks | `MILo/masks/17062025/A03_erode0` (Spartan) |
| overlay script | `scripts/erode_fracture_overlay.py` |
| pictures | `artifacts/A03_metric/erode_overlay/` (fetched, gitignored) |
| result | `A03_BENT_SOLVE_AND_CLAMP_ARTEFACTS.md` §3 |
