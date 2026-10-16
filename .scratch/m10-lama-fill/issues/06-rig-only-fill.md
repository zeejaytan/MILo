# 06: Rig-only LaMa fill (background untouched)

**What to build:** filled photographs where ONLY rig pixels become plausible clay — the black studio background stays byte-identical. New treatment (user decision 2026-10-17); the ticket-02 complement-mask repaint stands retired.

**Answers:** M10

**Blocked by:** 04-same-voxel-extract-measure (complement construction NO-GO; rig-only is the follow-up treatment).

**Status:** resolved

- [x] Per-view rig mask = rig pixels only (steel rods/clamps/jaws, blue knobs, white plastic, rubber, blue base), MINUS `A03_erode0` sherd pixels (0px change at the sherd boundary, same as 02). Segmentation method + threshold stated in-ticket (e.g. luminance-based: background is near-black studio — state the exact rule, threshold value, and per-view rig-pixel fraction mean/range). Sherd edges protected: no fill bleed into sherd pixels (verified by filled∩sherd = 0).
- [x] Fill with the same pins as 02 (no rebuild): pinned `advimman/lama@786f5936` + big-lama (`/data/gpfs/projects/punim2657/PGSR/lama_trial/big-lama/big-lama/{config.yaml,models/best.ckpt}`) in env `lama02`; same predict.py command shape (pad_out_to_modulo=8), per-view 3200x2133 NEAREST, no cross-view propagation.
- [x] Background + sherd byte-identical: `max|Δ| = 0.0` over ALL pixels outside the rig inpaint mask, every view. Only rig-mask pixels may change. Accepted imperfections stated (white turntable ticks / marker squares if the luminance rule catches them — they are background furniture, not sherd occluders; quantify how many px).
- [x] Filled-area flag per view (= rig inpaint mask) in ticket-02 flag form for downstream exclusion; jaw-contact exclusion carried from 02 (empty list — recompute-or-reference stated).
- [x] Mask-overlay renders (mask on photo, 3+ views incl. one rod-against-sherd view like A31_1123) saved for LEAD eye-check before acceptance; `sacct` State/ExitCode recorded; heavy work on compute nodes only; outputs under new untracked `/data/gpfs/projects/punim2657/MILo/output/17062025/m10_ticket06/`; no tracked edits, no commit/push.

## Result (lead review, 2026-10-17) — ACCEPTED AS PARTIAL TREATMENT, ticket 07 unlocked

Jobs lead-verified COMPLETED 0:0 (stage-v1c 33211541, fill-v1c 33212622[0-7], verify-v1c 33216062). Numbers match verify.json: 164/164, outside-mask Δ=0, mask∩sherd=0, changed∩sherd=0, rig frac mean 0.194 (0.175-0.210) vs 02's ~0.98. Mask method: smooth-bg deviation (400x267 median-15, dev>22 OR lum<18 for black rubber, CC<64px dropped, dilate 5px, sherd re-subtracted) — global threshold proven impossible first (bg luminance spans 19-204 under the spotlight). Lead eye-check (overlay + filled + 2 full-res zooms, A31_1123): thin rods/clamps dissolved, background gradient intact, sherds crisp; NO rod ghosts (02's failure mode fixed). PARTIAL (lead-probed, not just reported): smooth mid-gray clamp faces remain unfilled+unflagged (worker caveat 1, confirmed); lead pixel-probe of top-jaw bbox (x1580-1920,y280-620): maskfrac 0.236, in-mask Δ=23.1, outmask Δ=0 — smooth lit-rubber jaw interiors missed, training as content like control. VALIDITY FRAMING (binding on 08): misses dilute the treatment toward null — they CANNOT fake a win (flagged fills excluded from scoring; unfilled rig = same as control). So: B win = win; B null = INCONCLUSIVE (refine masks, e.g. close-operation on enclosed smooth zones), NOT a NO-GO. Evidence: `.../m10_ticket06/` (images_filled/, masks_inpaint/, flags/, overlays/ incl. A31_1123, verify.json, per_view_verify.json).
