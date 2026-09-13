# 01: New PGSR sibling shell

**What to build:** a new top-level PGSR project folder standing beside the existing reconstruction projects, so PGSR work stops living inside the MILo fork.

**Answers:** M8

**Blocked by:** None (can start immediately).

**Status:** resolved

- [x] Sibling folder exists with the standing project shape: writable fork remote plus canonical read-only upstream, job-script area, heavy outputs gitignored with cluster-only data, small renders and metrics as the local landing zone, project working notes
- [x] Intent area reserves prefix R with M8 named as the question this first work answers; no duplicate question opened for the same verdict
- [x] Nothing PGSR-side imports or reads from the MILo fork at build, train or fuse time; the MILo tracked fork-change list gains no entry
- [x] Cluster compute reuses the existing conda env where its imports resolve; no fresh env build unless an import probe fails, and then only the additive delta is recorded
- [ ] Link gate reports zero errors

## Comments

- 2026-09-09: shell built on the laptop (own repo, `main`; origin → intended `zeejaytan/PGSR` fork, still to be created; upstream → `zju3dv/PGSR` read-only). Standing shape in place: remote helpers with PGSR paths, heavy-data gitignore, project notes, intent area reserving R with M8 named. Umbrella remote accident on the way (stray `upstream` added to `C:/PR/.git`) reverted and verified; umbrella `AGENTS.md` working-tree edit predates this work and was left alone. Status left `ready-for-agent` — resolving waits for the M8 write-back (05), since a resolved ticket must move its question.
- 2026-09-09: fork created (`zeejaytan/PGSR`) and shell pushed (shell `adfdf52` + history merge `2e03931`, upstream README kept as the load-bearing doc, ours folded into AGENTS.md). SSH push refused (key not offered), so origin is HTTPS — either load the key or keep HTTPS. Spartan checkout owed at first job (04). Box 1 now holds.

## Answer 2026-09-13

Shell did its job and stayed clean: every PGSR job (trains 30390922/30424099, extracts 30481815/30483922, probes on holder 30472519) ran from the sibling checkout; R reserved with M8 named (`PGSR/intent/README.md`); env reused with only the recorded additive delta (`diff-plane-rasterization`, `pytorch3d v0.7.7`); MILo's fork-change list gained nothing. Gate box unticked: the loop gate still reports one error, pre-existing and unrelated (M6 ticket resolved without its question moving — not this effort's to fix). M8 answered NO as mesh route; no R question opened (viewing-only left for a future R if wanted).
