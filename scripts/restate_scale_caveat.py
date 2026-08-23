"""Revise the accuracy statement on meshes that were already put into millimetres.

WHAT THIS DOES NOT DO: change any scale factor. Every mesh this touches keeps exactly the
mm-per-unit it was written with, and no .ply is opened. It refuses if the recorded factor
does not match the one in the sidecar, because that would mean the pair had drifted apart
and a caveat is the least of the problem.

WHY IT EXISTS. `scale_mesh.py` used to write:

    "precision ~1%; accuracy capped by the nominal 190x130 mm reference"

which was honest and unsatisfying: the 190 x 130 mm came from the conservator's record and
nothing had ever checked it, so the accuracy had no ceiling anyone could state. The
turntable marker board now provides one. Sixteen machine-detected coded targets on a
printed 40 mm lattice give a ruler about sixty times tighter than the base plate's own
internal disagreement, and under it the plate's LONG edge measures 189.20 mm against 190
declared -- 0.42% out. The short edge is still unchecked, because the Metashape point that
would have checked it is precisely the point found to be misplaced (by about 4.5 mm).

The factor is the mean of both edges, so half its reference is now verified and half is
not. That is what the new caveat says.

Read docs/notes/2026-08-22-turntable-markers.md section 10 before using this. In particular
section 10 is where it is established that the plate really is 190 x 130 -- by a route that
does not touch Metashape -- and therefore that these meshes need no numeric correction. If
that had gone the other way, this script would have been the wrong tool entirely: the
meshes would have needed rescaling, not re-annotating.

Usage:
    python scripts/restate_scale_caveat.py <dir-or-file> [...] [--apply]

Without --apply it prints what it would change and touches nothing.
"""
import argparse
import json
import sys
from pathlib import Path

OLD_CAVEAT = "precision ~1%; accuracy capped by the nominal 190x130 mm reference"
NEW_CAVEAT = ("precision ~1%; long edge of the 190x130 mm reference verified to 0.42% "
              "against the turntable marker board, short edge unverified")
REFERENCE_CHECK = "turntable board, docs/reference/turntable-board-03072025-N01.json"


def sidecars(targets):
    out = []
    for t in targets:
        p = Path(t)
        if p.is_dir():
            out += sorted(p.rglob("*.scale.json"))
        elif p.name.endswith(".scale.json"):
            out.append(p)
        else:
            print(f"  skipping {p} -- not a .scale.json and not a directory")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("targets", nargs="+", help="directories or .scale.json files")
    ap.add_argument("--apply", action="store_true",
                    help="write the change. Without this, nothing is modified.")
    a = ap.parse_args()

    files = sidecars(a.targets)
    if not files:
        sys.exit("No .scale.json files found. Nothing to do.")

    changed = skipped = refused = 0
    for p in files:
        d = json.loads(p.read_text())

        # The factor must survive untouched, and must still agree with the measurement it
        # was derived from. A sidecar whose factor no longer matches its own numbers has a
        # bigger problem than its wording, and quietly rewriting the prose on top of it
        # would hide that.
        factor = d.get("mm_per_unit")
        m = d.get("measured") or {}
        recorded = m.get("mm_per_unit")
        if recorded is None and {"mm_per_unit_long", "mm_per_unit_short"} <= set(m):
            recorded = 0.5 * (m["mm_per_unit_long"] + m["mm_per_unit_short"])
        if factor is None or recorded is None or abs(factor - recorded) > 1e-6 * max(1.0, factor):
            print(f"  REFUSED {p}")
            print(f"          mm_per_unit {factor} does not match its own measurement "
                  f"{recorded} -- look at this file, do not re-annotate it")
            refused += 1
            continue

        if d.get("caveat") == NEW_CAVEAT:
            skipped += 1
            continue
        if d.get("caveat") != OLD_CAVEAT:
            print(f"  REFUSED {p}")
            print(f"          caveat is not the one this script knows how to replace:")
            print(f"          {d.get('caveat')!r}")
            refused += 1
            continue

        d["caveat"] = NEW_CAVEAT
        d["reference_check"] = REFERENCE_CHECK
        print(f"  {'rewrote' if a.apply else 'would rewrite'} {p}   "
              f"(mm_per_unit {factor:.5f}, unchanged)")
        if a.apply:
            p.write_text(json.dumps(d, indent=2))
        changed += 1

    print(f"\n{changed} to change, {skipped} already current, {refused} refused")
    if refused:
        print("Refusals are not failures of this script -- look at those files.")
    if changed and not a.apply:
        print("Nothing was written. Re-run with --apply.")
    return 1 if refused else 0


if __name__ == "__main__":
    sys.exit(main())
