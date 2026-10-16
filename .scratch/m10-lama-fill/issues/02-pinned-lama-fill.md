# 02: Pinned LaMa fill of rig pixels at full resolution

**What to build:** filled photographs where steel becomes plausible clay, using only the proven pins — so the A/B trains stand on identical pixels except the fill.

**Answers:** M10

**Blocked by:** 01-mechanism-occlusion-check (fill only if coincidence shown; otherwise this ticket never runs).

**Status:** ready-for-agent

- [ ] Fill with pinned `advimman/lama@786f5936` + big-lama (`/data/gpfs/projects/punim2657/PGSR/lama_trial/big-lama/big-lama/{config.yaml,models/best.ckpt}`) in env `lama02`; command `TORCH_HOME=<gate> PYTHONPATH=lama_trial/lama <lama02 python> bin/predict.py model.path=<big-lama> indir=<image.png + image_mask001.png> outdir=<outdir>` (pad_out_to_modulo=8)
- [ ] Inpaint mask = complement of `A03_erode0` tight masks (clamp/rig/steel only), 0px dilation, no feather, per-view 3200x2133 NEAREST, no cross-view propagation; break pixels + jaw-contact (unseen-in-all-views) excluded
- [ ] Outside-mask `max|Δ| = 0.0` check on every view; full-res outputs named alongside `data/17062025/A03_sherds/images_masked/` inputs
- [ ] Filled-area flag written per view (which pixels are invented clay) in a form ticket 04 can honour downstream; flag excludes filled regions from all mm scoring
- [ ] No training-mask change (fill in photographs only); `sacct` recorded; heavy work on compute node / held allocation only
