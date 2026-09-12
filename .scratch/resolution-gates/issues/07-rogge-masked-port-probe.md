# 07: Rogge masked-loss port + probe (no rasterizer change)

**What to build:** the published masked-training recipe, hand-ported into the
pinned 2DGS checkout, proven on a short probe before any full build — background
loss plus two-sided masked photometric loss, occlusion pruning explicitly deferred.

**Answers:** M6

**Blocked by:** 05 (baseline mesh + maps); reads M5's verdict as its risk register.

**Status:** resolved NO-GO (2026-09-10 — retire branch, do not fund 08)

- [x] Recipe ported per `MarcelRogge/object-centric-2dgs@bdbabdc` (README-only repo,
  base 2DGS `19eb5f1` Aug-2024; ours `f3e3b9f` — recipe is version-agnostic
  Python): masked photometric loss (`gt*mask`, `render*mask`), background loss
  `mean(alpha*(1-mask))` at λ=0.5 using the already-returned `rend_alpha`
  (no rasterizer change), masks from the existing RGBA alpha band. Port lives
  outside upstream files (trial patch dir + flag), commit recorded in M6
- [x] Probe train (~7k iters, same `A03_sherds`, `-r 1`): 78,227 → 4,620
  Gaussians (94% drained — worse than M5's 91%), bg 0.00195 (rig gone),
  held-out PSNR 11.6 dB vs control 21.2 at same iters (renders collapsed).
  Eye verification 2026-09-10 (`artifacts/2dgs-a03/probe_A31_1100.png`):
  frame black, zero steel, sherds reduced to translucent smears — masking
  works, clay destroyed. Agent eye; conservator confirm pending.
- [x] NO-GO stops here: retire the branch at probe weight, do not fund 08

## Comments

- 2026-09-13, discriminating probe per user go (cliff analogy falsified by
  margin-independence): background weight 0.1 vs 0.5, job 30485175 (short
  GPU, same data/flags otherwise). Drain scales with weight → background
  pressure is the vector. Unchanged → reset/cull ratchet dominates. Poll running.

- 2026-09-12, dilated probe verdict: 78,227 → 5,781 (92.6% drained vs 94%),
  PSNR 11.59 vs 11.57, bg 0.00193 — margin changes nothing; same collapse,
  same trade. Renders rendering (30483899) for the residue eye check. The
  margin-vs-residue question is answered on numbers; residue viewing to follow.
- 2026-09-12, eye on dilated renders (`artifacts/2dgs-a03/dprobe_A31_1100.png`):
  identical ghosts — black frame, no steel fins anywhere, sherds translucent
  smears. Margin bought neither rims nor residue; there is nothing here to
  tolerate or reject. Dilated branch dead with the parent. No further masked
  variants without fresh justification.

- 2026-09-12, dilated probe per user decision (margin vs residue question is
  theirs to judge): dataset `A03_dilated` built (164 views, coverage 2.7% vs
  2.28%; overlays eye-checked, margin small, jaws at grips as expected).
  Probe 30467156 (short GPU, same 7k/λ0.5). Residue verdict lands with its
  renders. Poll running.

- 2026-09-12, transfer boundary (user: why doesn't the paper's claim hold
  here?): it holds in its domain (textured single objects, sporadic mask
  error, benchmark averages) and fails at ours (plain clay with no regrowth
  gradients, systematic occlusion-boundary outlines, per-sherd completeness
  + 1 mm bar). Paper's own ablations chart the trade; we live past its
  tested corner. Finding, not accusation.

- 2026-09-09, port committed in the trial clone (`rogge port`: +33/-4,
  `train.py` + `arguments/__init__.py`, never pushed — clone is untracked
  working area): `--lambda_bg` (default 0.0 = upstream behavior) gates the
  whole pair, never bg alone (paper Fig.8). Occlusion pruning NOT ported.
  Probe 30287835 (short GPU, `--lambda_bg 0.5`, `--iterations 7000`, separate
  `output/A03_probe_masked`), poll running. Baseline line dropped per user:
  unmasked bounded fusion is off published practice (died 128G/512G/1TB +
  trunc4); verdict reads off masked meshes.

- 2026-09-07, audit: the Rogge repo ships NO code (README recipe only), so this
  is a hand-port, not a drop-in. Occlusion pruning needs CUDA rasterizer edits
  plus rebuild — deferred to 08 ONLY if the probe survives on losses alone
  (opacity-threshold pruning through density control is automatic). M5's two
  warnings transfer unchanged: 6 px eroded rims on every view (their stated
  uncovered case) and density drain (222k→18k on MILo).
