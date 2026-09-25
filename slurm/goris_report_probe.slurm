#!/bin/bash
#SBATCH --job-name=goris-probe
#SBATCH --account=punim2657
#SBATCH --partition=gpu-a100
#SBATCH --gres=gpu:1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=03:00:00
#SBATCH --output=/data/gpfs/projects/punim2657/MILo/logs/goris_probe_%j.log

# Ticket gor-is-mesh/02 diagnostic, part 2: WHICH view hangs the tracer.
#
# Part 1 (diag 31201057) proved the wedge: faulthandler stacks sit in
# reflect_trace->trace inside training_report's test-set render at iter 2000.
# Camera params for all 164 views check finite (pycolmap audit 2026-09-25),
# so it is not a corrupt pose — it is a view/scene interaction.
#
# This job retrains 0->2000 (minutes at 40it/s), saves, then renders test
# views ONE PROCESS EACH under `timeout`: a device hang kills only that
# view's probe. Train-view controls included (expect OK).
#
# Usage:
#   ./scripts/remote/pull_and_sbatch.sh slurm/goris_report_probe.slurm

set -euo pipefail

MILO_ROOT=/data/gpfs/projects/punim2657/MILo
GORIS=$MILO_ROOT/gor-is
ENV_PREFIX=$MILO_ROOT/envs/milo
PKGS=$MILO_ROOT/goris_pkgs
DATA=$MILO_ROOT/data/goris_A03
OUT=$MILO_ROOT/output/goris_probe

echo "=== GOR-IS report-probe started $(date) on $(hostname) ==="
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
echo "--- train 0 -> 2000 (fast) ---"
python -u train.py -s "$DATA" -i images --random_background --resolution 2 \
    --depth_ratio 0.0 --eval --logger none -m "$OUT" \
    --iterations 2000 --save_iterations 2000 --test_iterations 100000

echo "--- per-view trace probe (timeout 180 each) ---"
PROBE="$MILO_ROOT/repo/scripts/goris_probe_view.py"
PASS=0; HANG=0; FAILED=""
while read -r v; do
    name="${v%.*}"
    if timeout 180 python -u "$PROBE" -s "$DATA" -i images -m "$OUT" \
        --resolution 2 --iteration 2000 --view "$name" --split test; then
        PASS=$((PASS + 1))
    else
        code=$?
        if [[ $code -eq 124 ]]; then
            echo "HANG view=$name split=test (killed at 180s)"
            HANG=$((HANG + 1)); FAILED="$FAILED $name"
        else
            echo "ERROR view=$name split=test exit=$code"
            HANG=$((HANG + 1)); FAILED="$FAILED $name(err$code)"
        fi
    fi
done < "$DATA/test_list.txt"
echo "test views: pass=$PASS hang/fail=$HANG ::$FAILED"

for v in A31_1101 A31_1102 A31_1103; do
    timeout 180 python -u "$PROBE" -s "$DATA" -i images -m "$OUT" \
        --resolution 2 --iteration 2000 --view "$v" --split train \
        && echo "control $v OK" || echo "control $v NOT-OK"
done

echo "=== GOR-IS report-probe finished $(date) ==="
