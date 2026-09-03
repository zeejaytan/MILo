# 01: The comparison refuses when it cannot establish scale

**What to build:** `compare_meshes.py` finds out what units each mesh is in before it
reports a single millimetre, by reading the `.scale.json` sidecar beside each one. When
both meshes declare millimetres, the comparison runs as it does today and additionally
prints, above the numbers, where each mesh's millimetres came from, the precision that
source declares, and any disagreement the sidecar recorded inside its own measurement.
When either sidecar is missing, or the two disagree on units, the script stops with a
non-zero exit and says which mesh and why — no millimetre figure is printed at all.

Where only shape matters, `--shape-only` runs the half of the comparison that does not
depend on units — outline agreement against held-out photographs — and suppresses every
millimetre figure: surface disagreement, wall thickness, the extents read-out and the
scale bar. It has to be asked for by name, so a shape answer can never be mistaken for a
metric one.

The refusal is proved able to fire, not merely observed not to. `--self-test` builds
synthetic meshes and sidecars in a temporary directory, runs the real path, and asserts
the exit status against answers fixed in advance — the same shape as
`check_turntable.py:self_test`, and for the same reason: a gate that has only ever been
seen to pass is indistinguishable from one that always passes.

**Answers:** `M3`

**Blocked by:** None (can start immediately)

**Status:** done — 2026-09-03

- [x] Both meshes declare millimetres and agree → exit 0, millimetre figures present,
      and the scale source, its stated precision and the sidecar's own disagreement
      figures printed above the results for both meshes
- [x] Either sidecar missing → non-zero exit naming which mesh, and **no millimetre
      figure anywhere** in stdout, stderr or the written report
- [x] The two sidecars disagree on units → non-zero exit
- [x] `--shape-only` with no sidecar at all → exit 0, outline agreement present, every
      millimetre figure absent — **the gate and the suppression are asserted; the outline
      figures themselves were not run**, because that path needs nvdiffrast on a GPU node
- [x] A sidecar recording a rejected sub-measurement and a large cross-cloud
      disagreement → exit 0, with that disagreement printed rather than buried in JSON
- [x] `frac_within_0.5mm` / `frac_within_1mm` are computed against thresholds converted
      into mesh units, not against raw 0.5 and 1.0 — the specific defect that started this
- [x] `--self-test` asserts the **exit status** for every case above and returns non-zero
      if any case comes out wrong

## Comments

**2026-09-03 — done on branch `markers-turntable`.** `scripts/compare_meshes.py` now takes
the scale decision before the capture, the COLMAP model or the CUDA renderer are touched,
so `--self-test` runs on the laptop in a few seconds and needs no data.

Two things came out of the work that were not in the ticket:

- `slurm/milo_compare.slurm` runs under `set -e`, so the gate now stops that job. The two
  new exit statuses (2 = a mesh has no sidecar, 3 = the two disagree on units) are
  documented above the call, with the fix for each.
- The refuse-versus-degrade decision was written up as `docs/adr/0001-...`, which the spec
  had flagged as likely.

Verified against the real sidecars in `artifacts/A02_metric` and `artifacts/A03_metric`:
the gate passes and prints the source, the ~1 % stated precision, and A03's 5.4 %
sparse-versus-dense disagreement, which until now was reachable only by opening the JSON.
