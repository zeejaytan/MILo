# 01: Pinned GOR-IS build plus A03 dataset conversion

**What to build:** a repeatable GOR-IS checkout at `eb36acc` with its own env, plus A03_sherds converted to its dataset layout, verified by eye before any GPU trains.

**Answers:** M9

**Blocked by:** None (can start immediately).

**Status:** ready-for-agent

- [ ] Reuse probe: `envs/milo` python imports torch, diff_gaussian_rasterization, simple_knn, nvdiffrast, trimesh, open3d (all present 2026-09-18); sidecar `goris_pkgs` holds OptiX gtracer build + simple-lama only; full `from scene.gaussian_model import GaussianModel` smoke passes on a GPU node; `--logger none` avoids tensorboard; `--resolution 1` is explicit (default -1 would silently halve 3200px to 1600)
- [ ] A03_sherds converted: rig object_mask, chrome specular_mask, predicted normals, COLMAP sparse reused, train/val/test lists; layout matches `images/ object_mask/ specular_mask/ sparse/ normal/` plus lists
- [ ] Mask panels rendered (`mask_content.py` split + photo|mask|clay panels) and looked at: steel vs clay cm² per view stated; erode0 edge verified not to eat the rim
- [ ] No training started in this ticket; conversion artefacts land in gitignored `artifacts/`, never in git

## Comments

- 2026-09-18 (laptop): GOR-IS cloned on Spartan working area at `gor-is@eb36acc`, submodules checked out (glm x2, simple-knn). Reuse probe on login node: `envs/milo` carries torch 2.3.1+cu118, torchvision, numpy, cv2, trimesh, open3d, scipy, sklearn, tqdm, plyfile, matplotlib, PIL, nvdiffrast, diff_gaussian_rasterization, simple_knn — all present; missing only tensorboard (avoided via `--logger none`) and simple-lama (sidecar at ticket 02 stage). OptiX/7.6.0 module exists; CUDA up to 12.8. Masks/normals optional in the loader (`None` path) — v1 ships rig object_mask only.
- 2026-09-18 (login node, dry-run): 164 views; sherd 155,381 px = 2.28% of frame = 69 cm2/view; rig 1,477,857 px = 21.65% = 652 cm2/view; 21 test / 143 train. Matches traps.md direction (61/644). Converter: `scripts/goris_convert_A03.py` (rig = old foreground minus erode0 sherd, refuses on size mismatch). Live run reached 20/164 masks before the ssh window closed; resume logic committed (`034535b`).
- 2026-09-18 (laptop): convert resume submitted as CPU job + gtracer/reuse smoke submitted as GPU job — PENDING ssh recovery (two `kex_exchange_identification` resets after ~20 sessions this conversation; likely throttle). Job IDs to follow here with `sacct` State/ExitCode per workspace rule 4. Nothing trains in this ticket.
