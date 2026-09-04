#!/bin/bash
#SBATCH --job-name=milo-prune
#SBATCH --account=punim2657
#SBATCH --partition=gpu-a100
#SBATCH --gres=gpu:1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=16
#SBATCH --mem=150G
#SBATCH --time=12:00:00
#SBATCH --output=/data/gpfs/projects/punim2657/MILo/logs/milo_prune_%j.log

# Pruned tet extraction (intent M4, ticket 02): run MILo's native
# marching-tetrahedra flow from clay-voted Gaussians only.
#
#   step 1  scripts/prune_rig_gaussians.py  -> kept_idx.npy  (done, ticket 01:
#           8,686 of 222,678 Gaussians kept on A03 at keep-ratio 0.8)
#   step 2  this job: milo/mesh_extract_sdf.py --keep-idx kept_idx.npy
#           -> mesh_learnable_sdf_pruned.ply
#
# The keep indices enter at the existing downsample-index seam before pivots
# are built; pivots, triangulation, refinement and marching tetrahedra run
# unchanged, at trained pivot spread (no downsample compensation -- a pruned
# set keeps full clay density). Training-time masking stays closed (removed at
# 770338f for painting 0.6-0.9 mm of edge); nothing retrains here.
#
# Usage:
#   ./scripts/remote/pull_and_sbatch.sh slurm/milo_prune_extract.slurm \
#        17062025/A03_sherds 17062025/A03_nomask 17062025/A03_prune

set -euo pipefail

CAPTURE="${1:?usage: sbatch milo_prune_extract.slurm <capture> <trained_run> <out_name>}"
TRAINED="${2:?second argument is the finished run to read Gaussians from}"
OUT_NAME="${3:?third argument is where to write the mesh}"

MILO_ROOT=/data/gpfs/projects/punim2657/MILo
REPO_DIR=$MILO_ROOT/repo
ENV_PREFIX=$MILO_ROOT/envs/milo
DATA_DIR=$MILO_ROOT/data/$CAPTURE
SRC_DIR=$MILO_ROOT/output/$TRAINED
OUT_DIR=$MILO_ROOT/output/$OUT_NAME
KEEP_IDX="$OUT_DIR/kept_idx.npy"
PRUNED="$OUT_DIR/mesh_learnable_sdf_pruned.ply"

echo "=== pruned tet extraction started $(date) on $(hostname) ==="
echo "  Gaussians from : $SRC_DIR"
echo "  keep set       : $KEEP_IDX"
echo "  writing to     : $OUT_DIR"
nvidia-smi | head -15 || true

[[ -f "$SRC_DIR/point_cloud/iteration_18000/point_cloud.ply" ]] || {
    echo "No trained Gaussians at $SRC_DIR/point_cloud/iteration_18000/" >&2; exit 1; }
[[ -f "$KEEP_IDX" ]] || {
    echo "No keep set at $KEEP_IDX -- run scripts/prune_rig_gaussians.py first" >&2; exit 1; }

module purge
module load GCC/11.3.0 OpenMPI/4.1.4
module load CUDA/11.8.0
module load Miniforge3/24.7.1-2
export CUDA_HOME="${EBROOTCUDA:?}"
export LD_LIBRARY_PATH="$CUDA_HOME/targets/x86_64-linux/lib:${LD_LIBRARY_PATH:-}"
export OMP_NUM_THREADS="${SLURM_CPUS_PER_TASK:-8}"

eval "$(conda shell.bash hook)"
conda activate "$ENV_PREFIX"

# Share the trained run by symlink so its meshes stay untouched.
mkdir -p "$OUT_DIR"
for f in point_cloud cameras.json input.ply; do
    if [[ -e "$SRC_DIR/$f" ]]; then
        ln -sfn "$SRC_DIR/$f" "$OUT_DIR/$f"
    fi
done
cp -f "$SRC_DIR/cfg_args" "$OUT_DIR/cfg_args"

# The scale factor, read once, so the pruned mesh lands in the same millimetres.
WORK=$(python3 -c "import json;print(json.load(open('$DATA_DIR/capture.json'))['work_dir'])")
FACTOR=$(python3 - "$WORK/measurement.env" <<'PY'
import sys
env = dict(l.strip().split("=", 1) for l in open(sys.argv[1]) if "=" in l)
f1 = float(env["d1_real_m"]) / float(env["d1_rec_units"])
f2 = float(env["d2_real_m"]) / float(env["d2_rec_units"])
print(f"{(f1 + f2) / 2:.9f}")
print(f"  the two scale bars disagree by {abs(f1-f2)/((f1+f2)/2)*100:.1f}% -- every "
      f"millimetre figure from this mesh carries at least that", file=sys.stderr)
PY
)
MM_PER_UNIT=$(python3 -c "print(f'{$FACTOR * 1000.0:.4f}')")
echo "  scale          : $MM_PER_UNIT mm per scene unit"

if [[ -f "$PRUNED" ]]; then
    echo "  $PRUNED exists already -- skipping the extraction."
else
    cd "$REPO_DIR/milo"
    python -u mesh_extract_sdf.py \
        -s "$DATA_DIR" -m "$OUT_DIR" -i images_masked -r 1 --eval \
        --iteration 18000 \
        --imp_metric indoor \
        --init learnable \
        --config default \
        --keep-idx "$KEEP_IDX" \
        --out-name "$(basename "$PRUNED")"
fi
[[ -f "$PRUNED" ]] || { echo "extraction wrote no mesh" >&2; exit 1; }

echo
echo "--- millimetres $(date) ---"
cd "$REPO_DIR"
python scripts/apply_scale.py --capture "$DATA_DIR/capture.json" \
    --mesh "$PRUNED" --out "$OUT_DIR/mesh_learnable_sdf_pruned_mm.ply" --force-factor "$FACTOR"

echo
echo "=== what the pruned mesh holds (A03 holds TEN sherds) ==="
python scripts/mesh_report.py "$OUT_DIR/mesh_learnable_sdf_pruned_mm.ply" --expect-pieces 10

echo
ls -la "$OUT_DIR"/*.ply
echo "=== finished $(date) ==="
echo "LOOK AT THE MESH before believing any number above -- ticket 03 renders the"
echo "0.10 mm/px break-face proof (pruned vs unpruned vs OpenMVS, same window)."
