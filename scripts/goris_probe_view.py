"""Render ONE view through the full PBR+trace path with NaN diagnostics.

Used by slurm/goris_report_probe.slurm: each view runs in its own process
under `timeout`, so a device hang kills only that view's probe and the
driver learns exactly which views hang.

Prints one line: OK <view> | HANG (via timeout, no line) plus NaN stats
printed BEFORE the trace call:
  nan_bounds=<k> = Gaussians whose bound size is not finite
  nan_rays=<k>   = trace rays that are not finite
A nonzero nan_bounds with a subsequent hang convicts degenerate bounds;
a hang with all-finite inputs convicts the tracer state itself.

Usage:
  python scripts/goris_probe_view.py -s <data> -m <model> --iteration 2000
      --view A31_1100 --split test --resolution 2
"""
import argparse
import sys

import torch


def parse_args(argv=None):
    from arguments import ModelParams, PipelineParams
    from argparse import ArgumentParser
    parser = ArgumentParser()
    model = ModelParams(parser)
    pipe = PipelineParams(parser)
    parser.add_argument("--iteration", type=int, required=True)
    parser.add_argument("--view", type=str, default=None,
                        help="required for split=test|train, ignored for report")
    parser.add_argument("--split", type=str, default="test",
                        choices=["test", "train", "report"])
    return model, pipe, parser.parse_args(argv)


def main():
    model, pipe, args = parse_args()
    dataset = model.extract(args)
    from scene import GaussianModel, Scene
    from gaussian_renderer import render

    gaussians = GaussianModel(dataset.sh_degree)
    scene = Scene(dataset, gaussians, load_iteration=args.iteration,
                  shuffle=False)
    pipe_obj = pipe.extract(args)
    bg = torch.tensor([0., 0., 0.], device="cuda")

    def render_one(cam):
        pkg = render(cam, gaussians, pipe_obj, bg, 0.0)
        return gaussians.pbr(cam, pkg["rend_alpha"], pkg["rend_normal"],
                             pkg["surf_depth"], pkg["rend_diffuse"],
                             pkg["rend_fresnel"], pkg["rend_roughness"], bg)

    def nan_bounds():
        with torch.no_grad():
            v = gaussians.get_boundings(gaussians.alpha_min)[0].detach()
            return int((~torch.isfinite(v)).any(dim=1).sum())

    if args.split == "report":
        # The scheduled loop itself: all test views then 5 train samples,
        # sequentially in ONE process — exactly what training_report does.
        # A hang here with clean per-view isolation convicts accumulation
        # across the loop, not any view.
        train = scene.getTrainCameras()
        cams = list(scene.getTestCameras()) + [train[i % len(train)]
                                               for i in range(5, 30, 5)]
        for i, cam in enumerate(cams):
            n_b = nan_bounds()
            out = render_one(cam)
            n_c = int((~torch.isfinite(out["render_color"])).sum())
            print(f"REPORTLOOP {i + 1}/{len(cams)} view={cam.image_name} "
                  f"nan_bounds={n_b} nan_color={n_c}", flush=True)
        print("REPORTLOOP-OK", flush=True)
        return
    cams = (scene.getTestCameras() if args.split == "test"
            else scene.getTrainCameras())
    cam = next(c for c in cams if c.image_name == args.view)
    n_nan_b = nan_bounds()
    out = render_one(cam)
    n_nan_c = int((~torch.isfinite(out["render_color"])).sum())
    print(f"OK view={args.view} split={args.split} "
          f"nan_bounds={n_nan_b} nan_color={n_nan_c}", flush=True)


if __name__ == "__main__":
    sys.exit(main())
