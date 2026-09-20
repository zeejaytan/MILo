#!/bin/bash
#SBATCH --job-name=goris-inpaint
#SBATCH --account=punim2657
#SBATCH --partition=gpu-a100
#SBATCH --gres=gpu:1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=128G
#SBATCH --time=24:00:00
#SBATCH --output=/data/gpfs/projects/punim2657/MILo/logs/goris_inpaint_%j.log

# Ticket gor-is-mesh/02, stage B: 2D inpaint -> 3D inpaint -> rig-free render.
#
# Requires stage A (goris_recon): iteration_30000 cloud + removal/ renders.
# Fails fast if those are absent. Direct script calls (NOT launcher.py):
# launcher hardcodes --resolution 512/4; full resolution is --resolution 1.
# --eval honours our 143/21 lists; --logger none; LaMa weights pre-fetched
# (TORCH_HOME below; compute nodes offline).
#
# This is the heavyweight: 143 views x 7 maps of LaMa, then 4000 iters of
# warp+LaMa+LPIPS optimisation. If the partition rejects 24h, split 2D/3D.
#
# Usage (only after recon COMPLETED):
#   ./scripts/remote/pull_and_sbatch.sh slurm/goris_inpaint.slurm

set -euo pipefail

MILO_ROOT=/data/gpfs/projects/punim2657/MILo
GORIS=$MILO_ROOT/gor-is
ENV_PREFIX=$MILO_ROOT/envs/milo
PKGS=$MILO_ROOT/goris_pkgs
DATA=$MILO_ROOT/data/goris_A03
OUT=$MILO_ROOT/output/goris_A03

echo "=== GOR-IS inpaint started $(date) on $(hostname) ==="
nvidia-smi | head -8 || true
cd "$GORIS" && git rev-parse HEAD
[[ -f "$OUT/point_cloud/iteration_30000/point_cloud.ply" ]] || { echo "no 30k cloud — run goris_recon first" >&2; exit 1; }
[[ -d "$OUT/train/ours_30000/removal" ]] || { echo "no removal/ renders — run goris_recon first" >&2; exit 1; }

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
COMMON="-s $DATA -i images --random_background --resolution 1 --depth_ratio 0.0"

echo "--- inpainting2D (LaMa fill of 7 maps x 143 views) ---"
python inpainting2D.py --eval --iteration 30000 -s "$DATA" -m "$OUT" -i images --resolution 1

echo "--- inpainting3D (30000 -> 34000, material + reflection-mask) ---"
python inpainting3D.py $COMMON --eval --logger none -m "$OUT" --iterations 34000 --load_inpainted --use_material_inpainting --use_reflection_mask --densify_until_iter 32000 --densify_from_iter 30500

echo "--- render_inpainting3D (rig-free views, no mesh) ---"
python render.py $COMMON --iteration 34000 -m "$OUT" --use_pbr --skip_mesh --skip_train --is_removal

echo "--- density census ---"
OUT="$OUT" python - <<'PY'
import glob, os
from plyfile import PlyData
plys = sorted(glob.glob(os.environ["OUT"] + "/point_cloud/iteration_34000/*.ply"))
for p in plys:
    print(f"{os.path.basename(p)}: {PlyData.read(p)['vertex'].count} points")
PY

echo "=== GOR-IS inpaint finished $(date) ==="
