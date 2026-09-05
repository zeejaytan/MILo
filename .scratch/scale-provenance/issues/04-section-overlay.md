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

**Status:** done — 2026-09-05

- [x] The render is a section through the wall, at a view that resolves wall thickness —
      not a whole-object view
- [x] Both meshes appear in the same picture, distinguishable, in the same frame
- [x] The millimetre scale bar is burnt in and is correct for the units the sidecars
      declare — it does not fall back to assuming 1.0
- [x] In `--shape-only` mode no scale bar is drawn, and the picture does not imply a size
- [x] The render is written whatever the numbers say

## Comments

**2026-09-05 — done on branch `markers-turntable`.** `scripts/section_overlay.py`.

**A cut, not a render — and the plan this replaced was the wrong instrument twice over.**
The ticket was carried forward with a note that it needed nvdiffrast on a GPU node.
Checked before spending anything: nvdiffrast is a *differentiable* rasteriser and nothing
here needs gradients; `render_mesh.py` already rasterises on this laptop with no GPU; and,
decisively, a rasterised viewpoint is the exact instrument that has failed in this repo
four times by being too coarse for the effect under test. `trimesh.Trimesh.section()`
gives the wall outline itself, in millimetres, with no viewpoint to get wrong — the
workspace rule "when a proxy view keeps failing, render the measured quantity itself".
Worth doing; not worth doing with nvdiffrast for this. No GPU allocation, no job sign-off.

**The picture answers the question the numbers cannot.** A sherd 8% too large looks like a
sherd. Two 6 mm walls, one of them 8% oversize, cut and overlaid, are unmistakable:
`artifacts/section/demo_8pc.png`.

On real data, `artifacts/section/A02_sherd_y.png` cuts A02's crop on the y axis and is
worth describing exactly, because it is less tidy than a first read of it suggested. The
cut leaves **four separate lumps** of the OpenMVS mesh spread across the tray, and only the
top-right one has a MILo outline beside it; the other three MILo marks on the picture are
single specks. Where the two do sit together, MILo's outline runs a little outside
OpenMVS's. That is **one plane through one crop**, and three quarters of what the plane hit
has nothing to compare against — not a statement about either method's accuracy.

The figure reads **wall 3.64 mm on 'openmvs'**, at 8.9 px/mm, with a 20 mm bar burnt in —
and the spread printed beside it is the part to read: thinnest 5% **1.08 mm**, longest
**11.78 mm**. A median with that much either side of it is not a clean wall measurement; it
is a median over three outlines of a broken crop, and the caption now says so on the
picture rather than leaving the bare 3.64 to be quoted.

**The figure depends on which mesh is named first, and by a lot.** The cut is one plane
through the first mesh's centroid, and that mesh is also the one measured. `--mesh
openmvs=… --mesh milo=…` gives 3.64 mm across three outlines at 8.9 px/mm; naming `milo`
first gives **8.89 mm across one outline at 13.3 px/mm** — a different plane through a
different mesh. Nothing printed is false (the caption names the mesh), but the dependency
was far too quiet, so the caption now states it in the picture.

`A02_sherd_shapeonly.png` is the same cut with no bar and no unit anywhere.

**Five defects were found by looking at the pictures, not by the self-test.** Each is now
a check, so none can come back quietly.

- **Chords 700 mm long across an empty turntable**, medianed into a confident "wall
  14.59 mm". Nothing stopped a measuring ray leaving the clay. Fixed with an even-odd
  parity test on each chord's midpoint.
- **Two cutting planes instead of one.** The origin was each mesh's own centroid, so two
  meshes were cut in different places and each outline re-centred on itself — a placement
  error would have vanished into the frame. One shared plane now, from the first mesh
  named; `--offset` moves that plane, never one mesh's.
- **"wall 0.13 mm"** on the real crop: dozens of sub-millimetre stray fragments outnumber
  the clay and win a median. Outlines shorter than a tenth of the longest are now drawn
  but not measured, and the caption says how many of each.
- **A zoomed view spilled over its own scale bar and caption.** The cut is drawn on its own
  image and pasted in, so it is clipped at the panel edge.
- **`--shape-only` slid the two meshes apart**, inviting a reader to see a disagreement
  that is not in the geometry. One shared normalisation now, from the first mesh.

**A sixth, found by re-reading the picture after the fix: the caption had gone stale.** The
shape-only footer still said "each outline is scaled to its own extent" — describing the
code as it was two fixes earlier. A caption that misdescribes its own picture is the
failure this script exists to catch. Both captions are now returned in `info["notes"]` and
checked against the numbers the same run reported.

**50 checks pass, and 12 deliberate mutations were each caught.** Getting there mattered
more than the number. Mutations survived two sweeps, and each survivor exposed a test that
only looked like it tested its fix:

- **Every fixture was a hollow cylinder — a pot, not a sherd.** A cylinder cuts as two
  separate outlines, so a ray from the outer one always finds the inner one and the
  neighbour guard was never asked to do anything. A fragment cuts as ONE outline, out along
  the outside and back along the inside. `_sherd_fixture` builds one.
- **Casting the ray both ways was untestable, and untested, on every fixture.** Deleting
  the second cast changed no result anywhere — each fixture happens to be traced the
  agreeable way round. The input that tells them apart is the same outline traced
  backwards: with one cast it then measures nothing at all. Which way `section()` traces a
  loop is an accident of the mesh, not a fact about the pot, so that is the property worth
  asserting, and it now is.
- **The thin-wall case asserted "the wall is 40 px across"** — true by construction, since
  the window is sized from whatever wall was measured. It could not tell 0.8 mm from a ray
  that skipped the wall entirely. It now asserts the millimetres.
- **The speck case could not fail, and took three attempts to fix.** Forty 0.4 mm squares:
  an outline shorter than one sampling step is never sampled, so no number of them moves a
  median. Then long thin flakes around a hollow cylinder: a cylinder's outline is only
  ~250 mm, so the flakes had to stay short to fall under a tenth of it, and short outlines
  are eaten by the neighbour guard instead. Both versions passed with the filter **deleted**.
  What works is what the real crop is — one fragment with a 451 mm outline surrounded by
  20 flakes of 18 mm outline and 0.13 mm across. With the filter the wall reads 6.00 mm;
  without it, 0.13 mm, which is what A02 actually printed.
- **The centimetre case did not exist.** Every metric fixture had a factor of exactly 1.0,
  so "ignore the sidecar and assume 1.0" was invisible — which is box 3 of this ticket.

Two numbers beyond the median are now reported and asserted, because a median survives a
great deal of nonsense: the **longest** chord (where a ray across the tray shows) and the
**fifth percentile** (where the 2 mm gap to a neighbouring fragment shows).

**What this does not say.** Nothing here is a claim about MILo or OpenMVS. It is failure
mode 2 — the ruler — made visible. The 1 mm offset between the two outlines at A02 is one
cut through one crop of one capture: a lead, not a finding.

**Exit codes** follow ticket 01: 0 drawn, 2 a mesh has no scale record, 3 the records
disagree, and 4 (new) the plane misses every mesh. Nothing is written on 2, 3 or 4.

### What `/code-review` changed (2026-09-05, after the above)

Two axes against `9301cac`. Both found real things; all are fixed here.

**Spec axis — three that were implemented but wrong.**

- **Box 1 was a tautology.** "A view that resolves wall thickness" was checked by printing
  pixels-per-millimetre — but the window is *sized from* the wall figure, so that number is
  arithmetic on the figure and cannot disagree with it. The `THE VIEW IS TOO COARSE`
  warning it guarded was unreachable code. The warning is gone; the caption now says the
  px figure follows from the measurement rather than confirming it, and points the reader
  at the spread, which a bad measurement *can* contradict.
- **`--shape-only` dropped `--offset` from the caption**, so a cut the user had deliberately
  moved looked identical to one through the centroid. It is stated in every mode now, and
  in shape-only it says the offset is in the mesh's own units and not a physical length.
- **`.get(tag, 1.0)` was the degrade ADR 0001 bans** — a missing factor would have silently
  treated a metre-scale mesh as millimetres. Gone; past the gate every mesh has a factor,
  so it is indexed and a `KeyError` would be loud.

**Standards axis — three hard breaches.**

- The sidecar path was re-derived by hand in two fixtures instead of calling
  `sidecar_path()`, which is the standard `compare_meshes.py` states.
- A comment moved into `scale_sidecar.py` described failures that script does not have.
- `return 4, None` was a bare literal, absent from the exit-code table, the docstring and
  `--help`. It is `RC_PLANE_MISSES` now, named beside the shared ones.

Plus duplication: one `panel_px_per_mm()` and one `whole_view()` now replace four and three
copies. That was not cosmetic — the copy in the caption drifting from the one in the
drawing is exactly a ruler wrong about its own picture, so there is now a check that
projects a known 10 mm and counts the pixels between them.

**And one more found by looking at the re-rendered picture: the caption ran off the edge.**
The sentence telling a reader how to judge the number was cut in half by the frame. Caption
lines are wrapped to the panel and the footer grows to fit; `caption_overflow_px` is
reported and asserted to be 0.

**Two `wall` figures now exist in this repo and they are not the same number.**
`compare_meshes.wall_thickness()` samples ~20,000 rays over the whole surface in 3D
(median with p10/p90); `section_overlay.wall_chords()` measures across the outlines of one
cutting plane in 2D (median with longest and thinnest-5%). A section answers "how thick is
the wall *here*, where I can put callipers"; the 3D one answers "how thick is this sherd
overall". They will disagree, and neither is wrong. Both docstrings now say so, because a
conservator handed both without that will read the difference as an error in one of them.

**One review claim was checked and rejected.** The Spec axis read the two-way ray cast as
scope creep beyond the spec's Q3. It is not: without it the measurement depends on which
way `section()` happened to trace the outline. What was true is that nothing tested it —
see the mutation list above.
