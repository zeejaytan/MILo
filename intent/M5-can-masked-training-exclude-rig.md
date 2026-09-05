# M5 — Can both-sides-plus-alpha training exclude the rig without eating the rim?

**Status:** open — probe GO (see below); full-pair scoring (ticket 04) pending · **Blocked by:** none

## Why it matters

Training unmasked grows the rig alongside the clay, and every extraction path inherits
steel. The one training-time mask tried painted background over 0.6–0.9 mm of break
face and was removed. The published construction (mask render *and* photograph, plus a
background loss on alpha outside the mask) costs ~3% shape on its benchmark — but that
benchmark's masks are tight with sporadic errors, while ours erode 6 px on every view
along the edge reassembly reads, the paper's stated uncovered case. If the rim survives,
rig exclusion moves to training time and no extraction path ever sees steel. If the
erosion carves, training-time masking stays closed with numbers attached.

## Done when

- [x] Probe pair verdict (2026-09-06): band alpha outside 0.0008–0.0037 (tripwire 0.2
      never threatened); 6 rim-band pairs hold fracture relief with no 0.6–0.9 mm
      recession. GO. Bonus: control masked-PSNR on held-out clay swings 10–28 dB
      (median 18.2) vs masked 20–25 (median 23.9) — unmasked training fails novel
      views on ~1/3 of held-out angles; masked holds all 21.
- [ ] Full A/B deltas (if the probe survives): break-face arc agreement in mm on 2–3
      edges, flat-wall noise in mm on the same boxes, held-out masked rendering deltas
- [ ] Conservator eye sign-off beside the numbers; whole-object chamfer never scores this
- [ ] Clamp-contact faces either observed by re-mount or written down as permanently
      unobserved with the consequence for joins that cross them (shared with M2)

## Gate / stop condition

If band alpha drains below 0.2 with receding rims at probe, or arc recession approaches
the 0.6–0.9 mm erosion width at full runs, stop: training-time masking is hostile to clay
rims and rig exclusion stays a fusion/extraction-time operation. If arc loss is a material
fraction of a break face either way, M2's fieldwork gate rules — the mount changes and no
loss recovers it. This is a claim about the method on this material (type 1) unless the
numbers say otherwise.

## Source

`docs/notes/2026-09-06-masked-milo-training.md` (construction, rim analysis, DTU costs);
`docs/notes/2026-09-05-mask-fragility-3dgs-vs-milo.md` §§1–2; `.scratch/masked-training/`
spec + tickets 01–04; probe job 30090865. Related: M2 (masking vs break face, fieldwork
gate), M1 (whether any of this is worth doing for this material).
