# 07: Minimal wedge repro — smallest view set that stalls

**What to build:** the smallest A03 view subset that reproduces the reflect_trace wedge, plus a matched subset that trains clean.

**Answers:** M9

**Blocked by:** 05 (subset design follows the autopsy features).

**Status:** ready-for-agent

- [ ] Wedge set (killers + nearest neighbours) vs clean set (neighbours only), trained as short legs from scratch — bounded at 2 GPU legs total, first save inside the wall
- [ ] Subset lists are copies (train_list.05wedge.txt style); the curated train_list.txt and its train_list.143.txt backup are never overwritten by this ticket
- [ ] Verdict recorded: minimal wedging set (list the views) vs clean set, or no-repro-under-X-views (say so explicitly — routes back to 08 as "trigger unidentified")
- [ ] No edits to the authors' tree; no curation of the main training lists here

## Comments

- 2026-10-19 (lead): bounded by conservator decision — 2 legs, then verdict whatever the outcome. Uses the 4000-iter wedge point as the repro bar: a subset that sails past 5000 iters does not reproduce it.
