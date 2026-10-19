# 13d: Jaw-fingertip cleanup (targeted, no full rebuild)

**What to build:** composites with no rubber left.

**Answers:** M10. **Blocked by:** 13c. **Status:** ready-for-agent.

Lead-verified facts 2026-10-18 (do not re-derive): composite A33_1177 at full res shows solid black rubber jaws on sherd faces, in NEITHER mask. Steel, knobs, rods are gone.
Refs: T13c composite, dilated masks, builder build_masks_v13c.py under the 17062025 output tree (worker knows these paths from tickets 10-13c).

- Detect: dark smooth low-lum pixels on/near sherd in NEITHER mask; report per-view px + thresholds.
- Fill ONLY those pixels with the refined fork (T10 recipe, env lama02, A100) from surrounding sherd.
- Paste into copies of the T13c composite under new untracked m10_ticket13d output dir.
- Verify: outside-jawmask identity vs T13c composite every view; 164/164 present.
- Stage worst-10 triptychs (photo | T13c composite | T13d composite) + full-res jaw crops; copy to laptop artifacts m10t13d.
- No full re-mask/refill, no tracked edits, no commit/push, compute nodes only, sacct recorded.