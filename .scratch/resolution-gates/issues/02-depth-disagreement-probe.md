# 02: Depth-disagreement probe on A03

**What to build:** the one new seam — a script that renders per-view depth from the
trained A03 Gaussians, projects it into a common frame, and reports cross-view depth
disagreement in **millimetres**: the honest resolution floor M1's first box needs.

**Answers:** M1

**Blocked by:** None (can start immediately; reading the number against the bar happens
in 04).

**Status:** ready-for-agent

- [ ] New script reuses the existing dataset readers (no new data path); reviewable on
      the laptop before any job is submitted
- [ ] Disagreement reported in **mm** on A03 (median + spread, not a single mean), with
      the scale sidecar the number stands on
- [ ] Job submission approved explicitly before sbatch (standing rule); logs fetched to
      `artifacts/`, never committed
- [ ] M1's first box ticked with the date, or the failure written into M1 in one line

## Comments

- 2026-09-06: script + job reviewed, committed (`8ac54fb`), submitted as job
  30131641 (`A03_sherds` / `A03_nomask`). Boxes stay open until the number lands
  and is read against the ~1 mm bar in 04.
- 2026-09-06: job 30131641 FAILED in 25 s — singleton-dim broadcast crash at
  `depth_disagreement.py:66` (render outputs 3D, gt mask 2D). Fixed in
  `.scratch/alt-extractors` ticket 02 (squeeze to 2D at the seam + loud shape
  refusal in `unproject`; crash reproduced and fix verified synthetically on
  the laptop). Resubmitted; see alt-extractors ticket 02 for the new job id.
- 2026-09-06: resubmitted with the fix as job 30132793 (same args
  `17062025/A03_sherds 17062025/A03_nomask`). Number lands in
  `output/17062025/A03_nomask/depth_disagreement.json`.
