# 06: Rig-only LaMa fill (background untouched)

**What to build:** filled photographs where ONLY rig pixels become plausible clay — the black studio background stays byte-identical. New treatment (user decision 2026-10-17); the ticket-02 complement-mask repaint stands retired.

**Answers:** M10

**Blocked by:** 04-same-voxel-extract-measure (complement construction NO-GO; rig-only is the follow-up treatment).

**Status:** ready-for-agent

- [ ] Per-view rig mask = rig pixels only (steel rods/clamps/jaws, blue knobs, white plastic, rubber, blue base), MINUS `A03_erode0` sherd pixels (0px change at the sherd boundary, same as 02). Segmentation method + threshold stated in-ticket (e.g. luminance-based: background is near-black studio — state the exact rule, threshold value, and per-view rig-pixel fraction mean/range). Sherd edges protected: no fill bleed into sherd pixels (verified by filled∩sherd = 0).
- [ ] Fill with the same pins as 02 (no rebuild): pinned `advimman/lama@786f5936` + big-lama (`/data/gpfs/projects/punim2657/PGSR/lama_trial/big-lama/big-lama/{config.yaml,models/best.ckpt}`) in env `lama02`; same predict.py command shape (pad_out_to_modulo=8), per-view 3200x2133 NEAREST, no cross-view propagation.
- [ ] Background + sherd byte-identical: `max|Δ| = 0.0` over ALL pixels outside the rig inpaint mask, every view. Only rig-mask pixels may change. Accepted imperfections stated (white turntable ticks / marker squares if the luminance rule catches them — they are background furniture, not sherd occluders; quantify how many px).
- [ ] Filled-area flag per view (= rig inpaint mask) in ticket-02 flag form for downstream exclusion; jaw-contact exclusion carried from 02 (empty list — recompute-or-reference stated).
- [ ] Mask-overlay renders (mask on photo, 3+ views incl. one rod-against-sherd view like A31_1123) saved for LEAD eye-check before acceptance; `sacct` State/ExitCode recorded; heavy work on compute nodes only; outputs under new untracked `/data/gpfs/projects/punim2657/MILo/output/17062025/m10_ticket06/`; no tracked edits, no commit/push.
