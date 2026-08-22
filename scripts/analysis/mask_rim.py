"""What did MILo actually get told was "object", and how much of it was not sherd?

Reads the alpha channel of the images MILo trained on -- not a mask folder that might have
been regenerated since, the actual training input. Compares the wide mask (the retrain)
against the tight sherd outline, and reports WHERE the extra area sits: hugging the sherd
edge, or out on the rig.

That distinction is the whole question. On a turntable the backdrop is the one thing that
does not turn with the sherd, so any backdrop inside the mask is view-inconsistent: the
same pixel is a different colour every frame while claiming to be one surface. Where that
sits is where the floaters go.
"""
import sys
from pathlib import Path

import numpy as np
import cv2

PX_PER_MM = 5.0          # measured: focal 6830 px at 1368 mm standoff

wide = Path(sys.argv[1])
tight = Path(sys.argv[2])

names = sorted(p.name for p in tight.iterdir() if p.suffix.lower() in (".png", ".jpg"))[::16]
bands = np.array([2, 5, 10, 20, 50, 200, 1e9])       # px from the true sherd outline
acc = np.zeros(len(bands))
cov_w = cov_t = 0.0
n = 0

for nm in names:
    a = cv2.imread(str(wide / nm), cv2.IMREAD_UNCHANGED)
    b = cv2.imread(str(tight / nm), cv2.IMREAD_UNCHANGED)
    if a is None or b is None or a.ndim < 3 or a.shape[2] < 4 or b.shape[2] < 4:
        continue
    A, B = a[..., 3] > 127, b[..., 3] > 127
    if B.sum() == 0:
        continue
    d = cv2.distanceTransform((~B).astype(np.uint8), cv2.DIST_L2, 5)
    extra = d[A & ~B]
    acc += np.histogram(extra, bins=np.r_[0, bands])[0]
    cov_w += A.mean()
    cov_t += B.mean()
    n += 1

if not n:
    sys.exit("no comparable RGBA pairs")

acc /= n
print(f"sampled {n} views of what MILo was actually trained on")
print(f"  wide mask (the retrain) covers {100*cov_w/n:.1f}% of the frame")
print(f"  tight sherd outline            {100*cov_t/n:.1f}% of the frame")
print("\n  the extra area, by how far it sits from the nearest real sherd pixel:")
lo = 0.0
tot = acc.sum()
for hi, k in zip(bands, acc):
    label = f"{lo:.0f}-{hi:.0f} px" if hi < 1e8 else f"over {lo:.0f} px"
    mm = f"({lo/PX_PER_MM:.0f}-{hi/PX_PER_MM:.0f} mm)" if hi < 1e8 else ""
    print(f"    {label:>12} {mm:>12}  {k/1e3:8.0f}k px/view  {100*k/tot:5.1f}%")
    lo = hi
hug = acc[:3].sum()
print(f"\n  {100*hug/tot:.1f}% of the extra area is within 10 px (2 mm) of a real sherd edge")
print(f"  = {hug/1e3:.0f}k px per view of backdrop pressed against the sherd outline,")
print("    trained as if it were part of the object.")
