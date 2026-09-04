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
- [x] The two sidecars disagree on units → non-zero exit. **Two spellings of the same
      unit are not a disagreement** — `mm` and `millimetres` compare equal, because the
      comparison is on the size the name denotes, not on the string
- [x] `--shape-only` → exit 0, outline agreement present, every millimetre figure absent.
      Asserted in both the no-sidecar case and the case that could actually leak: **both
      meshes fully scaled and `--shape-only` asked for anyway**, where no scale factor
      may reach stdout or the written report. Scope stated exactly, because the ADR
      lesson is not to claim reach you do not enforce: what is suppressed is every
      figure measured off the mesh and every factor that could produce one. The
      sidecar's naming provenance — which mesh could have been measured and on whose
      authority — is deliberately kept, and the reference plate's own name contains its
      dimensions. **The gate and the suppression are asserted; the outline figures
      themselves were not run**, because that path needs nvdiffrast on a GPU node
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

### 2026-09-04 — after code review

`/code-review` against `fae2c88` ran two axes. Five findings were fixed here; three
became follow-up work.

Fixed:

- **`mm` and `millimetres` were refused as a unit conflict.** `MM_PER_UNIT_BY_NAME`
  existed to accept aliases and the agreement test compared the raw strings, so a
  correctly-scaled pair got exit 3 and the message "one of them was never scaled" —
  false, and the kind of wrong refusal that gets a gate commented out. Now compares the
  factor the name denotes. Asserted.
- **`--shape-only` wrote `mm_per_unit: 373.73` into `comparison.json`** via the raw
  sidecar echo, and printed the sidecar's precision caveat. A suppressed millimetre with
  the factor still in the JSON is one multiplication from being reported. Scale factors
  are now stripped from the report and the caveat is not printed in shape-only; the
  naming provenance stays. Asserted on the case that could leak, which was previously
  unasserted.
- **`--self-test` was registered in argparse and unreachable** — dispatch scanned
  `sys.argv` while three flags were `required=True`, so `--help` advertised a flag the
  parser could never accept. The four paths are now checked after parsing, and the
  self-test dispatches through argparse as `check_turntable.py` does.
- **The module docstring still said "renders are written whatever the numbers say"**,
  which a scale refusal makes false — it returns before any mesh is loaded.
- **`slurm/milo_compare.slurm` documented exit 2 as "no sidecar"**; it also fires for
  units the script will not guess at.

Follow-up, not done here:

- `silhouette_compare.py:176` still does `doc.get("mm_per_unit", 1.0)` — the exact
  degrade-to-default ADR 0001 bans, inside the ADR's stated scope. **Ticket 05 or an ADR
  scope amendment; open decision.**
- `self_test` asserts `exit_code_for_scale(scale_decision(...))`, never `main()`. The
  spec asked for the real path. Ticket 05.
- `sidecar_path` / `read_scale` are private to this script and there is no writer for
  derived sidecars — ticket 03 is blocked on that extraction, which is where the
  `ScaleDecision` type and the `extents_mm` / `extents_units` schema switch should be
  dealt with too.
