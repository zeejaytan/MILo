# 01: Mechanism check — coarse patches vs rig occlusion

**What to build:** a map proving (or refuting) that the coarse patches of the sherd-only mesh sit where the rig hid clay, before any fill runs.

**Answers:** M10

**Blocked by:** None (can start immediately).

**Status:** ready-for-agent

- [ ] Build occlusion map on A03 (`2025-06-17/A03`): reproject sherd mesh verts into all 143 training views with COLMAP poses (`data/17062025/A03_sherds/sparse/0/`, `output/17062025/A03_nomask/cameras.json`, 3200x2133 PINHOLE fx 6829.81) using the `scripts/cull_diag.py` projector pattern (~2min CPU); per-view visibility from the 164 `A03_erode0` masks (`/data/gpfs/projects/punim2657/MILo/masks/17062025/A03_erode0/masks_sherds/`, mean coverage 2.28%)
- [ ] Overlay coarse patches (thin/hollow zones of a clean erode0 re-extract — NOT the old dilated-mask `mesh_sherds_mm.ply`) against rig-occluded pixels; validate against the 131-hole baseline (per-piece open-edge mm; rims on flared edges / mount underside / clamp-jaw patches)
- [ ] Render one representative case before/after at a view resolving the tested scale + a viewpoint-proof metric (hole/open-edge mm per piece)
- [ ] Verdict with numbers: coincidence → ticket 02 unlocked; NO coincidence → STOP, re-diagnose training-time drain (M5), no fill
- [ ] `check_turntable.py` gate run on the COLMAP model; `sacct` State/ExitCode recorded; laptop-side poll on any sbatch; small checks in held allocation (`scripts/gpu_session.sh`), never login-node heavy work
