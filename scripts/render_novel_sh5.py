"""Render 15 novel SH5 close-ups from the trained A02 checkpoint (step 2a).

Five base views (Step 0 ranking) x 3 variants:
  exact   same pose — pure synthetic duplicate, controls "more views" vs "new views"
  dolly   same orientation, centre moved 7% toward the SH5 box centre
  mid     orientation halfway to the next base view + 7% dolly — new baseline

All poses stay within a few degrees of real poses: far novel poses render
blur/noise that then poisons the very reconstruction they should help
(0.561 -> 0.445 lp/mm elsewhere). Same intrinsics, full resolution.

Writes RENDER_SH5_01..15.JPG plus poses.json (K, R, T per render for the
registration step). base_views.json records the design.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import torch
import torchvision
from arguments import ModelParams, PipelineParams, get_combined_args
from gaussian_renderer import GaussianModel
from gaussian_renderer.radegs import render_radegs as render
from scene import Scene
from scene.cameras import Camera
from utils.general_utils import safe_state

BASE = ["A23_1029.JPG", "A23_1030.JPG", "A25_1095.JPG", "A23_1028.JPG", "A22_0997.JPG"]
DOLLY = 0.07


def orthonormalize(M: np.ndarray) -> np.ndarray:
    U, _, Vt = np.linalg.svd(M)
    R = U @ Vt
    if np.linalg.det(R) < 0:
        U[:, -1] *= -1
        R = U @ Vt
    return R


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--boxes", required=True)
    ap.add_argument("--sherd", default="SH5")
    ap.add_argument("--out", required=True)
    mp = ModelParams(ap, sentinel=True)
    pp = PipelineParams(ap)
    args = get_combined_args(ap)
    safe_state(True)

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    d = json.loads(Path(args.boxes).read_text())
    scale = float(d["mm_per_unit"])
    box = next(b for b in d["boxes"] if b["id"] == args.sherd)
    target = (np.array(box["min_mm"]) + np.array(box["max_mm"])) / 2 / scale

    dataset = mp.extract(args)
    gaussians = GaussianModel(dataset.sh_degree)
    scene = Scene(dataset, gaussians, load_iteration=-1, shuffle=False)
    bg = torch.tensor([0, 0, 0], dtype=torch.float32, device="cuda")
    by_name = {Path(c.image_name).stem: c for c in scene.getTrainCameras()}
    BASE_STEMS = [Path(b).stem for b in BASE]
    missing = [b for b in BASE_STEMS if b not in by_name]
    assert not missing, f"base views not in train set: {missing}"

    spec = []
    with torch.no_grad():
        for i, name in enumerate(BASE):
            t = by_name[Path(name).stem]
            nxt = by_name[Path(BASE[(i + 1) % len(BASE)]).stem]
            R0 = t.R if isinstance(t.R, np.ndarray) else t.R.detach().cpu().numpy()
            T0 = t.T if isinstance(t.T, np.ndarray) else t.T.detach().cpu().numpy()
            R1 = nxt.R if isinstance(nxt.R, np.ndarray) else nxt.R.detach().cpu().numpy()
            T1 = nxt.T if isinstance(nxt.T, np.ndarray) else nxt.T.detach().cpu().numpy()
            C0 = -R0.T @ T0
            C1 = -R1.T @ T1
            Cd = C0 + DOLLY * (target - C0)
            Rm = orthonormalize((R0 + R1) / 2)
            Cm = (C0 + C1) / 2 + DOLLY * (target - (C0 + C1) / 2)
            variants = {
                "exact": (R0, T0),
                "dolly": (R0, -R0 @ Cd),
                "mid": (Rm, -Rm @ Cm),
            }
            for kind, (Rn, Tn) in variants.items():
                Rn = orthonormalize(np.asarray(Rn, float))
                Tn = np.asarray(Tn, float)
                n = len(spec) + 1
                fname = f"RENDER_SH5_{n:02d}.JPG"
                h, w = t.image_height, t.image_width
                dummy = torch.zeros((3, h, w), dtype=torch.float32)
                view = Camera(colmap_id=0, R=Rn, T=Tn, FoVx=t.FoVx, FoVy=t.FoVy,
                              image=dummy, gt_alpha_mask=None, image_name=fname,
                              uid=n, trans=t.trans, scale=t.scale)
                img = render(view, gaussians, pp.extract(args), bg)["render"]
                torchvision.utils.save_image(img, str(out / fname))
                spec.append({"file": fname, "from": name, "kind": kind,
                             "R": Rn.tolist(), "T": Tn.tolist(),
                             "width": w, "height": h})
                print(f"{fname} from {name:14s} {kind:5s}", flush=True)
    (out / "poses.json").write_text(json.dumps(spec, indent=1))
    (out / "base_views.json").write_text(json.dumps(
        {"base": BASE, "dolly": DOLLY, "box_centre_units": target.tolist()}, indent=1))
    print(f"wrote {len(spec)} renders to {out}")


if __name__ == "__main__":
    main()
