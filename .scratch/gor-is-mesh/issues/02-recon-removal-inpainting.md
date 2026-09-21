# 02: Recon, removal and intrinsic inpainting on A03

**What to build:** the full GOR-IS removal run on the converted A03 capture at full resolution, ending with clean rig-free renders — the splat that ticket 03 will mesh.

**Answers:** M9

**Blocked by:** 01-pinned-build-conversion.

**Status:** in-progress (recon submitted; inpainting job lands after iter speed is known)

- [x] Pipeline fixed at the pinned commit with full-resolution, lists-honouring `--eval` (143/21), `--logger none`, `--resolution 1` — recon job `slurm/goris_recon.slurm` (train 30k → remove_object → metrics → density census), SUBMITTED `30753265` 2026-09-19, poll running
- [ ] Held-out render PSNR reported as viewing signal only, never in mm; density counts (Gaussians in vs out) reported — ~90%+ drain stops the route at probe weight per M5/M6
- [ ] Rig-free renders show zero steel to the eye on whole-tray views; inpainting2D/3D + final render ride a second job sized from recon iter speed; inpainted jaw-contact regions tagged as invented for ticket 04 exclusion
- [ ] Logs and renders land in gitignored `artifacts/` / Spartan output; no mesh in this ticket

## Comments

- 2026-09-19: supersedes the launcher.py line above (launcher hardcodes `--resolution 512/4` and `--skip_mesh` on removal; direct `train.py`/`render.py` calls with `--resolution 1` instead). LaMa weights pre-fetched to `goris_cache/` (compute nodes offline); `--eval` honours train/test lists.
- 2026-09-21: full-res recon `30762677` hit the 12h wall at 4000/30000 with nothing saved (first save at 7000) — ~10s/iter at 3200px with ray-traced lighting ≈ 80 GPU-hours. User decision: `--resolution 2` (1600px, 0.42mm/px, 2.4× over the ~1mm grain), two chained legs via `--start_checkpoint`. M9 amended openly. Leg 1 (`goris_recon.slurm`, 0→15000) submitted as below; leg 2 follows on COMPLETED.
