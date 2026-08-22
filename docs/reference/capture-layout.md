# How the Rabati captures are organised

> ## ⚠ Do not use the turntable marker before 2025-07-03 N01
>
> **Up to and including 2025-07-03 M04 the marker was placed incorrectly.** Do not feed
> it to feature recognition, registration or alignment on any of those captures — it
> will drag the solve off, and the result can still look plausible while being wrong.
> Scale and align those from the **13x19 cm base** instead.
>
> **From the N01 batch (2025-07-03) onwards the marker is on the turntable** and is the
> intended alignment reference. The record says so itself in N01's measurement cell:
> *"Use base as scale, marker on turntable for alignment."* Everything from N01 on,
> including all of 2026, is fine.
>
> **The cutoff is a place in the record, not a date.** M01-M04 were shot on the same day
> as N01 but come before it, and they carry the bad marker. Read `markers_usable` in
> `scanning-record.json`, or the Marker column in `scanning-record.md`; do not work it
> out from the date. To gate a pipeline step on it, ask the script — it exits 2 when the
> marker must not be used:
>
>     python scripts/build_scanning_record.py --drive D:/ --check 03072025/M04
>     python scripts/build_scanning_record.py --check 2026-06-16/A01

Authoritative source: `Rabati 2025 scanning record.xlsx` and
`Rabati 2026 scanning record.xlsx` in this directory, copied from the conservator's own
record. Read those before assuming anything about a capture.

`scripts/build_scanning_record.py` turns both spreadsheets into
**`scanning-record.json`** (one object per photo set, shorthand expanded) and
**`scanning-record.md`** (the same thing as tables). Read those from code; do not
hand-edit them, and re-run the script when a spreadsheet changes:

    python scripts/build_scanning_record.py --drive D:/

`--drive` also counts the frames actually present in each capture directory on the
laptop's capture drive and lists every place the record and the disk disagree.

## A "pottery tree" is the unit of reconstruction

The record's own key:

> `A01` = tree1 for object A, `A02` = tree2, `B01` = new object B tree1, etc.
> Clamp ID in brackets. Top of the tree base (blue metal base) = 13x19 cm.
> Camera: ISO 100, F/16, 1/1.6, WB auto. Approx 20 min shooting time per tree.

A tree is one loading of the clamp rig, photographed all the way round — roughly 120
frames in 2025 and 160 in 2026. **One tree = one reconstruction.** Where a single object
needs several loadings, they are numbered as parts: A01, A02, A03, A04 are four parts of
the same object A, shot across 16-17 June 2025.

In the JSON, `object` is that shared letter and `capture_id` is `<date>/<set>` — see the
2026 warning below for why the set on its own is not a key.

## Where a tree lives on disk

Most dates hold several trees, one subdirectory each:

    Rabati2025/17062025/A02/     <- one tree
    Rabati2025/17062025/A03/     <- another tree
    Rabati2025/04052025/O01/     ...

**16062025 is the exception**: it holds a single tree (A01) with the photographs directly
in the date directory and no subdirectory at all.

    Rabati2025/16062025/*.JPG    <- 177 photographs, ALL of tree A01

Three other directory names do not match the record, all listed under "Sets whose
directory is not named after the set" in `scanning-record.md`:

- **`04052025` is 2025-07-04**, not 4 May. The record's own date cell reads `04/07/205`;
  both are slips for the same day. Nothing was shot in May.
- **`25062025/G01` is tree J01.** The J series starts that morning and the first folder
  was left with the previous name. `21062025/G01` is a real and *different* tree — the
  two are not the same object.
- **`Pot01` / `Pot02`** are the record's `Pot 01` / `Pot 02`, without the space.

## The filename prefix is not a tree ID

Filenames look like `A11_0704.JPG`, `A12_0772.JPG`, `A13_0805.JPG`, `A14_0837.JPG`. Those
prefixes come from the camera, not from the record, and they do **not** mark trees or
batches. On 16062025 the frame numbers run continuously straight through them —
0704-0771, 0772-0804, 0805-0836, 0837-0880 — one unbroken shooting sequence of one tree.

This has already caused one wrong turn: the prefixes were read as batch boundaries, the
177 photographs were split into four "captures" of 68/33/32/44, and A11 was reconstructed
alone. It produced a technically clean reconstruction of a third of an object. Different
sherds face the camera at different angles as you walk around a tree, so four sample
frames showing different sherds is exactly what one tree looks like — the evidence was
consistent with the correct answer too.

## 2026 season

40 trees over five days, 15-19 June 2026, and a different rig from 2025.

**Tree IDs restart on 2026-06-16, so the set name alone is ambiguous.** `A01` exists on
both 15 and 16 June and they are *different trees holding different bags* — and the bags
are swapped between the two days, which is exactly how a wrong pairing would look if you
matched by name:

| Directory | Bag | Frames |
|---|---|---|
| `15062026/A01` | Loc 2522 Bag 68 | 97 |
| `15062026/A02` | Loc 2522 Bag 73 | 130 |
| `16062026/A01` | Loc 2522 Bag 73 | 135 |
| `16062026/A02` | Loc 2522 Bag 68 | 128 |

Always key a 2026 capture by **date and set** (`capture_id` in the JSON). This did not
arise in 2025, where every set name was used once.

Other things that changed:

- **Light box, not the open rig.** One light front left, one back right, one top through
  diffusing material. The record notes that masking "cut processing time by half".
- **Camera heights are recorded**: 850, 950, 1200, 1310, 1450 mm. The frame count also
  rose from ~120 to ~160 per tree, which would be five rings of about 32 — but the record
  does not say how many rings were shot, and that pairing has not been checked against
  the frames themselves.
- **The base is described only as "metal base", still 13x19 cm.** Same scale reference.
- **Shutter speed is not recorded for 2026** — the sheet gives ISO 100, F/16, WB auto and
  omits the 1/1.6 that 2025 carried.
- Several trees are of joining fragments, flagged in the record: `D01`/`D02` connected rim
  pieces, `D03` connected handle, `D04` three large pieces connected, `D05`/`D06` connected
  via marking (and to each other), `D07` base pieces with a two-piece join, `C06` a
  matching pair. These are the ones worth looking at for break-surface work.
- **`2026-06-16/A01` is flagged "Need to rescale before use".** Do not treat its scale as
  settled.
- A reminder for a future season, not yet shot: bags 570, 569, 568, Loc 1401, D8.2 have
  pieces that fit together.

## Notes in the record that bear on reconstruction quality

- **A01 (16062025): "Ceramic tray, First trail run, may need to reshot."** The first
  capture of the season and flagged as provisional by the person who shot it. Poor results
  here say more about the capture than about any software.
- **B01 (18062025):** "few small sherds cannot fit on clamp".
- **N01-N05 (03072025):** "Use base as scale, marker on turntable for alignment. No dense
  cloud straight to model" — a different processing route, and the point at which the
  marker becomes usable. See the warning at the top of this file: everything before N01
  has the marker in the wrong place, M01-M04 on the same day included.
- **Site01, Site02 (02072025):** shot outdoors, ISO 100 F/8 1/250 direct sunlight, not the
  indoor rig settings.

The blue metal base is 13x19 cm, which is a scale reference present in most frames.

## Where the photographs actually are

Every tree is shot as a **JPG + NEF pair**. Seven 2025 sets have exactly one more JPG
than NEF, and `03072025/N01` has seven more — a frame was removed from one side, so the
JPG count is not automatically the whole capture. All eight are listed in
`scanning-record.md`.

The photographs of record are on Mediaflux. As of 2026-08-22 the Spartan copy under
`/data/gpfs/projects/punim2657/Rabati2025/` holds only `16062025` and `17062025`; **no
2026 capture has been uploaded to Spartan yet.** The frame counts in `scanning-record.md`
were read from the laptop's capture drive (`D:`), which is a working copy, not the archive.
