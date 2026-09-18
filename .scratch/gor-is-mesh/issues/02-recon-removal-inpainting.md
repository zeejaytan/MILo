# 02: Recon, removal and intrinsic inpainting on A03

**What to build:** the full GOR-IS removal run on the converted A03 capture at full resolution, ending with clean rig-free renders — the splat that ticket 03 will mesh.

**Answers:** M9

**Blocked by:** 01-pinned-build-conversion.

**Status:** ready-for-agent

- [ ] `launcher.py --recon --remove_object --inpainting2D --inpainting3D --render_inpainting3D` runs at the pinned commit on A03 at full capture resolution with `--eval` held-out views; iteration counts and GPU/job IDs logged
- [ ] Held-out render PSNR reported as viewing signal only, never in mm; density counts (Gaussians in vs out) reported — ~90%+ drain stops the route at probe weight per M5/M6
- [ ] Rig-free renders show zero steel to the eye on whole-tray views; inpainted jaw-contact regions tagged as invented for ticket 04 exclusion
- [ ] Logs and renders land in gitignored `artifacts/` / Spartan output; no mesh in this ticket
