## Problem Statement

**Answers:** M2 (MILo project — this spec is the plan that settles whether training-time masking eats the break face).

MILo trains unmasked by design, so the clamp rig trains alongside the clay and every extraction path inherits steel. The one attempt at training-time masking painted background over 0.6–0.9 mm of real fracture edge and was removed. The published both-sides-plus-alpha construction fits this codebase in about 15 lines, costs ~3% shape on its benchmark — but that benchmark's masks are tight with sporadic errors, while ours are shrunk 6 px on every view along exactly the edge reassembly reads, the paper's stated uncovered case. The conservator needs a measured answer, not a citation.

## Solution

Port the both-sides masked loss plus background loss into MILo training, gated and guarded, and run it against an unpatched control on A03 with identical seed and config: an ~8k-iteration probe pair first (cheap early kill), then two full runs only if the probe survives. Score break-face arc in millimetres, never whole-object chamfer. Either the rim holds and training-time rig exclusion reopens, or the erosion carves and it stays closed with numbers attached.

## User Stories

1. As a conservator, I want the rig excluded at training time if possible, so that no downstream step ever sees steel.
2. As a conservator, I want proof the 0.6–0.9 mm fracture rim survives masked training, so that the edge the matcher reads is photographed clay, not background paint.
3. As a conservator, I want clamp-contact faces pre-registered and excluded from scoring, so that honesty about unobserved clay is never punished as damage.
4. As a conservator, I want break-face agreement in mm of arc on 2–3 sampled edges, so that the verdict is about joins, not averages.
5. As a conservator, I want rim close-ups at 0.10 mm/px or tighter before any number, so that a wrong-scale picture cannot hide etching the way full views hid smoothing before.
6. As a researcher, I want masked and control runs on identical seed and config over the existing sherd-only dataset, so that the delta is the loss and nothing else.
7. As a researcher, I want the cheap probe to gate the expensive pair, so that a draining eroded band stops 12 GPU-h before they burn.
8. As a researcher, I want flat-wall noise beside arc agreement, so that background-pressure roughening shows even where edges hold.
9. As a researcher, I want held-out masked rendering quality as a tripwire, so that gross damage is caught before any meshing.
10. As a researcher, I want the background weight at its published value with the ladder held back, so that one variable moves at a time.
11. As a researcher, I want the result written back into intent M2 with a date, so that the masking question closes either way.

## Implementation Decisions

- Loss construction from the object-centric 2DGS paper, three parts or none: two-sided masked photometric loss (photo times mask against render times mask), background loss as the mean of rendered alpha outside the mask at weight 0.5, depth and normal terms untouched.
- Training masks are the erode0 set that sits on the clay edge, not the 6 px-eroded set: rim supervision matters more than rig safety, and stray rig pixels lean on the background loss plus 143-view consensus.
- Rasterizer stays on the production radegs path, the only one whose render dict carries gradient-capable alpha; the GOF path has no alpha hook and is out of scope for this ticket.
- The background term starts with the regulariser kick around iteration 3000, never from zero: the early render path has no alpha key and would crash, and holding pressure also spares rim seed points before densification and depth re-init.
- Occlusion-aware pruning from the paper is deliberately not ported (kernel change, not loss change); existing opacity-plus-size pruning plus frustum culling stands, and surviving interior floaters cost memory, not rim geometry.
- DSSIM-over-masked-frames is watched, not pre-fixed: its window straddles the sharp mask boundary and can etch rims. The L1 fallback ships behind a flag from the start, so the probe can flip it without a rebuild; it runs only if rims etch.
- The gamma ladder (0.25/0.5/1.0) runs only if 0.5 damages rims; the A/B runs once at the published value.
- Clamp-contact faces are hand-marked boxes on the sampled edges before any run, recorded in the probe ticket, and excluded from arc scoring: honesty about unobserved clay is never punished as damage.
- The probe stops on a number plus a picture: mean alpha inside the eroded band below 0.2 at 8k iterations *and* receding rim renders stop the full pair; the number alone never stops it.
- Scope is one capture (A03) and one seed; second seeds and second trees follow only if the verdict is releasable.

## Testing Decisions

- A good test here compares behaviours between two runs, never against ground truth (none exists): arc-loss delta, noise delta, masked rendering delta, all A-minus-B on named edges and boxes.
- Modules under test: the patched loss block (masked photometric parity with control where the mask is one; background term zero where the mask is one), the alpha hook path (present on radegs from the kick iteration on), and the probe instrumentation (per-view alpha mass inside the eroded band plus rim renders).
- Prior art to follow: the `--eval` every-8th-view holdout discipline with sherds-only second pass; the thirteen-plate verification habit (every claim paired with a figure); gate-style self-checks that prove the instrumentation can fail (a fully-masked view must read zero alpha mass).
- The render is part of the test: no scoring box ticks without rim close-ups at 0.10 mm/px or tighter on the same edges for both runs.

## Out of Scope

- Re-animating any one-sided patch (background composited without masking the render, or vice versa).
- The GOF rasterizer alpha hook, occlusion-aware pruning kernels, diffusion repair models.
- Fusion, tiling, block-limit, voxel or component-filter work; OpenMVS, COLMAP or photogrammetry config changes.
- Re-photography, remounting or lighting changes for clamp contact.
- Second seeds, second captures or the gamma ladder unless the base A/B passes.

## Further Notes

- Answers intent M2; M1's gate still stands around this work (depth-disagreement and OpenMVS-on-A03 decide whether any of this is worth doing for this material — this spec is the branch where training-time exclusion earns its GPU-h).
- Triage state for the coming tickets: ready-for-agent once cut via `to-tickets`.
