#!/bin/bash
#SBATCH --job-name=goris-sample
#SBATCH --account=punim2657
#SBATCH --partition=gpu-a100
#SBATCH --gres=gpu:1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=06:00:00
#SBATCH --output=/data/gpfs/projects/punim2657/MILo/logs/goris_sample_%j.log

# Ticket gor-is-mesh/02: POSITIVE CONTROL. Authors' own synthetic scene 1
# with THEIR settings (launcher: RES=512, 30k recon). Paper expects ~1.5h
# total on a 3090 at 512px.
#
# Settles env-vs-material: COMPLETED past iter 4000 here proves the stack
# (env + sidecar + OptiX fork) trains their data, and our wedge is
# material/data-specific. A wedge HERE instead clears the material verdict
# and convicts the environment/fork.
#
# Usage:
#   ./scripts/remote/pull_and_sbatch.sh slurm/goris_sample.slurm

set -euo pipefail

MILO_ROOT=/data/gpfs/projects/punim2657/MILo
GORIS=$MILO_ROOT/gor-is
ENV_PREFIX=$MILO_ROOT/envs/milo
PKGS=$MILO_ROOT/goris_pkgs
DATA=$MILO_ROOT/data/goris_sample/scene_1_colmap
OUT=$MILO_ROOT/output/goris_sample

echo "=== GOR-IS sample baseline started $(date) on $(hostname) ==="
nvidia-smi | head -5 || true
cd "$GORIS" && git rev-parse HEAD
[[ -f "$DATA/train_list.txt" ]] || { echo "no sample dataset at $DATA" >&2; exit 1; }

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
    --iterations 30000 --test_iterations 100000 \
    --save_iterations 5000 10000 15000 20000 25000 \
    --checkpoint_iterations 15000

echo "=== GOR-IS sample baseline finished $(date) ==="
