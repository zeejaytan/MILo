# 07: Minimal wedge repro — smallest view set that stalls

**What to build:** the smallest A03 view subset that reproduces the reflect_trace wedge, plus a matched subset that trains clean.

**Answers:** M9

**Blocked by:** 05 (subset design follows the autopsy features).

**Status:** ready-for-agent

- [ ] Wedge set (killers + nearest neighbours) vs clean set (neighbours only), trained as short legs from scratch — bounded at 2 GPU legs total, first save inside the wall
- [ ] Subset lists are copies (train_list.05wedge.txt style); the curated train_list.txt and its train_list.143.txt backup are never overwritten by this ticket
- [ ] Verdict recorded: minimal wedging set (list the views) vs clean set, or no-repro-under-X-views (say so explicitly — routes back to 08 as "trigger unidentified")
- [ ] No edits to the authors' tree; no curation of the main training lists here

## Evidence (worker 2026-10-20)

Subset design (from 05 neighbour table — killers + frame-adjacent passing neighbours):

- WEDGE set (12 views, `data/goris_A03_t07wedge/train_list.txt`): A31_1111(K) A31_1110 A31_1112 A32_1142(K) A32_1141 A32_1143 A32_1151(K) A32_1150 A32_1152 A33_1176(K) A33_1175 A33_1177. Test: A31_1100 (held-out, trains on all 12). All 8 neighbours verified in-train in curated `train_list.txt`; all 4 killers verified excluded.
- CLEAN set (8 views, `data/goris_A03_t07clean/train_list.txt`): the 8 neighbours only. Test: A31_1100.
- Both dirs symlink images/object_mask/sparse/mask_panels to `data/goris_A03/`; only the list files are new. Curated `train_list.txt` + `train_list.143.txt` untouched (verified, not written).
- Legs: `slurm/goris_t07wedge.slurm` (job 33449900) + `slurm/goris_t07clean.slurm` (job 33449901), committed as c29386b. Settings mirror the wedging recon: --resolution 2 --depth_ratio 0.0 --random_background --eval --logger none, faulthandler diag wrapper, --test_iterations 100000 (no in-training reports), --iterations 6000, saves+chkpnts every 1000, 24h wall on gpu-a100 (first save ~3h, inside wall).
- Config validation (login node, env python + sidecar, real ModelParams parser): wedge dir loads train=12 [A31_1110 A31_1111 A31_1112 A32_1141 A32_1142 A32_1143 A32_1150 A32_1151 A32_1152 A33_1175 A33_1176 A33_1177] test=1 [A31_1100]; clean dir loads train=8 (neighbours only) test=1 [A31_1100]. Masks/images resolve via symlinks. Jobs will start clean.
- Status: both jobs SUBMITTED 2026-10-20 (sbatch 33449900 wedge, 33449901 clean), PENDING (Priority) at last poll — GPU queue busy. sacct/iters pending — poll then record.

## Comments

- 2026-10-19 (lead): bounded by conservator decision — 2 legs, then verdict whatever the outcome. Uses the 4000-iter wedge point as the repro bar: a subset that sails past 5000 iters does not reproduce it.
