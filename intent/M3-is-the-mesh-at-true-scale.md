# M3 — How do we know a mesh is at true scale?

**Status:** open — **a verified route exists for 59 of 118 captures; the other 59 have no
scale source and nothing marks them** · **Blocked by:** none · **Effort:** ~1 day

## Why it matters

Photogrammetry recovers shape up to an unknown overall size. Something in the scene has to
supply the millimetres. If that something is wrong, **every measurement downstream is wrong
by a constant factor and still looks entirely plausible** — a sherd 8% too large is not
visibly a mistake.

It matters most where sizes are compared. Chamfer distance depends on object size unless
the data is normalised, and that has already produced a false finding in this workspace.
Two meshes at two scales will compare cleanly and mean nothing.

**How much error is too much is now answerable in physical terms.** M1 puts the resolution
the material needs at about **0.21 mm**, with 0.822 mm currently reached. A scale error of
1% on a 100 mm sherd is **1 mm** — several times the entire resolution budget, and larger
than the difference between the two extraction routes M1 is trying to choose between. So a
scale error large enough to matter is small enough to be invisible.

## What is already known

- **The metric route is built and verified** (2026-08-23). The turntable marker board's
  printed pitch was measured with a ruler on the physical sheet at **40 mm**, giving a
  reference about sixty times tighter than the blue base plate.
- **The N01 Metashape chunk is 1.2–1.4% too large** — about **1.2–1.4 mm on a 100 mm
  sherd** — from one misplaced click on a hand-clicked scale bar. Recorded in
  `docs/reference/turntable-board-03072025-N01.json`; apply it if any N01 measurement is
  taken from Metashape. **This is a broken measurement, not a broken method or a wrong
  reference.**
- **The blue plate itself is fine, and A01–A04 need no correction.** Two routes that never
  touch Metashape both land where a 190 × 130 mm plate should. Those meshes were never
  scaled through the broken reference.
- **The scanning record enumerates every capture and flags marker usability**:
  **118 captures**, all with files on disk. **59 have a usable marker** — 19 in 2025 from
  `2025-07-03/N01` onward, plus all 40 in 2026. **59 do not** — every 2025 capture before
  `2025-07-03/N01`, marker placed incorrectly.
- **A scale sidecar already exists.** `scale_mesh.py` writes `<mesh>.scale.json`.
- **The reconstruction pipeline already gates on the board** where a reference exists
  (`slurm/reconstruct_group.slurm`, strict branch, exit 3 = the check could not be made and
  the job stops). Nothing gates on scale *after* the mesh is built.

## The gap that makes this live

**A mesh can lose its sidecar and nothing notices.** `scale_mesh.py` writes
`<mesh>.scale.json`, but anything that *derives* a mesh — cropping, decimating, re-exporting
— produces a file with no sidecar beside it. The scaled parent knew what units it was in;
the crop does not, and looks identical.

`compare_meshes.py` now refuses such a mesh rather than measuring it (below). Nothing else
does. Every other script that reports millimetres still takes the units on trust, and
`silhouette_compare.py` still falls back to `mm_per_unit = 1.0` when the sidecar is absent —
the degrade-to-default that ADR 0001 exists to ban.

## Done when

- [ ] **Every one of the 118 captures has a stated scale source**, recorded with the
      capture rather than inferred later. For the 59 with a usable marker that is the board;
      for the other 59 it is either a named alternative or the capture is **marked
      non-metric** so nothing quietly measures against it
- [ ] **A round-trip on at least one sherd**: a caliper measurement in millimetres against
      the same dimension read off the mesh, with the **disagreement** reported, not the
      agreement. Judged against **the precision the mesh's own sidecar declares** — about
      1% today, because the 190 × 130 mm plate has its long edge verified to 0.42% and its
      short edge unverified. A fixed target would ask the mesh to beat its own reference,
      and would go stale the moment the short edge is checked. Report the number whether it
      passes or not. **This one is a bench measurement, not a ticket** — it needs the
      physical sherd; it lands in `docs/notes/`
- [x] **`compare_meshes.py` refuses to compare two meshes whose scale it cannot establish.**
      **Done 2026-09-03** (`.scratch/scale-provenance/issues/01`). It reads `.scale.json`
      for both before loading anything, and exits 2 if either is missing and 3 if the two
      disagree on units; `--shape-only` is the named way to run the unit-free half.
      `--self-test` asserts the exit status on synthetic fixtures, so the gate is proved
      able to fail rather than only observed to pass — that was the `check_turntable.py`
      lesson. It also fixed the defect underneath: `frac_within_0.5mm` was computed against
      a raw 0.5 in whatever units the mesh happened to be in. **Reviewed and corrected
      2026-09-04**: as first written the gate refused `mm` against `millimetres` as a unit
      conflict, and `--shape-only` still wrote the scale factor into the report — a gate
      that rejects correct work, and a suppression one multiplication from leaking. Both
      fixed and asserted
- [ ] **One before/after picture**: the same two meshes overlaid, with the millimetre scale
      bar burnt in, at a view that resolves the wall — the sherd in **section**, not a
      three-quarter view of the whole body, because a scale error is a proportional change
      and a whole-object view cannot show one

## Gate

Where scale cannot be established for a capture, that capture may still be used for **shape**
questions but must not enter any **size-dependent** measurement. Say which is which in the
capture record.

If the 59 unmarked captures have no alternative scale source, that is not a failure — it is
a scope statement, and it halves the metric corpus. Record it as such rather than letting
those captures drift into a comparison later.

## Source

`docs/notes/2026-08-22-turntable-markers.md` §8, §10, §11; `docs/reference/scanning-record.json`;
workspace `docs/glossary.md` (chamfer distance and normalisation); `../AGENTS.md` traps.
