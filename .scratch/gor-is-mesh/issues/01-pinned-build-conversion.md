# 01: Pinned GOR-IS build plus A03 dataset conversion

**What to build:** a repeatable GOR-IS checkout at `eb36acc` with its own env, plus A03_sherds converted to its dataset layout, verified by eye before any GPU trains.

**Answers:** M9

**Blocked by:** None (can start immediately).

**Status:** resolved 2026-09-19 (conversion + reuse smoke green; no training run here)

- [x] Reuse probe: `envs/milo` + `goris_pkgs` sidecar (gtracer 0.1.0 OptiX build, simple-lama, mediapy, lpips — all `--no-deps`, shadow guard green); smoke `30752840` COMPLETED 0:0 2026-09-19 (rasterizer + nvdiffrast + gtracer ok; gaussian_model + renderer ok; mediapy + lpips + simple-lama import ok; torch 2.3.1+cu118 gpu True); `--logger none`; `--resolution 1` explicit
- [x] A03_sherds converted: rig object_mask, chrome specular_mask, predicted normals, COLMAP sparse reused, train/val/test lists; layout matches `images/ object_mask/ specular_mask/ sparse/ normal/` plus lists — DONE 2026-09-18, convert job `30715195` COMPLETED 0:0: `data/goris_A03/` holds 164 images symlinks, sparse/0 copy, 164 object_masks, 143/21/21 lists; specular/normal absent by design (loader None-path)
- [x] Mask panels rendered (`mask_content.py` split + photo|mask|clay panels) and looked at: steel vs clay cm2 per view stated; erode0 edge verified not to eat the rim — DONE 2026-09-18, agent eye on 4 panels (`artifacts/goris_A03_panels/`): middle band carries clamps, rods, blue knobs, base plate and dial with sherd-shaped cut-outs; right band is clay only. Base plate and dial ride with the rig (scale comes from the sidecar at scoring time, not from the removed base). Conservator eye stays at ticket 04.
- [x] No training started in this ticket; conversion artefacts land in gitignored `artifacts/`, never in git

## Answer

Reuse earns it: no fresh env. Dataset `data/goris_A03` verified by eye (164 rig masks, base+dial kept, 143/21/21 lists). Ticket 02 unblocked.

## Comments

- 2026-09-18 (laptop): GOR-IS cloned on Spartan working area at `gor-is@eb36acc`, submodules checked out (glm x2, simple-knn). Reuse probe on login node: `envs/milo` carries torch 2.3.1+cu118, torchvision, numpy, cv2, trimesh, open3d, scipy, sklearn, tqdm, plyfile, matplotlib, PIL, nvdiffrast, diff_gaussian_rasterization, simple_knn — all present; missing only tensorboard (avoided via `--logger none`) and simple-lama (sidecar at ticket 02 stage). OptiX/7.6.0 module exists; CUDA up to 12.8. Masks/normals optional in the loader (`None` path) — v1 ships rig object_mask only.
- 2026-09-18 (login node, dry-run): 164 views; sherd 155,381 px = 2.28% of frame = 69 cm2/view; rig 1,477,857 px = 21.65% = 652 cm2/view; 21 test / 143 train. Matches traps.md direction (61/644). Converter: `scripts/goris_convert_A03.py` (rig = old foreground minus erode0 sherd, refuses on size mismatch). Live run reached 20/164 masks before the ssh window closed; resume logic committed (`034535b`).
- 2026-09-18 (laptop): convert resume submitted as CPU job + gtracer/reuse smoke submitted as GPU job — SUBMITTED after ssh recovery: convert `30715195`, smoke `30715196`. Laptop-side polls running on both per workspace rule 4.
- 2026-09-18: convert `30715195` COMPLETED 0:0. Panels fetched to `artifacts/goris_A03_panels/` (gitignored) and looked at — rig/shard split clean, base+dial ride with rig. Convert rewrite `30720700` (keep base+dial) COMPLETED; agent eye caught dark jaw pads kept as dial, threshold raised 5k→25k half-px, rewrite `30720989` COMPLETED 0:0: kept band now dial+base only (kept 253→120 cm2/view, rig 399→532), clamp fragments back in removal. Panels in `artifacts/goris_A03_panels2/` (gitignored). Smoke `30715196` FAILED 1:0 — diagnosed: sidecar pip installs dragged torch 2.8.0/numpy 2.0.2 shadowing env torch 2.3.1 (undefined-symbol ImportError); gtracer 0.1.0 itself built fine. Fix committed: `--no-deps` + shadow guard; sidecar wiped; resubmitted as `30721180`. Nothing trains in this ticket.
- 2026-09-19: smoke `30721180` FAILED 1:0 on `mediapy` (pure-python gap in render_utils); sweep found `lpips` waiting at the next stage too; both added `--no-deps` (wandb/tensorboard exempt: try/except-guarded, `--logger none`). Resubmit `30752840` COMPLETED 0:0 — full import cover green. Recon `30753265` FAILED in minute one: env rasterizer lacks the depth flag (TypeError in build_rasterizer). Fix: vendored depth-fork built into sidecar (smoke `30761807` green on everything except a vacuous rasterizer check; check corrected to directory presence, smoke `30762580` COMPLETED with fork built + full cover green). Recon resubmitted as `30762677`, poll running. Nothing trains in this ticket.
