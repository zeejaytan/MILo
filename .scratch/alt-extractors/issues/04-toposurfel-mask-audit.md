# 04: TopoSurfel mask-path audit (desk, no GPU)

**What to build:** the paper answer to whether TopoSurfel can exclude the rig on this material — a stated mask route or a documented no-build, decided on the laptop before any GPU burns.

**Answers:** M7

**Blocked by:** None (can start immediately).

**Status:** ready-for-agent

- [ ] Audit reads the shipped arguments and extraction path at the pinned commit and states where a mask would enter (masked PGSR init, fusion-time depth zeroing, or neither exists)
- [ ] Either the mask route is written down precisely enough to build, or the track is declared a no-build with the reason — "assume it works" is not an outcome
- [ ] TopoSurfel and PGSR commits pinned in this file; the 32,768-block assumption for its TSDF extraction recorded as binding-until-shown-otherwise
