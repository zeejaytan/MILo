# 05: Eye QA + verdict + write-back to M10

**What to build:** the conservator's witnessed verdict on both arms, then the question closed whatever the outcome.

**Answers:** M10

**Blocked by:** 04-same-voxel-extract-measure.

**Status:** ready-for-agent

**Needs-eye:** `visual-qa/viewer/pairs/m10_ab.json` (both-arm ridge-resolving sherd close-ups; stage via `viewer/stage_pair.py`, serve `viewer/view_juglet.py`, laptop-only; previews decimated — target_faces + resolution_floor stated so ~0.2mm ridge judgement uses full mesh)

- [ ] Stage left/right pair in shared COLMAP frame, millimetres, with src + manifest previews per `docs/agents/visual-qa.md`; ticket closes on witnessed look + conservator note in the pair log (same-round agent reply), never numbers alone
- [ ] Verdict against the gate: density-as-clay + break untouched + flag honoured → keep, scope capture two; no gain / break moves / wall roughens / smooth fake → retire NO, LaMa stays visualisation-only on MILo
- [ ] Write back into `intent/M10-does-lama-fill-keep-density-through-crop.md` (`## Where it stands` + `Weight:` / `Next:` / `Picture:` / `Viewer:`): tick Done-when boxes with date, or amend/retire the question (number kept); rebuild board (`python scripts/build_board.py`)
- [ ] `python ../scripts/check_intent_links.py` = 0; one finished ticket per commit with why-message; commit straight to `master` on `zeejaytan/MILo`, never upstream
