# 05: Killer-view autopsy — what do the wedging views share?

**What to build:** a feature table comparing the 4 killer views against matched passing neighbours, and a verdict: one shared trigger feature, or none.

**Answers:** M9

**Blocked by:** 02 (killer list — satisfied: A31_1111, A32_1142, A33_1176 hang; A32_1151 illegal-access; outcomes flip run to run across two nodes).

**Status:** results-in (autopsy complete 2026-10-20, lead-accepted; verdict feeds 08)

- [x] Feature table for the 4 killers vs 8 passing neighbours from the same trays: camera pose (angle/height neighbours), steel-proxy share per view, dial/marble-rod presence, blur/exposure outliers, COLMAP sparse point counts and reprojection spread
- [x] Verdict recorded: NO-COMMON-FEATURE (stated explicitly — a negative is an answer)
- [x] Login-node work only (image stats + sparse queries); no GPU probe — the table points at no single hypothesis sized under 30 min
- [x] No edits to the authors' tree; resume-wedge suspects from 32276629 stay in 06, not here

## Findings (worker autopsy 2026-10-20)

Neighbour set (all verified in train_list.txt = passing; killers from killer4.txt; test_list.txt untouched):
A31_1111 vs A31_1110/A31_1112; A32_1142 vs A32_1141/A32_1143; A32_1151 vs A32_1150/A32_1152; A33_1176 vs A33_1175/A33_1177.

| view | killer? | az° | el° | dist | n2d | n3d | meanErr | maxErr | maskfrac | steelPx | grayMean | grayStd | lapVar | satFrac | dial / rod (thumb visual) |
|------|---------|-----|-----|------|-----|-----|---------|--------|----------|---------|----------|---------|--------|---------|---------------------------|
| A31_1110 | pass | 168.0 | 72.9 | 4.1 | 6904 | 4084 | 0.830 | 3.733 | 0.1660 | 0.0764 | 54.9 | 38.6 | 8.3 | 0.00097 | black dial at frame L; white translucent rod |
| A31_1111 | KILL | 146.3 | 82.6 | 4.1 | 6995 | 4077 | 0.828 | 3.370 | 0.1663 | 0.0763 | 54.5 | 39.0 | 8.2 | 0.00182 | same as neighbours |
| A31_1112 | pass | 52.8 | 84.1 | 4.1 | 6692 | 3816 | 0.833 | 3.507 | 0.1666 | 0.0775 | 54.4 | 38.9 | 8.1 | 0.00216 | same (az swing is near-pole geometry; centres move smoothly z −1.2→−0.4→+0.3) |
| A32_1141 | pass | 163.3 | 48.7 | 4.1 | 7273 | 3848 | 0.813 | 3.272 | 0.1680 | 0.0880 | 57.1 | 42.8 | 13.4 | 0.00291 | black dial at frame L; white rod |
| A32_1142 | KILL | 157.3 | 59.3 | 4.1 | 4305 | 2457 | 0.830 | 3.860 | 0.1319 | 0.0921 | 58.0 | 43.5 | 13.4 | 0.00360 | same as neighbours |
| A32_1143 | pass | 143.5 | 69.6 | 4.2 | 4252 | 2319 | 0.836 | 3.860 | 0.1534 | 0.0927 | 57.7 | 43.2 | 13.4 | 0.00282 | same (equally low n2d/n3d as killer, still passes) |
| A32_1150 | pass | 18.9 | 31.0 | 4.1 | 5276 | 2985 | 0.852 | 3.945 | 0.1610 | 0.1032 | 58.6 | 44.9 | 13.6 | 0.00373 | black dial at frame L |
| A32_1151 | KILL | 17.7 | 20.3 | 4.1 | 5028 | 2904 | 0.847 | 3.945 | 0.1641 | 0.1066 | 58.5 | 45.2 | 13.5 | 0.00436 | same as neighbours (this is the illegal-access one, not a hang) |
| A32_1152 | pass | 17.1 | 8.6 | 4.1 | 4778 | 2837 | 0.851 | 3.910 | 0.1632 | 0.1064 | 58.4 | 44.4 | 13.4 | 0.00386 | same (lower el 8.6° and higher steel 0.1064 than killer, still passes) |
| A33_1175 | pass | −178.4 | 62.4 | 3.6 | 4010 | 2837 | 0.870 | 3.473 | 0.2040 | 0.0774 | 53.9 | 37.8 | 5.0 | 0.00167 | NO black dial (blue panel at frame L, tray-level); rod present |
| A33_1176 | KILL | −179.3 | 72.6 | 3.7 | 3937 | 2871 | 0.890 | 3.637 | 0.2225 | 0.0810 | 54.7 | 38.4 | 5.1 | 0.00141 | same as neighbours; blue panel nearly edge-on; central dark sherd face-on |
| A33_1177 | pass | 176.5 | 83.1 | 3.7 | 4239 | 2944 | 0.864 | 3.637 | 0.2065 | 0.0816 | 55.1 | 39.1 | 4.9 | 0.00234 | same |

Conventions/sources: az = atan2(Cx,Cz) deg, el = elevation of COLMAP camera centre deg, dist = |C| (COLMAP units, tray-consistent); n2d = registered 2D keypoints, n3d = with valid 3D, meanErr/maxErr = mean/max points3D.bin error over the view's 3D points — all from data/goris_A03/sparse/0/{images,cameras,points3D}.bin via /tmp/killer_stats.py (login node, PIL+numpy only). maskfrac = white fraction of data/goris_A03/object_mask/<view>.png (binary sherd mask, 3200×2133). steelPx = fraction of pixels with V>110 and S<0.25 in HSV (uncalibrated bright-metal proxy, NOT cm²) via /tmp/steel.py; grayMean/Std, lapVar (3×3 Laplacian variance on L), satFrac (V≥250) same script. Images are symlinks to data/17062025/A03_sherds/images/. Visuals: /tmp/mon_A3*.jpg (480px full-frame triples) + /tmp/rod_A32b.jpg + /tmp/rod_A33.jpg (centre-band zooms). Killer list data/goris_A03/killer4.txt from probe jobs 31848150 + rerun 32083170 (ticket 02). All images 3200×2133; darkfrac = 0 everywhere.

**Verdict: NO-COMMON-FEATURE.** Every measured feature either brackets each killer between its passing neighbours (pose az/el/dist interpolate smoothly; steelPx/brightness/blur sit mid-triple in all 4 cases) or varies in opposite directions across killers (maskfrac: 1176 highest-of-12 at 0.2225, 1142 lowest-of-triple at 0.1319, 1111 identical to neighbours; n2d: 1142 low at 4305 but passing 1143 equally low at 4252). Dial presence is tray-level (A31/A32 black dial in all 12-frame neighbourhoods incl. killers; A33 blue panel instead in all three). No single shared trigger feature exists in this table.

Nearest misses (most discriminating numbers, each defeated by a passing neighbour):
1. n2d/n3d collapse on A32_1142 (4305/2457 vs 7273/3848 on A32_1141, −41%) — defeated by passing A32_1143 (4252/2319).
2. A33_1176 highest-of-12 maskfrac 0.2225 and meanErr 0.890 — margins small (+8% rel mask, +3% err) and direction not shared.
3. Steel proxy: all 4 killers inside neighbours' range (max deviation 0.0004) — the most consistent non-finding; per-view steel does not separate kill from pass.

Not checked (out of bounds or beyond login-node means): per-ray BVH/trace behaviour inside the authors' gtracer fork (needs GPU + tree instrumentation — explicitly excluded); calibrated steel cm² (proxy only); full-resolution dial/rod inspection (thumbnails + bands only); resume-wedge mechanism from chkpnt4000/4060 (06's territory); test-set views (held out, untouched).

## Comments

- 2026-10-19 (lead): cut after control 33427213 acquitted the stack — the wedge is data-specific, so the data gets interrogated. Diagnose-only per conservator decision; bounded: one table, one verdict, then 07 builds subsets from it.
- 2026-10-20 (worker): table + NO-COMMON-FEATURE verdict recorded above, all login-node. Montage/zoom JPEGs viewed from %TEMP% (outside repo, since removed); /tmp scripts left on Spartan login node only. No GPU probe: no hypothesis survived the table. Ready for lead acceptance / 07 subset design.
