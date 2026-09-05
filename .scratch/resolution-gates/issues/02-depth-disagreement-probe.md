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
