#!/bin/bash
#SBATCH --job-name=goris-t07clean
#SBATCH --account=punim2657
#SBATCH --partition=gpu-a100
#SBATCH --gres=gpu:1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=128G
#SBATCH --time=24:00:00
#SBATCH --output=/data/gpfs/projects/punim2657/MILo/logs/goris_t07clean_%j.log

# Ticket gor-is-mesh/07: minimal wedge repro — CLEAN leg (8 neighbours only).
#
# Trains from scratch on the 8 frame-adjacent neighbours only
# (data/goris_A03_t07clean/train_list.txt) — matched control: if the wedge
# leg stalls and this sails past 5000, the trigger is in the 4 killers.
# Settings mirror the wedging recon (ticket 02): --resolution 2,
# --depth_ratio 0.0, --random_background, --eval, --logger none.
# --test_iterations 100000 disables in-training test renders (report theory
# is dead; the wedge strikes without reports). Faulthandler wrapper names
# the op on a wedge. Runs to 6000: past 5000 clean = NO-REPRO (ticket bar).
# Saves+chkpnts every 1000 (first save ~3h, inside the wall).
#
# Usage:
#   ./scripts/remote/pull_and_sbatch.sh slurm/goris_t07clean.slurm

set -euo pipefail

MILO_ROOT=/data/gpfs/projects/punim2657/MILo
GORIS=$MILO_ROOT/gor-is
ENV_PREFIX=$MILO_ROOT/envs/milo
PKGS=$MILO_ROOT/goris_pkgs
DATA=$MILO_ROOT/data/goris_A03_t07clean
OUT=$MILO_ROOT/output/goris_t07clean

echo "=== GOR-IS T07 clean leg started $(date) on $(hostname) ==="
nvidia-smi | head -8 || true
cd "$GORIS" && git rev-parse HEAD
[[ -f "$DATA/train_list.txt" ]] || { echo "no subset lists at $DATA" >&2; exit 1; }
wc -l "$DATA/train_list.txt" "$DATA/test_list.txt"

module purge
module load GCC/11.3.0 OpenMPI/4.1.4
module load CUDA/11.8.0
module load Miniforge3/24.7.1-2
module load OptiX/7.6.0
export CUDA_HOME="${EBROOTCUDA:?}"
export CPATH="$CUDA_HOME/targets/x86_64-linux/include:${CPATH:-}"
export LD_LIBRARY_PATH="$CUDA_HOME/targets/x86_64-linux/lib:${LD_LIBRARY_PATH:-}"
export PATH="$CUDA_HOME/bin:$PATH"
export PYTHONNOUSERSITE=1
export TORCH_CUDA_ARCH_LIST="8.0;8.9;9.0"
export PYTHONPATH="$PKGS:${PYTHONPATH:-}"
export TORCH_HOME="$MILO_ROOT/goris_cache"
export XDG_CACHE_HOME="$MILO_ROOT/goris_cache"
export OMP_NUM_THREADS="${SLURM_CPUS_PER_TASK:-8}"

eval "$(conda shell.bash hook)"
conda activate "$ENV_PREFIX"
python -c "import torch; assert torch.cuda.is_available(); print('torch', torch.__version__, 'gpu ok')"

cd "$GORIS"
python -u "$MILO_ROOT/repo/scripts/goris_diag_train.py" ./train.py \
    -s "$DATA" -i images --random_background --resolution 2 --depth_ratio 0.0 \
    --eval --logger none -m "$OUT" \
    --iterations 6000 --test_iterations 100000 \
    --save_iterations $(seq 1000 1000 6000) \
    --checkpoint_iterations $(seq 1000 1000 6000)

echo "=== GOR-IS T07 clean leg finished $(date) ==="
