"""What units is this mesh in, and what physical object said so.

A mesh file carries no units. PLY, OBJ and STL all store a coordinate as a bare number
and none of them has a field that says what it means. The millimetres come from something
physical in the scene -- the turntable marker board, or the blue base plate -- and
`scale_mesh.py` records which, in a `<mesh>.scale.json` sidecar written beside the scaled
mesh.

THIS MODULE IS THE SIDECAR CONTRACT, in one place, because two scripts now need it and
they must not drift apart:

  * `compare_meshes.py` READS it, and refuses to print a millimetre it cannot stand behind.
  * `crop_mesh.py` CARRIES it, so a mesh cut out of a scaled mesh is still a scaled mesh.

The reading half lived inside `compare_meshes.py` until 2026-09-04 and worked; the writing
half did not exist at all, which is why `artifacts/A03_metric/` holds sixteen derived
meshes with nothing beside them saying what they are in. A crop looks identical to its
parent and is the file people actually measure.

CARRIED, NEVER INVENTED. `carry_sidecar` copies the parent's statement and adds who its
parent was and what operation produced it. It never manufactures one: a crop of a mesh
with no scale record gets no scale record, because a default would be a guess wearing a
provenance field's clothes (see
`docs/adr/0001-refuse-rather-than-degrade-when-scale-is-unknown.md`).

THREE STATES, NOT TWO, and the third is why `sidecar_state` exists rather than only
`read_scale`. A sidecar that is absent and one that is there but damaged mean opposite
things. Absent says nobody ever measured this object. Damaged says somebody did and the
record has been lost -- and treating that as "never scaled" is the degrade-to-default the
ADR bans, one layer down: it would let `scale_mesh.py` apply a factor to a mesh that
already carries one, which is invisible and makes every measurement wrong by the square of
the factor.
"""
import json
from datetime import datetime, timezone
from pathlib import Path

SIDECAR_SUFFIX = ".scale.json"

# Unit names a sidecar may declare, and what one mesh unit is worth in millimetres.
# Anything not on this list is refused rather than guessed at.
MM_PER_UNIT_BY_NAME = {
    "millimetres": 1.0, "millimeters": 1.0, "mm": 1.0,
    "centimetres": 10.0, "centimeters": 10.0, "cm": 10.0,
    "metres": 1000.0, "meters": 1000.0, "m": 1000.0,
}

# Every key whose value is a scale FACTOR -- a number a reader could multiply a mesh
# coordinate by to get millimetres. Under --shape-only none of them may reach a written
# report: a suppressed read-out with the factor still in the JSON is not a suppressed
# millimetre, it is a millimetre one multiplication away.
SCALE_FACTOR_KEYS = ("mm_per_unit", "mm_per_unit_long", "mm_per_unit_short",
                     "long_units", "short_units", "measured")

# What a mesh's scale sidecar turned out to be. Three, not two -- see the module
# docstring: "absent" and "damaged" mean opposite things and must not share a return value.
PRESENT = "present"        # a sidecar is there and parses to an object
ABSENT = "absent"          # no sidecar -- nothing ever measured this mesh
UNREADABLE = "unreadable"  # a sidecar is there and cannot be trusted -- do not proceed


def sidecar_path(mesh_path) -> Path:
    """<mesh>.ply -> <mesh>.scale.json, the name scale_mesh.py writes."""
    return Path(mesh_path).with_suffix(SIDECAR_SUFFIX)


def sidecar_state(mesh_path):
    """(state, doc_or_reason) -- the one place a sidecar is judged readable or not.

    `doc_or_reason` is the parsed sidecar when PRESENT, None when ABSENT, and a sentence
    saying what is wrong with the file when UNREADABLE. Every caller that must tell a
    damaged record from an absent one goes through here, so there is one definition of
    "corrupt" rather than one per script.
    """
    p = sidecar_path(mesh_path)
    if not p.exists():
        return ABSENT, None
    try:
        doc = json.loads(p.read_text())
    except (OSError, ValueError) as exc:
        return UNREADABLE, ("%s is there but cannot be read (%s)" % (p.name, exc))
    if not isinstance(doc, dict):
        return UNREADABLE, ("%s does not contain a JSON object" % p.name)
    return PRESENT, doc


def read_scale(mesh_path):
    """The scale sidecar beside a mesh, or None if there is not one we can read.

    Collapses UNREADABLE into None, so use it only where a damaged sidecar and an absent
    one lead to the same action -- refusing to report a millimetre, which is what
    `compare_meshes.py` does either way. Anywhere the two differ, call `sidecar_state`.
    """
    state, doc = sidecar_state(mesh_path)
    return doc if state == PRESENT else None


def internal_disagreements(sidecar: dict) -> list:
    """What the scale measurement recorded about disagreeing with itself.

    A02/A03 were scaled off a 190 x 130 mm plate measured on two edges and on two point
    clouds. Those figures live in the sidecar and have never been printed anywhere: a
    5.4 % gap between the sparse and dense clouds was reachable only by opening the JSON.
    """
    out = []
    m = sidecar.get("measured") or {}
    d = m.get("disagreement")
    if isinstance(d, (int, float)):
        out.append("the two reference edges disagree by %.1f%%" % (d * 100))
    x = m.get("cross_cloud_disagreement")
    if isinstance(x, (int, float)):
        out.append("the sparse and dense clouds disagree by %.1f%%" % (x * 100))
    for sub in m.get("measurements") or []:
        if sub.get("accepted") is False:
            out.append("the %s cloud's measurement was rejected"
                       % (sub.get("cloud") or "unnamed"))
    return out


def without_scale_factors(sidecar):
    """The sidecar's provenance -- who supplied the millimetres -- with no factor left.

    Keeps units, source, capture, method, scaled_at, caveat and the derived_* fields,
    because under --shape-only it is still worth recording which meshes could have been
    measured and on whose authority. Drops everything a downstream reader could compute
    with.
    """
    if not isinstance(sidecar, dict):
        return sidecar
    return {k: v for k, v in sidecar.items() if k not in SCALE_FACTOR_KEYS}


# --------------------------------------------------------------------------------------
# Carrying a scale statement onto a mesh derived from another one
# --------------------------------------------------------------------------------------

CARRIED = "carried"        # the parent had a scale record; the derived mesh now has one
NO_PARENT_SCALE = "none"   # the parent had none, so neither has the derived mesh
# UNREADABLE is defined above with the other sidecar states -- a damaged parent record
# stops the operation, and it is the same damage `sidecar_state` names.


def check_parent_sidecar(parent_mesh):
    """Is this mesh fit to be cut? Ask BEFORE producing the derived mesh.

    Returns (ok, message_or_None). A caller that only checks after writing its output has
    not refused anything: the file is on disk, and a message saying REFUSED is then simply
    untrue. `crop_mesh.py` calls this before it loads the mesh, so a damaged sidecar costs
    nothing and leaves nothing behind.
    """
    state, detail = sidecar_state(parent_mesh)
    if state != UNREADABLE:
        return True, None
    return False, (
        "%s. That is not the same as a mesh with no scale record: something measured this "
        "object and the record has been damaged. Refusing to cut it, because the crop "
        "would claim nothing and the next person would read the silence as 'never "
        "scaled'." % detail)


def carry_sidecar(parent_mesh, out_mesh, operation, note=None):
    """Give a derived mesh the scale statement of the mesh it was cut from.

    Returns (outcome, message). The caller decides what to do with UNREADABLE; the point
    of returning it rather than treating it as "no scale" is that a corrupt sidecar and an
    absent one mean opposite things. An absent one says nobody ever measured this. A
    corrupt one says somebody did and we just lost it, and quietly continuing would turn a
    recoverable file problem into a mesh that claims nothing.

    `operation` says what produced the derived mesh, in words a conservator can read six
    months later -- not "crop", but what was kept and on what basis.

    The derived sidecar names only its IMMEDIATE parent. A crop of a crop carries the
    chain by pointing at the file above it, which still has its own sidecar; there is no
    accumulated history here to fall out of date.
    """
    parent, out = Path(parent_mesh), Path(out_mesh)
    out_side = sidecar_path(out)
    state, doc = sidecar_state(parent)

    if state != PRESENT:
        # A stale sidecar beside the output is worse than none: it describes whatever was
        # written there last time, and the file has just been replaced. This has to happen
        # for BOTH failing states -- a damaged parent record leaves the output exactly as
        # unaccountable as an absent one, so leaving last run's sidecar to speak for it
        # would be provenance invented, which is the one thing this module must not do.
        stale = ""
        if out_side.exists():
            out_side.unlink()
            stale = (" The sidecar left beside %s by an earlier run has been removed, "
                     "because it described a different mesh." % out.name)

        if state == UNREADABLE:
            return UNREADABLE, (
                "%s. Something measured this object and the record has been damaged, which "
                "is not the same as never having been measured -- so nothing was carried."
                % doc + stale)
        return NO_PARENT_SCALE, (
            "%s has no scale record, so the crop has none either. Provenance is carried, "
            "never invented: nothing here knows what units this mesh is in, and "
            "compare_meshes.py will refuse it rather than measure it." % parent.name
            + stale)

    derived = dict(doc)
    # Resolved, not as typed: `--mesh ../milo_mm.ply` resolves differently depending on
    # where the crop was run from, and a provenance field that only works from one working
    # directory is not provenance. This records what was cut at the time it was cut; the
    # read-out prints the name.
    derived["derived_from"] = str(parent.resolve())
    derived["derived_by"] = operation
    derived["derived_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
    if note:
        derived["derived_note"] = note

    out_side.parent.mkdir(parents=True, exist_ok=True)
    out_side.write_text(json.dumps(derived, indent=2))
    return CARRIED, ("wrote %s -- %s, from %s, carried from %s"
                     % (out_side.name, derived.get("units"),
                        derived.get("source") or "an unrecorded source", parent.name))
