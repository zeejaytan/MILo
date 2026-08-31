import os
import sys
BASE_DIR = os.path.dirname(  # milo/
    os.path.dirname(  # milo/eval/
        os.path.dirname(os.path.abspath(__file__))  # milo/eval/dtu/
    )
)
sys.path.append(BASE_DIR)
import gc
import torch
from scene import GaussianModel
from argparse import ArgumentParser
from arguments import ModelParams, PipelineParams
import math
import numpy as np
import open3d as o3d
import open3d.core as o3c
from scene.dataset_readers import sceneLoadTypeCallbacks
from utils.camera_utils import cameraList_from_camInfos


def load_camera(args):
    if os.path.exists(os.path.join(args.source_path, "sparse")):
        scene_info = sceneLoadTypeCallbacks["Colmap"](args.source_path, args.images, args.eval)
    elif os.path.exists(os.path.join(args.source_path, "transforms_train.json")):
        print("Found transforms_train.json file, assuming Blender data set!")
        scene_info = sceneLoadTypeCallbacks["Blender"](args.source_path, args.white_background, args.eval)
    return cameraList_from_camInfos(scene_info.train_cameras, 1.0, args)




def extract_mesh(dataset, pipe, checkpoint_iterations=None, occupancy_mode="occupancy_shift",
                 voxel_size=0.002, block_count=50000, trunc_voxel_multiplier=8.0,
                 ply_name="recon_tsdf.ply", mm_per_unit=None, o3d_device_str="CPU:0"):
    # [SHERD FORK] voxel_size, block_count and trunc_voxel_multiplier were hard-coded or
    # left at Open3D's default. DTU normalises every scan to a fixed size, so one voxel
    # size fits the benchmark; our captures are in COLMAP units that differ per capture,
    # and 0.002 units is 0.75 mm on A03 -- 3.6x coarser than the 0.21 mm/px the depth maps
    # are actually rendered at. The defaults below are the author's effective values, so a
    # faithful run still needs no flags.
    #
    # THE TRAP, if you refine voxel_size: Open3D's truncation band is
    # trunc_voxel_multiplier * voxel_size, and upstream passes neither argument, so it sits
    # at 8 -- one block wide, which is why 8 pairs with block_resolution 16. Shrink the
    # voxel 4x and the band shrinks 4x too, from ~6 mm to ~1.5 mm on A03. Gaussian-rendered
    # depth disagrees between views by more than that in places, and when it does the
    # surfaces stop reinforcing and the mesh fragments into holes. Raise the multiplier in
    # step with the refinement to hold the band at a fixed PHYSICAL width, and the two
    # questions -- how finely am I sampling, how much depth noise am I tolerating -- stay
    # separate instead of being silently welded together.
    gaussians = GaussianModel(dataset.sh_degree)
    output_path = os.path.join(dataset.model_path,"point_cloud")
    iteration = 0
    if checkpoint_iterations is None:
        for folder_name in os.listdir(output_path):
            iteration= max(iteration,int(folder_name.split('_')[1]))
    else:
        iteration = checkpoint_iterations
    output_path = os.path.join(output_path,"iteration_"+str(iteration),"point_cloud.ply")
    print(f"[INFO] Extracting mesh from model {output_path}")

    gaussians.load_ply(output_path)
    try:
        gaussians.set_occupancy_mode(occupancy_mode)
    except:
        print(f'[ WARNING ] Failed to set occupancy mode to {occupancy_mode}')
    print(f'Loaded gaussians from {output_path}')
    
    kernel_size = dataset.kernel_size
    
    bg_color = [1, 1, 1]
    background = torch.tensor(bg_color, dtype=torch.float32, device="cuda")
    viewpoint_cam_list = load_camera(dataset)

    depth_list = []
    color_list = []
    alpha_thres = 0.5
    for viewpoint_cam in viewpoint_cam_list:
        # Rendering offscreen from that camera 
        render_pkg = render(viewpoint_cam, gaussians, pipe, background, kernel_size)
        rendered_img = torch.clamp(render_pkg["render"], min=0, max=1.0).cpu().numpy().transpose(1,2,0)
        color_list.append(np.ascontiguousarray(rendered_img))
        depth = render_pkg["median_depth"].clone()
        if viewpoint_cam.gt_mask is not None:
            depth[(viewpoint_cam.gt_mask < 0.5)] = 0
        depth[render_pkg["mask"]<alpha_thres] = 0
        depth_list.append(depth[0].cpu().numpy())

    n_masked = sum(1 for c in viewpoint_cam_list if c.gt_mask is not None)
    print(f"[INFO] {n_masked} of {len(viewpoint_cam_list)} views carried a mask. "
          f"Views without one contribute their whole depth map, background included.")

    # [SHERD FORK] Upstream's bare empty_cache() here frees only PyTorch's *cache*, not its
    # live tensors -- and the live tensors are the problem. cameraList_from_camInfos puts
    # every training image AND its alpha on the GPU: 143 views x 3200x2133 x (3+1) channels
    # x 4 bytes is about 15.6 GiB, and the Gaussians sit alongside it. Open3D's CUDA
    # allocator then asks the driver for its own memory and gets nothing, which is how this
    # OOM'd on an 80 GB A100 while reserving 3.8 GiB for the voxel grid (job 29626640).
    # The depth and colour maps are already numpy on the host by this point, and the fusion
    # below needs only intrinsics, extrinsics and image size from each camera, so the
    # pixels can go. Counting the masks first, above, is what makes that safe.
    if torch.cuda.is_available():
        reserved_before = torch.cuda.memory_reserved() / 1024 ** 3
    del gaussians
    for cam in viewpoint_cam_list:
        for attr in ("original_image", "gt_mask", "gt_alpha_mask", "depth_image", "mask"):
            if torch.is_tensor(getattr(cam, attr, None)):
                setattr(cam, attr, None)
    gc.collect()
    torch.cuda.empty_cache()
    if torch.cuda.is_available():
        free_b, total_b = torch.cuda.mem_get_info()
        print(f"[INFO] GPU after releasing the render state: torch reserved "
              f"{reserved_before:.1f} -> {torch.cuda.memory_reserved() / 1024 ** 3:.1f} GiB; "
              f"{free_b / 1024 ** 3:.1f} of {total_b / 1024 ** 3:.1f} GiB free on the card. "
              f"Open3D allocates outside this and needs room here, not in torch's cache.")
    band = trunc_voxel_multiplier * voxel_size
    if mm_per_unit:
        print(f"[INFO] TSDF voxel {voxel_size} units = {voxel_size * mm_per_unit:.3f} mm; "
              f"truncation band +/-{band * mm_per_unit:.2f} mm "
              f"(multiplier {trunc_voxel_multiplier}); block_count {block_count} "
              f"= {block_count * 80 / 1024 / 1024:.1f} GiB reserved.")
    else:
        print(f"[INFO] TSDF voxel size {voxel_size} scene units, truncation band "
              f"+/-{band} units (multiplier {trunc_voxel_multiplier}), "
              f"block_count {block_count}.")
    if abs(trunc_voxel_multiplier * 16.0 / 8.0 - 16.0) > 1e-9:
        print(f"[INFO] the band is {2 * trunc_voxel_multiplier / 16.0:.2f} blocks thick, "
              f"so expect roughly that multiple of the blocks a multiplier of 8 would need.")
    # [SHERD FORK] upstream hard-codes CPU:0. The installed wheel DOES ship a CUDA build
    # (open3d/cuda/pybind*.so, 800 MB), and open3d/__init__.py picks it automatically when
    # it sees a GPU -- so on a compute node this can run on CUDA:0 and is far faster, since
    # fusion cost grows as 1/voxel^2. The catch is that block_count is a reservation of
    # whichever device's memory: 80 KiB per block, so 1.5M blocks is 114 GiB and will not
    # fit an A100. Coarse rungs on GPU, fine rungs on CPU. Default stays the author's.
    if o3d_device_str.upper().startswith("CUDA") and not o3d.core.cuda.is_available():
        print(f"[WARNING] {o3d_device_str} asked for but Open3D sees no CUDA device "
              f"(__DEVICE_API__={getattr(o3d, '__DEVICE_API__', '?')}). Falling back to "
              f"CPU:0. On a login node this is expected; in a job it is not.",
              file=sys.stderr)
        o3d_device_str = "CPU:0"
    # [SHERD FORK] check the card has room BEFORE asking, because an Open3D CUDA OOM is not
    # a recoverable exception here: it raises, then aborts the process while unwinding
    # ("Block of ... should have been recorded") and takes the job with it. A pre-flight
    # test costs nothing and downgrades to host RAM instead of dying. The margin is loose
    # on purpose -- integration allocates per-view scratch on top of the grid.
    if o3d_device_str.upper().startswith("CUDA") and torch.cuda.is_available():
        need_gib = block_count * 81920 / 1024 ** 3
        free_gib = torch.cuda.mem_get_info()[0] / 1024 ** 3
        if free_gib < need_gib * 1.5 + 4.0:
            print(f"[WARNING] the voxel grid wants {need_gib:.1f} GiB and only "
                  f"{free_gib:.1f} GiB is free on the card. Fusing on CPU:0 instead: "
                  f"slower, but a CUDA OOM here aborts rather than raises.",
                  file=sys.stderr)
            o3d_device_str = "CPU:0"
    print(f"[INFO] Open3D {o3d.__version__} fusing on {o3d_device_str} "
          f"(device API: {getattr(o3d, '__DEVICE_API__', '?')}); "
          f"{block_count * 80 / 1024 / 1024:.1f} GiB reserved there.")
    o3d_device = o3d.core.Device(o3d_device_str)
    vbg = o3d.t.geometry.VoxelBlockGrid(attr_names=('tsdf', 'weight', 'color'),
                                            attr_dtypes=(o3c.float32,
                                                         o3c.float32,
                                                         o3c.float32),
                                            attr_channels=((1), (1), (3)),
                                            voxel_size=voxel_size,
                                            block_resolution=16,
                                            block_count=block_count,
                                            device=o3d_device)
    for color, depth, viewpoint_cam in zip(color_list, depth_list, viewpoint_cam_list):
        depth = o3d.t.geometry.Image(depth)
        depth = depth.to(o3d_device)
        color = o3d.t.geometry.Image(color)
        color = color.to(o3d_device)
        W, H = viewpoint_cam.image_width, viewpoint_cam.image_height
        fx = W / (2 * math.tan(viewpoint_cam.FoVx / 2.))
        fy = H / (2 * math.tan(viewpoint_cam.FoVy / 2.))
        intrinsic = np.array([[fx,0,float(W)/2],[0,fy,float(H)/2],[0,0,1]],dtype=np.float64)
        intrinsic = o3d.core.Tensor(intrinsic)
        extrinsic = o3d.core.Tensor((viewpoint_cam.world_view_transform.T).cpu().numpy().astype(np.float64))
        # [SHERD FORK] the trailing 1.0, 8.0 are depth_scale and depth_max, NOT truncation.
        # trunc_voxel_multiplier is the next positional argument in both calls and upstream
        # never passes it; it must be given to BOTH or the block allocation will not cover
        # the band the integration then tries to write into.
        frustum_block_coords = vbg.compute_unique_block_coordinates(
                                                                        depth,
                                                                        intrinsic,
                                                                        extrinsic,
                                                                        1.0, 8.0,
                                                                        trunc_voxel_multiplier
                                                                    )
        vbg.integrate(
                        frustum_block_coords,
                        depth,
                        color,
                        intrinsic,
                        extrinsic,
                        1.0, 8.0,
                        trunc_voxel_multiplier
                    )

    # [SHERD FORK] block_count is a capacity allocated up front. On CUDA:0 the hashmap
    # rehashes and GROWS past it -- job 29694649 reserved 50,000 and ended on 290,640
    # (581%) without complaint, so nothing was dropped, but the reservation stopped
    # meaning anything and the run's memory estimate was 6x low.
    #
    # Do NOT read a claim about CPU:0 into that. Job 29694649's CPU retry segfaulted while
    # over capacity and job 29695830's segfaulted at 72.7% OF capacity, so overflow was
    # never the cause: Open3D 0.19.0 CPU integration simply does not survive a grid this
    # size here. CPU is not a fallback at this scale, whatever the reservation.
    #
    # The number is still the measurement a finer rung is sized from: blocks grow as
    # (old_voxel / new_voxel)^2, times the band thickness increase (2 * multiplier / 16).
    used = 0
    try:
        used = vbg.hashmap().size()
        print(f"[INFO] blocks used: {used:,} of {block_count:,} reserved "
              f"({100.0 * used / max(block_count, 1):.1f}%); "
              f"{used * 80 / 1024 / 1024:.1f} GiB of grid.")
        if used > block_count:
            print(f"[WARNING] the reservation was exceeded ({used:,} > {block_count:,}). "
                  f"CUDA grew to fit. Rerun with --block_count {int(used * 1.4)} or more "
                  f"so the memory figures in this log mean something.", file=sys.stderr)
    except Exception:
        print("[INFO] could not read block usage from the grid.")

    # [SHERD FORK] Marching cubes allocates ONE scratch tensor sized by the active block
    # count -- {n_blocks, 16, 16, 16, 4} int32 in VoxelBlockGridImpl.h, i.e. exactly 64 KiB
    # per block -- and reports its failure as "Unable to allocate assistance mesh structure
    # for Marching Cubes with N active voxel blocks". That message names the voxel size and
    # sounds like a hard ceiling on N. It is not: it is an ordinary allocation failure, and
    # the arithmetic below is what decides.
    #
    # Job 29694649 hit it with 290,640 blocks because block_count was 50,000 and the
    # hashmap had grown to fit -- reallocation leaves the old buffer alive, so the card was
    # holding far more than the grid's nominal size. Reserve the blocks up front and the
    # same extraction fits: 290,640 blocks is 19.1 GiB of scratch on top of the grid.
    #
    # vbg.cpu() is Open3D's own suggested escape and it segfaulted on a 72.7%-full grid
    # (job 29695830, exit 139), as did CPU integration (job 29694649). BOTH of those were
    # 290,640-block grids -- 22 GiB -- because the clamp rig was still in the mask. This
    # file used to conclude from them that "there is no host fallback". That generalised a
    # 22 GiB result into a property of Open3D, and it was wrong: the host path had simply
    # never been tried at a sane size.
    #
    # And fitting on the card is NOT sufficient either. Job 29771412 had a 34,129-block
    # grid, wanted 2.1 GiB of scratch with 73.9 GiB free, and CUDA extraction still died
    # with an illegal memory access inside Open3D's MemoryManagerCUDA -- the same crash as
    # isl-org/Open3D#4824, unfixed since 2022. So the arithmetic below is a necessary
    # condition, not a sufficient one, and the caller should be prepared to try CPU:0.
    if o3d_device_str.upper().startswith("CUDA") and torch.cuda.is_available():
        scratch_gib = used * 65536 / 1024 ** 3
        free_gib = torch.cuda.mem_get_info()[0] / 1024 ** 3
        print(f"[INFO] marching cubes needs a {scratch_gib:.1f} GiB scratch tensor for "
              f"{used:,} active blocks; {free_gib:.1f} GiB free on the card.")
        if scratch_gib + 3.0 > free_gib:
            print(f"[ERROR] that does not fit on the card. Try --o3d_device CPU:0, which "
                  f"needs {used * 80 / 1024 / 1024:.1f} GiB of host RAM for the grid; "
                  f"coarsen --voxel_size (blocks fall as its square); or cut what the masks "
                  f"keep -- on A03 with the clamp rig in, 91% of the masked area was rig.",
                  file=sys.stderr)
            sys.exit(1)
    mesh = vbg.extract_triangle_mesh()
    mesh.compute_vertex_normals()
    out_ply = os.path.join(dataset.model_path, ply_name)
    o3d.io.write_triangle_mesh(out_ply, mesh.to_legacy())
    n_v = len(mesh.vertex["positions"])
    print(f"[INFO] wrote {out_ply}: {n_v:,} vertices.")
    if n_v == 0:
        # A fine voxel with the default multiplier is the way this happens: the band gets
        # narrower than the disagreement between views and nothing ever reinforces.
        print("[ERROR] the fusion produced an empty mesh. Raise --trunc_voxel_multiplier "
              "or coarsen --voxel_size.", file=sys.stderr)
        sys.exit(1)
    print("done!")

if __name__ == "__main__":
    parser = ArgumentParser(description="Training script parameters")
    lp = ModelParams(parser)
    pp = PipelineParams(parser)
    parser.add_argument("--checkpoint_iterations", nargs="+", type=int, default=None)
    parser.add_argument("--rasterizer", default="radegs", type=str, choices=["radegs", "gof"])
    parser.add_argument("--occupancy_mode", type=str, default="occupancy_shift")
    # [SHERD FORK] all default to the author's effective values; passing none of them
    # reproduces upstream behaviour exactly.
    parser.add_argument("--voxel_size", type=float, default=0.002)
    parser.add_argument("--block_count", type=int, default=50000)
    parser.add_argument("--trunc_voxel_multiplier", type=float, default=8.0,
                        help="TSDF truncation band, in voxels. Raise it in step with any "
                             "refinement of --voxel_size to hold the band at a fixed "
                             "physical width.")
    parser.add_argument("--ply_name", type=str, default="recon_tsdf.ply",
                        help="output filename inside the model directory, so a sweep of "
                             "voxel sizes does not overwrite itself.")
    parser.add_argument("--o3d_device", type=str, default="CPU:0",
                        help="Open3D device for the TSDF fusion, e.g. CUDA:0. The wheel "
                             "ships a CUDA build; the limit is that block_count reserves "
                             "80 KiB per block on that device's memory.")
    parser.add_argument("--mm_per_unit", type=float, default=None,
                        help="reporting only: prints voxel size and truncation band in "
                             "millimetres so a wrong scale is obvious in the log.")
    args = parser.parse_args(sys.argv[1:])
    
    print(f"[INFO] Using {args.rasterizer} as rasterizer.")
    if args.rasterizer == "radegs":
        from gaussian_renderer.radegs import render_radegs as render
    elif args.rasterizer == "gof":
        from gaussian_renderer.gof import render_gof as render
    else:
        raise ValueError(f"Invalid rasterizer: {args.rasterizer}")
    
    
    with torch.no_grad():
        extract_mesh(lp.extract(args), pp.extract(args), args.checkpoint_iterations, args.occupancy_mode,
                     voxel_size=args.voxel_size, block_count=args.block_count,
                     trunc_voxel_multiplier=args.trunc_voxel_multiplier,
                     ply_name=args.ply_name, mm_per_unit=args.mm_per_unit,
                     o3d_device_str=args.o3d_device)
        
        
    
    