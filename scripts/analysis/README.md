# Why one capture's mesh comes out coarser than another's

These are the measuring instruments from the August 2026 investigation into why the MILo
mesh of the A03 sherds came back visibly coarser and more ragged around the fragment edges
than the A02 mesh, which had looked smooth. They are kept because the question is not
closed, and because several of them exist to stop a specific wrong answer being given again.

Run them from the Spartan working area with the `milo` conda environment:

```bash
module load Miniforge3/24.7.1-2
source activate /data/gpfs/projects/punim2657/MILo/envs/milo
python per_sherd2.py A02=<mesh.ply>:<mm_per_unit> A03=<mesh.ply>:<mm_per_unit>
```

Several scripts (`render_a04.py`, `three_sherds.py`) have the output paths for a specific
comparison written into them; they are records of a particular figure, not general tools.

## The one number that matters

**Vertices per cm² of terracotta surface.** Not total vertex count, not median edge length
over the whole scene. Those are dominated by however much backdrop, clamp and rig each
mesh happens to contain, and they differ between captures for reasons that have nothing to
do with the sherds. Comparing scene-wide numbers produced a confident, published, wrong
claim that A03 was *finer* than A02 — the reverse of the truth. `sherd_density.py` and
`per_sherd2.py` isolate the sherd by vertex colour before measuring anything.

Millimetres between sample points is the plain-language form: `10 / sqrt(vertices per cm²)`.

## What the instruments measure

| Script | Question it answers |
|---|---|
| `sherd_density.py` | How finely is the sherd surface sampled, sherd only, whole mesh |
| `per_sherd2.py` | The same per fragment, with area, elongation and brightness beside it |
| `edge_quality.py` | Torn boundary: open edge length per cm². Separates carving damage from reconstruction |
| `sherd_closeup.py`, `three_sherds.py`, `render_a04.py` | Draw fragments at a matched mm-per-pixel so coarseness can be seen, not just totalled |
| `pixels_per_mm.py`, `resolution.py` | The physical ceiling on detail: focal length ÷ camera distance |
| `sherd_signal.py` | Brightness, local contrast and focus on the sherd interiors |
| `rig_sharpness.py` | The same, on the **clamp** — the same physical object every capture day, so it is the control |
| `sherd_pixels.py` | How much of the frame a sherd occupies, and how much of its outline sits against the rig |
| `mask_rim.py` | Where the extra area in a loose training mask actually falls |
| `match_quality.py` | Features detected and matched per photograph |
| `feature_spread.py` | Where in the frame those features sit — detects whether a mask was applied at the camera-solving stage |
| `init_vs_final.py` | Sparse seed points landing on each fragment, and how many views saw them, against the final sampling density |

## What has been measured so far

Vertices per cm², fragments over 20 cm² only, so size is held roughly constant:

| Capture | Training | Fragments over 20 cm² |
|---|---|---|
| A02 | unmasked | 829, 884 |
| A01 (16062025) | unmasked | 534, 796, 801 |
| A03 | masked | 378, 534 |
| A04 | masked | 161, 299 |

## Ruled out, with the test that ruled it out

- **How much scene the training mask includes.** A03 retrained at 4.1% vs 23.9% mask
  coverage — 5.8× more scene, 6.9× more Gaussians — gave 445 vs 456 v/cm². A 2% move.
- **A mask applied at the camera-solving stage.** `feature_spread.py`: A03's detected
  features cover 68% of the frame. Not masked there.
- **Silhouette carving.** Raw 3.82 vs carved 3.79 cm of torn edge per cm².
- **Photograph resolution.** 5.0 pixels/mm on every capture.
- **Fragment size.** r = −0.07 across 25 fragments in three captures. See the caveat below.
- **Too few starting points.** A03 has the *most* sparse seeds per cm² of sherd (347 vs
  A02's 110) and the worst result.
- **A worse camera solve.** A03 has the *lowest* reprojection error of the three (0.768 px
  vs A02's 0.841) and the longest feature tracks. Reprojection error has now rated a worse
  reconstruction better twice in this workspace; see `../../docs/lessons.md` upstream.
- **Softer photographs.** `rig_sharpness.py` on the clamp — identical hardware, consecutive
  days — puts A03 at 0.94× of A02. The pictures are not softer.

## Still open

Every masked training run sits below every unmasked one, while varying the mask *width*
within one capture changes nothing. That is two unmasked runs against three masked ones,
and masking is confounded with which capture and which sherds — the unmasked runs are also
the ones with the largest fragments. **It is a lead, not a finding.** The test that would
settle it is to mask A02 and retrain: if masked A02 still returns ~838 v/cm², masking is
finished as an explanation.

A04 additionally mixes two photograph series in one solve — 30 frames named `A35_*` and
130 named `A42_*`. Worth checking before A04 is used for anything.

## The caveat this directory exists to carry

The first version of the per-fragment test kept only strongly terracotta fragments above
3000 vertices, which left **three per capture**. Three points will trend whichever way you
hope. It gave +0.72 for A02 and −0.53 for A03, and only the +0.72 was reported, producing a
confident explanation built on fragment size that the conservator refuted from the published
table within a minute. Widening to 25 fragments gave −0.07.

`per_sherd2.py` replaces that script and prints every capture's correlation with its n
beside it. **When it prints a statistic for several groups, report every group or report
none.** The missing groups are where the answer usually is.
