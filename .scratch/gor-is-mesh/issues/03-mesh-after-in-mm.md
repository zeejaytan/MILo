# 03: Mesh-after with voxel and band in millimetres (REQUIRED)

**What to build:** a mesh taken from the inpainted GOR-IS splat via the manual `render.py` mesh path — this step is required, not optional, and its voxel and band are stated in mm.

**Answers:** M9

**Blocked by:** 02-recon-removal-inpainting.

**Status:** ready-for-agent

- [ ] Manual `render.py` WITHOUT `--skip_mesh` on the iteration-34000 inpainted model, bounded first (`--voxel_size --sdf_trunc --depth_trunc` all stated in mm, mesh saved as `fuse.ply` plus `_post.ply`); unbounded only as a named second variant
- [ ] Voxel size, truncation band, depth range, cluster-keep count and scale sidecar recorded beside the mesh; `compare_meshes.py` refusal without sidecar verified, not assumed
- [ ] Mesh is non-empty, ten sherds separable by component filter, zero steel to the eye on whole-tray views; extraction log kept with block counts and device
- [ ] Inpainted-contact faces tagged in the mesh metadata for exclusion in ticket 04; tag method recorded
