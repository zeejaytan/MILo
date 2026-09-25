#!/bin/bash
#SBATCH --job-name=goris-rloop
#SBATCH --account=punim2657
#SBATCH --partition=gpu-a100-short
#SBATCH --gres=gpu:1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=01:00:00
#SBATCH --output=/data/gpfs/projects/punim2657/MILo/logs/goris_rloop_%j.log

# Ticket gor-is-mesh/02 diagnostic, part 2b: the scheduled loop itself.
#
# Part 2a (probe 31278872) cleared all 24 views in ISOLATION, yet the diag
# run wedged inside training_report's sequential 26-view loop. This job
# renders that exact loop (21 test + 5 train-sample views, one process) on
# the probe's saved iter-2000 cloud under `timeout`: hang convicts
# accumulation across the loop; REPORTLOOP-OK clears the loop and points
# back at scene-instance nondeterminism.

set -euo pipefail

MILO_ROOT=/data/gpfs/projects/punim2657/MILo
GORIS=$MILO_ROOT/gor-is
ENV_PREFIX=$MILO_ROOT/envs/milo
PKGS=$MILO_ROOT/goris_pkgs
DATA=$MILO_ROOT/data/goris_A03
OUT=$MILO_ROOT/output/goris_probe

echo "=== GOR-IS report-loop probe started $(date) on $(hostname) ==="
[[ -f "$OUT/point_cloud/iteration_2000/point_cloud.ply" ]] || { echo "no probe cloud" >&2; exit 1; }

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

timeout 3000 python -u "$MILO_ROOT/repo/scripts/goris_probe_view.py" \
    -s "$DATA" -i images -m "$OUT" --eval --resolution 2 \
    --iteration 2000 --split report
code=$?
echo "exit=$code (124 = hung in the loop; 0 with REPORTLOOP-OK = loop clear)"
exit $code
