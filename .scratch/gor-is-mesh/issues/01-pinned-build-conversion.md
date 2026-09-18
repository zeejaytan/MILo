# 01: Pinned GOR-IS build plus A03 dataset conversion

**What to build:** a repeatable GOR-IS checkout at `eb36acc` with its own env, plus A03_sherds converted to its dataset layout, verified by eye before any GPU trains.

**Answers:** M9

**Blocked by:** None (can start immediately).

**Status:** ready-for-agent

- [ ] Reuse probe: `envs/milo` python imports torch, diff_gaussian_rasterization, simple_knn, nvdiffrast, trimesh, open3d (all present 2026-09-18); sidecar `goris_pkgs` holds OptiX gtracer build + simple-lama only; full `from scene.gaussian_model import GaussianModel` smoke passes on a GPU node; `--logger none` avoids tensorboard; `--resolution 1` is explicit (default -1 would silently halve 3200px to 1600)
- [ ] A03_sherds converted: rig object_mask, chrome specular_mask, predicted normals, COLMAP sparse reused, train/val/test lists; layout matches `images/ object_mask/ specular_mask/ sparse/ normal/` plus lists
- [ ] Mask panels rendered (`mask_content.py` split + photo|mask|clay panels) and looked at: steel vs clay cm² per view stated; erode0 edge verified not to eat the rim
- [ ] No training started in this ticket; conversion artefacts land in gitignored `artifacts/`, never in git
