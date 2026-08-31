import os
import sys
BASE_DIR = os.path.dirname(  # milo/
    os.path.dirname(  # milo/eval/
        os.path.dirname(os.path.abspath(__file__))  # milo/eval/dtu/
    )
)
sys.path.append(BASE_DIR)


# [SHERD FORK] Which Open3D binary gets used is decided at IMPORT time, not at the call,
# so it has to be settled here. open3d/__init__.py imports the CPU pybind and then
# REPLACES it with the CUDA one if open3d_core_cuda_device_count() > 0 -- a count that
# honours CUDA_VISIBLE_DEVICES. Blanking that variable across the import and restoring it
# immediately therefore yields the CPU binary while leaving the GPU to PyTorch, which has
# not created a context yet (importing torch does not initialise CUDA).
#
# This matters because the CUDA binary's marching cubes is broken on this installation.
# Measured, not inferred: on a compute node extract_triangle_mesh() died on BOTH devices
# of the CUDA build -- "illegal memory access" on CUDA:0 (job 29771412) and a segfault on
# CPU:0 (job 29774524) -- with a 2.6 GiB grid and 73.9 GiB free. The same call on an
# identical toy scene succeeds in the CPU build. isl-org/Open3D#4824 reports the CUDA
# crash, unfixed since 2022. So "--o3d_device CPU:0" must mean the CPU *binary*; asking
# for the CPU device of the CUDA binary is what the failing job actually got, and it is
# not the same thing.
def _wants_cuda_open3d(argv):
    for i, a in enumerate(argv):
        if a == "--o3d_device" and i + 1 < len(argv):
            return argv[i + 1].upper().startswith("CUDA")
        if a.startswith("--o3d_device="):
            return a.split("=", 1)[1].upper().startswith("CUDA")
    return False


_O3D_CUDA = _wants_cuda_open3d(sys.argv)
_SAVED_CVD = os.environ.get("CUDA_VISIBLE_DEVICES")
if not _O3D_CUDA:
    os.environ["CUDA_VISIBLE_DEVICES"] = ""
import open3d as o3d
import open3d.core as o3c
if not _O3D_CUDA:
    if _SAVED_CVD is None:
        os.environ.pop("CUDA_VISIBLE_DEVICES", None)
    else:
        os.environ["CUDA_VISIBLE_DEVICES"] = _SAVED_CVD

import gc
import torch

# Pin PyTorch's view of the devices now, immediately after the variable is restored, so the
# blanking above cannot leak into the rendering that follows. torch caches this on the first
# call; making that call here rather than a thousand lines later removes the ordering
# question entirely. If it is ever False on a GPU node, the import trick is the suspect.
if not _O3D_CUDA and not torch.cuda.is_available():
    print("[WARNING] hiding the GPU across the Open3D import also cost PyTorch its CUDA "
          "device. Depth rendering will fall back to CPU and be unusably slow. Run with "
          "--o3d_device CUDA:0 to skip the trick, and expect the extraction bug back.",
          file=sys.stderr)

from scene import GaussianModel
from argparse import ArgumentParser
from arguments import ModelParams, PipelineParams
import math
import numpy as np
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
                 ply_name="recon_tsdf.ply", mm_per_unit=None, o3d_device_str="CPU:0",
                 allow_mc_overflow=False):
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

    # [SHERD FORK] Look at the depth maps BEFORE they reach the voxel grid. Open3D does not
    # check them, and one non-finite value is enough to poison the TSDF; marching cubes then
    # indexes an array from that TSDF and walks off the end of it, which surfaces as a
    # segfault at extraction -- a long way from the cause, and indistinguishable from a
    # library bug. A synthetic sphere extracts fine at 9,672 blocks on this same install,
    # so "too big" does not explain A03's 34,129, and this is the other candidate.
    # Sanitise rather than abort: a NaN in one corner of one view should not cost the run,
    # but it must be reported, because a large count is a statement about the RENDERER.
    nonfinite = negative = clipped = 0
    dmin, dmax = np.inf, -np.inf
    for d in depth_list:
        bad = ~np.isfinite(d)
        nb = int(bad.sum())
        if nb:
            d[bad] = 0.0
            nonfinite += nb
        neg = d < 0
        nn = int(neg.sum())
        if nn:
            d[neg] = 0.0
            negative += nn
        pos = d[d > 0]
        if pos.size:
            dmin = min(dmin, float(pos.min()))
            dmax = max(dmax, float(pos.max()))
            clipped += int((pos > 8.0).sum())
    total_px = sum(d.size for d in depth_list)
    print(f"[INFO] depth maps: {nonfinite:,} non-finite and {negative:,} negative pixels of "
          f"{total_px:,} ({100.0 * (nonfinite + negative) / max(total_px, 1):.4f}%), "
          f"all set to 0. Kept depths run {dmin:.3f} to {dmax:.3f} scene units"
          + (f" = {dmin * mm_per_unit:.0f} to {dmax * mm_per_unit:.0f} mm." if mm_per_unit else "."))
    if nonfinite or negative:
        print(f"[WARNING] the Gaussian renderer produced {nonfinite + negative:,} unusable "
              f"depth values. They are zeroed here, but a large fraction means the depth "
              f"being fused is not trustworthy wherever it survived either.", file=sys.stderr)
    if clipped:
        print(f"[WARNING] {clipped:,} pixels are beyond the depth_max of 8.0 scene units "
              f"and Open3D will ignore them. If that is a large number the scene is not "
              f"where this code assumes it is.", file=sys.stderr)

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
    # The build matters more than the device here: the CUDA build's marching cubes fails
    # on this installation whichever device it is handed. "cpu" below is the good case.
    print(f"[INFO] Open3D {o3d.__version__} fusing on {o3d_device_str} "
          f"(binary: {getattr(o3d, '__DEVICE_API__', '?')}); "
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

    # [SHERD FORK] Last look before the call that keeps dying. extract_triangle_mesh()
    # crashes without a message on either device here, so anything wrong with the grid has
    # to be caught on this side of it -- afterwards there is only an exit code. A synthetic
    # sphere extracts cleanly at 9,672 blocks in this same install, which rules out sheer
    # size as the whole story and leaves the grid's CONTENTS as the thing to check.
    try:
        tsdf = vbg.attribute("tsdf").cpu().numpy()
        wt = vbg.attribute("weight").cpu().numpy()
        n_bad_t = int(np.count_nonzero(~np.isfinite(tsdf)))
        n_bad_w = int(np.count_nonzero(~np.isfinite(wt)))
        occupied = wt > 0
        n_occ = int(occupied.sum())
        print(f"[INFO] grid contents: {n_bad_t:,} non-finite TSDF and {n_bad_w:,} non-finite "
              f"weight values; {n_occ:,} voxels carry any weight "
              f"({100.0 * n_occ / max(tsdf.size, 1):.2f}% of the buffer).")
        if n_occ:
            t_occ = tsdf[occupied]
            print(f"[INFO] TSDF over the {n_occ:,} written voxels: "
                  f"{float(t_occ.min()):+.3f} to {float(t_occ.max()):+.3f} "
                  f"(it is a signed distance in band units, so it should stay within +/-1).")
        if n_bad_t or n_bad_w:
            print(f"[ERROR] the fused grid contains non-finite values. Marching cubes builds "
                  f"its vertex indices from these, so this is very likely the segfault: it "
                  f"would crash at any block count, and the synthetic test never had one.",
                  file=sys.stderr)
        del tsdf, wt
        gc.collect()
    except Exception as e:
        print(f"[INFO] could not inspect the grid contents ({e}); continuing.")

    # [SHERD FORK] THE HARD LIMIT, measured: extract_triangle_mesh() allocates one scratch
    # tensor of 64 KiB per ACTIVE block ({n,16,16,16,4} int32). At 32,768 blocks that is
    # exactly 2^31 bytes, and Open3D 0.19.0 sizes the allocation with a signed 32-bit
    # integer, so at or above that count it wraps negative and the process dies -- a
    # segfault on CPU, an "illegal memory access" on CUDA, with no message either way.
    #
    # Demonstrated on a synthetic sphere in this install, nothing to do with sherds:
    #     9,672 blocks (0.59 GiB) -> 1,747,748 vertices, fine
    #    28,176 blocks (1.72 GiB) -> 5,086,918 vertices, fine
    #    34,184 blocks (2.09 GiB) -> core dumped
    #    38,464 blocks (2.35 GiB) -> core dumped
    # A03 sits at 34,129 -- 4% past the cliff -- which is why every extraction had failed
    # while free memory was abundant. Four jobs read this as a memory problem. It never was.
    # isl-org/Open3D#4824 is the same crash, also reported near this size, unfixed since 2022.
    #
    # Refuse rather than crash. A checked limit that names the number is worth more than a
    # core dump, and the caller can act on it: blocks fall as the SQUARE of the voxel size,
    # so a 5% coarser voxel buys 10% fewer blocks.
    MC_BLOCK_LIMIT = 32768
    if used >= MC_BLOCK_LIMIT and not allow_mc_overflow:
        safe_voxel = voxel_size * math.sqrt(used / (MC_BLOCK_LIMIT * 0.95))
        print(f"[ERROR] {used:,} active blocks is at or past Open3D's marching-cubes limit "
              f"of {MC_BLOCK_LIMIT:,} ({used * 64 / 1024 / 1024:.2f} GiB of scratch, and the "
              f"allocation size is a signed 32-bit integer that wraps at 2.00 GiB). Calling "
              f"extract_triangle_mesh() now would segfault with no message, on either "
              f"device, however much memory is free.\n"
              f"        Fixes, in order of honesty: --voxel_size {safe_voxel:.5f} or coarser "
              f"(blocks fall as its square"
              + (f"; that is {safe_voxel * mm_per_unit:.3f} mm against the current "
                 f"{voxel_size * mm_per_unit:.3f} mm" if mm_per_unit else "")
              + f"); tighten the masks so less is fused; or extract in spatial chunks, each "
              f"under the limit. --allow_mc_overflow forces the call if you want the crash.",
              file=sys.stderr)
        sys.exit(2)

    sys.stdout.flush()
    sys.stderr.flush()
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
    parser.add_argument("--allow_mc_overflow", action="store_true",
                        help="call extract_triangle_mesh() even at 32,768+ active blocks, "
                             "where Open3D 0.19.0's scratch allocation overflows a signed "
                             "32-bit byte count and the process dies without a message. "
                             "Only useful for reproducing that crash.")
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
                     o3d_device_str=args.o3d_device,
                     allow_mc_overflow=args.allow_mc_overflow)
        
        
    
    