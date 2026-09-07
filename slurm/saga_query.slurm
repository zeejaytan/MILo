#!/bin/bash
#SBATCH --job-name=saga-query
#SBATCH --account=punim2657
#SBATCH --partition=gpu-a100-short
#SBATCH --gres=gpu:1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=01:00:00
#SBATCH --output=/data/gpfs/projects/punim2657/MILo/logs/saga_query_%j.log

# Ticket alt-09: SAGA post-hoc filter, stage 2 — headless mask-prompt query.
#
# GPU leg only (renders + cosine sims + keep sets + overlays). Fusion rides a
# separate CPU job after the overlays have been looked at — never fuse blind.
# Primary threshold prespecified: 0.6 (see scripts/saga_mask_query.py).
#
# Usage:
#   ./scripts/remote/pull_and_sbatch.sh slurm/saga_query.slurm

set -euo pipefail

SAGA_ROOT=/data/gpfs/projects/punim2657/saga
MILO_ROOT=/data/gpfs/projects/punim2657/MILo
REPO_DIR=$MILO_ROOT/repo
ENV_PREFIX=$MILO_ROOT/envs/saga
SRC_DIR=$MILO_ROOT/saga_data/A03
MODEL_DIR=$MILO_ROOT/output/saga_A03
OUT_DIR=$MODEL_DIR/query

echo "=== SAGA query started $(date) on $(hostname) ==="
nvidia-smi | head -5 || true

[[ -f "$MODEL_DIR/point_cloud/iteration_10000/contrastive_feature_point_cloud.ply" ]] || {
    echo "No trained features — run slurm/saga_train.slurm first" >&2; exit 1; }
cd "$SAGA_ROOT" && git rev-parse HEAD

module purge
module load GCC/11.3.0 OpenMPI/4.1.4
module load CUDA/11.8.0
module load Miniforge3/24.7.1-2
export CUDA_HOME="${EBROOTCUDA:?}"
export LD_LIBRARY_PATH="$CUDA_HOME/targets/x86_64-linux/lib:${LD_LIBRARY_PATH:-}"
export PYTHONNOUSERSITE=1
export OMP_NUM_THREADS="${SLURM_CPUS_PER_TASK:-8}"

eval "$(conda shell.bash hook)"
conda activate "$ENV_PREFIX"

mkdir -p "$OUT_DIR"
python -u "$REPO_DIR/scripts/saga_mask_query.py" \
    --saga_root "$SAGA_ROOT" --src "$SRC_DIR" --model "$MODEL_DIR" \
    --out "$OUT_DIR" 2>&1 | tee "$OUT_DIR/log_query.txt"

[[ -f "$OUT_DIR/query_report.json" ]] || { echo "query wrote no report" >&2; exit 1; }
echo "=== finished $(date) ==="
echo "Look at $OUT_DIR/overlay_*.png before any fusion."
