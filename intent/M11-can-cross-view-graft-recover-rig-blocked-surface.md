# M11 — Can cross-view graft recover rig-blocked sherd surface from real pixels?

**Status:** open · **Blocked by:** none (M10 closed-keep 2026-10-17) · **Effort:** roughly 1–2 weeks (probe, graft build, eye gate, retrain only if the eye says so) · **Correction 2026-10-18:** first version wrongly targeted jaw-covered face; jaws ride with the sherd so that clay is visible nowhere — scope is rig-blocked surface only (user correction, intent edited in place, git holds the earlier telling)

## Why it matters

Two occluders, two fates — corrected 2026-10-18, because the first telling blurred them. The clamp's rubber jaws ride *with* the sherd on the turntable: they sit on the same face patch in every view, so that clay is seen nowhere and no graft can recover it (LaMa proved it too — ticket 13d: a masked prong filled dark, mean change ~2.5 grey levels, because the rim is mostly darkness). The *rig itself* is the graftable case: static steel the turning sherd passes behind, so surface hidden in one view stands genuinely visible in sisters. The graft target is rig-blocked surface only; jaw-covered face stays excluded, by geometry, not by choice.

Plain terms: the rubber jaw travels with the pottery, so no photo ever sees beneath it — that clay is gone and stays gone. But the sherd also swings behind the fixed steel rigging, and what one photo loses to steel, a sister photo sees as plain clay. The test is whether geometry (camera positions + depth, which this project already owns) can carry those genuine clay pixels across — so the rig-blocked surface arrives whole, measured throughout, with nothing hallucinated.

## Opinion before acting (workspace rule — researched, then stated)

Worth doing **for this**, as an adaptation, not an adoption. The literature survey (2026-10-18, `docs/notes/multiview-completion-survey.md`) returned a clean negative: no paper or codebase does faithful cross-view texture transfer as its stated task. The closest mechanism precedent is 3DGIC (Huang et al., CVPR 2025, arXiv:2502.11801): its depth-guided stage shrinks each inpainting mask to pixels visible in *no* view by projecting visible background across views, and only then fills the remainder — "visible-anywhere ⇒ copy, visible-nowhere ⇒ hallucinate". We borrow the split and refuse the second half: visible-anywhere ⇒ copy real pixels; visible-nowhere ⇒ leave out and say so, never hallucinate. That refusal is load-bearing — it keeps every grafted pixel on the measured side of the 2026-10-05 marking rule (diffusion-invented fill must be labelled generated, never treated as measured evidence), which LaMa fill could never satisfy on sherd faces.

Three cautions. First, the probe comes before the build and counts rig-blocked pixels only — jaw-covered face is out of scope by the correction above, visible nowhere in any view. If most rig-blocked surface also turns out visible nowhere (grazing angles), there is nothing to copy and the question stops at a number. Second, cross-view pixels disagree (lighting, exposure, resampling) — the graft needs photometric matching plus the same outside-mask guarantees LaMa refills honoured (untouched pixels bit-identical), or it is a fancier fake. Third, 3DGIC's code is deletion-framed and its licence unverified — borrow the idea from the paper, do not depend on the repo until the licence is checked.

## Done when

- [ ] Visibility probe: for rig-blocked (not jaw-covered) pixels, what fraction is genuinely visible in ≥1 other view (date, ticket, job)
- [ ] Graft build: pose+depth projection carrying real pixels across, with photometric match and outside-mask guarantees verified per view
- [ ] Eye gate: grafted faces staged in visual-qa beside control; conservator confirms clay, not smear — need-eye pair logged with same-round reply
- [ ] Retrain + measure only if the eye passes: density/roughness vs control with grafted regions flagged as measured-but-relocated
- [ ] Write back here (Where it stands + Weight / Next / Picture / Viewer) whatever the outcome; rebuild board

## Where it stands

Not yet started — question posed 2026-10-18 after the 13d LaMa negative and the literature survey.

Weight: none yet — no pixels counted, no probe run.
Next: run the visibility probe.
Picture: none yet.
Viewer: none yet.

## Gate / stop condition

- Rig-blocked surface mostly visible nowhere → stop at the probe; fall back to excluding jawed views (M10 Next) rather than building the graft. (Jaw-covered face is visible nowhere by construction — never in scope.)
- Grafted pixels fail bit-identical-outside or photometric match → stop; a graft that alters its neighbours is a fake.
- Eye reads smear, seams, or wrong clay → retire NO; graft stays unbuilt, exclusion stands.
- Eye confirms clay with flags honoured → keep; retrain and measure, then scope the second capture with jaw-aware posing.

## Source

User request 2026-10-18 (write the graft intent, adapting 3DGIC's mechanism to a task its authors never posed); literature survey 2026-10-18 (`docs/notes/multiview-completion-survey.md`, 11 candidates, clean negative); 3DGIC (Huang et al., CVPR 2025, https://arxiv.org/abs/2502.11801, project https://peterjohnsonhuang.github.io/3dgic-pages — mechanism precedent only, licence unverified); [M10](M10-does-lama-fill-keep-density-through-crop.md) (closed-keep; rig-only fill pays back the masking drain; jaws-on-face unfixable by LaMa, ticket 13d); user decision 2026-10-05 (diffusion-invented fill marked generated, never measured); intent numbering permanent — M11 follows M10.
