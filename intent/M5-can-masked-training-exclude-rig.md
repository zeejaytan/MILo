# M5 — Can both-sides-plus-alpha training exclude the rig without eating the rim?

**Status:** answered NO on A03 (2026-09-06) — see verdict below · **Blocked by:** none

## Why it matters

Training unmasked grows the rig alongside the clay, and every extraction path inherits
steel. The one training-time mask tried painted background over 0.6–0.9 mm of break
face and was removed. The published construction (mask render *and* photograph, plus a
background loss on alpha outside the mask) costs ~3% shape on its benchmark — but that
benchmark's masks are tight with sporadic errors, while ours erode 6 px on every view
along the edge reassembly reads, the paper's stated uncovered case. If the rim survives,
rig exclusion moves to training time and no extraction path ever sees steel. If the
erosion carves, training-time masking stays closed with numbers attached.

## Done when

- [x] Probe pair verdict (2026-09-06): band alpha outside 0.0008–0.0037 (tripwire 0.2
      never threatened); rim renders held fracture relief. Probe-level GO — overturned
      by the full build below; the probe measured pressure, not density.
- [x] Full A/B deltas: agreement median 0.41 mm / 62.7% within 0.5 mm (control-side
      tail is clamp steel, expected); roughness masked 0.11 vs control 0.04 mm median
      (CONFOUNDED — control box holds polished steel; not a surface ranking);
      held-out masked-PSNR masked 23.9 dB every view vs control 10–28 dB.
- [x] Conservator eye sign-off (2026-09-06): masked mesh much coarser than control —
      failed approach.
- [ ] Clamp-contact faces either observed by re-mount or written down as permanently
      unobserved (shared with M2 — survives this verdict; the mount question is
      independent of which stage excludes the rig).

## Verdict 2026-09-06: no — masked training excludes the rig and coarsens past use

The rim survived (no recession, relief intact in renders) and the rig is gone (all ten
pieces read as clay, background alpha ~0.001) — the masking construction works as
advertised. The mesh still fails: background loss plus density control drained the set
from 222,678 to 18,443 Gaussians (~91% fewer), pivot spacing grew with it, and the tet
skin comes out visibly coarser than control (276k vs 2.6M vertices; eye-confirmed).
Same trade as post-training pruning (M4), moved one stage earlier: every exclusion of
Gaussians must be paired with replacement, and this construction pairs it with nothing —
densification runs on schedule but has no reason to re-supply clay the loss keeps
draining. This is a claim about the method on this material (type 1), not a broken ruler:
the numbers are same-frame millimetres and the eye is direct.

## Gate / stop condition

Fired. Training-time masking stays closed on this material; rig exclusion stays a
fusion/extraction-time operation. The DTU ~3% cost does not transfer to eroded
turntable masks — the gap here is density collapse, not chamfer points. M2's fieldwork
gate (mount change vs written-off contact) and M1's gate (OpenMVS on A03, same ruler)
stand as the live branches.

## Source

`docs/notes/2026-09-06-masked-milo-training.md`; `docs/notes/2026-09-05-mask-fragility-3dgs-vs-milo.md`
§§1–2; `.scratch/masked-training/` tickets 01–04; probe jobs 30090865/30094277/30099987,
render job 30121191, verdict extractions 30125644/45.
