# 02: Every capture states where its millimetres come from

**What to build:** the scanning record answers, for all 118 captures, the question "what
physical object supplied the millimetres here?" — the turntable marker board, the blue
base plate, or nothing. Captures with no source are marked **non-metric**, so a later
comparison cannot quietly measure against them and neither can a later agent.

This is a recording task, not a measurement one: the marker usability is already in the
record, and the base plate is an accepted source for the pre-marker captures. What is
missing is the statement. Until it exists, the corpus cannot say how much of itself is
metric, and "59 of 118" is a fact we happen to remember rather than one the data asserts.

**Answers:** `M3`

**Blocked by:** None (can start immediately)

**Status:** done - 2026-09-04

- [x] Every one of the 118 entries carries a named scale source, or is explicitly marked
      non-metric — no entry is silent
- [x] The field is written by the script that generates the record, not patched in by
      hand, so a re-run does not lose it
- [x] The read-out states the counts in plain terms: how many captures are metric, by
      which source, and how many are not
- [x] The base plate's caveat travels with it — a capture scaled from the plate says so,
      and says the precision is about 1%, not the board's much tighter figure

## Comments

**2026-09-04 — done on branch `markers-turntable`.**

**The ticket's premise was wrong, and the correction matters more than the code.** It
assumed a usable marker meant the marker supplied the millimetres — "59 of 118 are metric".
It does not. The record itself keeps the two apart: N01's own measurement cell reads *"Use
base as scale, marker on turntable for alignment"*. `markers_usable` answers *may I align
on this*, which is a different question from *what supplied the millimetres*.

Three things came out of reading the spreadsheets rather than the ticket:

- **The board is a scale source for exactly one capture**, `2025-07-03/N01`, because the
  factor is measured by fitting that capture's own cameras onto the board and only
  `docs/reference/turntable-board-03072025-N01.json` has been derived. Crediting the other
  58 to the board would have invented 58 measurements — the thing this feature exists to
  stop.
- **The plate covers both seasons**, because each sheet declares it at the top: 2025 *"Top
  of the tree base (blue metal base) = 13x19cm"*, 2026 *"Top of the tree base (metal base)
  = 13x19cm"*. That is the record's own statement about the rig, and the rig is in every
  capture.
- **So no capture is non-metric.** 118 of 118 can state a source: 117 the plate, 1 the
  board. The corpus is not halved. What is halved is nothing — the earlier "59 of 118"
  was a marker count wearing a scale count's name.

The 2025 `measurement` cells (*"Mark1-2: 18cm, mark3-4: 42.4cm"*) are hand-ruled distances
between marks on the rig. They are kept as `scale.recorded`, beside the source rather than
folded into it: they corroborate, they are not the ruler, and promoting them would quietly
re-scale seventy captures.

**The non-metric branch is live, not decorative.** The plate is a source *because the sheet
declares it* — `plate_declaration()` matches the note, and a season that stops declaring it
becomes non-metric. That rule can fail, which is the point: "118 of 118" is now something
the data asserts and could stop asserting, not something we remember. The self-test drives
that branch on a fixture season with no declaration, because no real capture triggers it
today and an unexercised branch is an unchecked one.

**Two gates, two questions.** `--check` (exit 2) still answers *may I align on the marker*.
`--scale-check` (exit 2) answers *may I take a millimetre off this*. They disagree on real
data and the self-test asserts the disagreement: `03072025/M04` fails `--check` and passes
`--scale-check`. A stale record exits **3**, not 2 — "cannot answer" is not "no", and
conflating them would mark the whole corpus unmeasurable the moment the JSON went stale.
`find_capture` is shared so the two cannot drift into answering one question about a
different capture.

**A defect this work caused, found, and fixed.** Rebuilding the record on a day the capture
drive was unplugged **deleted all 118 frame counts** from the committed JSON, and the
deletion looked exactly like a record that never had them. `carry_disk_counts` now carries
the last scan forward and the Markdown says *CARRIED FROM AN EARLIER SCAN, not re-counted*.
The regenerated JSON is now purely additive against `HEAD` — 1063 insertions, 0 deletions.

**Checks: 25, all passing, and seven deliberate mutations were each caught by the check
meant to catch it** — the plate assumed instead of read, a usable marker treated as a
ruler, a stale record answering "no", the gate never refusing, a board reference nobody can
open accepted, the frame counts dropped, and a non-metric capture handed the plate's
precision.

**Not fixed, pre-existing:** `--check 16062025/A01` exits 3 because that capture's
directory is the bare date with no per-tree subdirectory, so the directory-name lookup
misses it. `--check 2025-06-16/A01` works. Same on `HEAD`; not introduced here.

### What `/code-review` changed (2026-09-04, after the above)

The review ran two axes against `1d16acf`. Seven findings held up; all are fixed here.
Two of them were **wrong statements**, not untidy ones — the record was telling a
conservator something false:

- **The read-out inverted precision and accuracy.** It said deriving board references for
  the other 58 captures "would tighten them". The board is the tighter *instrument* (16
  coded targets, lattice fit far below a millimetre) but the *looser ruler*: its absolute
  size is a ruler reading of the printed sheet at ±1.25%, against the plate's long edge
  verified to 0.42%. Deriving them buys **repeatability, not accuracy**, and the summary
  now says so. It had contradicted the comment in `scale_sidecar.py` that explains exactly
  this.
- **2026 was credited with a check made on the 2025 rig.** All 40 of 2026's captures were
  stamped `blue base plate` with a caveat quoting the 0.42% long-edge verification — which
  was made through `2025-07-03/N01`, on the 2025 rig. 2026's sheet says only "metal base",
  and nothing in the record says it is the same object. The caveat now names where the
  check was made and states it has **not** been repeated on any later rig. Same dimensions
  is not the same object measured.
- **`PLATE_HOW` asserted more than the record does** — "the one physical scale present in
  every capture of that season" is a claim about the rig, not a reading of the sheet. It
  now says what the sheet declares, and that unocclusion is what `scale_mesh.py` finds out
  per mesh.
- **Two gates could be asked at once.** `--check` and `--scale-check` together made the
  exit status ambiguous about which question it answered. `ap.error` now refuses the pair.
- **`frame_counts_from` could be read half-way.** It carried a bare drive name with a
  sibling `frame_counts_rescanned: false` beside it saying not to believe it. One value
  now carries the whole sentence, the sibling key is gone, and `to_markdown` lost the
  parameter that travelled with it (Standards: Data Clumps).
- **`carry_disk_counts` sat below the self-test banner** in a file already edited for two
  reasons (Standards: Divergent Change). Moved up with the other record-building code.
- **The `recorded` docstring called all the cells hand-ruled distances.** Fourteen are the
  record's clearest scale statement — *"Use base as scale, marker on turntable for
  alignment"*. The paragraph now says both, which is why the cells are carried whole and
  printed rather than parsed.

**A defect the fixes themselves introduced, found by the self-test.** Wrapping the drive
name in the CARRIED sentence made `carry_disk_counts` non-idempotent: a second rebuild on
a second unplugged day would have wrapped the sentence inside itself, and a third inside
that. It is now a no-op on an already-carried value, and there is a check for it.

**Checks: 26, all passing. Eight deliberate mutations, all eight caught** — the seven from
the first pass plus the re-wrapping one above.

Two review points were **considered and rejected, with reasons**:

- *Drop `--scale-check` and the second `--self-test` seam.* Kept. The gate is what makes
  the field enforceable rather than decorative, and the spec's "one seam" line bans a test
  *framework*, not a second `--self-test` in a second script.
- *Create `CONTEXT.md`.* Not created. `AGENTS.md` says `/domain-modeling` writes it lazily
  when the first term is actually resolved, and explicitly that it must not be created
  empty.

**The regenerated record is not purely additive any more, and should not be.** 238
insertions against 239 deletions: 117 `precision` lines and 117 `how` lines carry the
corrected wording, and the two `frame_counts_*` header keys became one. All 118 entries
still carry `on_disk` and all 118 carry `scale` — no data was dropped.
