# M10 — LaMa-filled rig pixels keep sherd density through the crop (spec)

**Answers:** M10 (MILo project — this spec is the plan tickets 01–05 execute).

**Prior work searched:** GitHub "advimman/lama", "LaMa inpainting big-lama"; Hugging Face "smartywu/big-lama". Found: https://github.com/advimman/lama (pinned 786f5936b27fb3dacd2b1ad799e4de968ea697e7) + weights https://huggingface.co/smartywu/big-lama/resolve/main/big-lama.zip — reused, not rebuilt (PGSR tickets 01, 02, 09 + calibration).

## Problem statement

MILo trains a beautiful full scene on A03 — rig, clay, everything — but the sherd-only crop comes out coarse, as if clay drained in the crop. Working hypothesis: rig/clamps occlude sherd surface in many views, so those patches reach surfacing thinly observed or hollow and the cut-away fills coarsely. Painting rig pixels with LaMa *before* training would give the surface something to stand on in every view, so the crop keeps clay.

Plain terms: where the clamp covers pottery, cameras see steel instead of clay. Test whether showing training plausible clay there (invented surface, clearly labelled, never scored) leaves cut-out sherds denser and truer without moving break edges a join reads.

## Decisions (interview 2026-10-16, all recommended options taken)

- Capture: A03 one-capture A/B (`2025-06-17/A03`, photos `/data/gpfs/projects/punim2657/Rabati2025/17062025/A03/`, 165 files / 164 registered; dataset `/data/gpfs/projects/punim2657/MILo/data/17062025/A03_sherds/`, masks `A03_erode0` 164 PNGs, coverage mean 2.28%).
- Gate authority: mechanism check first; coarse patches NOT coinciding with occlusion → stop before filling, re-diagnose training-time drain (M5 lesson).
- Eye: both-arm ridge-resolving close-ups staged in `visual-qa/`, verdict blocks on conservator eye (`Needs-eye:` on ticket 05).
- Fill scope: rig/clamp/steel face pixels only, at full photo resolution, per-view independently. Break pixels never filled (break inside sherd mask; clamp sits on face only). Jaw-contact (unseen-in-all-views) excluded from fill and scoring. Fill goes into photographs, never into a training mask (2026-08-24 finding stands). Filled areas flagged and excluded from every mm score (demonstrated, not painted).
- Pins reused: `advimman/lama@786f593`, big-lama weights at `/data/gpfs/projects/punim2657/PGSR/lama_trial/big-lama/big-lama/{config.yaml,models/best.ckpt}`, env `lama02` (MILo env lacks albumentations; pinned 0.5.2 incompatible). Narrow-band: complement of `A03_erode0`, 0px dilation, no feather, 3200x2133 NEAREST, no cross-view propagation. Command: `bin/predict.py model.path=<big-lama> indir=<image.png + image_mask001.png> outdir=<outdir>` with `TORCH_HOME` + `PYTHONPATH=lama_trial/lama`. Calibration transfers (structured content continues, 8.60/16.50 vs 5.51/6.98 same order). PGSR R2 verdict: reconstruction failed, fill unjudged, LaMa acquitted — pins transfer.
- Trains: fresh paired A/B, identical seed/config/iterations (existing `A03_nomask` seed unrecorded → cannot exact-resume; ticket 03 pins determinism given MILo train exposes no seed arg). Canonical flags: `train.py -s -m -i -r 1 --eval --imp_metric indoor --rasterizer radegs --dense_gaussians --decoupled_appearance`, 30k iters, `configs/fast` + `cfg_args` merge.
- Extraction: same-voxel both arms, voxel + band stated in mm. Scale `mm_per_unit 373.7333` (±1.4% bar disagreement); `markers_usable false` (scale from 190x130mm base). Prior ceiling 0.0022u = 0.822mm / ±6.58mm / 32,209 blocks (0.002u = 0.75mm overflows 32,768 cliff). Existing `mesh_sherds_mm.ply` was carved with old dilated masks → re-extract clean erode0 baseline, do not reuse as evidence.
- Measures: density as counts (verts/faces/per-cm2 via `mesh_report.py` / `render_mesh.py`) AND relief in mm (surface_disagreement median/p90/p99/max + frac-within-0.5/1mm; raking + 10mm bar) stated separately — smooth fake must not pass. Break-face arc agreement in mm; any break move = contamination, trial stops (ticket 04 must pin the hook: `wall_chords`/`wall_thickness`/`surface_disagreement` candidates only — no `break_arc` function exists).
- Second capture scoped only on clay-with-break-untouched + flag-honoured success. Otherwise retire NO; LaMa stays visualisation-only on MILo.
- Complement-mask verdict (2026-10-17, ticket 04): filled arm 0 verts incl. 4x-band diags both devices vs control 57,632 — NO-GO, retired at one-capture weight.
- Rig-only variant (user decision 2026-10-17): remove the rig, not the background — inpaint mask = rig pixels only, studio background byte-identical. Separate treatment, own chain (06 → 07 → 08), judged on its own; the complement NO stands regardless.

## Done when (from intent, unchanged)

- Mechanism check: coarse patches coincide with rig-occluded pixels (occlusion map from existing masks) — fill only if they do.
- Pinned LaMa fill of rig/clamp pixels at full photo resolution on A03; break + permanent contacts excluded.
- A/B trains identical seed/config/iterations: filled vs unmasked control.
- Same-voxel extraction both arms, voxel and band in mm.
- Density counts AND relief mm separately; break-arc mm; break move stops trial.
- Filled-area flag written and honoured downstream; filled regions excluded from scoring.
- Sherd close-ups both arms + conservator eye sign-off.

## Stop conditions

- No coincidence → stop before fill.
- No density gain, break moves, or wall roughens clearly vs control → retire NO.
- Density as smooth fake → retire NO at one-capture weight; no second capture.
- Clay + break untouched + flag honoured → keep; only then scope capture two.

## Ticket order (sequential — same data/files)

01 mechanism-occlusion-check → 02 pinned-lama-fill → 03 paired-ab-trains → 04 same-voxel-extract-measure → 05 eye-qa-writeback → 06 rig-only-fill → 07 rig-only-train → 08 rig-only-extract-measure. One finished ticket per commit; judgement (intent writes, verdicts, Needs-eye) stays with the session.
