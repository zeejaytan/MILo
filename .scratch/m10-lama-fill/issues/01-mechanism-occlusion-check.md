# 01: Mechanism check — coarse patches vs rig occlusion

**What to build:** a map proving (or refuting) that the coarse patches of the sherd-only mesh sit where the rig hid clay, before any fill runs.

**Answers:** M10

**Blocked by:** None (can start immediately).

**Status:** resolved

- [x] Build occlusion map on A03 (`2025-06-17/A03`): reproject sherd mesh verts into all 143 training views with COLMAP poses (`data/17062025/A03_sherds/sparse/0/`, `output/17062025/A03_nomask/cameras.json`, 3200x2133 PINHOLE fx 6829.81) using the `scripts/cull_diag.py` projector pattern (~2min CPU); per-view visibility from the 164 `A03_erode0` masks (`/data/gpfs/projects/punim2657/MILo/masks/17062025/A03_erode0/masks_sherds/`, mean coverage 2.28%)
- [x] Overlay coarse patches (thin/hollow zones of a clean erode0 re-extract — NOT the old dilated-mask `mesh_sherds_mm.ply`) against rig-occluded pixels; validate against the 131-hole baseline (per-piece open-edge mm; rims on flared edges / mount underside / clamp-jaw patches)
- [x] Render one representative case before/after at a view resolving the tested scale + a viewpoint-proof metric (hole/open-edge mm per piece)
- [x] Verdict with numbers: coincidence → ticket 02 unlocked; NO coincidence → STOP, re-diagnose training-time drain (M5), no fill
- [x] `check_turntable.py` gate run on the COLMAP model; `sacct` State/ExitCode recorded; laptop-side poll on any sbatch; small checks in held allocation (`scripts/gpu_session.sh`), never login-node heavy work

## Result (lead review, 2026-10-16) — GO, ticket 02 unlocked

Worker ran clean (job 33166058, COMPLETED 0:0, 2:45; check_turntable exit 0, 349° coverage). Lead verified: opened `artifacts/m10_t01_rep_piece2_pair.png` — the red loop sits on clamp steel in A31_1123 and on clay face in A32_1139; `holes.csv` on Spartan matches the reported table exactly; sacct confirms COMPLETED.

- Piece 2 (~6x6x8 cm sherd): 463.0 mm open hole-edge, 276.5 mm (60%) at vis_frac<0.25; biggest hole 427.3 mm reprojects 0/667 in-mask (steel) vs 548/667 (clay).
- Top-10 totals: 81 holes, 2781.7 mm open edge, 1012.0 mm (36%) occluded; mesh-wide median visfrac 0.797.
- Honest exception recorded: piece 3 holds 442.3 mm of holes with only 9.3 mm occluded — not every coarse patch is rig-driven, but the gate (coincidence exists, 7+ of 10 pieces 25–60% occluded edge) is met.
- Baseline honesty verified: `recon_tsdf_v0.0022.ply` fused from the unmasked train with alphas bit-identical to erode0 — holes are not dilated-carve artifacts.
- Evidence: `/data/gpfs/projects/punim2657/MILo/output/17062025/m10_ticket01/` (holes.csv, per_view.csv, occlusion.npz, rep.json, rep renders), log `m10_t01_occl_33166058.log`.
