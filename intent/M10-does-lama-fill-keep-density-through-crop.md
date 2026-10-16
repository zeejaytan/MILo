# M10 — Does LaMa-filled rig pixels let MILo keep sherd density through the crop?

**Status:** open · **Blocked by:** none · **Effort:** roughly 1 week (pinned fill, one-capture A/B on existing data)

## Why it matters

MILo trains a beautiful full scene — rig, clay, everything. But the moment just the sherds are cut out of it, they come out coarse, as if the clay drained away in the crop. The working hypothesis: the rig and clamps hide parts of the sherd surface from the cameras, so those patches arrive at the surfacing step thinly observed or hollow, and the cut-away mesh fills them in coarsely. Painting the rig pixels back in with LaMa *before* training would give the sherd surface something to stand on in every view — so the crop keeps clay instead of draining.

Plain terms: where the clamp covers the pottery, the cameras see steel instead of clay. The test is whether showing the training plausible clay in those spots (a fraction of a millimetre of invented surface, clearly labelled as such) leaves the cut-out sherds denser and truer, without moving the break edges a join reads.

## Opinion before acting (workspace rule — researched, then stated)

Worth doing **for this**, with the mechanism check first. The fill setup is proven and reusable, not to be rebuilt: pinned `advimman/lama@786f593` + big-lama weights, narrow-band construction that keeps views clean, and a calibration showing it completes structure properly (PGSR tickets 01, 02, 09). And MILo is the right stage for the question PGSR could not answer: full MILo scenes already hold faces, so the fill gets judged through a reconstruction that can keep one.

Three cautions, all load-bearing. First, M5's lesson: if the coarseness comes from training *draining* clay (background loss, pruning) rather than from missing observations, extra pixels change nothing — so the first box confirms the coarse patches sit where the rig occluded, before any fill runs. Second, filled pixels are invented clay by construction: rig sits on face only, so break pixels are never filled, and filled areas are flagged and excluded from every millimetre score. Third, the 2026-08-24 finding stands — MILo needs the full picture for training, so the fill goes into the *photographs*, never into a training mask.

## Done when

- [x] Mechanism check (done 2026-10-16, ticket 01, job 33166058 COMPLETED): coarse patches coincide with rig occlusion — piece 2: 463.0 mm open edge, 276.5 mm (60%) at vis<0.25, 427 mm hole on steel (0/667) vs clay (548/667), render-verified by lead; top-10 36% occluded; P3 exception noted (442 mm holes, only 9.3 occluded) — fill unlocked
- [x] Pinned LaMa fill (done 2026-10-16, ticket 02, fill 33167281[0-7] + verify 33171383 all COMPLETED): 164/164 views; outside-mask Δ=0, break-touch 0 px, 164 flags; jaw-contact list empty (0 verts unseen in all 143 train views); lead eye-check confirms no mask leak — soft LaMa ghosts + retextured background correctly flagged, carried as known caveats — A/B unlocked
- [x] A/B trains (done 2026-10-16, ticket 03, 33192555 + 33192982 COMPLETED): identical seed(0-by-construction)/config, 18k iters (configs/fast overrides 30k default — ticket wording corrected); control 225k Gaussians loss 0.047 vs filled 8.3k loss 0.081 — strong pixel-driven divergence, judged at extraction, not rerun
- [ ] Same-voxel extraction both arms, voxel and band stated in **millimetres**
- [ ] Density as counts (Gaussians, verts, footprint in mm) AND relief in mm, stated separately — a finely-sampled smooth fake must not pass
- [ ] Break-face arc agreement in **mm**; any break move is contamination, trial stops
- [ ] Filled-area flag written and honoured downstream (demonstrated, not painted); filled regions excluded from mm scoring
- [ ] Sherd close-ups at ridge-resolving views, both arms, plus conservator eye sign-off

## Gate / stop condition

- Coarse patches do NOT coincide with occlusion → stop before filling; the drain is elsewhere (training-time), re-diagnose.
- No density gain, or break moves, or wall roughens clearly vs control → retire NO; LaMa stays visualisation-only on MILo.
- Density returns as smooth fake on the fill → retire NO at one-capture weight; do not fund a second capture.
- Density returns as clay with break untouched and flag honoured → keep, and only then scope the second capture.

## Source

User request 2026-10-16 (MILo scene great, sherd crop coarse; fill the gap with LaMa); PGSR lama-face-fill spec close + R2 verdict 2026-10-16 (reconstruction failed, fill unjudged; pins and calibration transfer); [M5](M5-can-masked-training-exclude-rig.md) (drain mechanism); [M4](M4-can-rig-gaussians-be-pruned-after-training.md) (pruning trade); [M1](M1-resolution-the-material-needs.md) (~1 mm requirement); user decision 2026-10-05 (LaMa for clamp-face holes and coarseness); 2026-08-24 finding (MILo needs the full picture; masking hurts mesh generation).
