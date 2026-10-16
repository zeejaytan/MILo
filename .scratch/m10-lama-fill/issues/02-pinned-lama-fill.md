# 02: Pinned LaMa fill of rig pixels at full resolution

**What to build:** filled photographs where steel becomes plausible clay, using only the proven pins — so the A/B trains stand on identical pixels except the fill.

**Answers:** M10

**Blocked by:** 01-mechanism-occlusion-check (fill only if coincidence shown; otherwise this ticket never runs).

**Status:** resolved

- [x] Fill with pinned `advimman/lama@786f5936` + big-lama (`/data/gpfs/projects/punim2657/PGSR/lama_trial/big-lama/big-lama/{config.yaml,models/best.ckpt}`) in env `lama02`; command `TORCH_HOME=<gate> PYTHONPATH=lama_trial/lama <lama02 python> bin/predict.py model.path=<big-lama> indir=<image.png + image_mask001.png> outdir=<outdir>` (pad_out_to_modulo=8)
- [x] Inpaint mask = complement of `A03_erode0` tight masks (clamp/rig/steel only), 0px dilation, no feather, per-view 3200x2133 NEAREST, no cross-view propagation; break pixels + jaw-contact (unseen-in-all-views) excluded
- [x] Outside-mask `max|Δ| = 0.0` check on every view; full-res outputs named alongside `data/17062025/A03_sherds/images_masked/` inputs
- [x] Filled-area flag written per view (which pixels are invented clay) in a form ticket 04 can honour downstream; flag excludes filled regions from all mm scoring
- [x] No training-mask change (fill in photographs only); `sacct` recorded; heavy work on compute node / held allocation only

## Result (lead review, 2026-10-16) — ACCEPTED, ticket 03 unlocked

First worker exited mid-ticket (staging done, fill never submitted); resume worker completed fill+verify. Jobs (all COMPLETED 0:0, lead-confirmed via sacct): stage 33166888, fill array 33167281[0-7] (~47-64 min/task CPU), verify 33171383. Numbers match verify.json on disk: 164/164 views, outside-mask max|Δ|=0, break-touch 0 px, 164 flags, inside_changed_frac_mean 0.999939, jaw-contact list EMPTY (0 verts unseen in all 143 train views — nothing to exclude). Held-out 21 eval views filled identically, no differential treatment. Evidence: `.../MILo/output/17062025/m10_ticket02/` (out/, images_filled/, flags/, verify.json, per_view_verify.json, jaw_contact_exclusion.json).

Lead eye check (A31_1123, input vs mask vs filled + 2 full-res zooms, artifacts/m10_t02_*): sherds intact; clamp jaws + rod replaced by soft LaMa ghosts (light rod-band remnant, dark jaw smudges, white edge halos) and the black studio background by dark-green texture. Mask crop confirms rod/jaw pixels were IN the fill region — no mask leak; ghosts are correctly flagged and excluded from scoring. Caveats carried to 04: (1) ghosts are the treatment's weak point — if B loses, suspect #1; they cannot fake a win (flag-excluded). (2) Background repaint (black→texture) is admitted only in the dilated band; part of the treatment, not a defect. Note: filled files are PNG bytes under .JPG names — ticket 03 must byte-handle accordingly.
