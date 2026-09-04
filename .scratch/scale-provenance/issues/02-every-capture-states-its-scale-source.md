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
