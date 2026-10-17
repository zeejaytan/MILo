# 05: Eye QA + verdict + write-back to M10

**What to build:** the conservator's witnessed verdict on both arms, then the question closed whatever the outcome.

**Answers:** M10

**Blocked by:** 04-same-voxel-extract-measure.

**Status:** resolved

**Needs-eye:** pairs m10_rigfill (control vs rigfill) + m10_fullscene (cropped full scene vs rigfill) staged in the viewer and served on localhost:8081 — SUPERSEDES the original m10_ab plan (moot: complement B had no mesh).

## Witnessed verdict (conservator, 2026-10-17, same-round reply given)

Full scene much coarser; control and LaMa not much different. Background restated by conservator: masking the rig in photos drains the blob available at surfacing, which coarsens the crop; LaMa pays back the drain by providing scene where no original view exists. Standing rule recorded: full-scene meshes always staged cropped to rig+sherds (written into m10_fullscene.json frame_note).

- [x] Stage left/right pair in shared COLMAP frame, millimetres, with src + manifest previews per `docs/agents/visual-qa.md`; ticket closes on witnessed look + conservator note in the pair log (same-round agent reply), never numbers alone
- [x] Verdict against the gate: density-as-clay + break untouched + flag honoured → keep, scope capture two; no gain / break moves / wall roughens / smooth fake → retire NO, LaMa stays visualisation-only on MILo — VERDICT: KEEP (rigfill +11% verts, Rq parity, no break move, flag honoured; eye confirms)
- [x] Write back into `intent/M10-does-lama-fill-keep-density-through-crop.md` (`## Where it stands` + `Weight:` / `Next:` / `Picture:` / `Viewer:`): tick Done-when boxes with date, or amend/retire the question (number kept); rebuild board (`python scripts/build_board.py`)
- [x] `python ../scripts/check_intent_links.py` = 0; one finished ticket per commit with why-message; commit straight to `master` on `zeejaytan/MILo`, never upstream

- [ ] Stage left/right pair in shared COLMAP frame, millimetres, with src + manifest previews per `docs/agents/visual-qa.md`; ticket closes on witnessed look + conservator note in the pair log (same-round agent reply), never numbers alone
- [ ] Verdict against the gate: density-as-clay + break untouched + flag honoured → keep, scope capture two; no gain / break moves / wall roughens / smooth fake → retire NO, LaMa stays visualisation-only on MILo
- [ ] Write back into `intent/M10-does-lama-fill-keep-density-through-crop.md` (`## Where it stands` + `Weight:` / `Next:` / `Picture:` / `Viewer:`): tick Done-when boxes with date, or amend/retire the question (number kept); rebuild board (`python scripts/build_board.py`)
- [ ] `python ../scripts/check_intent_links.py` = 0; one finished ticket per commit with why-message; commit straight to `master` on `zeejaytan/MILo`, never upstream
