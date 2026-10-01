#!/bin/bash
#SBATCH --job-name=goris-tviews
#SBATCH --account=punim2657
#SBATCH --partition=gpu-a100-short
#SBATCH --gres=gpu:1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=02:00:00
#SBATCH --output=/data/gpfs/projects/punim2657/MILo/logs/goris_tviews_%j.log

# Ticket gor-is-mesh/02 diagnostic, part 2c: per-TRAIN-view trace probe.
#
# The 4060 pre-death cloud renders all 21 test views + report loop clean,
# yet training wedges in forward trace right after. Untested: the other
# ~138 train views on THIS scene state. Each view renders in its own
# process under `timeout`: exit 124 names a hanging view, anything else
# moves the wedge back into training dynamics (backward/optimizer).

set -euo pipefail

MILO_ROOT=/data/gpfs/projects/punim2657/MILo
GORIS=$MILO_ROOT/gor-is
ENV_PREFIX=$MILO_ROOT/envs/milo
PKGS=$MILO_ROOT/goris_pkgs
DATA=$MILO_ROOT/data/goris_A03
OUT=$MILO_ROOT/output/goris_A03
ITER=4060

echo "=== GOR-IS train-view probe started $(date) on $(hostname) ==="
[[ -f "$OUT/point_cloud/iteration_$ITER/point_cloud.ply" ]] || { echo "no cloud" >&2; exit 1; }

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

PROBE="$MILO_ROOT/repo/scripts/goris_probe_view.py"
PASS=0; BAD=0; FAILED=""
while read -r v; do
    name="${v%.*}"
    out=$(timeout 120 python -u "$PROBE" -s "$DATA" -i images -m "$OUT" \
        --eval --resolution 2 --iteration "$ITER" --view "$name" --split train 2>&1)
    code=$?
    if [[ $code -eq 0 ]] && echo "$out" | grep -q "^OK"; then
        PASS=$((PASS + 1))
    elif [[ $code -eq 124 ]]; then
        echo "HANG view=$name split=train (killed at 120s)"
        BAD=$((BAD + 1)); FAILED="$FAILED $name(hang)"
    else
        echo "ERROR view=$name split=train rc=$code :: $(echo "$out" | grep -E "Error|error" | head -1)"
        BAD=$((BAD + 1)); FAILED="$FAILED $name(err$code)"
    fi
done < "$DATA/train_list.txt"
echo "train views: pass=$PASS bad=$BAD ::$FAILED"
echo "=== GOR-IS train-view probe finished $(date) ==="
