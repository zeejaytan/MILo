#!/bin/bash
#SBATCH --job-name=goris-resume
#SBATCH --account=punim2657
#SBATCH --partition=gpu-a100
#SBATCH --gres=gpu:1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=128G
#SBATCH --time=12:00:00
#SBATCH --output=/data/gpfs/projects/punim2657/MILo/logs/goris_resume_%j.log

# Ticket gor-is-mesh/02: checkpoint-resume leg.
#
# Takes CHKPNT (iteration number present as chkpnt<CHKPNT>.pth) and TARGET
# (final iteration) as sbatch args. Saves clouds + checkpoints every 1000
# above CHKPNT so no wedge can cost more than ~1000 iters. Report loop stays
# off (--test_iterations 100000); scoring is post-hoc (ticket 04).
#
# Usage:
#   sbatch slurm/goris_resume.slurm 4000 15000

set -euo pipefail

MILO_ROOT=/data/gpfs/projects/punim2657/MILo
GORIS=$MILO_ROOT/gor-is
ENV_PREFIX=$MILO_ROOT/envs/milo
PKGS=$MILO_ROOT/goris_pkgs
DATA=$MILO_ROOT/data/goris_A03
OUT=$MILO_ROOT/output/goris_A03
FROM="${1:?need checkpoint iter}"; TO="${2:?need target iter}"
CHK="$OUT/chkpnt$FROM.pth"

echo "=== GOR-IS resume $FROM -> $TO started $(date) on $(hostname) ==="
nvidia-smi | head -5 || true
cd "$GORIS" && git rev-parse HEAD
[[ -f "$CHK" ]] || { echo "no $CHK" >&2; exit 1; }

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

SAVES=$(seq $((FROM + 1000)) 1000 $TO | tr '\n' ' ')
cd "$GORIS"
python -u "$MILO_ROOT/repo/scripts/goris_diag_train.py" ./train.py \
    -s "$DATA" -i images --random_background --resolution 2 --depth_ratio 0.0 \
    --eval --logger none -m "$OUT" --iterations "$TO" --test_iterations 100000 \
    --save_iterations $SAVES --checkpoint_iterations $SAVES \
    --start_checkpoint "$CHK"

echo "=== GOR-IS resume $FROM -> $TO finished $(date) ==="
