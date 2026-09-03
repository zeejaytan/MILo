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

**Status:** ready-for-agent

- [ ] Every one of the 118 entries carries a named scale source, or is explicitly marked
      non-metric — no entry is silent
- [ ] The field is written by the script that generates the record, not patched in by
      hand, so a re-run does not lose it
- [ ] The read-out states the counts in plain terms: how many captures are metric, by
      which source, and how many are not
- [ ] The base plate's caveat travels with it — a capture scaled from the plate says so,
      and says the precision is about 1%, not the board's much tighter figure
