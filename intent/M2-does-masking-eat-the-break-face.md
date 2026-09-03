# M2 — Does masking the clamps destroy the thing we are trying to measure?

**Status:** open — measured once, and it is at the limit · **Blocked by:** none

## Why it matters

The sherds are held in clamps. The clamps are masked out, and the mask is shrunk by six
pixels so that clamp-straddling pixels never receive a depth. Vertex counts and overall
object size said the sherds survived that.

**Those numbers cannot answer the question.** A six-pixel rim taken off a fracture edge is
exactly the geometry a reassembly matcher reads. The statistic and the thing at stake are
about different parts of the object.

## What is already known

- Six pixels is **at the limit** on fracture ridges — measured on A03, not comfortably
  clear of it.
- The **clamp-contact surface is still unobserved**: not measured badly, not measured at
  all. A join that runs through it cannot be assessed.
- Separately, the clamp edge produces a mixed-pixel strip about **0.6 mm** wide in
  `Densify`, which is where the horn artefacts came from — the clamp costs geometry in
  more than one way.

## Done when

- [ ] The shrunk outline drawn on the photographs at a zoom where six pixels are obvious,
      on fracture edges specifically, not on the sherd outline generally
- [ ] A statement of how much break face is lost, in **millimetres of arc length**, not in
      pixels or vertex counts
- [ ] The clamp-contact surface either observed by a re-mount, or written down as
      permanently unobserved with the consequence spelled out for anyone reading a join
      that crosses it

## Gate

If the loss is a material fraction of a typical break face, then the capture rig has to
change — a different mount, or two mounts per sherd — and no amount of downstream
processing recovers it. That is a fieldwork decision with a long lead time, so it should
be reached early rather than at write-up.

## Source

`docs/notes/2026-08-20-erosion-fracture-overlay-design.md`;
`docs/notes/A03_BENT_SOLVE_AND_CLAMP_ARTEFACTS.md` §3;
`docs/notes/03072025-N01_TAIL_FIX.md`.
