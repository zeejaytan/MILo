## Problem Statement

**Answers:** M9 (MILo project — this spec is the plan that tickets 01–04 execute).

Unmasked MILo keeps the clamp rig; masked DTU fusion removes it but smooths to 0.822 mm voxels against ~1 mm break-face grain, with a 4.1 mm depth floor underneath. GOR-IS removes the rig plus its reflections and fills behind it in intrinsic space. Its default run never meshes. The conservator needs to know whether a mesh taken after GOR-IS inpainting keeps ridge relief with zero steel — as record, as complement to OpenMVS, or not at all. Inpainted jaw contact is invented clay and never scores as measurement.

## Solution

Pin GOR-IS at `eb36acc`, convert A03_sherds to its dataset layout, run recon → removal → 2D/3D inpaint on one capture at full resolution, then a manual mesh-after with voxel and band stated in mm. Proof is the same three boxes every GS route faces: depth disagreement in mm, same-ruler fraction within 1 mm vs OpenMVS (inpainted contact excluded), ridge-resolving close-ups plus eye sign-off, and steel cm² left.

## User Stories

1. As a conservator, I want a rig-free mesh with no steel in it, so reassembly never matches clamp geometry.
2. As a conservator, I want break-face relief to ~1 mm preserved, so joins seat on real relief.
3. As a conservator, I want jaw-contact fill marked as invented and excluded from every mm score, so I see missing evidence instead of false clay.
4. As a conservator, I want close-up renders at ridge scale, so a whole-tray view cannot hide smoothing again.
5. As a researcher, I want voxel size and truncation band stated in mm, so the mesh can be compared on the same ruler.
6. As a researcher, I want depth disagreement in mm on the same capture, so the floor is measured not assumed.
7. As a researcher, I want the verdict written back into intent M9 with a date, so the question closes whatever the outcome.

## Implementation Decisions

- Pin `applezyh/GOR-IS@eb36acc` (2026-05-30) before any job; separate `envs/goris` (python 3.12, nvdiffrast, OptiX gtracer fork per its README, incl. IRGS#5 segfault workaround). Never reuse `envs/milo`.
- Dataset `data/17062025/A03_sherds` converted once: rig object_mask (inverse of erode0 as start, verified by eye), chrome specular_mask (new), predicted normals (new), COLMAP sparse reused, train/val/test lists. Full resolution, no silent downsample.
- Pipeline per `launcher.py`/`run.sh`: `--recon` 30k → `--remove_object` → `--inpainting2D` → `--inpainting3D` 34k (`--load_inpainted --use_material_inpainting --use_reflection_mask`), `--render_inpainting3D`. Mesh-after is a manual `render.py` WITHOUT `--skip_mesh`, bounded first, voxel/sdf/depth in mm.
- Post pass `post_process_mesh` cluster count recorded; inpainted-contact faces tagged and excluded from every mm comparison.
- Scope is one capture (A03), one seed. Workspace rule governs submits: standing sign-off, laptop-side poll on every submit.

## Testing Decisions

- Outside behaviour only: steel cm² left, fraction within 1 mm vs OpenMVS (inpainted contact excluded), depth disagreement mm, held-out render PSNR as viewing signal only.
- Render is part of the test: no box ticks without ridge-resolving close-ups, GOR-IS mesh vs OpenMVS side by side, plus conservator eye.
- Guards prove they can fail: compare refuses without scale sidecars; synthetic fixture for the exclusion is preferred over assertion-free runs.

## Out of Scope

- Retraining MILo/2DGS/PGSR; any change to MILo training loss or extraction.
- Tiling, block-limit work, Open3D version changes, VDBFusion.
- OpenMVS/COLMAP config changes; re-photography or remounting (M2 gate stands separately).
- Full-tray production runs or a second capture before the one-capture verdict lands.

## Further Notes

- Answers intent M9. M1's requirement (~1 mm) and OpenMVS ceiling transfer in; MILo-specific boxes do not gate this except the ruler (M3 sidecars).
- If density drains ~90%+ the way M5/M6 did, retire at probe weight — do not tune through it.
