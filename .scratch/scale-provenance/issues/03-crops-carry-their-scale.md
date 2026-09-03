# 03: A crop is as accountable as the mesh it was cut from

**What to build:** cutting a mesh down — cropping to the rig, cropping to a sherd — keeps
the scale statement with the piece that comes out. The derived sidecar records the same
units and factor as its parent, plus which mesh it came from and what operation produced
it, so a crop can be traced back to the physical object that supplied its millimetres.

Demoable end to end: crop a metric mesh, then compare the crop against its parent with
ticket 01's script. Today that comparison refuses, because the crop has no sidecar and
nothing remembers that it is still in millimetres. After this it reports millimetres and
names the source.

**Answers:** `M3`

**Blocked by:** 01 (the sidecar reader and the contract it enforces)

**Status:** ready-for-agent

- [ ] Cropping a mesh that has a sidecar produces a crop that has one
- [ ] The derived sidecar names its parent mesh and the operation that made it
- [ ] Cropping a mesh with **no** sidecar produces a crop with no sidecar — provenance is
      carried, never invented
- [ ] The comparison from ticket 01 accepts a crop against its parent and prints the
      source it inherited
