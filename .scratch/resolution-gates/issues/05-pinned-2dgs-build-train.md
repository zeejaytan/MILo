# 05: Pinned 2DGS build and train on A03_sherds

**What to build:** 2DGS at a commit pinned in M6 before anything runs, trained on the
existing `A03_sherds` dataset at full capture resolution, mesh extracted with voxel size
and truncation band stated in **millimetres**. This ticket exists only if 04 says go.

**Answers:** M6

**Blocked by:** 04 (gate verdict — do not start on any other basis).

**Status:** ready-for-agent

- [ ] Commit pinned in M6's file before the first job; build from that commit only
- [ ] Training reuses `A03_sherds` (existing fusion-time masks — no new masking, no
      relitigation of retired M4/M5)
- [ ] Voxel size and truncation band reported in **mm**; block count checked against the
      32,768 cliff before extraction is attempted (refuse-before-call, per the
      established gate)
- [ ] Job submission approved explicitly before sbatch (standing rule)
