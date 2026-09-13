# 03: Cheap boxes before any PGSR build

**What to build:** the two low-cost measurements that gate the GPU spend, on the same capture and the same ruler the verdict will use.

**Answers:** M8

**Blocked by:** 01 new sibling shell.

**Status:** resolved

- [x] Photogrammetry-route baseline reused on the capture: fraction of sherd surface within the roughly-one-millimetre relief the break faces need, with scale provenance stated, no second ruler
- [x] Input steel-versus-clay split recorded for the inputs actually to be used, with remaining steel to be stated later in square centimetres on each extracted mesh
- [x] Go or no-go for the live build written down: if the baseline already clears the bar, the swap case must meet parity-plus or complementary coverage, not merely run
- [x] No training, no extraction, no batch submission in this ticket

## Comments

- 2026-09-09: both boxes answered by reuse, nothing re-measured. No GPU, no jobs, read-only checks only.
- **Baseline (from M1, verdict 2026-09-06, not re-run):** OpenMVS flat-surface wobble **0.186 mm** on A02 (same-rig-class material — under the ~1 mm bar with margin), plus A03 sherd-only outlines **OpenMVS 42.2% vs MILo 8.6%** (job 30158911, 21 held-out views, direction honest per overlays; overfill fringes explain the gap to A02's 66%). Requirement **~1 mm relief** (grains ~0.7–1.2 mm from photo measurement; conservator concurred 2026-09-06). Weight and caveats travel with it: one capture each, different capture and coarser fabric for A02, and A02's SH5 warning that one smoothed edge hid in an average. A03 flat-noise and per-sherd millimetres stay struck unless a future outline disagrees.
- **Inputs actually to be used (verified on Spartan, read-only):** `data/17062025/A03_sherds` exists — 164/164 registered/on-disk, `sparse/0/*.bin` COLMAP model present, `llffhold=8`, masks from `masks/17062025/A03_erode0/masks_sherds` (NEAREST-resized 5568×3712 → 3200×2133, corner shift 1.23 px within the 2 px allowance). Mask coverage mean **2.28%** (1.5–3.1%) matches the project record; steel-vs-clay split per that record: kept area 23.84% → 2.28%, non-sherd **627 → 16 cm²** per view, 8–10 sherds resolved per view against 10 existing. Remaining steel on each extracted mesh gets stated in cm² at ticket 04.
- Two honest discrepancies for 04 to carry, not to block on: (a) the project notes say "143 views" for A03 but the dataset holds **164** — count 164 as the trial's N and say so; (b) the dataset sidecar has **no scale applied yet** (`scale_factor: None`) — 04 anchors scale per M3 (sidecar or SCALE.txt) and refuses rather than measures if it cannot.
- **Go/no-go: GO, with the bar set.** The baseline already clears ~1 mm, so per the spec gate and M8 this trial must earn parity-plus (match/beat OpenMVS with ridge-resolving renders), complementary coverage (honest holes OpenMVS misses), or viewing-only — merely running is a NO. Status left `ready-for-agent`; resolving waits for the M8 write-back (05).

## Answer 2026-09-13

Gates did their job: the trial ran exactly the GO it was given and met none of the three earn-its-keep outcomes as a mesh route (parity-plus: no — lumpy/partial at 0.75 mm grid; complementary coverage: no — honest holes plus forced-10 amputations, nothing OpenMVS misses recovered; viewing-only: unjudged). The steel split recorded here (2.28% keep, 627→16 cm²/view) is inherited by the verdict. M8 answered NO as mesh route.
