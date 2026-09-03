# M3 — How do we know a mesh is at true scale?

**Status:** open · **Blocked by:** none · **Effort:** small, and it gates comparisons

## Why it matters

Photogrammetry recovers shape up to an unknown overall size. Something in the scene has to
supply the millimetres. If that something is wrong, **every measurement downstream is
wrong by a constant factor and still looks entirely plausible** — a sherd 8% too large is
not visibly a mistake.

It matters most where sizes are compared. Chamfer distance depends on object size unless
the data is normalised, and that has already produced a false finding in this workspace.
Two meshes at two scales will compare cleanly and mean nothing.

## What is already known

- The turntable marker is **unusable before 2025-07-03 N01** — so for the earlier captures
  the scale has to come from somewhere else, or those captures are not metric.
- The conservator's scanning record says to use the base as scale, with the marker on the
  turntable; how much of the turn the marker actually covers has been measured.

## Done when

- [ ] A stated scale source **per capture**, recorded with the capture, not inferred later
- [ ] For captures before 2025-07-03 N01: either an alternative source, or those captures
      marked non-metric so nothing quietly measures against them
- [ ] A round-trip check on at least one sherd — a caliper measurement against the mesh, in
      millimetres, with the disagreement reported rather than the agreement
- [ ] **Scale checked before any two meshes are compared.** This belongs in the comparison
      script, not in a paragraph

## Gate

Where scale cannot be established for a capture, that capture may still be used for shape
questions but must not enter any size-dependent measurement. Say which is which in the
capture record.

## Source

`docs/notes/2026-08-22-turntable-markers.md`; workspace `docs/glossary.md` (chamfer
distance and normalisation); `../AGENTS.md` traps.
