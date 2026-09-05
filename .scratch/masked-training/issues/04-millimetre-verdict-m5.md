# 04: Millimetre verdict plus M5 write-back

**What to build:** the verdict package for M2 on the A/B pair — break-face arc deltas in mm on 2–3 edges (contact faces excluded), flat-wall noise deltas on the same boxes, held-out masked rendering deltas, rim close-ups at 0.10 mm/px or tighter for both runs, conservator eye sign-off beside the numbers, and the one-line write-back into intent M5 with a date. Whole-object chamfer is banned from this verdict.

**Answers:** M5

**Blocked by:** 03 (needs both trained models).

**Status:** claimed (extracting both verdict meshes, then arc/noise scoring)

- [ ] Arc agreement deltas in mm of arc per sampled edge, contact faces excluded throughout
- [ ] Flat-wall noise deltas in mm on the same boxes for both runs
- [ ] Held-out masked rendering deltas reported before any meshing claim
- [ ] Rim renders at 0.10 mm/px or tighter resolve the erosion band for both runs
- [ ] Human in the loop: conservator eye verification beside the numbers; M2 updated with the date whatever the outcome

## Comments — verdict meshes building (2026-09-06)

Native tet extractions submitted: job 30123272 (masked probe -> A03_probe_masked_mesh),
job 30123273 (control probe -> A03_probe_ctrl_mesh). Scoring (arc-mm, noise-mm, eye,
M5 write-back) runs when both land.

## Comments 2 — stale-cfg crash, resubmitted (2026-09-06)

Jobs 30123272/73 died in seconds: mesh_extract_sdf.py read args.keep_idx directly,
but the cfg_args copied from the pre-flag probe runs has no such attribute. Same
config-layer family as the read_config lesson — fixed with getattr defaults.
Resubmitted as 30125644 (masked) + 30125645 (control).

## Comments 2 — numbers in hand, eye pending (2026-09-06)

Verdict meshes: masked 276k verts / 10 clay pieces, control 2.6M verts incl. a
9.2 m room piece. Piece-1 box (65x63x73 mm from masked largest component):
masked 56,695 verts, control 38,768 verts inside.
Agreement (same-frame mm, symmetric nearest-neighbour): masked->ctrl median
0.41 mm, p90 1.29, 62.7% within 0.5 mm; ctrl->masked median 0.49, p90 10.7 (tail
is rig steel in the control box — expected, it models the clamp).
Roughness (3 mm local-plane RMS, 4k samples): masked median 0.11 / p90 0.29 mm;
control median 0.04 / p90 0.13 mm — CONFOUNDED: the control box holds polished
steel, so this does not rank clay surfaces; stated, not used.
Held-out masked-PSNR: masked median 23.9 dB (20–25 all views) vs control 18.2
(10–28, ~1/3 views failed). Six rim-band pairs viewed by agent: rig gone,
fracture relief intact, no rim recession. Conservator eye + M5 write-back pending.
