"""Run MILo's own DTU silhouette cull on a mesh, and report what it removed.

This is a driver, not a reimplementation. The cull itself is
`milo/eval/dtu/evaluate_dtu_mesh.py:cull_mesh`, imported and called unmodified, so
what happens here is exactly what the authors do to isolate an object on the DTU
benchmark. Their own evaluation script calls it on `recon_tsdf.ply`, which is what
`mesh_extract_dtu.py` writes -- the two are a pair.

What their cull does, in plain terms: project every mesh vertex into every training
camera, and keep a vertex only if it lands inside the sherd outline in EVERY view.
A vertex that falls outside the picture frame in some view is excused for that view
(`sampled_mask + (1. - valid)`), so views that simply do not see a region do not
delete it. The outline is dilated by a 6-pixel disc first, which is the same
"grow the mask, never shrink it" instinct a fracture edge needs -- a tight mask
eats break edges before it eats background.

That all-views rule is the difference that matters here. The mask test inside
`--init integration` keeps anything seen inside an outline in AT LEAST ONE view,
which the mounting rig passes easily because it sits behind the sherds from many
angles on a turntable.

The counts printed below are a check that the cull ran, not evidence about the
break surfaces. Render the mesh before believing anything about its geometry.
"""
import argparse
import os
import sys

import numpy as np
import torch
import trimesh

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "milo"))

from arguments import ModelParams, PipelineParams  # noqa: E402
from eval.dtu.evaluate_dtu_mesh import cull_mesh  # noqa: E402
from gaussian_renderer import GaussianModel  # noqa: E402
from scene import Scene  # noqa: E402


def main():
    parser = argparse.ArgumentParser(
        description="Cull a mesh to the sherd silhouettes using MILo's DTU cull_mesh()."
    )
    model = ModelParams(parser, sentinel=False)
    PipelineParams(parser)
    parser.add_argument("--mesh", required=True, help="mesh to cull")
    parser.add_argument("--out", required=True, help="where to write the culled mesh")
    parser.add_argument("--iteration", default=-1, type=int)
    args = parser.parse_args()

    torch.cuda.set_device(torch.device("cuda:0"))

    dataset = model.extract(args)
    gaussians = GaussianModel(dataset.sh_degree)
    # The Gaussians are loaded only because Scene() insists on them; the cull reads
    # camera poses and gt_mask, nothing else.
    scene = Scene(dataset, gaussians, load_iteration=args.iteration, shuffle=False)
    cameras = scene.getTrainCameras()

    n_masked = sum(1 for c in cameras if c.gt_mask is not None)
    print(f"[INFO] {len(cameras)} training cameras, {n_masked} with a mask.")
    if n_masked == 0:
        # Without masks cull_mesh keeps everything, and would report a clean pass
        # while having done nothing at all. That is the silent-success failure the
        # workspace rules exist to stop.
        print("[ERROR] No camera carried a mask. Did you pass -i images_masked?", file=sys.stderr)
        sys.exit(1)
    if n_masked != len(cameras):
        print(f"[WARNING] {len(cameras) - n_masked} cameras have no mask. The cull is an "
              f"all-views test, so those views cannot remove anything.", file=sys.stderr)

    mesh = trimesh.load(args.mesh, process=False)
    if isinstance(mesh, trimesh.Scene):
        mesh = trimesh.util.concatenate(list(mesh.geometry.values()))
    before_v, before_f = len(mesh.vertices), len(mesh.faces)
    ext = mesh.vertices.max(0) - mesh.vertices.min(0)
    print(f"[INFO] before: {before_v:,} vertices, {before_f:,} faces, "
          f"extent {ext[0]:.3f} x {ext[1]:.3f} x {ext[2]:.3f} scene units")

    mesh = cull_mesh(cameras, mesh)

    after_v, after_f = len(mesh.vertices), len(mesh.faces)
    if after_v == 0:
        print("[ERROR] The cull removed every vertex. Check that the masks line up with "
              "the photographs before reading anything into this.", file=sys.stderr)
        sys.exit(1)
    ext = mesh.vertices.max(0) - mesh.vertices.min(0)
    print(f"[INFO] after : {after_v:,} vertices ({100*after_v/max(before_v,1):.1f}% kept), "
          f"{after_f:,} faces, extent {ext[0]:.3f} x {ext[1]:.3f} x {ext[2]:.3f} scene units")

    mesh.export(args.out)
    print(f"[INFO] wrote {args.out}")


if __name__ == "__main__":
    main()
