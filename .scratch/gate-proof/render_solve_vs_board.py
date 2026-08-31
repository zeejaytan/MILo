"""Draw the N01 solve against the board reference, at two scales.

The gate reported agreement to 0.00 deg. A number that good is a bug until it has been
looked at, so this draws the thing the number is about: where COLMAP put each photograph,
where the board says it was, and the sparse cloud they were solved from.

Two scales on purpose. The overview panel would look identical for a solve 20 mm out --
the rig is 800 mm across and 20 mm is a line width -- so the second panel is the residual
itself, per frame, unbinned and unprojected, at the scale the claim is made at.
"""
import json, sys
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parents[0]))
import importlib.util
spec = importlib.util.spec_from_file_location("ct", sys.argv[3])
ct = importlib.util.module_from_spec(spec); spec.loader.exec_module(ct)

model, refp, out = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[4])
ref = json.loads(refp.read_text())
C, names = ct.read_camera_centres(model)
pts = ct.read_points(model)

fr = ref["frames"]
stem = {Path(n).stem: i for i, n in enumerate(names)}
common = [k for k in fr if Path(k).stem in stem]
th = np.radians([fr[k]["deg"] for k in common])
rr = np.array([fr[k]["radius_m"] for k in common])
hh = np.array([fr[k]["height_m"] for k in common])
R = np.stack([rr * np.cos(th), rr * np.sin(th), hh], 1)      # board frame, metres
A = C[[stem[Path(k).stem] for k in common]]

s, Rot, t = ct.umeyama(A, R)
Aa = (s * (Rot @ A.T).T + t)                                  # model -> board frame
P = (s * (Rot @ pts.T).T + t)

resid_mm = np.linalg.norm(Aa - R, axis=1) * 1000
ang = np.degrees(np.arctan2(Aa[:, 1], Aa[:, 0])) - np.degrees(th)
ang = (ang + 180) % 360 - 180

fig = plt.figure(figsize=(16, 5.6))
ax = fig.add_subplot(131)
sub = P[np.random.default_rng(0).choice(len(P), min(40000, len(P)), replace=False)]
ax.scatter(sub[:, 0], sub[:, 1], s=.5, c="#bbb", lw=0)
ax.plot(R[:, 0], R[:, 1], "o", ms=7, mfc="none", mec="#1a7", mew=1.4, label="board says")
ax.plot(Aa[:, 0], Aa[:, 1], ".", ms=3.5, c="#c33", label="COLMAP put it")
ax.set_aspect("equal"); ax.legend(loc="upper right", fontsize=8)
ax.set_title("looking down the turntable axis\n(119 photographs, 88,107 points)", fontsize=9)
ax.set_xlabel("metres")

ax = fig.add_subplot(132)
ax.scatter(sub[:, 0], sub[:, 2], s=.5, c="#bbb", lw=0)
ax.plot(R[:, 0], R[:, 2], "o", ms=7, mfc="none", mec="#1a7", mew=1.4)
ax.plot(Aa[:, 0], Aa[:, 2], ".", ms=3.5, c="#c33")
ax.set_aspect("equal")
ax.set_title("from the side\nheight measured from the board plane", fontsize=9)
ax.set_xlabel("metres")

ax = fig.add_subplot(133)
order = np.argsort([fr[k]["deg"] for k in common])
ax.bar(np.arange(len(common)), resid_mm[order], width=1.0, color="#c33")
ax.axhline(1.24, color="#1a7", ls="--", lw=1.2,
           label="reference's own circle residual, 1.24 mm")
ax.set_ylim(0, max(2.0, resid_mm.max() * 1.15))
ax.set_xlabel("photograph, in order round the turn")
ax.set_ylabel("distance from where the board says, mm")
ax.legend(fontsize=8)
ax.set_title(f"the residual itself, per photograph\nmedian {np.median(resid_mm):.2f} mm, "
             f"worst {resid_mm.max():.2f} mm", fontsize=9)

fig.suptitle(f"03072025/N01 COLMAP solve vs the turntable board  --  scale "
             f"1 model unit = {1/s*1000:.1f} mm ... aligned on {len(common)} frames",
             fontsize=10)
fig.tight_layout()
fig.savefig(out, dpi=130)
print(f"wrote {out}")
print(f"residual mm: median {np.median(resid_mm):.3f}  90th {np.percentile(resid_mm,90):.3f}  "
      f"worst {resid_mm.max():.3f}")
print(f"angle deg:   median {np.median(abs(ang)):.4f}  worst {abs(ang).max():.4f}")
