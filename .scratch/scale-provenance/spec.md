# Scale provenance: a mesh must be able to say what units it is in

**Answers:** `M3` (how do we know a mesh is at true scale?)
**Status:** ready-for-agent
**Branch:** `scale-provenance`

## Problem Statement

Every measurement taken off a reconstructed sherd is in millimetres only because something
in the scene supplied the millimetres. If that something is wrong, or was never applied,
**every downstream number is wrong by a constant factor and still looks entirely
plausible** — a sherd 8% too large is not visibly a mistake.

Two things are true in this repo right now:

1. **The comparison script cannot tell.** `compare_meshes.py` computes point-to-surface
   distance whose own docstring says the result is *"in mesh units"*, then reports it as
   `frac_within_0.5mm` and `frac_within_1mm` against hardcoded thresholds. Its
   `--mm-per-unit` flag reaches only the render's scale bar, never the distance
   calculation, and it never reads the scale sidecar that would tell it. A mesh in any
   units other than millimetres yields a millimetre agreement figure that is not in
   millimetres, and nothing in the script can notice.

2. **Derived meshes lose their provenance.** `scale_mesh.py` writes a `<mesh>.scale.json`
   sidecar recording the factor, the source, the internal disagreement and a stated
   precision. Every script that derives a new mesh — cropping, sherd extraction, erosion —
   writes a `.ply` and no sidecar. The geometry is still in millimetres; the *statement*
   that it is has been dropped.

This blocks a specific piece of research. `M1` asks whether MILo or OpenMVS reaches the
resolution a break face needs, and its criterion is that the two are *"compared on the
same ruler."* That comparison runs through the script in (1), on meshes derived by the
scripts in (2).

**This is failure mode 2 — the measurement is broken — not a failure of either
reconstruction method.** Nothing here says a mesh is wrong. It says we cannot currently
demonstrate that it is right.

## Solution

A mesh carries its scale claim with it, and the script that compares two meshes refuses to
report millimetres unless both claims are present and agree.

Concretely, from the user's perspective:

- Comparing two meshes that both know their scale works exactly as it does today, plus the
  scale source and its stated precision are printed with the results.
- Comparing a mesh that does not know its scale **stops with a non-zero exit** and says
  which mesh and why.
- Where only shape matters, an explicitly requested mode runs the scale-free half of the
  comparison — silhouette agreement on held-out views — and suppresses every millimetre
  figure rather than printing one that cannot be trusted.
- Cropping a mesh carries the sidecar forward, so a crop is as trustworthy as its parent
  and says so.
- The round-trip against a physical caliper measurement is reported as a **disagreement in
  millimetres**, and is judged against the precision the mesh's own sidecar declares
  rather than against a number chosen by hand.

## User Stories

1. As a conservator, I want a comparison between two meshes to refuse to run rather than
   report a millimetre figure it cannot stand behind, so that no result enters my notes
   whose units are unknown.
2. As a conservator, I want to know which physical object supplied the millimetres for a
   given mesh, so that I can judge how much a measurement from it is worth.
3. As a conservator, I want the stated precision of that scale source printed beside every
   millimetre result, so that I do not read three decimal places off a 1% ruler.
4. As a conservator, I want a mesh whose scale cannot be established to still be usable for
   shape questions, so that half a capture season is not discarded for a reason that does
   not apply to shape.
5. As a conservator, I want shape-only mode to be something I ask for by name, so that it
   can never happen silently and be mistaken for a metric result.
6. As a conservator, I want a cropped sherd to carry the same scale record as the mesh it
   was cut from, so that the crop I actually measure is as accountable as the whole tree.
7. As a conservator, I want a caliper measurement compared against the mesh with the
   **disagreement** reported, so that agreement is a finding rather than an assumption.
8. As a conservator, I want the caliper check judged against the mesh's own declared
   precision, so that the test does not go stale when the reference improves.
9. As a conservator, I want a picture of the two meshes overlaid with a millimetre scale
   bar, in section, so that a proportional error is visible rather than merely computed.
10. As a conservator, I want every capture in the record to name its scale source, so that
    I can see at a glance how much of the corpus is metric.
11. As a conservator, I want captures with no scale source marked non-metric, so that
    nothing quietly measures against them later.
12. As a researcher, I want the M1 route comparison to be demonstrably on one ruler, so
    that a resolution difference between MILo and OpenMVS means what it says.
13. As a researcher, I want a large internal disagreement inside a scale measurement
    surfaced beside the result, so that a 5.4% cross-cloud gap is not reachable only by
    opening a JSON file.
14. As a researcher, I want the refusal to be an exit status and not a printed warning, so
    that a pipeline stops instead of continuing past it.
15. As a researcher, I want the gate proved able to fail, not only observed to pass, so
    that a gate that always passes is distinguishable from one that works.
16. As an agent working here later, I want the sidecar's meaning written down once, so
    that I do not infer the contract from one example and get it wrong.

## Implementation Decisions

**Q1 — the caliper tolerance is derived, not fixed.** The round-trip is judged against the
precision the mesh's own sidecar declares, not against a hand-chosen constant. The current
sidecars state `precision ~1%`, because the 190 x 130 mm reference has its long edge
verified to 0.42% against the marker board and its short edge unverified — and the factor
is the mean of both. A fixed 0.5% target would demand the mesh beat its own reference, and
would go stale the moment the short edge is checked. The disagreement in millimetres is
reported whether it passes or not.

**Q2 — refuse by default, degrade only on request.** Missing or disagreeing scale is a
non-zero exit. A `--shape-only` flag runs silhouette agreement on held-out views, which the
script's own documentation states is unaffected by mesh units, and suppresses every
millimetre figure including the surface-disagreement block, the wall-thickness
distribution and the scale bar. A check that prints and continues is not a gate; that
lesson is already recorded in this repo, where the turntable check was called with
`|| true` and could not fail.

**Q3 — scope is the comparison script plus one shared helper, wired into cropping only.**
The helper reads a sidecar, and writes a derived sidecar that records its parent and what
operation produced it. It is wired into mesh cropping, because crops are what the M1
comparison actually consumes. Sherd extraction and erosion outputs are left for whenever
those scripts are next touched — the helper makes that a small change rather than a
rewrite.

**Q4 — the blue base plate is an accepted scale source, with its caveat carried.** It is
the only physical scale present in the pre-marker captures, its measurement script already
refuses rather than reports when its own checks fail, and it is verified to 0.42% on one
edge. A stated source with a stated weakness is a scale source; an unstated one is the
problem. What is added is a per-capture field naming which source was used, not a new
instrument.

**Q5 — internal disagreement is surfaced, not disqualifying.** A mesh whose sidecar records
`accepted: true` is treated as scaled, even where a sub-measurement was rejected. But every
disagreement figure the sidecar carries — between the two plate edges, and between the
sparse and dense clouds — is printed beside the millimetre results. Rejecting such meshes
outright would discard the capture M1 depends on; hiding the figure is how a 5.4% gap stays
invisible.

**The sidecar is the contract.** It already carries units, the factor, the source, the
per-edge measurements, an `accepted` flag, the disagreement figures, a stated precision and
a reference check. Nothing new is invented; what changes is that a second script now reads
it. Two meshes are comparable when both declare millimetres and neither is missing.

**The comparison prints provenance with results.** Scale source, stated precision, and the
disagreement figures, for both meshes, above the numbers rather than in a footnote.

## Testing Decisions

**A good test here asserts the exit status, not the printed text.** This is not a general
principle imported from elsewhere — it is the specific mistake this repo has already made.
`check_turntable.py` printed a correct page of disagreeing frames while returning 0, so the
frame count was right and the gate was dead. The fix was making the self-test assert the
status. Anything that only checks output would pass on a gate that never stops anything.

**One seam: `compare_meshes.py --self-test`**, following `check_turntable.py` exactly.
Synthetic meshes are built in a temporary directory with sidecars written by hand, the real
comparison path is run, and the exit status is asserted against an answer known in advance.
No new test framework, no `tests/` directory; this repo has neither, and adding one for a
single seam would be a second convention.

The cases, each with its right answer fixed in advance:

- both meshes declare millimetres and agree → **0**, and the millimetre block is present
- one mesh has no sidecar → **non-zero**, and no millimetre figure is printed anywhere
- the two sidecars disagree on units → **non-zero**
- no sidecar, `--shape-only` requested → **0**, silhouette figures present, every
  millimetre figure absent
- a sidecar carrying a rejected sub-measurement and a large cross-cloud disagreement →
  **0**, with the disagreement printed

**Prior art:** `check_turntable.py:self_test` — three synthetic COLMAP models, answers known
in advance, statuses asserted. Its docstring states the reasoning and should be read before
writing this one.

**The picture is an acceptance criterion, not a debugging step.** One overlay of the two
meshes with the millimetre scale bar burnt in, **in section** — a proportional error cannot
be seen in a three-quarter view of a whole sherd, and four successive views in this repo
have already failed by being too coarse for the effect being tested.

**The caliper round-trip is a measurement, not a unit test.** It needs the physical sherd
and is recorded in `docs/notes/`, with the disagreement in millimetres stated whichever way
it comes out.

## Out of Scope

- **Re-scaling any existing mesh.** Nothing here changes a factor. A01–A04 were never
  scaled through the reference found to be misplaced and need no correction.
- **Improving the scale reference.** Verifying the plate's short edge is real work and a
  separate question; this spec carries the existing caveat rather than removing it.
- **Sherd extraction and erosion sidecars.** The helper makes these small; they are not
  done here.
- **Marker-guided matching.** Measured and recommended against for this material.
- **Anything about which reconstruction route is better.** That is `M1`. This spec only
  makes its comparison trustworthy.
- **A test framework.** One seam, one self-test, the existing convention.

## Further Notes

**Weight.** Two captures (A02, A03) carry sidecars today. Everything measured here is on
those, so the self-test's synthetic fixtures are what prove the gate — not the corpus.

**The record side is countable.** 118 captures, all with files on disk; 59 have a usable
marker (19 in 2025 from `2025-07-03/N01` onward, all 40 in 2026) and 59 do not. Under Q4
the base plate covers the second group, so this is a recording task rather than a
measurement one — but it is a task, and until it is done the corpus cannot say how much of
itself is metric.

**Vocabulary.** *Scale source*, *metric mesh*, *sidecar* and *accepted* are used
consistently across these scripts and defined nowhere. They belong in `CONTEXT.md`, which
does not yet exist and should be created when the first of them is actually pinned down.

**Likely ADR.** Refuse-versus-degrade (Q2) is hard to reverse once other scripts depend on
the behaviour, is surprising without the `|| true` history behind it, and is a real
trade-off against usability. That is all three tests, so it should be written down.
