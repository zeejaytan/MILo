# 07: TopoSurfel one-capture A/B, full resolution

**What to build:** TopoSurfel judged on masking at full capture density — a mesh with voxel and band in millimetres, scored same-ruler against MILo and OpenMVS with ridge renders and steel in cm².

**Answers:** M7

**Blocked by:** 01 (OpenMVS on A03, same ruler), 02 (depth disagreement in mm), 04 (mask-path audit).

**Status:** ready-for-agent

- [ ] Builds only if 04 stated a mask route and 01–02 left a bar worth chasing; otherwise this ticket closes unbuilt citing the gate
- [ ] Trained and extracted at full capture resolution on the existing sherd-only dataset, voxel size and truncation band stated in mm, block counts and free-memory figures printed before any extraction
- [ ] Same-ruler scoring vs MILo's DTU route and OpenMVS (fraction within M1 requirement), break-face close-ups resolving ~0.2 mm ridges, remaining steel in cm² — no box ticks on whole-tray views
