#!/bin/bash
#SBATCH --job-name=goris-diag2
#SBATCH --account=punim2657
#SBATCH --partition=gpu-a100-short
#SBATCH --gres=gpu:1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=02:00:00
#SBATCH --output=/data/gpfs/projects/punim2657/MILo/logs/goris_diag2_%j.log

# Ticket gor-is-mesh/02 diagnostic, part 3: time-vs-memory around iter 4000.
#
# Part 2 cleared views and loop; the report theory died with them (the
# reportless recon STILL wedged at ~4030, pace decaying 32->3 it/s across
# ~30 iters with stable point count — a progressive crawl, then stall).
# This wraps build_bvh/trace/reflect_trace with timing + allocated/reserved
# memory every 50 iters to 4100: climbing time at flat memory = compute
# pathology; climbing memory = leak (their gtracer fork is modified).
# No edits to their tree (monkeypatch in the wrapper).

set -euo pipefail

MILO_ROOT=/data/gpfs/projects/punim2657/MILo
GORIS=$MILO_ROOT/gor-is
ENV_PREFIX=$MILO_ROOT/envs/milo
PKGS=$MILO_ROOT/goris_pkgs
DATA=$MILO_ROOT/data/goris_A03
OUT=$MILO_ROOT/output/goris_diag2

echo "=== GOR-IS diag2 started $(date) on $(hostname) ==="
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
python -u "$MILO_ROOT/repo/scripts/goris_diag_timing.py" ./train.py \
    -s "$DATA" -i images --random_background --resolution 2 --depth_ratio 0.0 \
    --eval --logger none -m "$OUT" \
    --iterations 4100 --save_iterations 4000 4050 --test_iterations 100000

echo "=== GOR-IS diag2 finished $(date) ==="
