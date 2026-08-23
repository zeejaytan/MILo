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


def check_capture(seasons, wanted) -> int:
    """Answer 'may I use the marker on this capture?' for one capture.

    Exit 2 when the marker must not be used, so a pipeline step can gate on it:

        python scripts/build_scanning_record.py --check 03072025/M04 || exit 1
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
        print("no such capture in the record: {}".format(wanted))
        print("(directory names only resolve when --drive is also given)")
        return 3
    if len(hits) > 1:
        print("ambiguous: {}".format(", ".join(h["capture_id"] for h in hits)))
        return 3
    e = hits[0]
    print("{}  object {}  {}".format(e["capture_id"], e["object"], e["labels"][0]["label"]
                                     if e["labels"] else "(no bag label)"))
    if e.get("on_disk"):
        print("  directory {}  {} JPG / {} NEF".format(
            e["on_disk"]["dir"], e["on_disk"]["jpg"], e["on_disk"]["nef"]))
    if e["markers_usable"]:
        print("  MARKER OK - {}".format(e["markers_note"]))
        return 0
    print("  MARKER UNUSABLE - {}".format(e["markers_note"]))
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
    for s in seasons:
        out += ["## {}".format(s["season"]), "", "Source: `{}`".format(s["source"]), ""]
        if s["notes"]:
            out += ["Season notes from the top of the sheet:", ""]
            out += ["- {}".format(n) for n in s["notes"]]
            out.append("")
        out += [
            "| Date | Set | Label (bag) | RSPF | Measurement | Note | Frames | Marker |",
            "|---|---|---|---|---|---|---|---|",
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
            ]
            out.append("| " + " | ".join(c.replace("|", "/") for c in cells) + " |")
        out.append("")
    if drive:
        out += [
            "## Frames on the capture drive",
            "",
            "Counted under `{}` — the laptop's capture drive, a snapshot at generation".format(drive),
            "time and **not** the photographs of record (those are on Mediaflux, and on",
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
    args = ap.parse_args()

    # --check reads the BUILT RECORD, and takes the short path out before anything
    # touches a spreadsheet. See the note by _openpyxl(): this is the branch that runs on
    # a cluster node from slurm/, where the xlsx toolchain is not installed and where an
    # environment failure would read as a verdict.
    if args.check and not args.drive:
        built = REFERENCE / "scanning-record.json"
        if not built.exists():
            sys.exit("no built record at {} -- run this script with no arguments first"
                     .format(built))
        sys.exit(check_capture(json.loads(built.read_text(encoding="utf-8"))["seasons"],
                               args.check))

    seasons = []
    for season, fname in SEASONS.items():
        path = REFERENCE / fname
        if not path.exists():
            sys.exit("missing spreadsheet: {}".format(path))
        seasons.append(parse_sheet(path, season))

    flag_markers(seasons)

    unmatched = []
    if args.drive:
        unmatched = attach_disk(seasons, scan_drive(Path(args.drive)))

    if args.check:
        sys.exit(check_capture(seasons, args.check))

    out_dir = Path(args.out_dir)
    doc = {
        "generated_by": "scripts/build_scanning_record.py",
        "sources": {str(k): v for k, v in SEASONS.items()},
        "frame_counts_from": args.drive,
        "seasons": seasons,
    }
    (out_dir / "scanning-record.json").write_text(
        json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (out_dir / "scanning-record.md").write_text(
        to_markdown(seasons, args.drive, unmatched), encoding="utf-8"
    )
    total = sum(len(s["entries"]) for s in seasons)
    print("wrote scanning-record.json and scanning-record.md - {} photo sets".format(total))
    for u in unmatched:
        print("  unmatched:", u)


if __name__ == "__main__":
    main()
