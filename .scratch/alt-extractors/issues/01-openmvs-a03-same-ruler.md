# 01: OpenMVS on A03, same ruler

**What to build:** the M1 baseline this whole comparison stands on — the COLMAP → OpenMVS route's meshes for A03 scored against the M1 requirement on one enforced ruler.

**Answers:** M1

**Blocked by:** None (can start immediately).

**Status:** ready-for-agent

- [ ] OpenMVS meshes for A03 measured with scale sidecars enforced — an unscaled mesh is refused, not measured
- [ ] Fraction of sherd surface within the M1 ~1 mm relief bar reported in mm, with the figure and the meshes named so M7 reuses them, not a second ruler
- [ ] If OpenMVS already meets the requirement, the stop condition is stated in the ticket: record it and halt the swap tracks

## Comments

- 2026-09-06 (scope downgrade, conservator-confirmed): the full cross-mesh
  millimetre replication is struck. A02 already settled OpenMVS-vs-MILo
  decisively on same-rig-class material (flat noise 0.186 vs 0.485 mm), with
  the caveat that one A02 sherd lost its edge silently in an average — and the
  4.1 mm depth floor closed the MILo side of M1 on its own. What the gate still
  needs from A03 is directional only (does OpenMVS clear ~1 mm here), answered
  by: (a) shape-only silhouette compare on the shared fixed frame (staged),
  (b) flat noise via the A02 `stage5_noisefloor.py` pattern in the mesh's own
  frame, (c) break-face renders. Per-sherd mm replication returns only if (a)
  disagrees with A02.
- 2026-09-06: downgrade committed; shape-only compare submitted as job 30154980
  (fixed-frame OpenMVS mm + boxed MILo mm). Laptop-side poll running
  (background shell; `slurm_poll.sh` itself uses bare `ssh`, which hangs from
  WSL here — same squeue/sacct loop over Windows ssh instead). Final State /
  ExitCode to be recorded here on completion.
- 30154980 FAILED in 2:00 (sacct State=FAILED ExitCode=1:0): nvdiffrast
  `interpolate` rejects the strided view `n[None]` in `compare_meshes.py`
  `Renderer.render` — one-line `.contiguous()` fix committed, resubmit pending
  approval.
- Resubmitted 2026-09-06 as job 30155899 (same inputs + fix), laptop poll
  running; final State / ExitCode to follow here.
- 30155899 FAILED in 1:58 (State=FAILED ExitCode=1:0), further along: renders
  ran, report written, then crashed reading out empty silhouette means. Cause:
  masks on disk are `<name>.JPG.png` but compare looked for `<stem>.png` — all
  21 held-out masks missed, zero rows, None means. Fixed with a both-names
  lookup plus a loud no-masks refusal instead of a traceback. Caveat recorded:
  these are rig-in user masks, so the outline scores rig + sherds for both
  meshes equally; sherd-only silhouette is follow-up if numbers demand it.
- Resubmitted 2026-09-06 as job 30156362 (both fixes in), poll watching.
- 30156362 COMPLETED in 1:58 but scored 9.8% vs 0.3% — looked wrong, was
  wrong: rendering millimetre meshes against unit cameras magnifies ~374x, so
  almost nothing projected inside the frame (proven: mesh centroid dead ahead
  of the camera landed at NDC -7.3; sparse points validate the same projection
  code at 98.8%). No successful full-metric compare has ever run since the
  scale gate was added — mm meshes pass the gate but break rendering, unit
  meshes have no valid sidecar. Fixed in `compare_meshes.py`: meshes return to
  model units at load via each sidecar's measured factor (refuses without
  one), mm figures use the measured factor instead of the name-mapped 1.0,
  size-gate comment corrected (content moves extents too), self-test proves
  the conversion (PASS on laptop). OpenMVS side cropped to the shared box:
  100% kept, extents ratio 1.06 — inside the gate. Resubmit pending approval.
- Approved and resubmitted 2026-09-06 as job 30157052 (boxed pair +
  harmonization fix), poll watching; final State / ExitCode to follow here.
- 30157052 COMPLETED 0:0 but the numbers invert reality: MILo 85.5% vs OpenMVS
  21.4% against rig-in masks. The overlays show why — MILo's native mesh keeps
  the whole rig (green on rig = agreement with rig pixels), OpenMVS is
  sherds-only (blue everywhere the rig stands). It is a rig-presence test, not
  a sherd-quality test: type-2 ruler failure, caught by looking. The honest
  rerun is sherd-only masks (alpha extracted from `A03_sherds/images_masked`,
  21 held-out views, `masks_sherd_png/`) via an alternate capture json.
  Slurm job takes optional capture path as 5th arg now.
- Sherd-only rerun submitted 2026-09-06 as job 30158911 (same boxed pair,
  `capture_sherds.json` with masks from `images_masked` alpha, 21 held-out
  views), poll watching; numbers + overlays on landing. This answers the
  directional question the (a)/(b) pick above left open; per-sherd mm stays
  struck unless the silhouette disagrees with A02.
- 30158911 COMPLETED 0:0: sherd-only outlines, OpenMVS 42.2% (worst 26.0%) vs
  MILo 8.6% (worst 6.0%), 21 views. Overlays (`artifacts/A03_compare/`)
  confirm the direction is honest this time: OpenMVS green lands on sherds
  with red overfill fringes; MILo renders mostly rig steel (red) with sherds
  peeking through. 42% is below A02's 66% — overfill fringes, not pose error.
  Flat noise (b) still open: A02 `stage5_noisefloor.py` needs A03 footprint
  judgment calls, not a mechanical rerun — half-day task, named here so it is
  not mistaken for done.

- 2026-09-06: started while user away. Found the M1-gate compare job 30131757
  (submitted 2026-09-06) FAILED in 1:50 — refusal was correct, but the stated
  reason misleads. Measured on the node: MILo `mesh_mm.ply` spans ~983 mm,
  OpenMVS `scene_refined_mm.ply` spans ~643 mm, and their bounding boxes barely
  overlap — different content in different frames (MILo kept ~1 m of
  surroundings; OpenMVS is a tray crop), not a units mismatch. Both sidecars
  claim the same mm factor. Next step is a common-box crop before comparing,
  NOT a blind resubmit — resubmitting the same job reproduces the same refusal.
  Parked for user confirm since it changes the comparison basis.
- 2026-09-06: user pointed at `docs/notes/A02_MESH_METHOD_COMPARISON.md`
  (COMPLETE 2026-08-18, A02, 7 sherds, 4 methods). What it settles:
  (a) OpenMVS flat-surface noise **0.186 mm** vs MILo 0.485 mm — the other
  route already under the ~1 mm bar on noise, same verdict direction as the
  fresh A03 4.1 mm depth floor; (b) the crop problem is SOLVED precedent, not
  a guess — A02 hit the identical "MILo mesh is the whole room" issue
  (their measurement #6) and fixed it with shared sherd boxes measured
  identically for all methods; the stage scripts survive locally under
  `artifacts/A02_metric/verification/scripts/`. What it does NOT settle:
  M1's box as written says A03, not A02 (one tree, different capture); and
  the SH5 caveat cuts against a clean "OpenMVS clears the bar" — OpenMVS
  smoothed one fracture edge out of existence and no method recovered it
  (capture problem, cleared of smoothing-knob blame in job 29892523), so the
  note's own next step is "check break edges per sherd". Proposed path:
  replicate the A02 shared-box method on A03's 10 sherds, edge-check-first
  rather than ranking-first. Awaiting user pick: (a) tick M1's second box via
  A02 with a capture-substitution amendment, or (b) run the A03 shared-box
  rerun.
- 2026-09-06 (parallel session): root cause is deeper than content. `dense_fixed`
  vs `dense_masked` are DIFFERENT reconstructions, not one frame: pairwise camera
  distances across 164 shared views give unit-ratio spread 0.29–1.11, and a
  best-fit similarity leaves 2.5 m median residual on a 1.4 m ring. The
  mask-frame OpenMVS mesh scaled with the MILo factor was wrong-scaled and has
  been deleted (file + sidecar). Redone correctly: `dense_fixed`
  `scene_refined_mm.ply` + sidecar (same reconstruction as the MILo training
  data, factor valid), MILo mesh cropped to its box keeps 98.8% of faces
  (`mesh_mm_boxed.ply`, sidecar carried) — same frame confirmed by behaviour.
  Remaining extents ratio ~1.25 is backdrop content, not units; the gate's
  premise (shared frame ⇒ sizes must agree) does not cover it. Next: shape-only
  silhouette compare (shared frame now valid), mm figures per-sherd à la A02.
