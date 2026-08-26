#!/bin/bash
#SBATCH --job-name=milo-dtu
#SBATCH --account=punim2657
#SBATCH --partition=gpu-a100
#SBATCH --gres=gpu:1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=200G
#SBATCH --time=6:00:00
#SBATCH --output=/data/gpfs/projects/punim2657/MILo/logs/milo_dtu_%j.log

set -euo pipefail

# Run MILo's OWN object-isolation route -- the one its authors use for the DTU benchmark,
# which is the same situation as ours: a small object on a stand, photographed against a
# background it must be separated from. Two steps, and this job keeps the mesh from EACH so
# they can be compared rather than conflated:
#
#   step 1  milo/eval/dtu/mesh_extract_dtu.py   -> recon_tsdf.ply
#           Renders depth from the trained Gaussians for every training view, sets depth to
#           ZERO wherever the mask is dark, and TSDF-fuses what is left. Masked pixels never
#           enter the voxel grid, so this genuinely deletes background rather than relabelling
#           it -- unlike the cull inside --init integration, which marks unseen space SOLID.
#
#   step 2  scripts/cull_dtu_mesh.py            -> recon_tsdf_culled.ply
#           Calls evaluate_dtu_mesh.py:cull_mesh unmodified. Keeps a vertex only if it lands
#           inside a 6-pixel-dilated sherd outline in EVERY training view. That all-views rule
#           is the difference from the integration cull's at-least-one-view rule, which the
#           mounting rig walks straight through because it sits behind the sherds from many
#           angles on a turntable.
#
# WHAT THIS IS AND IS NOT. This is a mechanism check, not a candidate production route.
# Step 1 is Open3D TSDF fusion of MILo's rendered depth maps -- a different mesh extractor
# from the marching-tetrahedra-on-Gaussians that produced mesh_learnable_sdf.ply. The GOF
# line of work this inherits from explicitly presents marching tetrahedra as the improvement
# OVER TSDF fusion, so expect step 1's geometry to be blunter, and do not read that bluntness
# as an effect of masking.
#
# RESOLUTION. The author's voxel size is 0.002 scene units. On A03 (373.7 mm per unit) that
# is 0.75 mm -- coarser than the 0.41-0.51 mm the carved mesh already samples at. The default
# below is the author's, unchanged, because the point is to see what THEIR step does. Pass a
# smaller VOXEL to go finer; raise BLOCKS with it or the voxel grid runs out of blocks.
#
# Usage:
#   ./scripts/remote/pull_and_sbatch.sh slurm/milo_extract_dtu.slurm \
#        17062025/A03 17062025/A03_nomask 17062025/A03_dtu [voxel_size] [block_count]

CAPTURE="${1:?usage: sbatch milo_extract_dtu.slurm <capture> <trained_run> <out_name> [voxel] [blocks]}"
TRAINED="${2:?second argument is the finished run to read Gaussians from}"
OUT_NAME="${3:?third argument is where to write the meshes}"
VOXEL="${4:-0.002}"
BLOCKS="${5:-50000}"

MILO_ROOT=/data/gpfs/projects/punim2657/MILo
REPO_DIR=$MILO_ROOT/repo
ENV_PREFIX=$MILO_ROOT/envs/milo
DATA_DIR=$MILO_ROOT/data/$CAPTURE
SRC_DIR=$MILO_ROOT/output/$TRAINED
OUT_DIR=$MILO_ROOT/output/$OUT_NAME

echo "=== DTU-route extraction started $(date) on $(hostname) ==="
echo "  Gaussians from : $SRC_DIR"
echo "  writing to     : $OUT_DIR"
echo "  voxel / blocks : $VOXEL / $BLOCKS"
nvidia-smi | head -15 || true

[[ -f "$SRC_DIR/point_cloud/iteration_18000/point_cloud.ply" ]] || {
    echo "No trained Gaussians at $SRC_DIR/point_cloud/iteration_18000/" >&2; exit 1; }
[[ -d "$DATA_DIR/images_masked" ]] || {
    echo "No RGBA image set at $DATA_DIR/images_masked -- rerun colmap_to_milo.py" >&2; exit 1; }

if [[ -f "$OUT_DIR/recon_tsdf.ply" ]]; then
    echo "$OUT_DIR already holds recon_tsdf.ply. Move it aside or pick another name." >&2
    exit 1
fi

module purge
module load GCC/11.3.0 OpenMPI/4.1.4
module load CUDA/11.8.0
module load Miniforge3/24.7.1-2
export CUDA_HOME="${EBROOTCUDA:?}"
export LD_LIBRARY_PATH="$CUDA_HOME/targets/x86_64-linux/lib:${LD_LIBRARY_PATH:-}"

eval "$(conda shell.bash hook)"
conda activate "$ENV_PREFIX"

# Share the trained Gaussians by symlink so the unmasked run's meshes stay untouched.
mkdir -p "$OUT_DIR"
for f in point_cloud cameras.json input.ply; do
    if [[ -e "$SRC_DIR/$f" ]]; then
        ln -sfn "$SRC_DIR/$f" "$OUT_DIR/$f"
    fi
done
cp -f "$SRC_DIR/cfg_args" "$OUT_DIR/cfg_args"

# The scale factor, read once and reused, so both meshes land in the same millimetres.
WORK=$(python3 -c "import json;print(json.load(open('$DATA_DIR/capture.json'))['work_dir'])")
FACTOR=$(python3 - "$WORK/measurement.env" <<'PY'
import sys
env = dict(l.strip().split("=", 1) for l in open(sys.argv[1]) if "=" in l)
f1 = float(env["d1_real_m"]) / float(env["d1_rec_units"])
f2 = float(env["d2_real_m"]) / float(env["d2_rec_units"])
print(f"{(f1 + f2) / 2:.9f}")
print(f"  the two scale bars disagree by {abs(f1-f2)/((f1+f2)/2)*100:.1f}% -- every "
      f"millimetre figure from these meshes carries at least that", file=sys.stderr)
PY
)
echo "  scale factor   : $FACTOR mm per scene unit"
python3 -c "print(f'  voxel {$VOXEL} units is {$VOXEL * $FACTOR:.2f} mm')"

echo
echo "=== step 1: masked depth fusion $(date) ==="
cd "$REPO_DIR/milo"
python eval/dtu/mesh_extract_dtu.py \
    -s "$DATA_DIR" \
    -m "$OUT_DIR" \
    -i images_masked \
    -r 1 \
    --eval \
    --rasterizer radegs \
    --voxel_size "$VOXEL" \
    --block_count "$BLOCKS"

[[ -f "$OUT_DIR/recon_tsdf.ply" ]] || { echo "step 1 wrote no mesh" >&2; exit 1; }

echo
echo "=== step 2: silhouette cull $(date) ==="
cd "$REPO_DIR"
python scripts/cull_dtu_mesh.py \
    -s "$DATA_DIR" \
    -m "$OUT_DIR" \
    -i images_masked \
    -r 1 \
    --eval \
    --mesh "$OUT_DIR/recon_tsdf.ply" \
    --out "$OUT_DIR/recon_tsdf_culled.ply"

echo
echo "=== millimetres $(date) ==="
python scripts/apply_scale.py --capture "$DATA_DIR/capture.json" \
    --mesh "$OUT_DIR/recon_tsdf.ply" \
    --out "$OUT_DIR/mesh_dtufusion_mm.ply" --force-factor "$FACTOR"
python scripts/apply_scale.py --capture "$DATA_DIR/capture.json" \
    --mesh "$OUT_DIR/recon_tsdf_culled.ply" \
    --out "$OUT_DIR/mesh_dtucull_mm.ply" --force-factor "$FACTOR"

echo
echo "=== what each step produced ==="
# A03 holds TEN sherds (masks.json: 10 instances per frame). Reported for both meshes so the
# effect of the cull is visible as a difference, not asserted.
python scripts/mesh_report.py \
    "$OUT_DIR/mesh_dtufusion_mm.ply" \
    "$OUT_DIR/mesh_dtucull_mm.ply" \
    --expect-pieces 10

echo
ls -la "$OUT_DIR"/*.ply
echo "=== finished $(date) ==="
echo "LOOK AT BOTH MESHES before believing any number above."
