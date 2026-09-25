#!/bin/bash
#SBATCH --job-name=goris-recon1
#SBATCH --account=punim2657
#SBATCH --partition=gpu-a100
#SBATCH --gres=gpu:1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=128G
#SBATCH --time=12:00:00
#SBATCH --output=/data/gpfs/projects/punim2657/MILo/logs/goris_recon_%j.log

# Ticket gor-is-mesh/02, stage A: recon + removal + eval on A03.
#
# Pinned gor-is@eb36acc, reused envs/milo + goris_pkgs sidecar (ticket 01).
# Direct train.py/render.py calls, NOT launcher.py: launcher hardcodes
# --resolution 512/4 and --skip_mesh on the removal render. Full resolution
# is --resolution 1 explicit (default -1 would halve 3200px to 1600);
# --eval honours our train/test lists (143/21); --logger none (log_utils
# tolerates missing wandb/tensorboard).
#
# Usage:
#   ./scripts/remote/pull_and_sbatch.sh slurm/goris_recon.slurm

set -euo pipefail

MILO_ROOT=/data/gpfs/projects/punim2657/MILo
GORIS=$MILO_ROOT/gor-is
ENV_PREFIX=$MILO_ROOT/envs/milo
PKGS=$MILO_ROOT/goris_pkgs
DATA=$MILO_ROOT/data/goris_A03
OUT=$MILO_ROOT/output/goris_A03

echo "=== GOR-IS recon started $(date) on $(hostname) ==="
nvidia-smi | head -8 || true
cd "$GORIS" && git rev-parse HEAD
[[ -d "$DATA/images" ]] || { echo "no dataset at $DATA" >&2; exit 1; }
[[ -d "$DATA/object_mask" ]] || { echo "no object masks" >&2; exit 1; }

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
# LaMa weights pre-fetched to project disk (compute nodes offline).
export TORCH_HOME="$MILO_ROOT/goris_cache"
export XDG_CACHE_HOME="$MILO_ROOT/goris_cache"
export OMP_NUM_THREADS="${SLURM_CPUS_PER_TASK:-8}"

eval "$(conda shell.bash hook)"
conda activate "$ENV_PREFIX"
python -c "import torch; assert torch.cuda.is_available(); print('torch', torch.__version__, 'gpu ok')"

cd "$GORIS"
# 2026-09-21 decision (user): full-res recon runs ~10s/iter (ray-traced
# lighting at 3200px) — 30k iters ≈ 80 GPU-hours, far past one 12h job and
# past sense for this trial. --resolution 2 (1600px, 0.42mm/px) still
# oversamples the ~1mm break-face grain 2.4x. Two chained legs via
# --start_checkpoint; leg 2 covers the second half. Recorded in ticket 02.
COMMON="-s $DATA -i images --random_background --resolution 2 --depth_ratio 0.0"
TRAIN="$COMMON --eval --logger none"

echo "--- recon leg 1 (0 -> 15000 iters) ---"
# 2026-09-25 diagnostic series (31201057/31276683/31278872/31279727):
# - every view traces clean in isolation (24/24) and in one sequential loop
#   (REPORTLOOP-OK); all 164 poses finite. No killer view, no killer loop.
# - wedges strike inside training_report's scheduled test-set renders at
#   some report (2000 in diag, 4000 in both recons), scene-state-dependent.
# The report mutates nothing (@torch.no_grad): disable it in-training
# (--test_iterations 100000) and evaluate post-hoc with the proven harness.
# Faulthandler wrapper names the op if the main loop ever wedges instead.
python -u "$MILO_ROOT/repo/scripts/goris_diag_train.py" ./train.py \
    $TRAIN -m "$OUT" --iterations 15000 --test_iterations 100000 \
    --save_iterations 5000 10000 15000 --checkpoint_iterations 15000

echo "--- density census leg 1 (M5/M6 drain tripwire: ~90% loss stops the route) ---"
OUT="$OUT" python - <<'PY'
import glob, os
from plyfile import PlyData
plys = sorted(glob.glob(os.environ["OUT"] + "/point_cloud/iteration_15000/*.ply"))
for p in plys:
    print(f"{os.path.basename(p)}: {PlyData.read(p)['vertex'].count} points")
PY

echo "=== GOR-IS recon leg 1 finished $(date) ==="
echo "NEXT: leg 2 = train --start_checkpoint chkpnt15000.pth to 30000, then remove_object + metrics."
