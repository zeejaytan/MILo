#!/usr/bin/env python3
"""Convert the conservator's Rabati scanning-record spreadsheets to JSON + Markdown.

The .xlsx files in ``docs/reference`` are the authoritative record of what was
photographed, copied verbatim from the conservator. They are convenient to fill in
and awkward to read from code: dates and labels are only written when they change,
and a repeated value is written as the word "same".

This script resolves those shorthands into one row per photo set and writes:

    docs/reference/scanning-record.json   machine readable, both seasons
    docs/reference/scanning-record.md     the same thing as tables

Optionally (``--drive D:\\``) it also counts the frames actually sitting in each
capture directory and attaches them, so a mismatch between the record and the disk
is visible instead of having to be remembered.

    python scripts/build_scanning_record.py --drive D:\\

Re-run it after the spreadsheets change; do not hand-edit the JSON or the Markdown.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path

# Imported where it is used, not here. --check is a GATE, called from Slurm on a cluster
# node whose environment has no openpyxl, and a gate that exits 1 saying "pip install
# openpyxl" is indistinguishable from a gate that failed the capture. It does not need the
# spreadsheets at all: docs/reference/scanning-record.json is the built artefact, it is
# committed, and it is what everything downstream already reads.
def _openpyxl():
    try:
        import openpyxl
    except ImportError:  # pragma: no cover
        sys.exit("openpyxl is required to REBUILD the record:  pip install "
                 "openpyxl. --check does not need it -- it reads "
                 "docs/reference/scanning-record.json)")
    return openpyxl

REPO = Path(__file__).resolve().parents[1]
REFERENCE = REPO / "docs" / "reference"

# The scale sources and what each is worth, from the module that also writes them into a
# mesh's sidecar. Imported rather than restated so the record and the mesh cannot end up
# quoting different precisions for the same ruler. Stdlib only, so --check still runs on a
# cluster node with no scientific stack.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from scale_sidecar import BOARD, PLATE, SOURCE_CAVEAT        # noqa: E402

SEASONS = {
    2025: "Rabati 2025 scanning record.xlsx",
    2026: "Rabati 2026 scanning record.xlsx",
}

# The spreadsheet writes a repeated cell as one of these words rather than repeating it.
DITTO = {"same", "as above", "continue", "ditto"}

# The turntable marker only becomes usable partway through the 2025 season.
# Before the N01 batch (2025-07-03) the marker was placed incorrectly, and feature
# matching against it drags the alignment off. From N01 onwards it sits on the
# turntable and is the intended alignment reference -- the record says so itself in
# N01's measurement cell: "Use base as scale, marker on turntable for alignment".
# The cutoff is a position in the record, not a date: M01-M04 were shot the same day
# as N01 but come before it, and their marker is the bad one.
MARKER_CUTOFF = (2025, "2025-07-03", "N01")
MARKER_WARNING = (
    "Marker placed incorrectly. Do NOT use it for feature recognition, registration "
    "or alignment -- it will pull the solve off. Scale and align from the 13x19 cm "
    "base instead."
)
MARKER_OK = (
    "Marker is on the turntable and is the intended alignment reference "
    "(N01 batch onwards)."
)

# Directory names on the capture drive that do not follow <DDMMYYYY>.
# 2025-07-04 was typed as "04052025" when the card was copied off the camera
# (the record itself has the same slip: the date cell reads "04/07/205").
DIR_ALIASES = {"04072025": "04052025"}
DIR_ALIAS_REASONS = {
    "04072025": "the card was copied into a directory named 04052025; the record's own "
                "date cell reads '04/07/205'. Both are slips for 2025-07-04."
}

# Photo sets whose directory on the capture drive is named differently from the record.
# (season directory, photo set in the record) -> directory on disk
ALIAS_REASONS = {
    ("25062025", "J01"): "directory left named G01; the record says J01",
    ("16062025", "A01"): "no per-tree subdirectory: the whole date directory is tree A01",
    ("04052025", "Pot 01"): "directory spells the set without the space",
    ("04052025", "Pot 02"): "directory spells the set without the space",
}

SET_ALIASES = {
    # 2025-06-25 starts the J series. The first tree's folder was left named G01,
    # which is also a real, different tree shot on 2025-06-21. The record says J01.
    ("25062025", "J01"): "G01",
    # 2025-06-16 is the one day whose photographs sit directly in the date directory,
    # with no per-tree subdirectory. All 177 frames are tree A01 (see capture-layout.md).
    ("16062025", "A01"): "16062025",
    ("04052025", "Pot 01"): "Pot01",
    ("04052025", "Pot 02"): "Pot02",
}


# --------------------------------------------------------------------------------------
# What physical object supplied the millimetres for each capture
# --------------------------------------------------------------------------------------
#
# WITHOUT THIS FIELD "59 of 118 are metric" is something we remember, not something the
# data says -- and remembering is how a non-metric capture drifts into a size comparison
# a year later.
#
# THE MARKER BEING USABLE DOES NOT MAKE IT THE RULER. `markers_usable` answers "may I
# align on this marker", which is a different question from "what supplied the
# millimetres", and the record says so itself: N01's own measurement cell reads *"Use base
# as scale, marker on turntable for alignment"*. The board only becomes a scale source for
# a capture once a reference has actually been DERIVED for it, because the factor is
# measured by fitting that capture's cameras onto the board. One exists. Crediting the
# other 58 to the board because the marker is visible in them would be inventing a
# measurement, which is the thing this whole feature exists to stop.
#
# The plate is what the record itself declares, once per season, at the top of the sheet:
# "Top of the tree base (blue metal base) = 13x19cm". That is a statement about the rig,
# and the rig is in every capture -- so it covers both seasons. It is a statement of what
# was SET UP, not a confirmation that the plate is unoccluded in every frame; scale_mesh.py
# is what finds that out per capture, and it refuses rather than reports when its own
# checks fail.

# capture_id -> the derived board reference for that capture. A capture is credited to the
# board only if it is in here AND the file is on disk; both are checked before writing.
BOARD_REFERENCES = {
    "2025-07-03/N01": "docs/reference/turntable-board-03072025-N01.json",
}

# What `frame_counts_from` says when the drive was not attached for this build.
CARRIED_MARKER = "CARRIED FROM AN EARLIER SCAN"
CARRIED_COUNTS = ("{drive}, " + CARRIED_MARKER + " -- not re-counted for this build, so a "
                  "capture added or deleted since is not reflected here")

PLATE_HOW = ("top face of the tree base, 190 x 130 mm, as declared once at the top of this "
             "season's sheet: {note!r}. That is the record's own statement about the rig "
             "this season was shot on -- it is not a confirmation that the plate is "
             "unoccluded in any given capture, which is what scale_mesh.py finds out per "
             "mesh, and refuses rather than reports when its checks fail.")
BOARD_HOW = ("16 coded targets on a printed 40 mm lattice, with the factor measured by "
             "fitting this capture's own cameras onto the board -- so it is a scale source "
             "only where that reference has been derived: {ref}")
NO_SCALE_HOW = ("nothing in this season's record names a physical object of known size. "
                "Shape questions only: this capture must not enter any measurement that "
                "depends on size, and no millimetre may be quoted from it.")

# The plate is a scale source because THE RECORD SAYS SO, once per season, not because we
# remember the rig. The two sheets word it differently -- 2025 "blue metal base", 2026
# "metal base" -- so match on the dimensions plus the word base, and keep the note verbatim
# in `declared_by` so the JSON carries the evidence rather than our reading of it. A season
# that stops declaring it becomes non-metric, which is the whole point: the rule has to be
# able to fail, or "118 of 118 are metric" is an assertion the code cannot lose.
#
# THE DECLARATION IS PER SEASON AND SO IS THE OBJECT. 2026's sheet says "metal base",
# without the colour, and nothing in the record says it is the same plate as 2025's. Each
# season is therefore credited from its own line, and the caveat says where the 0.42%
# long-edge check was actually made -- on the 2025 rig, through 2025-07-03/N01 -- rather
# than implying it was repeated later. Same dimensions is not the same object measured.
PLATE_DECLARATION = re.compile(r"13\s*x\s*19", re.I)


def plate_declaration(notes):
    """The season note that declares the base plate, verbatim, or None if there is none."""
    for n in notes or []:
        if PLATE_DECLARATION.search(n) and "base" in n.lower():
            return n
    return None


def flag_scale_sources(seasons, repo=REPO, references=None) -> None:
    """Give every capture a stated scale source, or mark it non-metric. Neither is silent.

    Writes `scale` on each entry:

        source       the physical object, or None
        how          what it is, in words a conservator can act on
        precision    what that source is worth, carried from the sidecar contract so the
                     record and the mesh cannot state different figures for the same ruler
        reference    the derived board reference, where one exists
        declared_by  the season note the plate claim rests on, verbatim
        recorded     the per-capture measurement cell, verbatim, or None
        metric       False exactly when there is no source. This is the field to gate on.

    `recorded` is the measurement cell VERBATIM, kept beside the source rather than folded
    into it, because the cells are not one kind of statement. Most hold hand-ruled
    distances between marks on the rig ("Mark1-2: 18cm, mark3-4: 42.4cm") at ruler
    precision on a printed sheet -- those corroborate, they are not the ruler, and
    promoting them to one would quietly re-scale seventy captures. Fourteen say something
    else entirely and say it better than any field here does: "Use base as scale, marker on
    turntable for alignment". Reading them is worth more than parsing them, so they are
    carried whole and printed by --scale-check.
    """
    references = BOARD_REFERENCES if references is None else references
    for ref_id, rel in references.items():
        if not (Path(repo) / rel).exists():
            raise SystemExit(
                "board reference {} is named for {} but is not on disk. Refusing to write "
                "a record that credits a capture to a ruler nobody can open."
                .format(rel, ref_id))

    seen = set()
    for s in seasons:
        declared = plate_declaration(s.get("notes"))
        for e in s["entries"]:
            cid = e["capture_id"]
            seen.add(cid)
            ref = references.get(cid)
            if ref:
                source, how = BOARD, BOARD_HOW.format(ref=ref)
            elif declared:
                source, how = PLATE, PLATE_HOW.format(note=declared)
            else:
                source, how = None, NO_SCALE_HOW
            e["scale"] = {
                "source": source,
                "how": how,
                "precision": SOURCE_CAVEAT[source] if source else None,
                "reference": ref,
                "declared_by": declared if source == PLATE else None,
                "recorded": e["measurement"],
                "metric": source is not None,
            }

    missing = sorted(set(references) - seen)
    if missing:
        raise SystemExit(
            "board reference named for {}, which is not a capture in the record. A "
            "reference pointed at nothing would silently credit no capture at all."
            .format(", ".join(missing)))


def scale_summary(seasons) -> list:
    """The counts in plain terms: how much of the corpus can be measured, and on what."""
    ent = [e for s in seasons for e in s["entries"]]
    by_source = {}
    for e in ent:
        by_source.setdefault(e["scale"]["source"], []).append(e)

    metric = [e for e in ent if e["scale"]["metric"]]
    lines = ["%d of %d captures can state where their millimetres come from."
             % (len(metric), len(ent))]
    for source in sorted(by_source, key=lambda x: (x is None, x or "")):
        got = by_source[source]
        if source is None:
            lines.append("  %3d NON-METRIC -- no scale source. Shape questions only; "
                         "nothing may measure a size against these." % len(got))
            continue
        lines.append("  %3d from the %s -- %s" % (len(got), source, SOURCE_CAVEAT[source]))

    # NOT "would tighten them". The board is the tighter INSTRUMENT and the LOOSER ruler:
    # its lattice fits to a fraction of a millimetre, but its absolute size rests on a
    # ruler reading of the printed sheet at +/-1.25%, against the plate's long edge
    # verified to 0.42%. Precision and accuracy are different questions -- see
    # scale_sidecar.py -- and telling a conservator the looser ruler is the upgrade is
    # exactly the confusion this record exists to remove.
    derivable = [e for e in ent
                 if e["markers_usable"] and not e["scale"]["reference"]]
    lines.append("%d more carry a usable marker board that no reference has been derived "
                 "from, so the board is not their ruler. Deriving one would make them far "
                 "more REPEATABLE, not more accurate: the board's absolute size is a ruler "
                 "reading of the printed sheet (+/-1.25%%), looser than the plate's "
                 "verified long edge." % len(derivable))
    return lines


def norm(cell) -> str:
    if cell is None:
        return ""
    if isinstance(cell, dt.datetime):
        return cell.date().isoformat()
    return str(cell).strip()


def parse_date(raw: str, season: int):
    """Return an ISO date, tolerating the hand-typed '04/07/205'."""
    if not raw:
        return None
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw):
        return raw
    m = re.fullmatch(r"(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})", raw)
    if m:
        d, mth, y = (int(x) for x in m.groups())
        if y < 1000:
            # "205" for 2025 -- a dropped digit. The season is the only sane reading.
            y = season
        try:
            return dt.date(y, mth, d).isoformat()
        except ValueError:
            return None
    return None


def resolve(raw: str, previous):
    """Expand a ditto cell against the previous resolved value."""
    if not raw:
        return None
    if raw.lower() in DITTO:
        return previous
    return raw


def season_notes(rows):
    """Free text written above the header row (rig setup, camera settings, reminders)."""
    notes = []
    for row in rows:
        if row and row[0] == "Date":
            break
        for cell in row:
            if cell:
                notes.append(cell)
    return notes


def parse_sheet(path: Path, season: int) -> dict:
    wb = _openpyxl().load_workbook(path, data_only=True)
    ws = wb.worksheets[0]
    rows = [[norm(c) for c in r] for r in ws.iter_rows(values_only=True)]

    header_i = next(i for i, r in enumerate(rows) if r and r[0] == "Date")
    # Columns: Date | Photo Set | Lable | RSPF | Measurement | (blank) | Note
    DATE, SET, LABEL, RSPF, MEAS, _SPARE, NOTE = range(7)

    entries = []
    date = None
    last_label = None
    last_meas = None

    for row in rows[header_i + 1:]:
        if len(row) < 7:
            row = row + [""] * (7 - len(row))
        if not any(row[:7]):
            continue

        d = parse_date(row[DATE], season)
        if d:
            date = d
        raw_label, raw_meas = row[LABEL], row[MEAS]
        label = resolve(raw_label, last_label)
        meas = resolve(raw_meas, last_meas)
        if label:
            last_label = label
        if meas:
            last_meas = meas

        this_label = {"label": label, "rspf": row[RSPF] or None, "raw": raw_label or None}

        if row[SET]:
            photo_set = row[SET].strip()
            entries.append(
                {
                    "season": season,
                    # Unique key. In 2026 the tree letters restart on a new day, so
                    # "A01" alone is ambiguous -- 2026-06-15/A01 and 2026-06-16/A01
                    # are different trees holding different bags.
                    "capture_id": "{}/{}".format(date, photo_set),
                    # Trees sharing a letter are loadings of the same object.
                    "object": re.match(r"[A-Za-z]+", photo_set).group(0),
                    "date": date,
                    "date_raw": row[DATE] or None,
                    "photo_set": photo_set,
                    "labels": [this_label] if (label or row[RSPF]) else [],
                    "measurement": meas,
                    "measurement_raw": raw_meas or None,
                    "note": row[NOTE] or None,
                }
            )
        elif entries:
            # A continuation row: another bag / RSPF belonging to the set above it.
            if label or row[RSPF]:
                entries[-1]["labels"].append(this_label)
            if row[NOTE]:
                prev = entries[-1]["note"]
                entries[-1]["note"] = "{}; {}".format(prev, row[NOTE]) if prev else row[NOTE]

    return {"season": season, "source": path.name, "notes": season_notes(rows), "entries": entries}


def flag_markers(seasons) -> None:
    """Mark every capture shot before the N01 batch as marker-unusable.

    Walked in record order, because the cutoff is a position in the record and not a
    date: M01-M04 share 2025-07-03 with N01 but were shot before it.
    """
    usable = False
    for s in sorted(seasons, key=lambda x: x["season"]):
        for e in s["entries"]:
            if (e["season"], e["date"], e["photo_set"]) == MARKER_CUTOFF:
                usable = True
            e["markers_usable"] = usable
            e["markers_note"] = MARKER_OK if usable else MARKER_WARNING
    if not usable:
        raise SystemExit(
            "marker cutoff {} not found in the record -- refusing to write, every "
            "capture would be flagged unusable".format(MARKER_CUTOFF)
        )


def scan_drive(drive: Path) -> dict:
    """Count JPG/NEF per <DDMMYYYY>/<set>/ directory on the capture drive."""
    found = {}
    for day in sorted(p for p in drive.iterdir() if p.is_dir()):
        if not re.fullmatch(r"\d{8}", day.name):
            continue
        subdirs = [p for p in day.iterdir() if p.is_dir() and not p.name.endswith(".files")]
        targets = [(day.name, day)] if not subdirs else [(s.name, s) for s in subdirs]
        for name, d in targets:
            jpg = nef = 0
            for f in d.iterdir():
                ext = f.suffix.upper()
                jpg += ext == ".JPG"
                nef += ext == ".NEF"
            if jpg or nef:
                found[(day.name, name)] = {
                    "dir": "{}/{}".format(day.name, name) if subdirs else day.name,
                    "jpg": jpg,
                    "nef": nef,
                }
    return found


def attach_disk(seasons, disk) -> list:
    """Match record rows to capture directories; return the rows that did not match."""
    used = set()
    unmatched = []
    for s in seasons:
        for e in s["entries"]:
            if not e["date"]:
                continue
            d = dt.date.fromisoformat(e["date"]).strftime("%d%m%Y")
            d = DIR_ALIASES.get(d, d)
            name = SET_ALIASES.get((d, e["photo_set"]), e["photo_set"])
            hit = disk.get((d, name)) or disk.get((d, name.replace(" ", "")))
            if hit:
                e["on_disk"] = dict(hit)
                reason = ALIAS_REASONS.get((d, e["photo_set"]))
                if reason:
                    e["on_disk"]["naming"] = reason
                used.add((d, hit["dir"].split("/")[-1]))
            else:
                unmatched.append("{} {} - no directory".format(e["date"], e["photo_set"]))
    for key in sorted(disk):
        if key not in used:
            unmatched.append("{} - directory with no row in the record".format(disk[key]["dir"]))
    return unmatched


def find_capture(seasons, wanted):
    """One capture from the record, by capture_id or by its directory on the drive.

    Returns (entry, None) or (None, why-not). Shared by the two gates below, which ask
    DIFFERENT questions of the same capture -- "may I align on the marker" and "may I take
    a millimetre off this" -- and two copies of this lookup could drift into answering one
    question about a different capture.
    """
    key = wanted.strip().strip("/").replace("\\", "/")
    hits = [
        e
        for s in seasons
        for e in s["entries"]
        if key in (e["capture_id"], (e.get("on_disk") or {}).get("dir"))
        or key.lower() == e["capture_id"].lower()
    ]
    if not hits:
        return None, ("no such capture in the record: {}\n"
                      "(directory names only resolve when --drive is also given)"
                      .format(wanted))
    if len(hits) > 1:
        return None, "ambiguous: {}".format(", ".join(h["capture_id"] for h in hits))
    return hits[0], None


def describe_capture(e) -> None:
    """The two lines both gates print first, so a wrong answer names the wrong capture."""
    print("{}  object {}  {}".format(e["capture_id"], e["object"], e["labels"][0]["label"]
                                     if e["labels"] else "(no bag label)"))
    if e.get("on_disk"):
        print("  directory {}  {} JPG / {} NEF".format(
            e["on_disk"]["dir"], e["on_disk"]["jpg"], e["on_disk"]["nef"]))


def check_capture(seasons, wanted) -> int:
    """Answer 'may I use the marker on this capture?' for one capture.

    Exit 2 when the marker must not be used, so a pipeline step can gate on it:

        python scripts/build_scanning_record.py --check 03072025/M04 || exit 1

    This is the ALIGNMENT question. It is not the scale question -- see
    `scale_check_capture` -- and the record itself keeps them apart: N01's measurement cell
    reads "Use base as scale, marker on turntable for alignment".
    """
    e, why = find_capture(seasons, wanted)
    if why:
        print(why)
        return 3
    describe_capture(e)
    if e["markers_usable"]:
        print("  MARKER OK - {}".format(e["markers_note"]))
        return 0
    print("  MARKER UNUSABLE - {}".format(e["markers_note"]))
    return 2


def scale_check_capture(seasons, wanted) -> int:
    """Answer 'may I take a millimetre off this capture?' for one capture.

    Exit 2 when the capture is non-metric, so a measurement step can gate on it:

        python scripts/build_scanning_record.py --scale-check 03072025/M04 || exit 1

    A capture can pass this and fail --check, and the reverse. Every 2025 capture before
    2025-07-03/N01 has an unusable marker and is still metric off the base plate; a capture
    in a season whose sheet never declared the plate would be the other way round.

    Exit 3 -- not 2 -- when the record predates this field. A record that cannot answer the
    question is not the same as a capture that answers "no", and a gate that conflated them
    would mark the whole corpus unmeasurable the moment the JSON went stale.
    """
    e, why = find_capture(seasons, wanted)
    if why:
        print(why)
        return 3
    describe_capture(e)
    sc = e.get("scale")
    if not sc:
        print("  this record was built before scale sources were recorded -- rebuild it "
              "with scripts/build_scanning_record.py before gating on scale")
        return 3
    if sc["metric"]:
        print("  SCALE OK - {} ({})".format(sc["source"], sc["how"]))
        print("  worth: {}".format(sc["precision"]))
        if sc.get("recorded"):
            print("  the sheet also records, by hand: {}".format(sc["recorded"]))
        return 0
    print("  NON-METRIC - {}".format(sc["how"]))
    return 2


def to_markdown(seasons, drive, unmatched) -> str:
    out = [
        "# Rabati scanning record",
        "",
        "**Generated by `scripts/build_scanning_record.py` — do not hand-edit.**",
        "Edit the spreadsheets in this directory and re-run the script.",
        "",
        "One row per **photo set** (one loading of the clamp rig, photographed all the way",
        "round — see `capture-layout.md`). The spreadsheets write a repeated value as the",
        'word "same"; those are expanded here. Where a set covers several excavation bags,',
        "each bag is on its own line in the Label column.",
        "",
        "## Do not use the turntable marker before 2025-07-03 N01",
        "",
        "**Every capture up to and including 2025-07-03 M04 has the marker in the wrong",
        "place.** Do not use it for feature recognition, registration or alignment: it will",
        "pull the solve off, and the reconstruction can still look plausible while being",
        "wrong. Scale and align those captures from the 13x19 cm base instead.",
        "",
        "From the **N01 batch (2025-07-03) onwards** the marker sits on the turntable and is",
        "the intended alignment reference -- the record says so in N01's own measurement",
        'cell: "Use base as scale, marker on turntable for alignment". Everything from there',
        "on, including all of 2026, is fine.",
        "",
        "The cutoff is a position in the record, not a date. **M01-M04 were shot on the same",
        "day as N01 but come before it, and their marker is the bad one.** Every row below",
        "carries the answer in its Marker column and every record in the JSON carries",
        "`markers_usable` -- read that field rather than reasoning from the date.",
        "",
    ]
    out += ["## Where the millimetres come from", ""]
    out += ["- " + x.strip() for x in scale_summary(seasons)]
    out += [
        "",
        "**A usable marker is not the same as a marker used for scale.** The Marker column",
        "answers *may I align on it*; the Scale column answers *what supplied the",
        "millimetres*. The board becomes a scale source for a capture only once a reference",
        "has been derived by fitting that capture's own cameras onto it -- one exists",
        "(`2025-07-03/N01`). Everything else is scaled from the base plate, which the",
        "spreadsheet declares at the top of each season's sheet.",
        "",
        "Gate on `scale.metric` in the JSON, or:",
        "",
        "```",
        "python scripts/build_scanning_record.py --scale-check 03072025/N01 || exit 1",
        "```",
        "",
    ]
    for s in seasons:
        out += ["## {}".format(s["season"]), "", "Source: `{}`".format(s["source"]), ""]
        if s["notes"]:
            out += ["Season notes from the top of the sheet:", ""]
            out += ["- {}".format(n) for n in s["notes"]]
            out.append("")
        out += [
            "| Date | Set | Label (bag) | RSPF | Measurement | Note | Frames | Marker "
            "| Scale |",
            "|---|---|---|---|---|---|---|---|---|",
        ]
        for e in s["entries"]:
            labels = "<br>".join(l["label"] or "" for l in e["labels"])
            rspf = "<br>".join(l["rspf"] or "" for l in e["labels"])
            disk = e.get("on_disk")
            frames = "{} JPG / {} NEF".format(disk["jpg"], disk["nef"]) if disk else "—"
            cells = [
                e["date"] or "",
                e["photo_set"],
                labels,
                rspf,
                e["measurement"] or "",
                e["note"] or "",
                frames,
                "ok" if e["markers_usable"] else "**DO NOT USE**",
                e["scale"]["source"] if e["scale"]["metric"] else "**NON-METRIC**",
            ]
            out.append("| " + " | ".join(c.replace("|", "/") for c in cells) + " |")
        out.append("")
    if drive:
        out += [
            "## Frames on the capture drive",
            "",
            "Counted under `{}` — the laptop's capture drive. A snapshot, and **not**".format(drive),
            "the photographs of record (those are on Mediaflux, and on",
            "Spartan once uploaded). Every tree is shot as a JPG+NEF pair, so the two",
            "counts should match.",
            "",
        ]
        pairs = [
            "{} ({}): {} JPG vs {} NEF".format(
                e["capture_id"], e["on_disk"]["dir"], e["on_disk"]["jpg"], e["on_disk"]["nef"]
            )
            for s in seasons
            for e in s["entries"]
            if e.get("on_disk") and e["on_disk"]["jpg"] != e["on_disk"]["nef"]
        ]
        if pairs:
            out += [
                "Sets where the JPG and NEF counts differ -- a frame was deleted from one",
                "of the two, so the JPG set is not necessarily the whole capture:",
                "",
            ]
            out += ["- {}".format(x) for x in pairs]
            out.append("")
        naming = [
            "{}: `{}` -- {}".format(e["capture_id"], e["on_disk"]["dir"], e["on_disk"]["naming"])
            for s in seasons
            for e in s["entries"]
            if e.get("on_disk") and e["on_disk"].get("naming")
        ]
        if naming:
            out += ["Sets whose directory is not named after the set:", ""]
            out += ["- {}".format(x) for x in naming]
            out.append("")
        if unmatched:
            out += ["Rows with no directory, and directories with no row in the record:", ""]
            out += ["- {}".format(u) for u in unmatched]
            out.append("")
    return "\n".join(out) + "\n"


def carry_disk_counts(seasons, built):
    """Keep the last drive scan when rebuilding without the drive attached.

    Returns the drive those counts came from, or None. The frame counts are a snapshot of
    a removable disk, not something the spreadsheets contain, so a rebuild on a day the
    drive is not plugged in would otherwise DELETE 118 of them from a committed file --
    and the deletion looks exactly like a record that never had them. Carried, and the
    drive it was scanned from is carried with it so the read-out cannot imply it is fresh.
    """
    if not built.exists():
        return None
    prior = json.loads(built.read_text(encoding="utf-8"))
    disk = {e["capture_id"]: e["on_disk"]
            for s in prior.get("seasons", []) for e in s["entries"] if e.get("on_disk")}
    if not disk:
        return None
    for s in seasons:
        for e in s["entries"]:
            if e["capture_id"] in disk:
                e["on_disk"] = disk[e["capture_id"]]
    # ONE value, not a drive name plus a flag beside it saying not to believe it. A reader
    # who takes `frame_counts_from` alone is entitled to be right about what it means.
    #
    # Idempotent: carrying an already-carried value returns it unchanged, or every rebuild
    # on a day the drive is unplugged would wrap the sentence in itself again.
    was = prior.get("frame_counts_from") or "an unnamed drive"
    if CARRIED_MARKER in was:
        return was
    return CARRIED_COUNTS.format(drive=was)


# --------------------------------------------------------------------------------------
# Self-test
# --------------------------------------------------------------------------------------
#
# Same shape as `check_turntable.py` and `compare_meshes.py --self-test`: synthetic
# records, assertions on the EXIT STATUS a caller would gate on, no framework and no
# tests/ directory.
#
# The one it exists for: TODAY NO CAPTURE IS NON-METRIC. Both sheets declare the base
# plate, so all 118 captures have a source and the non-metric branch never runs on real
# data. A branch that never runs is a branch nobody has checked, and the day a season's
# sheet omits the declaration is the day it matters most. So the fixtures below include a
# season that does not declare it, and assert the gate says no.


def _season(year, notes, entries):
    """A record shaped like parse_sheet's output, with only the fields scale code reads."""
    return {"season": year, "source": "fixture.xlsx", "notes": list(notes),
            "entries": [dict(capture_id=cid, object=cid.split("/")[1][0], date=cid.split("/")[0],
                             photo_set=cid.split("/")[1], labels=[], measurement=meas,
                             note=None, markers_usable=mk,
                             markers_note=MARKER_OK if mk else MARKER_WARNING)
                        for cid, mk, meas in entries]}


DECLARES_PLATE = ["Rabati fixture", "Top of the tree base (blue metal base) = 13x19cm"]
DECLARES_NOTHING = ["Rabati fixture", "Camera setting: ISO 100, F/16, WB auto"]


def self_test() -> int:
    import tempfile

    failures = []
    ran = []

    def check(cond, what):
        ran.append(what)
        print(("  ok   " if cond else "  FAIL ") + what)
        if not cond:
            failures.append(what)

    def case(got, want, what):
        check(got == want, "%s (exit %s, wanted %s)" % (what, got, want))

    with tempfile.TemporaryDirectory() as td:
        repo = Path(td)
        (repo / "refs").mkdir()
        ref_rel = "refs/board-fixture.json"
        (repo / ref_rel).write_text("{}")
        refs = {"2025-07-03/N01": ref_rel}

        print("-- a season that declares the plate makes every one of its captures metric")
        good = [_season(2025, DECLARES_PLATE,
                        [("2025-06-16/A01", False, None),
                         ("2025-07-03/M04", False, "Mark1-2: 18cm"),
                         ("2025-07-03/N01", True, "Use base as scale, marker for alignment")])]
        flag_scale_sources(good, repo=repo, references=refs)
        ent = {e["capture_id"]: e for e in good[0]["entries"]}
        check(all(e["scale"]["metric"] for e in ent.values()),
              "all three state a scale source")
        check(ent["2025-06-16/A01"]["scale"]["source"] == PLATE, "the plate is the default")
        check(ent["2025-07-03/N01"]["scale"]["source"] == BOARD,
              "and the one capture with a derived reference is credited to the board")
        check(ent["2025-07-03/N01"]["scale"]["reference"] == ref_rel,
              "naming the reference file, so the claim can be opened")
        check(ent["2025-06-16/A01"]["scale"]["precision"] == SOURCE_CAVEAT[PLATE],
              "the plate's caveat travels with it rather than being restated")
        check("13x19cm" in (ent["2025-07-03/M04"]["scale"]["declared_by"] or ""),
              "and the sheet's own words are on the record, not our reading of them")

        print("\n-- a usable marker is NOT a scale source on its own")
        # 19 captures in 2025 and all 40 in 2026 have a usable marker. One has a derived
        # board reference. If markers_usable were driving this, the other 58 would be
        # credited to a ruler nobody has measured for them.
        marked = _season(2026, DECLARES_PLATE, [("2026-06-15/A01", True, None)])
        flag_scale_sources([marked], repo=repo, references={})
        e = marked["entries"][0]
        check(e["markers_usable"] and e["scale"]["source"] == PLATE,
              "a capture whose marker is usable but unmeasured is still scaled from the plate")
        check(e["scale"]["reference"] is None, "and claims no board reference")

        print("\n-- a season that declares nothing is marked NON-METRIC, not assumed")
        bare = [_season(2027, DECLARES_NOTHING, [("2027-01-01/A01", True, None)])]
        flag_scale_sources(bare, repo=repo, references={})
        sc = bare[0]["entries"][0]["scale"]
        check(sc["metric"] is False and sc["source"] is None,
              "no source, and metric is False -- the field a caller gates on")
        check(sc["precision"] is None,
              "and no precision is quoted for a ruler that does not exist")

        print("\n-- the two gates answer different questions about the same capture")
        # This is the distinction the ticket exists to make. M04's marker is unusable and
        # its millimetres are fine; a capture in an undeclared season is the reverse.
        case(check_capture(good, "2025-07-03/M04"), 2, "--check refuses M04's marker")
        case(scale_check_capture(good, "2025-07-03/M04"), 0,
             "--scale-check accepts M04's millimetres from the plate")
        case(check_capture(bare, "2027-01-01/A01"), 0, "--check accepts the marker")
        case(scale_check_capture(bare, "2027-01-01/A01"), 2,
             "--scale-check refuses the millimetres")

        print("\n-- and a record built before this field says so instead of failing shut")
        stale = [_season(2025, DECLARES_PLATE, [("2025-06-16/A01", False, None)])]
        case(scale_check_capture(stale, "2025-06-16/A01"), 3,
             "a record with no scale field exits 3, not 2 -- 'cannot answer', not 'no'")
        case(scale_check_capture(good, "2025-06-16/Z99"), 3, "an unknown capture exits 3")

        print("\n-- a reference nobody can open is refused before anything is written")
        for bad, why in ((({"2025-07-03/N01": "refs/not-there.json"}), "the file is absent"),
                         (({"2999-01-01/Q01": ref_rel}), "it names no capture in the record")):
            try:
                flag_scale_sources(good, repo=repo, references=bad)
                check(False, "refused a board reference where %s" % why)
            except SystemExit:
                check(True, "refused a board reference where %s" % why)

        print("\n-- rebuilding without the capture drive keeps the last frame counts")
        # Not hypothetical: rebuilding this record on a day the drive was unplugged
        # deleted all 118 counts from the committed file, and the deletion read exactly
        # like a record that never had them.
        built = repo / "prior.json"
        built.write_text(json.dumps({
            "frame_counts_from": "D:/",
            "seasons": [{"entries": [{"capture_id": "2025-06-16/A01",
                                      "on_disk": {"dir": "16062025", "jpg": 177,
                                                  "nef": 177}}]}]}))
        fresh = [_season(2025, DECLARES_PLATE,
                         [("2025-06-16/A01", False, None), ("2025-07-03/M04", False, None)])]
        drive = carry_disk_counts(fresh, built)
        kept = fresh[0]["entries"][0].get("on_disk") or {}
        check(kept.get("jpg") == 177, "the earlier scan's counts are carried, not dropped")
        check(drive and drive.startswith("D:/") and CARRIED_MARKER in drive,
              "and one value names the drive AND says it was not re-counted -- no reader "
              "of it alone can think the counts are fresh")
        built.write_text(json.dumps({"frame_counts_from": drive, "seasons": [
            {"entries": [{"capture_id": "2025-06-16/A01", "on_disk": kept}]}]}))
        again = carry_disk_counts(fresh, built)
        check(again == drive,
              "and carrying an already-carried value leaves it alone, so a rebuild on a "
              "second unplugged day does not wrap the sentence in itself")
        check(fresh[0]["entries"][1].get("on_disk") is None,
              "a capture the earlier scan never saw is still left blank")
        check(carry_disk_counts(fresh, repo / "no-such.json") is None,
              "and with no earlier record there is nothing to carry")

        print("\n-- the read-out adds up")
        mixed = good + bare
        flag_scale_sources(mixed, repo=repo, references=refs)
        lines = scale_summary(mixed)
        check(lines[0].startswith("3 of 4 "), "the headline counts metric out of total")
        check(any("NON-METRIC" in x for x in lines),
              "the non-metric group is named rather than left out")
        check(any("1 from the %s" % BOARD in x for x in lines)
              and any("2 from the %s" % PLATE in x for x in lines),
              "and the per-source counts are separate")

    print("\nself-test: %s -- %d checks, %d failed"
          % ("FAIL" if failures else "PASS", len(ran), len(failures)))
    return 1 if failures else 0


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--drive", help="capture drive to count frames on, e.g. D:/")
    ap.add_argument("--out-dir", default=str(REFERENCE))
    ap.add_argument(
        "--check",
        metavar="CAPTURE",
        help="do not write anything; print one capture and exit 2 if its turntable "
        "marker must not be used. Accepts '2026-06-16/A01' or a capture directory "
        "name such as '16062026/A01' or '03072025/N01'.",
    )
    ap.add_argument(
        "--scale-check",
        metavar="CAPTURE",
        help="do not write anything; print where one capture's millimetres come from and "
        "exit 2 if there is no scale source, so nothing measures a size against it. A "
        "different question from --check, which is about alignment.",
    )
    ap.add_argument("--self-test", action="store_true",
                    help="run the built-in checks on synthetic records and exit")
    args = ap.parse_args()

    if args.self_test:
        sys.exit(self_test())

    # --check reads the BUILT RECORD, and takes the short path out before anything
    # touches a spreadsheet. See the note by _openpyxl(): this is the branch that runs on
    # a cluster node from slurm/, where the xlsx toolchain is not installed and where an
    # environment failure would read as a verdict.
    if args.check and args.scale_check:
        ap.error("--check and --scale-check ask different questions -- may I align on the "
                 "marker, and may I take a millimetre off this. Run one at a time, or the "
                 "exit status says which?")
    gate = check_capture if args.check else scale_check_capture
    asked = args.check or args.scale_check
    if asked and not args.drive:
        built = REFERENCE / "scanning-record.json"
        if not built.exists():
            sys.exit("no built record at {} -- run this script with no arguments first"
                     .format(built))
        sys.exit(gate(json.loads(built.read_text(encoding="utf-8"))["seasons"], asked))

    seasons = []
    for season, fname in SEASONS.items():
        path = REFERENCE / fname
        if not path.exists():
            sys.exit("missing spreadsheet: {}".format(path))
        seasons.append(parse_sheet(path, season))

    flag_markers(seasons)
    flag_scale_sources(seasons)

    unmatched = []
    out_dir = Path(args.out_dir)
    counted_from = args.drive
    if args.drive:
        unmatched = attach_disk(seasons, scan_drive(Path(args.drive)))
    else:
        counted_from = carry_disk_counts(seasons, out_dir / "scanning-record.json")

    if asked:
        sys.exit(gate(seasons, asked))

    doc = {
        "generated_by": "scripts/build_scanning_record.py",
        "sources": {str(k): v for k, v in SEASONS.items()},
        "frame_counts_from": counted_from,
        "seasons": seasons,
    }
    (out_dir / "scanning-record.json").write_text(
        json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (out_dir / "scanning-record.md").write_text(
        to_markdown(seasons, counted_from, unmatched), encoding="utf-8"
    )
    total = sum(len(s["entries"]) for s in seasons)
    print("wrote scanning-record.json and scanning-record.md - {} photo sets".format(total))
    for line in scale_summary(seasons):
        print(line)
    for u in unmatched:
        print("  unmatched:", u)


if __name__ == "__main__":
    main()
