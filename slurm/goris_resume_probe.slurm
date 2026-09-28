#!/bin/bash
#SBATCH --job-name=goris-rsprobe
#SBATCH --account=punim2657
#SBATCH --partition=gpu-a100
#SBATCH --gres=gpu:1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=04:00:00
#SBATCH --output=/data/gpfs/projects/punim2657/MILo/logs/goris_rsprobe_%j.log

# Ticket gor-is-mesh/02, autopsy resume 4000 -> 4100.
#
# Evidence so far (job 31335532): healthy to the 4000 densify at 29 it/s,
# then pace decay to ~3 it/s and a CUDA illegal-memory-access surfacing at
# traced_color[valid_mask] = outputs["color"] (async — true culprit is an
# earlier kernel). Saved chkpnt3000/chkpnt4000 are fully finite on CPU
# (35,756 -> 26,582 points, zero non-finite), so the poison appears AFTER
# 4000 with no save to catch it — loss and counts show no spike.
#
# This run resumes from chkpnt4000 with synchronous launches (names the real
# faulting kernel) and saves every 10 iters, so the pre-death cloud exists
# for CPU NaN autopsy whatever happens.

set -euo pipefail

MILO_ROOT=/data/gpfs/projects/punim2657/MILo
GORIS=$MILO_ROOT/gor-is
ENV_PREFIX=$MILO_ROOT/envs/milo
PKGS=$MILO_ROOT/goris_pkgs
DATA=$MILO_ROOT/data/goris_A03
OUT=$MILO_ROOT/output/goris_A03
CHK=$OUT/chkpnt4000.pth

echo "=== GOR-IS resume-autopsy started $(date) on $(hostname) ==="
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
export CUDA_LAUNCH_BLOCKING=1

eval "$(conda shell.bash hook)"
conda activate "$ENV_PREFIX"

cd "$GORIS"
python -u "$MILO_ROOT/repo/scripts/goris_diag_train.py" ./train.py \
    -s "$DATA" -i images --random_background --resolution 2 --depth_ratio 0.0 \
    --eval --logger none -m "$OUT" --iterations 4100 --test_iterations 100000 \
    --save_iterations 4010 4020 4030 4040 4050 4060 4070 4080 4090 \
    --checkpoint_iterations 4060 --start_checkpoint "$CHK"

echo "=== GOR-IS resume-autopsy finished $(date) ==="
