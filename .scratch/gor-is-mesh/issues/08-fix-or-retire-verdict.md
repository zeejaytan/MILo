# 08: Fix-or-retire verdict on the A03 wedge

**What to build:** the integrated verdict from 05–07, written back into M9 with a date: either a green-lit curated run with a hard exclusion budget, or retirement with the cause named.

**Answers:** M9

**Blocked by:** 05, 06, 07.

**Status:** resolved (M9 retired 2026-10-20 — verdict written back with one lead fix: tickets line closes 02/05/06/07 results-in plus 03/04 unexecuted)

- [x] Verdict integrates the three probes: trigger identified (name it) or unidentified (say so — the bounded series spent its budget)
- [x] Either: green-light for ONE curated full run with exclusion budget stated (8 total max per 02's stop rule, 4 already spent) — or retire the GOR-IS mesh route naming which of the three it is (method failed / ruler broken / reference wrong)
- [x] M9 updated with the verdict and date 2026-10-20 by lead; no second seed funded on a NO
- [x] No new GPU spend in this ticket; judgement stays here, not in a worker

## Verdict (worker 2026-10-20): RETIRE — method failed on this material

Trigger: UNIDENTIFIED at probe weight (bounded series spent its 2-leg budget).

- 05 autopsy: NO-COMMON-FEATURE across 12 views (4 killers vs 8 passing neighbours); steel-proxy max deviation 0.0004 — per-view content does not separate kill from pass.
- Control (ticket 02 record): authors' scene_1_colmap trained 0–30000 clean (job 33427213 COMPLETED 0:0, ~5 it/s, loss 0.007) — env + sidecar + OptiX fork ACQUITTED.
- 06 resume isolation: sample-control chkpnt15000→16000 resume ran full 1000/1000 iters COMPLETED (job 33449819, ~4.9 it/s, loss ~0.008, Points stable 57550) — resume path ACQUITTED; A03 resume-wedges (32085160, 32276629) are data-specific.
- 07 minimal repro: BOTH legs wedged at 4000/6000 in reflect_trace (gaussian_model.py:134 via pbr:178) — 12-view wedge set (Loss 0.02650, Points 51602, stuck since 04:50 ~7h) AND 8-view killer-free clean set (Loss 0.02458, Points 58133, ~6h, ~35 Timeout dumps). Jobs 33449900/33449901, both scancelled 2026-10-20. Killer views ACQUITTED as cause; trigger is A03-data state at/after iter 4000.
- Code read only (no GPU): gor-is/train.py:204–219 with arguments/__init__.py:131–134 — densify_from 500 / interval 500 / until 12000, opacity_reset every 3000. Iter 4000 is a ROUTINE densify_and_prune + compute_3D_filter step, NOT a unique schedule event (opacity resets at 3000/6000 both passed cleanly on both legs). Lead's prime suspect (a schedule event at 4000) is weakened as a single-event explanation; the remaining cumulative-state / BVH-pathology hypothesis needs code-level debugging outside the diagnose-only bound — deliberately untested.

Retire cause (M9 gate's three): METHOD FAILED — GOR-IS recon cannot train this capture at the required resolution (no mesh, no depth floor, no same-ruler fraction ever measured). NOT ruler-broken (scale sidecars never engaged — measurement never reached), NOT reference-wrong (no OpenMVS comparison ever ran). Density-drain clause (~90%+) never engaged (Points stable 51–58k, cf. control 57k); Open3D-ceiling clause never engaged (no extraction attempted).

Run-plan alternative REJECTED: the only changed hypotheses left (cumulative BVH pathology, densify/opacity schedule surgery, sub-512 resolution) all require either edits to the authors' tree (forbidden — diagnose-only, conservator decision) or dropping below the resolution box M9 openly amended to (1600px, 0.42 mm/px, 2.4× over ~1 mm grain). Killer-view exclusion (4 spent of the 8 stop-rule budget) has no hypothesis left after 07 — spending the remaining 4 would be hope, not diagnosis. No second seed per gate.

Exclusion budget: 4 of 8 spent (A31_1111, A32_1142, A32_1151, A33_1176 — curated out 143→139, backup train_list.143.txt); remaining 4 NOT spent — route retired, no further curation funded.

## Proposed M9 update (EXACT text for lead to apply — do not paraphrase)

> **Status:** retired 2026-10-20 (method failed on this material — bounded probe series closed, no second seed).
>
> - [x] Pinned build `applezyh/GOR-IS@eb36acc` in reused `envs/milo` + `goris_pkgs` sidecar (2026-09-19, ticket 01: full import smoke green on GPU), A03_sherds converted (rig object_mask eye-verified, base+dial kept; specular/normal via loader None-path; 143/21/21 lists), full resolution (`--resolution 1` explicit) — stands as built.
> - [ ] Recon → removal → 2D/3D inpaint → manual mesh-after — RETIRED UNEXECUTED 2026-10-20 (ticket 08): recon wedges at iter ~4000 on A03, no mesh ever existed.
> - [ ] Cross-view depth disagreement in mm — RETIRED UNMEASURED (never reached measurement).
> - [ ] Same-ruler fraction within ~1 mm vs OpenMVS — RETIRED UNMEASURED (inpainted-contact exclusion never engaged).
> - [ ] Break-face close-ups + conservator eye sign-off — RETIRED UNSTAGED (no renders to judge).
> - [ ] Rig check — PARTIAL: killers excluded 143→139 under 8-stop rule (4 of 8 spent, remainder unspent); steel cm² in mesh unmeasured (no mesh).
>
> Where-it-stands 2026-10-20: GOR-IS recon cannot train A03 past iter ~4000 — sample-scene control ran 0–30000 clean (job 33427213) and its resume ran clean (job 33449819), so the stack is acquitted; killer views acquitted (05 no-common-feature, 07 clean set wedged too, jobs 33449900/33449901); trigger unidentified at probe weight (iter 4000 is a routine densify step per code read, not a unique event). Cause: method failed, not ruler, not reference. Tickets 02/03/04 closed unexecuted.

## Comments

- 2026-10-19 (lead): closes the bounded probe series the conservator chose. Whatever the outcome, M9 gets a dated verdict — the question does not stay open on a maybe.
- 2026-10-20 (worker): verdict RETIRE recorded; box 3 left for lead (M9 edit is lead judgement). No GPU, no sbatch, no edits outside this file — only Spartan read-only code reads (train.py densify schedule) plus the six required reads.

