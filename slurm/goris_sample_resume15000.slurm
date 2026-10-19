#!/bin/bash
#SBATCH --job-name=goris-sample-resume
#SBATCH --account=punim2657
#SBATCH --partition=gpu-a100
#SBATCH --gres=gpu:1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=01:00:00
#SBATCH --output=/data/gpfs/projects/punim2657/MILo/logs/goris_sample_resume_%j.log

# Ticket gor-is-mesh/06: RESUME-WEDGE ISOLATION. Short resume of the sample
# positive control (job 33427213, COMPLETED 30000/30000) from chkpnt15000
# to 16000, asking whether ANY resume-from-checkpoint wedges on data known
# to train clean. Diagnose-only: no edits to the authors' tree, resume via
# --start_checkpoint only, minutes not hours.
#
# Verdict use: wedges on clean data => resume-path suspect (record, no
# patch); runs clean => resume-wedge is A03-data-specific.
#
# Usage (from the repo checkout on Spartan):
#   sbatch slurm/goris_sample_resume15000.slurm

set -euo pipefail

MILO_ROOT=/data/gpfs/projects/punim2657/MILo
GORIS=$MILO_ROOT/gor-is
ENV_PREFIX=$MILO_ROOT/envs/milo
PKGS=$MILO_ROOT/goris_pkgs
DATA=$MILO_ROOT/data/goris_sample/scene_1_colmap
OUT=$MILO_ROOT/output/goris_sample
CHK=$OUT/chkpnt15000.pth

echo "=== GOR-IS sample resume 15000 -> 16000 started $(date) on $(hostname) ==="
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

cd "$GORIS"
python -u "$MILO_ROOT/repo/scripts/goris_diag_train.py" ./train.py \
    -s "$DATA" -i images --random_background --resolution 512 \
    --depth_ratio 0.0 --eval --logger none -m "$OUT" \
    --iterations 16000 --test_iterations 100000 \
    --save_iterations 16000 \
    --checkpoint_iterations 16000 \
    --start_checkpoint "$CHK"

echo "=== GOR-IS sample resume 15000 -> 16000 finished $(date) ==="
