# 01: Pinned GOR-IS build plus A03 dataset conversion

**What to build:** a repeatable GOR-IS checkout at `eb36acc` with its own env, plus A03_sherds converted to its dataset layout, verified by eye before any GPU trains.

**Answers:** M9

**Blocked by:** None (can start immediately).

**Status:** ready-for-agent

- [ ] Repo pinned at `eb36acc` with submodule hashes recorded; env `envs/goris` builds per README (python 3.12, diff-gaussian-rasterization, simple-knn, nvdiffrast, OptiX gtracer fork); import smoke test passes on a GPU node
- [ ] A03_sherds converted: rig object_mask, chrome specular_mask, predicted normals, COLMAP sparse reused, train/val/test lists; layout matches `images/ object_mask/ specular_mask/ sparse/ normal/` plus lists
- [ ] Mask panels rendered (`mask_content.py` split + photo|mask|clay panels) and looked at: steel vs clay cm² per view stated; erode0 edge verified not to eat the rim
- [ ] No training started in this ticket; conversion artefacts land in gitignored `artifacts/`, never in git
