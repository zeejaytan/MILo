#!/bin/bash
#SBATCH --job-name=milo-learnable
#SBATCH --account=punim2657
#SBATCH --partition=gpu-a100
#SBATCH --gres=gpu:1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=16
#SBATCH --mem=150G
#SBATCH --time=12:00:00
#SBATCH --output=/data/gpfs/projects/punim2657/MILo/logs/milo_learnable_%j.log

# Native tet extraction from a trained run, unmodified flow (intent M5, ticket
# masked-training/04): default learnable init, default config, no keep set, no
# masks at extraction. Used to raise the two verdict meshes (control probe and
# masked probe) whose break faces and flat walls are then scored against each
# other in millimetres.
#
# Usage:
#   ./scripts/remote/pull_and_sbatch.sh slurm/milo_extract_learnable.slurm \
#        17062025/A03_sherds 17062025/A03_probe_masked 17062025/A03_probe_masked_mesh

set -euo pipefail

CAPTURE="${1:?usage: sbatch milo_extract_learnable.slurm <capture> <trained_run> <out_name>}"
TRAINED="${2:?second argument is the finished run to read Gaussians from}"
OUT_NAME="${3:?third argument is where to write the mesh}"

MILO_ROOT=/data/gpfs/projects/punim2657/MILo
REPO_DIR=$MILO_ROOT/repo
ENV_PREFIX=$MILO_ROOT/envs/milo
DATA_DIR=$MILO_ROOT/data/$CAPTURE
SRC_DIR=$MILO_ROOT/output/$TRAINED
OUT_DIR=$MILO_ROOT/output/$OUT_NAME
MESH="$OUT_DIR/mesh_learnable_sdf.ply"

echo "=== learnable tet extraction started $(date) on $(hostname) ==="
echo "  Gaussians from : $SRC_DIR"
echo "  writing to     : $OUT_DIR"
nvidia-smi | head -8 || true

[[ -f "$SRC_DIR/point_cloud/iteration_18000/point_cloud.ply" ]] || {
    echo "No trained Gaussians at $SRC_DIR/point_cloud/iteration_18000/" >&2; exit 1; }

module purge
module load GCC/11.3.0 OpenMPI/4.1.4
module load CUDA/11.8.0
module load Miniforge3/24.7.1-2
export CUDA_HOME="${EBROOTCUDA:?}"
export LD_LIBRARY_PATH="$CUDA_HOME/targets/x86_64-linux/lib:${LD_LIBRARY_PATH:-}"
export OMP_NUM_THREADS="${SLURM_CPUS_PER_TASK:-8}"

eval "$(conda shell.bash hook)"
conda activate "$ENV_PREFIX"

mkdir -p "$OUT_DIR"
for f in point_cloud cameras.json input.ply; do
    if [[ -e "$SRC_DIR/$f" ]]; then
        ln -sfn "$SRC_DIR/$f" "$OUT_DIR/$f"
    fi
done
cp -f "$SRC_DIR/cfg_args" "$OUT_DIR/cfg_args"

WORK=$(python3 -c "import json;print(json.load(open('$DATA_DIR/capture.json'))['work_dir'])")
FACTOR=$(python3 - "$WORK/measurement.env" <<'PY'
import sys
env = dict(l.strip().split("=", 1) for l in open(sys.argv[1]) if "=" in l)
f1 = float(env["d1_real_m"]) / float(env["d1_rec_units"])
f2 = float(env["d2_real_m"]) / float(env["d2_rec_units"])
print(f"{(f1 + f2) / 2:.9f}")
PY
)

if [[ -f "$MESH" ]]; then
    echo "  $MESH exists already -- skipping the extraction."
else
    cd "$REPO_DIR/milo"
    python -u mesh_extract_sdf.py \
        -s "$DATA_DIR" -m "$OUT_DIR" -i images_masked -r 1 --eval \
        --iteration 18000 \
        --imp_metric indoor \
        --init learnable \
        --config default
fi
[[ -f "$MESH" ]] || { echo "extraction wrote no mesh" >&2; exit 1; }

echo
echo "--- millimetres $(date) ---"
cd "$REPO_DIR"
MM_MESH="$OUT_DIR/mesh_learnable_sdf_mm.ply"
python scripts/apply_scale.py --capture "$DATA_DIR/capture.json" \
    --mesh "$MESH" --out "$MM_MESH" --force-factor "$FACTOR"

echo
python scripts/mesh_report.py "$MM_MESH" --expect-pieces 10

echo
ls -la "$OUT_DIR"/*.ply
echo "=== finished $(date) ==="
echo "LOOK AT THE MESH before believing any number above."
