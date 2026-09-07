# 07: Rogge masked-loss port + probe (no rasterizer change)

**What to build:** the published masked-training recipe, hand-ported into the
pinned 2DGS checkout, proven on a short probe before any full build — background
loss plus two-sided masked photometric loss, occlusion pruning explicitly deferred.

**Answers:** M6

**Blocked by:** 05 (baseline mesh + maps); reads M5's verdict as its risk register.

**Status:** ready-for-agent

- [ ] Recipe ported per `MarcelRogge/object-centric-2dgs@bdbabdc` (README-only repo,
      base 2DGS `19eb5f1` Aug-2024; ours `f3e3b9f` — recipe is version-agnostic
      Python): masked photometric loss (`gt*mask`, `render*mask`), background loss
      `mean(alpha*(1-mask))` at λ=0.5 using the already-returned `rend_alpha`
      (no rasterizer change), masks from the existing RGBA alpha band. Port lives
      outside upstream files (trial patch dir + flag), commit recorded in M6
- [ ] Probe train (~7k iters, same `A03_sherds`, `-r 1`): Gaussian-count trajectory
      vs control (274,704 @30k), alpha-outside-mask numbers, rim renders at a
      resolving view — GO/NO-GO for 08 with the reason named
- [ ] NO-GO stops here: retire the branch at probe weight, do not fund 08

## Comments

- 2026-09-07, audit: the Rogge repo ships NO code (README recipe only), so this
  is a hand-port, not a drop-in. Occlusion pruning needs CUDA rasterizer edits
  plus rebuild — deferred to 08 ONLY if the probe survives on losses alone
  (opacity-threshold pruning through density control is automatic). M5's two
  warnings transfer unchanged: 6 px eroded rims on every view (their stated
  uncovered case) and density drain (222k→18k on MILo).
