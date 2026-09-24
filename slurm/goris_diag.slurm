#!/bin/bash
#SBATCH --job-name=goris-diag
#SBATCH --account=punim2657
#SBATCH --partition=gpu-a100
#SBATCH --gres=gpu:1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=02:30:00
#SBATCH --output=/data/gpfs/projects/punim2657/MILo/logs/goris_diag_%j.log

# Ticket gor-is-mesh/02 diagnostic: BOTH recon runs went log-silent near
# iter 4000 with the process alive until the wall (hang signature, not
# throughput, not crash, not OOM). This run caps at 4500 iters with
# unbuffered output, saves bracketing the stall, and repeating stack dumps
# every 10 min so the wedged op names itself.
#
# Separate model dir (output/goris_diag) — never touches goris_A03.
# Costs one 2.5h job, not another 12h wall.
#
# Usage:
#   ./scripts/remote/pull_and_sbatch.sh slurm/goris_diag.slurm

set -euo pipefail

MILO_ROOT=/data/gpfs/projects/punim2657/MILo
GORIS=$MILO_ROOT/gor-is
ENV_PREFIX=$MILO_ROOT/envs/milo
PKGS=$MILO_ROOT/goris_pkgs
DATA=$MILO_ROOT/data/goris_A03
OUT=$MILO_ROOT/output/goris_diag

echo "=== GOR-IS diag started $(date) on $(hostname) ==="
nvidia-smi | head -5 || true
cd "$GORIS" && git rev-parse HEAD

module purge
module load GCC/11.3.0 OpenMPI/4.1.4
module load CUDA/11.8.0
module load Miniforge3/24.7.1-2
module load OptiX/7.6.0
export CUDA_HOME="${EBROOTCUDA:?}"
export LD_LIBRARY_PATH="$CUDA_HOME/targets/x86_64-linux/lib:${LD_LIBRARY_PATH:-}"
export PYTHONNOUSERSITE=1
export TORCH_CUDA_ARCH_LIST="8.0;8.9;9.0"
export PYTHONPATH="$PKGS:${PYTHONPATH:-}"
export TORCH_HOME="$MILO_ROOT/goris_cache"
export XDG_CACHE_HOME="$MILO_ROOT/goris_cache"
export OMP_NUM_THREADS="${SLURM_CPUS_PER_TASK:-8}"

eval "$(conda shell.bash hook)"
conda activate "$ENV_PREFIX"

cd "$GORIS"
python -u "$MILO_ROOT/repo/scripts/goris_diag_train.py" ./train.py \
    -s "$DATA" -i images --random_background --resolution 2 --depth_ratio 0.0 \
    --eval --logger none -m "$OUT" \
    --iterations 4500 --save_iterations 3500 4000 4100 4200 4300 4400 \
    --checkpoint_iterations 4000

echo "=== GOR-IS diag finished $(date) ==="
