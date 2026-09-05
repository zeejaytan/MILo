# M3 — How do we know a mesh is at true scale?

**Status:** open — **every one of the 118 captures now states where its millimetres come
from** (2026-09-04): 117 from the blue base plate, 1 from the turntable marker board. The
corpus is not halved and never was; the earlier "59 of 118" was a *marker* count wearing a
*scale* count's name. A mesh that cannot state its units is refused rather than measured
(`compare_meshes.py`), and a crop keeps the record of the mesh it was cut from. The
section picture exists and can show an 8% error (2026-09-05, `section_overlay.py`). What is
left is a bench measurement — **no sherd has been checked against a caliper** ·
**Blocked by:** none · **Effort:** one bench sitting

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
  printed pitch was measured with a ruler on the physical sheet at **40 mm**.
  **The board is the tighter instrument and the looser ruler, and the two must not be
  confused** (corrected 2026-09-04): its lattice fits to a fraction of a millimetre — rms
  0.196 mm over 16 coded targets, pitch SD 0.0146 mm on a 40 mm pitch — but its *absolute
  size* rests on a single ruler reading of a printed sheet, so its accuracy is capped at
  about **±1.25%**, looser than the plate's long edge verified to **0.42%**. Deriving board
  references for more captures would buy **repeatability, not accuracy**.
- **The N01 Metashape chunk is 1.2–1.4% too large** — about **1.2–1.4 mm on a 100 mm
  sherd** — from one misplaced click on a hand-clicked scale bar. Recorded in
  `docs/reference/turntable-board-03072025-N01.json`; apply it if any N01 measurement is
  taken from Metashape. **This is a broken measurement, not a broken method or a wrong
  reference.**
- **The blue plate itself is fine, and A01–A04 need no correction.** Two routes that never
  touch Metashape both land where a 190 × 130 mm plate should. Those meshes were never
  scaled through the broken reference.
- **The scanning record enumerates every capture, flags marker usability, and — since
  2026-09-04 — states each capture's scale source.** **118 captures**, all with files on
  disk. **59 have a usable marker** — 19 in 2025 from `2025-07-03/N01` onward, plus all 40
  in 2026. **59 do not** — every 2025 capture before `2025-07-03/N01`, marker placed
  incorrectly.
- **A usable marker is not a scale source, and conflating the two was the error here.**
  `markers_usable` answers *may I align on this*. The record says so in its own words: N01's
  measurement cell reads *"Use base as scale, marker on turntable for alignment"*. The
  board's factor is derived by fitting a capture's own cameras onto it, and only
  `docs/reference/turntable-board-03072025-N01.json` has ever been derived — so the board is
  the ruler for **one** capture, not 59. The plate is the ruler for the other 117, because
  each season's sheet declares it at the top: 2025 *"Top of the tree base (blue metal base)
  = 13x19cm"*, 2026 *"Top of the tree base (metal base) = 13x19cm"*.
- **2026's plate is credited from 2026's own line, and the 0.42% check was not repeated on
  it.** 2026's sheet says only "metal base", and nothing in the record says it is the same
  object as 2025's. Same dimensions is not the same object measured.
- **A scale sidecar already exists.** `scale_mesh.py` writes `<mesh>.scale.json`.
- **The reconstruction pipeline already gates on the board** where a reference exists
  (`slurm/reconstruct_group.slurm`, strict branch, exit 3 = the check could not be made and
  the job stops). Nothing gates on scale *after* the mesh is built.

## The gap that makes this live

**A mesh can lose its sidecar and nothing notices.** `scale_mesh.py` writes
`<mesh>.scale.json`, but anything that *derives* a mesh — cropping, decimating, re-exporting
— produces a file with no sidecar beside it. The scaled parent knew what units it was in;
the crop does not, and looks identical.

**Cropping is closed. 2026-09-04** (`.scratch/scale-provenance/issues/03`): `crop_mesh.py`
carries the parent's statement onto the crop, naming the mesh it was cut from and what the
cut kept, and the read-out marks an inherited scale as inherited rather than letting it read
like one taken off the object. Provenance is carried, never invented — a crop of an unscaled
mesh gets nothing, and is refused downstream. Verified on A02: the fresh crop of
`milo_mm.ply` (4,766,738 of 7,352,174 faces, 731.6 × 450.8 × 509.6 mm) compares at exit 0
and prints `cut from milo_mm.ply`; the crop made before this work still exits 2. The same
work found and closed a hole it would otherwise have widened — `scale_mesh.py` looked only
at the PLY header, which a crop no longer has, so a crop could have been scaled a **second**
time: 377× too large, invisible in the file.

**Decimating and re-exporting are still open**, and so is sherd extraction — sixteen meshes
in `artifacts/A03_metric/` still have no scale record. They are refused rather than measured,
which is the correct state until those scripts are next touched.

`compare_meshes.py` and `crop_mesh.py` are the only two scripts that hold the line. Every
other one that reports millimetres still takes the units on trust, and
`silhouette_compare.py` still falls back to `mm_per_unit = 1.0` when the sidecar is absent —
the degrade-to-default that ADR 0001 exists to ban.

## Done when

- [x] **Every one of the 118 captures has a stated scale source**, recorded with the
      capture rather than inferred later, with the rule able to say **non-metric** so
      nothing quietly measures against a capture that has none. **Done 2026-09-04**
      (`.scratch/scale-provenance/issues/02`, commits `92772e8`, `8ed9c29`): **118 of 118**
      — 117 from the blue base plate, 1 (`2025-07-03/N01`) from the marker board. Each
      entry carries what the source is, how it was established, what it is worth, the
      reference file where there is one, and the sheet's own declaring words. The gate is
      `build_scanning_record.py --scale-check <capture>`: exit 0 metric, 2 non-metric,
      **3 when the record cannot answer** — "cannot answer" is not "no", and conflating them
      would mark the whole corpus unmeasurable the moment the JSON went stale. The
      non-metric branch is **live, not decorative**: the plate counts because the sheet
      declares it, so a season that stops declaring it becomes non-metric, and the self-test
      drives that branch on a fixture season with no declaration. 26 checks; 8 deliberate
      mutations, all 8 caught
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
- [x] **One before/after picture**: the same two meshes overlaid, with the millimetre scale
      bar burnt in, at a view that resolves the wall — the sherd in **section**, not a
      three-quarter view of the whole body, because a scale error is a proportional change
      and a whole-object view cannot show one.
      **Done 2026-09-05** (`.scratch/scale-provenance/issues/04`, commit `3ab761e`).
      `scripts/section_overlay.py` cuts both meshes with **one** plane and measures the wall
      across the section in millimetres — a cut, not a rendered viewpoint, because a
      viewpoint is the instrument that has failed four times here. On synthetic geometry an
      8% error is unmistakable: two 6 mm walls, one of them 6.48 mm, at 7.2 px/mm —
      `artifacts/section/demo_8pc.png`.
      **The reading is that the instrument works, not that A02 has been checked.** The real
      cut (`artifacts/section/A02_sherd_y.png`) reports a wall of 3.64 mm on the OpenMVS
      mesh, with a thinnest-5% of 1.08 mm and a longest chord of 11.78 mm — a spread that
      wide is not one wall — and the crop it was taken from leaves four separate lumps, of
      which only one has a MILo outline beside it. The figure also depends on which mesh is
      named first (naming `milo` first gives 8.89 mm across one outline), because that mesh
      supplies the plane and is also the mesh measured; the caption states this on the
      picture. Nothing here is a claim about either method's accuracy — it is failure mode
      2, the ruler, made visible. 50 checks; 12 deliberate mutations, all 12 caught

## Gate

Where scale cannot be established for a capture, that capture may still be used for **shape**
questions but must not enter any **size-dependent** measurement. Say which is which in the
capture record.

**The scope statement, as of 2026-09-04: the metric corpus is the whole corpus.** All 118
captures can state a scale source, so none is barred from size-dependent measurement on
these grounds, and nothing is halved. That is a statement about *provenance*, not accuracy:
117 of them rest on a plate whose long edge is verified to 0.42% and whose short edge is
not, and 40 of those are a 2026 rig on which that check has never been repeated. A season
whose sheet stops declaring the plate would become non-metric, and `--scale-check` would
say so — the rule can fail, which is what makes "118 of 118" a finding rather than a
memory.

## Source

`docs/notes/2026-08-22-turntable-markers.md` §8, §10, §11; `docs/reference/scanning-record.json`;
workspace `docs/glossary.md` (chamfer distance and normalisation); `../AGENTS.md` traps.
