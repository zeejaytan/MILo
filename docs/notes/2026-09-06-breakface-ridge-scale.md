# Break-face ridge scale from A03 photographs (ticket 01, first measurement, 2026-09-06)

For M1's third box (stated requirement in mm). Six native-scale 900×900 crops cut on
the node from full-res A03 frames around the largest mask-blob boundary pixel
(`~/crop_breakface.py` on Spartan; crops in `artifacts/breakface_crops/`, gitignored).
Views spread across the ring (indices 0/27/54/81/108/135).

## Method (laptop, PIL+numpy, seconds)

Per crop: horizontal scanlines across the sherd face, large-scale shading removed
(51-px moving average), autocorrelation, lag where it first drops below 0.5 =
correlation length of the brightness relief. Pixel scale ≈ 0.12 mm/px for original
frames (0.21 mm/px at 3200 px undistorted × 3200/5568) — **approximate ±20%**: tree
depth varies per sherd and the undistort rescale is assumed, not solved.

## Result

| crop | corr. length | ×0.12 | grain ≈ 2× |
|---|---|---|---|
| A34_1208 (dark coarse face) | 3 px | 0.36 mm | ~0.7 mm |
| A31_1127 | 4 px | 0.48 mm | ~1.0 mm |
| A35_1235 | 4 px | 0.48 mm | ~1.0 mm |
| A31_1100, A33_1181, A32_1154 | 5 px | 0.60 mm | ~1.2 mm |

Relief features run **~0.5–1 mm**, not 0.21 mm. Photo support (0.21 mm/px undistorted)
oversamples them ~2–5×; the 0.822 mm voxel is marginal (~1 grain); a 0.45 mm tiled
voxel would roughly match the grain.

## Weight (read before citing)

- Brightness correlation is **not** geometric relief: albedo mottling and shading both
  feed it. Direction of bias unknown — this is a lead, not a requirement.
- mm/px is approximate (±20%) as stated above.
- n = 6 crops, 1 capture, 1 session. Ticket 01's box needs the conservator's confirm
  before M1 can cite a requirement.
