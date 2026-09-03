# 04: The picture that can actually show a scale error

**What to build:** one render that would make a scale error visible to the eye. The two
meshes overlaid, a millimetre scale bar burnt in, and the sherd shown **in section** —
cut through the wall — because a scale error is a proportional change and a three-quarter
view of a whole sherd cannot show one. A sherd 8% too large looks like a sherd.

This is an acceptance criterion for the comparison, not a debugging step afterwards. Four
successive views in this repo have already failed by being too coarse to resolve the
effect being tested, and a wear bug survived three rounds of numeric validation before
anyone drew the geometry.

**Answers:** `M3`

**Blocked by:** 01 (the comparison must know its units before a picture of them means
anything)

**Status:** ready-for-agent

- [ ] The render is a section through the wall, at a view that resolves wall thickness —
      not a whole-object view
- [ ] Both meshes appear in the same picture, distinguishable, in the same frame
- [ ] The millimetre scale bar is burnt in and is correct for the units the sidecars
      declare — it does not fall back to assuming 1.0
- [ ] In `--shape-only` mode no scale bar is drawn, and the picture does not imply a size
- [ ] The render is written whatever the numbers say
