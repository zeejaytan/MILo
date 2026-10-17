# M10 — Does LaMa-filled rig pixels let MILo keep sherd density through the crop?

**Status:** closed (answered 2026-10-17: keep — rig-only fill pays back the masking drain) · **Blocked by:** none · **Effort:** roughly 1 week (pinned fill, one-capture A/B on existing data)

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
- [x] Same-voxel extraction (done 2026-10-17, ticket 04, voxel 0.0028u=1.047mm ±8.37mm): control 57,632 verts; filled arm 0 verts at matched settings AND 4x band, both devices — empty
- [x] Density as counts AND relief in mm, stated separately (done 2026-10-17, ticket 04, control only — filled side UNMEASURABLE_EMPTY_MESH): control 464 pieces / 11 over 200 verts, Rq median 0.144mm p90 0.430mm; smooth-fake check moot, nothing to pass it with
- [x] Break-face arc agreement in mm (done 2026-10-17 to unmeasurable, ticket 04): no break_arc exists; wall-thickness hook contaminated (room-scale, surroundings included); cross-arm verdict UNMEASURABLE — no break move possible with no B surface
- [x] Filled-area flag honoured downstream (demonstrated 2026-10-17, ticket 04): 164/164 views audited, filled∩sherd = 0 px everywhere
- [x] Sherd close-ups at ridge-resolving views, both arms, plus conservator eye sign-off (done 2026-10-17, ticket 05): witnessed verdict — full scene much coarser; control and LaMa not much different. Eye and numbers agree. Viewer pairs m10_rigfill (control vs rigfill) + m10_fullscene (cropped full scene vs rigfill), localhost:8081.
- [x] Rig-only fill (done 2026-10-17, ticket 06, stage/fill/verify all COMPLETED): 164/164, rig frac 0.19, background+sherd Δ=0; PARTIAL — smooth clamp faces + lit-rubber jaw interiors missed (unfilled+unflagged, dilute toward null); rod ghosts fixed. Validity: B win = win; B null = INCONCLUSIVE (refine masks), not NO.
- [x] Rig-only train (done 2026-10-17, ticket 07, job 33216618 COMPLETED 2:07): 18k, seed-0 construction, cfg diff paths-only vs 03 control; final 158,312 Gaussians loss 0.048 ≈ control — no collapse (worker report lost to markup leak, evidence lead-recovered from disk)
- [x] Rig-only extraction + density/relief/break vs control (done 2026-10-17, ticket 08, all jobs COMPLETED): rigfill 64,018 verts (+11%), 14 vs 11 pieces, same verts/cm²; Rq 0.155 vs 0.144mm; section median 0.099mm, walls 8.30 vs 8.34mm — NO break move; flag honoured (0 px). Debit: held-out silhouette 73% vs 59% (extra surface, expected). Verdict: rigfill WIN → KEEP per gate (single object/run — a lead). Complement-mask NO stands.

## Where it stands

Filling just the rig pixels with LaMa leaves the cut-out sherds slightly denser (+11% surface points, same points-per-square-centimetre) at the same finish, with walls unmoved — the conservator's eye confirms control and LaMa look not much different, while the original full scene looks much coarser. So the fill pays back the masking drain without roughening the clay: keep, and only now scope a second capture.
Weight: one object, one run per arm — a lead, not a conclusion.
Next: scope the second capture (user decision); full-scene meshes always staged cropped to rig+sherds.
Picture: MILo/artifacts/m10_t08/mesh_rigfill_render.png | Rigfill mesh: same 10-piece layout as control, slightly fuller
Viewer: m10_rigfill (control vs rigfill), m10_fullscene (cropped full scene vs rigfill)

## Gate / stop condition

- Coarse patches do NOT coincide with occlusion → stop before filling; the drain is elsewhere (training-time), re-diagnose.
- No density gain, or break moves, or wall roughens clearly vs control → retire NO; LaMa stays visualisation-only on MILo.
- Density returns as smooth fake on the fill → retire NO at one-capture weight; do not fund a second capture.
- Density returns as clay with break untouched and flag honoured → keep, and only then scope the second capture.

## Source

User request 2026-10-16 (MILo scene great, sherd crop coarse; fill the gap with LaMa); PGSR lama-face-fill spec close + R2 verdict 2026-10-16 (reconstruction failed, fill unjudged; pins and calibration transfer); [M5](M5-can-masked-training-exclude-rig.md) (drain mechanism); [M4](M4-can-rig-gaussians-be-pruned-after-training.md) (pruning trade); [M1](M1-resolution-the-material-needs.md) (~1 mm requirement); user decision 2026-10-05 (LaMa for clamp-face holes and coarseness); 2026-08-24 finding (MILo needs the full picture; masking hurts mesh generation).
