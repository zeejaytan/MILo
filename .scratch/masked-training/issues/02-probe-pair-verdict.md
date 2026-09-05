# 02: Contact boxes plus probe pair verdict

**What to build:** hand-marked clamp-contact exclusion boxes on the 2–3 sampled break-face edges recorded on the ticket, two ~8k-iteration probe runs (patched weight 0.5 vs unpatched control, identical seed and config over the existing sherd-only dataset), eroded-band alpha curves plus rim renders, and the go/no-go on the stop rule.

**Answers:** M5

**Blocked by:** 01 (needs the patched loss and its instrumentation).

**Status:** resolved (probe job 30090865 FAILED on my flag spelling — `--masked-training` vs `--masked_training`; control leg had finished clean. Fixed with per-leg skip + CLI-name guard; resubmitted as 30094277, reusing control. Standing go for 03–04 on green holds.)

## Comments

2026-09-06: contact-face hand-marking skipped at the conservator's call. Consequence
stated plainly: arc scoring will include permanently unobserved clamp-contact faces,
so the masked run may read worse than it is where honesty leaves holes. Read any
contact-zone arc gap as missing surface, never as wrong surface, until boxes exist.

- [ ] Contact-exclusion boxes named per edge and recorded before any run; excluded from all arc scoring
- [ ] Both probe runs complete past depth re-init with identical seed and config, differing only in the patch flag
- [ ] Band-alpha curves plus rim close-ups at 0.10 mm/px or tighter exist for both runs
- [ ] Go/no-go applied on the recorded rule (band alpha below 0.2 *and* receding rims stops the pair); the verdict names numbers and pictures

## Comments 2 — probe collapsed into full runs (2026-09-06)

Job 30094277 taught us the probe design was fiction: train.py read_config lets
milo/configs/fast stomp --iterations, so both legs trained toward 18k, not 8k, and
the job died on its 6h limit with masked at ~14k. Control finished full-length
([ITER 18000] Saving Gaussians) and stands as the A/B control — no second control
ever runs. Masked-leg alpha to iter 13k: outside 0.0008–0.0037 (far below the 0.2
tripwire — background draining as designed), inside 0.009–0.017 and rising. The
number half of the stop rule reads GO; rim renders from the completed masked run
carry the other half.

## Comments 3 — masked training finished; renders resubmitted (2026-09-06)

Job 30099987 FAILED after training completed (render stage asked for
iteration_8000 clouds; runs are 18k — fixed). Masked run facts: 18,000/18,000
iters, final 18,443 Gaussians (background loss + density control drained ~91% of
the 222k start), band alpha outside 0.0018 / inside 0.0112 at close. Renders-only
resubmission 30121191 skips both finished trainings.

## Answer — GO (2026-09-06)

Number half: band alpha outside 0.0008–0.0037 from iter 8k to 18k, far below the
0.2 tripwire — background drains as designed. Picture half: 6 rim-band pairs
(3 spread held-out views x 2 windows) show masked renders rig-free with fracture
relief intact; no 0.6–0.9 mm rim recession anywhere. Bonus finding that dwarfs the
probe: control masked-PSNR on held-out clay pixels swings 10.1–28.0 dB view to
view (median 18.2) while masked holds 20.4–25.3 (median 23.9) — unmasked training
fails novel-view synthesis on ~1/3 of held-out views (renders empty room where
photos show sherds), masked training holds all 21. Renders + pairs fetched to the
laptop; per-view table on the ticket thread. Recorded into intent/M5.
