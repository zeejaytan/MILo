# How the Rabati 2025 captures are organised

Authoritative source: `Rabati 2025 scanning record.xlsx` in this directory, copied from
the conservator's own record. Read that before assuming anything about a capture.

## A "pottery tree" is the unit of reconstruction

The record's own key:

> `A01` = tree1 for object A, `A02` = tree2, `B01` = new object B tree1, etc.
> Clamp ID in brackets. Top of the tree base (blue metal base) = 13x19 cm.
> Camera: ISO 100, F/16, 1/1.6, WB auto. Approx 20 min shooting time per tree.

A tree is one loading of the clamp rig, photographed all the way round — roughly 150-180
frames. **One tree = one reconstruction.** Where a single object needs several loadings,
they are numbered as parts: A01, A02, A03, A04 are four parts of the same object A, shot
across 16-17 June.

## Where a tree lives on disk

Most dates hold several trees, one subdirectory each:

    Rabati2025/17062025/A02/     <- one tree
    Rabati2025/17062025/A03/     <- another tree
    Rabati2025/04052025/O01/     ...

**16062025 is the exception**: it holds a single tree (A01) with the photographs directly
in the date directory and no subdirectory at all.

    Rabati2025/16062025/*.JPG    <- 177 photographs, ALL of tree A01

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

## Notes in the record that bear on reconstruction quality

- **A01 (16062025): "Ceramic tray, First trail run, may need to reshot."** The first
  capture of the season and flagged as provisional by the person who shot it. Poor results
  here say more about the capture than about any software.
- **B01 (18062025):** "few small sherds cannot fit on clamp".
- **N01-N05 (03072025):** "Use base as scale, marker on turntable for alignment. No dense
  cloud straight to model" — a different processing route.
- **Site01, Site02 (02072025):** shot outdoors, ISO 100 F/8 1/250 direct sunlight, not the
  indoor rig settings.

The blue metal base is 13x19 cm, which is a scale reference present in most frames.
