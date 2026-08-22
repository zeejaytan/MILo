# Saying which surface was measured

Design note, 2026-08-20. Status: **design agreed, not implemented.**
Scope: written general, run and validated on **A03** only for now.
Companion: `A03_BENT_SOLVE_AND_CLAMP_ARTEFACTS.md`, whose section 3 this follows from.

## The finding that reshaped this note

This started as a plan to close the holes the clamp left in the A03 sherds. Halfway through
it, the eroded-mask route landed (`A03_BENT_SOLVE_AND_CLAMP_ARTEFACTS.md` §3, "grow for
solving, shrink for building"), and measuring its output settles the question:

| route | pieces | closed | genus | openings |
|---|---|---|---|---|
| dilated masks + silhouette carving (`clean/sherd_*_clean.ply`) | 3 measured | **0 of 3** | sherd 2 was genus 2 | 11 |
| eroded masks, no carving (`eroded_sherd_*.ply`) | 11 | **10 of 11** | all genus 0 | **0** |

The one open piece, `eroded_sherd_0`, is 192 × 226 mm — the base plate, not a sherd.

**There are no holes to fill on the route the project is moving to.** Erosion also fixed
something the carved route did not: `sherd_2.ply` was watertight but **genus 2**, carrying two
tunnels straight through it, and after carving it also had a pinch vertex whose Euler
arithmetic implied half a handle. `eroded_sherd_2` is a clean genus-0 shell. Both defects were
artefacts of building against dilated masks and then cutting, not properties of the pottery.

So the hole filler is **not being built**. What remains is the part that erosion makes more
urgent, not less.

## Why erosion raises the stakes on the visibility flag

The clamp genuinely covered part of each sherd. No route recovers that surface, and there is
no second pass to merge (below). The two routes differ only in what they do about it:

- **Carving was honest and ugly.** It left a hole. Anyone opening the mesh could see exactly
  where the data stopped.
- **Erosion is tidy and silent.** The mesher closes smoothly over the unobserved patch, and
  the result is a watertight sherd with interpolated surface sitting in it that looks
  identical to measured pottery.

Erosion is clearly the better route — no spikes, no stubs beside the fracture surface, no
fake break geometry, and the genus defect gone. But it removes the marker without removing
the missing data. `A03_BENT_SOLVE_AND_CLAMP_ARTEFACTS.md` already says so: the clamp-contact
surface "is currently closed over by the reconstruction and not marked as interpolated."

**Only a per-vertex record of what the cameras saw puts the marker back.** That is now the
whole of this build.

## Part 1 — the visibility map

### What it produces

A per-vertex count of how many photographs actually observed that vertex, carried in the PLY
beside the existing scale provenance. A03 registers 164 photographs, so the count runs 0–164.

This is deliberately **a count, not a yes/no flag.** Multi-view stereo cannot place a point it
saw once: with a single observation there is no baseline and no triangulated depth, so that
vertex's position came from interpolation as surely as a patch would. A binary flag would
stamp that surface "measured". A count makes never-seen (0), thinly-seen (1–2) and properly
measured (3+) all visible, costs the same to compute, and lets each consumer pick its own
threshold.

A view counts as observing a vertex when **all** of the following hold:

1. some triangle incident on the vertex won the depth test at a pixel in that view;
2. that pixel lies inside the sherd's mask — i.e. the clamp is not in front of it;
3. the surface faces the camera within 70°. A grazing look contributes almost nothing to
   triangulated depth and should not be counted as evidence.

Run it against **the eroded surface masks**, the same ones the mesh was built from. Using the
dilated `masks_object` here would count the clamp's own 8-pixel skirt as sherd and report
observed surface that was never seen.

### How

Reuse `scripts/silhouette_compare.py`'s nvdiffrast renderer rather than writing a new
projector. Its `Renderer.mask()` already builds the model-view-projection from the COLMAP
poses and rasterises on CUDA; the rasteriser's output carries per-pixel **triangle IDs**, so
"which triangles were visible in this view" reads straight out of the buffer. No depth
tolerance to tune, and the visibility map and the silhouette scoring then agree by
construction.

The step that is *not* optional is the occlusion test. Projecting a vertex and testing whether
it lands inside the mask marks the **back** of the sherd as observed, because the back projects
inside the silhouette too. The existing `support.npy` measures inside-the-outline, not
visibility, and cannot be reused for this.

Use the corrected solve (`sparse_nosherdrig/0`), all 164 views, not `--every 2`. GPU job on
Spartan; minutes, not hours.

### Where it goes in the file

| property | type | meaning |
|---|---|---|
| `n_views` | `uchar` (saturating at 255) | photographs that observed this vertex under the rule above |
| `origin` | `uchar` | 0 = photogrammetry surface, 1 = surface added by a later repair |

`origin` is carried even though nothing currently writes a 1, because `n_views` and `origin`
answer different questions — how much evidence, versus who put the surface here — and the
field should exist before it is needed rather than be retrofitted.

Sidecar `<stem>.provenance.json` alongside the existing `<stem>.scale.json`: tree ID, solve
and dense workspace paths, mask set used, number of views, incidence-angle threshold, the
histogram of `n_views`, and the fraction of surface at 0, 1–2 and 3+ views.

Risk to check early: trimesh's PLY writer must round-trip custom `uchar` vertex attributes. If
it does not, write the header directly — `silhouette_filter.py` already parses and re-emits
PLY headers by hand and can be borrowed from.

### Read it as evidence coverage, not reliability

A vertex seen in sixty views can still be wrong; the GLOMAP episode in `docs/lessons.md`
produced a duplicated reconstruction that every view agreed on. A03's own bent solve is the
same lesson: it scored *better* than the correct tree on every available number. `n_views`
records what the cameras saw, nothing more. It must never be presented, or used downstream, as
a quality score.

### Validation

**Look at it, per sherd.** Colour each mesh by `n_views` and render it. The never-observed
region must land where the clamp was — visible in the photographs and in the carved route's
holes, which make an independent check the eroded meshes cannot provide on their own. If the
zero-count region is somewhere else, the projection is wrong.

**A sanity floor, as `silhouette_filter.py` already does for support.** On a real mesh most
surface is seen in a large fraction of views. A low median means the projection is broken
rather than the sherd being poorly covered, and the run should refuse rather than emit a tidy
number. Print the histogram and set the reading from it.

**Cross-check against the retired route.** The eleven openings in `clean/sherd_*_clean.ply`
mark surface the carve judged unsupported. The corresponding region of the eroded mesh should
come out at or near zero views. Two independent methods agreeing on where the data stops is
worth more than either alone. This is the main reason to keep the carved meshes on disk.

**Quantify what it finds.** Report, per sherd: surface area at 0 views, at 1–2, and at 3+, in
mm² and as a percentage. That number is the answer to "how much of this sherd was actually
measured", and nothing in the project currently states it.

## Standing in the conservation record

This is paradata in the London Charter's sense, carried in the file rather than written in a
caption.

- London Charter 1.1, Principle 4.1: "It should be made clear what kind and status of
  information the 3D visualisation represents. The nature and degree of factual uncertainty of
  an hypothetical reconstruction… should be communicated." Principle 4.6 covers documentation
  of the interpretative process.
- Seville Principles, Principle 7: metadata and paradata should be machine-readable,
  standardised and available.
- Colour-coding certainty (documented / inferred / hypothetical) is established practice in
  virtual heritage.

A per-vertex view count satisfies these mechanically rather than editorially, and none of the
meshes in this project currently states it.

> `A03_BENT_SOLVE_AND_CLAMP_ARTEFACTS.md` quotes "informed CH curators usually do not accept
> that an algorithm is used to guess portions of a surface" without a source. Find the source
> or drop the quote before either note feeds a chapter.

## Part 2 — filling openings, held as a contingency only

Not being built. Recorded so the reasoning survives if the question comes back.

**It conflicts with a principle this project has already established.**
`A03_BENT_SOLVE_AND_CLAMP_ARTEFACTS.md` §3 states it plainly: *added geometry is worse than
missing geometry — missing surface only weakens a match, added surface creates false ones and
can physically block a sherd from seating.* A patch is added geometry. On the eroded route,
where the meshes are already closed, adding any would be pure cost.

**If it ever is needed**, the method is Liepa (2003): triangulate the rim, refine to the
surrounding triangle size, then fair by solving the bi-Laplace equation with two rings of real
vertices pinned, which gives C¹ across the seam so the surrounding curvature continues into
the patch. Liepa, P. 2003, 'Filling holes in meshes', *Eurographics Symposium on Geometry
Processing*, 200–206, [10.2312/SGP/SGP03/200-206](https://doi.org/10.2312/SGP/SGP03/200-206);
implemented in CGAL as `triangulate_refine_and_fair_hole`.

Three things learned in the diagnosis that any future attempt should start from:

- **Validate on signed, one-sided error.** For interpenetration rejection an outward bulge
  invents an overlap and rejects a correct join; an inward sag is harmless. Worst outward
  excursion is the number that matters, not RMS.
- **Measure it with synthetic holes.** Cut openings matched in size and shape into intact,
  well-observed wall on the same sherd, fill them, and compare against the surface deleted.
  That converts "it follows the curvature" into millimetres.
- **Generalised winding number makes filling avoidable for the interpenetration case.**
  Jacobson, Kavan & Sorkine 2013, 'Robust inside-outside segmentation using generalized
  winding numbers', *ACM TOG* 32(4),
  [10.1145/2461912.2461916](https://doi.org/10.1145/2461912.2461916), defines inside/outside
  robustly for meshes with holes. It gives no closed mesh for volume, but for "do these two
  sherds overlap" it needs no invented surface at all.

Measurements from the carved route, kept because they are the only direct measurement of how
much surface the clamp covered: eleven openings across three sherds, 184 mm² (2.1%), 497 mm²
(8.5%) and 98 mm² (1.7%) of surface area; largest empty circle inside any rim 5.0 mm, most
under 3 mm; local wall thickness 6.3–10.1 mm; every opening in one face of the wall with the
opposite face intact.

## Capture, which beats all of this

The Rabati rig is the Göttlich "pottery tree", and its originators shoot **two passes with the
clamps moved between them**, then merge — *A New Method for the Large-Scale Documentation of
Pottery Sherds…*, Open Archaeology 2020,
[10.1515/opar-2020-0133](https://doi.org/10.1515/opar-2020-0133). The 2024 refinement, *Pottery
from Motion*, [10.1515/opar-2024-0011](https://doi.org/10.1515/opar-2024-0011), reports that
marking sherds with non-permanent black dots cuts the merge from ~30 min to 5–10 min per
sherd, and that where they skip the merge the residual hole "did not affect automated
measurements" (citing Di Angelo et al. 2024).

The Rabati scanning record (`docs/reference/Rabati 2025 scanning record.xlsx`) shows A02, A03
and A04 as "Part 2/3/4" — separate loadings of *different* sherds from the same bag, not
re-grips of the same sherds. **There is no second pass to merge for A03.**

For the next field season the re-grip pass is the answer that needs no inference at all, and
the black-dot trick makes it affordable. That belongs in the capture-recipe chapter regardless
of what is built here.

> Author lists for the three papers above were not verified in this session. Check them
> against the DOIs before any of this is cited in the thesis.

## Deliverables

| file | what |
|---|---|
| `scripts/visibility_map.py` | per-vertex view counts via nvdiffrast; writes `n_views`, `origin` and `provenance.json`. General over trees; run on A03. |
| `artifacts/A03_metric/` renders | each sherd coloured by view count (gitignored) |
| `docs/notes/` results note | how much of each sherd was actually measured |

Out of scope: rerunning the reconstruction, changing the mask erosion, hole filling, and
anything touching trees other than A03.

## Downstream rules this creates

- Anything reporting a measurement from these meshes states the `n_views` distribution of the
  surface it measured.
- Reassembly excludes or down-weights surface at 0–2 views, with the threshold recorded. The
  clamps grip sherds **at their edges**, so the unobserved band sits on or beside the fracture
  surface — the one surface the matcher reads.
- The carved meshes stay on disk as the independent cross-check on where the data stops.

## What would change this design

- If the never-observed region does not land where the clamp was, the projection is wrong and
  nothing else in this note is worth acting on until that is fixed.
- If erosion turns out to have cost fracture-surface detail — **it has, on the
  photographs**: 6 px is 0.60–0.86 mm and already sits on the ridges
  (`A03_BENT_SOLVE_AND_CLAMP_ARTEFACTS.md` §3). The default is a ceiling, not a number to
  raise. If the production shrink changes, recompute the visibility map against whatever
  masks the final meshes are built from.
- If a re-grip second pass ever exists for these sherds, merge it. Measured surface beats an
  interpolated one every time, and the flag then records that improvement automatically.
