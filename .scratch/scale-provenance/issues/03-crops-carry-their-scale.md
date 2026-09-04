# 03: A crop is as accountable as the mesh it was cut from

**What to build:** cutting a mesh down — cropping to the rig, cropping to a sherd — keeps
the scale statement with the piece that comes out. The derived sidecar records the same
units and factor as its parent, plus which mesh it came from and what operation produced
it, so a crop can be traced back to the physical object that supplied its millimetres.

Demoable end to end: crop a metric mesh, then compare the crop against its parent with
ticket 01's script. Today that comparison refuses, because the crop has no sidecar and
nothing remembers that it is still in millimetres. After this it reports millimetres and
names the source.

**Answers:** `M3`

**Blocked by:** 01 (the sidecar reader and the contract it enforces)

**Status:** done — 2026-09-04

- [x] Cropping a mesh that has a sidecar produces a crop that has one
- [x] The derived sidecar names its parent mesh and the operation that made it — and what
      the cut kept, so "64.8% of 7,352,174 faces" is on the record rather than in a log
- [x] Cropping a mesh with **no** sidecar produces a crop with no sidecar — provenance is
      carried, never invented. A sidecar left beside the output by an earlier run is
      **removed**, because it describes a mesh that has just been replaced
- [x] The comparison from ticket 01 accepts a crop against its parent and prints the
      source it inherited, **marked as inherited**: a crop's millimetres were measured on
      its parent, not on the crop, and the read-out says which mesh and what cut

## Comments

**2026-09-04 — done on branch `markers-turntable`.**

`scripts/scale_sidecar.py` is the shared helper the spec's Q3 asked for. The reading half
moved out of `compare_meshes.py` unchanged; the writing half — `carry_sidecar` — is new.
`compare_meshes.py` imports it, so there is one definition of what a sidecar is rather
than two that can drift.

Three outcomes rather than two, and the third is the one that matters: a parent sidecar
that **exists and cannot be parsed** is not the same as an absent one. Absent says nobody
ever measured this object. Corrupt says somebody did and the record is damaged, and
continuing quietly would turn a recoverable file problem into a mesh that claims nothing
and reads as "never scaled". `crop_mesh.py` stops.

Two things came out of the work that were not in the ticket:

- **`scale_mesh.py`'s double-scaling guard had a hole this ticket would have widened.** It
  refuses any mesh whose PLY header carries a `comment units:` line. A crop is written by
  trimesh, which writes its own header, so the comment is gone while the scale is not —
  the sidecar now carries it. Checking only the header would have let exactly these files
  be scaled a second time, which is invisible and makes every measurement wrong by the
  square of the factor. `scale_mesh.py` now refuses on either signal. Verified both ways
  on real files: the crop is refused on its sidecar, `milo_mm.ply` on its header.
- **`render_mesh.py` captions a crop "arbitrary units"** — it reads the PLY header, which
  a crop no longer has, and does not read the sidecar. That is under-claiming, which is
  the safe direction, so it is not a defect. It is the same one-line reader as
  `silhouette_compare.py:176` and belongs with it in **ticket 05**.

Sherd extraction (`extract_sherds.py`) and the erosion outputs are still uncarried — that
is spec Q3's stated scope, not an oversight. Sixteen files in `artifacts/A03_metric/`
therefore still have no scale record; they are refused rather than measured, which is the
correct state until those scripts are next touched.

**Verified end to end on real data, not only on fixtures.** `artifacts/A02_metric/`:
`milo_mm_cropped_to_rig.ply` (the crop that exists today, made before any of this) is
refused with exit 2. A fresh crop of `milo_mm.ply` to the box `openmvs_refined_mm.ply`
agrees on keeps 4,766,738 of 7,352,174 faces, and the same comparison now exits 0, reports
millimetres, and prints `not scaled directly: cut from milo_mm.ply`. The crop was
**rendered** before any of that was reported: two views, 731.6 x 450.8 x 509.6 mm, the
clamp rig and sherds intact and the studio gone — the cut is a real cut, not an empty
mesh reading as one.

**The self-test runs `crop_mesh.py` and `scale_mesh.py` themselves**, in subprocesses,
rather than calling the helper they share. The helper being right is not the claim. 43
assertions pass, and seven deliberate mutations were each caught by the check meant to
catch it: the refusal moved back after the export, a damaged record treated as an absent
one, the sidecar ignored entirely, a scale invented for an unscaled parent, `derived_from`
dropped, a stale sidecar left in place, and the "inherited" line dropped from the read-out.

### What `/code-review` changed (2026-09-04, after the above)

The review ran two axes against `35be017`. Six findings held up; all are fixed here.

- **The refusal did not refuse.** `crop_mesh.py` exported the crop, *then* checked the
  parent's scale record, then printed "REFUSED". The file was already on disk — a message
  saying nothing happened, over the top of something that had. The check is now a
  pre-flight, before the mesh or the box references are even loaded, so a damaged record
  costs nothing and leaves nothing behind.
- **Two of the five mutations tested the helper, not the script** — and they were exactly
  the two behaviours the script's ordering got wrong. Both now run `crop_mesh.py` as a
  subprocess and assert the crop file is **absent**, not that the message reads well.
- **The `scale_mesh.py` assertions passed for the wrong reason.** Its fixture measurement
  lacked `accepted: true`, so the script refused the *measurement* and never reached the
  double-scaling guard being tested. A control case now proves an unscaled mesh with no
  sidecar **is** scaled, so the two refusals beside it are refusals.
- **`scale_mesh.py` degraded where ADR 0001 says refuse.** It used `read_scale`, which
  returns `None` for a damaged sidecar as well as an absent one — so a corrupt record let
  the mesh be scaled a second time, the worst case of all. It now uses `sidecar_state`.
- **Two definitions of "corrupt" in the module that claims to hold one.** `sidecar_state`
  is now the single three-outcome reader; `read_scale` wraps it and collapses damaged to
  absent only where the two lead to the same action.
- **A dangling ADR citation, an unused `DERIVED_KEYS`, and a cwd-dependent
  `derived_from`** (now resolved, so the field does not depend on where the crop was run).

One review claim was **checked and rejected**: that `check_intent_links.py` exits 0 while
printing ERROR. Run from the workspace root it exits 1. The gate is not broken.
