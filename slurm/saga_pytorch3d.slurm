#!/bin/bash
#SBATCH --job-name=saga-p3d
#SBATCH --account=punim2657
#SBATCH --partition=gpu-a100
#SBATCH --gres=gpu:1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=03:00:00
#SBATCH --output=/data/gpfs/projects/punim2657/MILo/logs/saga_pytorch3d_%j.log

# Ticket alt-09: compile pytorch3d from source into envs/saga.
#
# No wheel exists for (py311, torch 2.3, cu118) — the dl.fbaipublicfiles
# per-combo pages for pyt230/pyt231 come back empty. Source build at the
# version matching our torch era (v0.7.6 <-> torch 2.3). Needed because
# scene/gaussian_model_ff.py imports pytorch3d.ops.knn_points at module top
# and the contrastive-feature render smooths through it (smooth_K=16).
#
# Usage:
#   ./scripts/remote/pull_and_sbatch.sh slurm/saga_pytorch3d.slurm
#
# Everything else in the env (torch, rasterizers, sklearn, hdbscan) was built
# on the login node; only this compile needs nvcc + a GPU node.

set -euo pipefail

ENV_PREFIX=/data/gpfs/projects/punim2657/MILo/envs/saga

echo "=== pytorch3d source build started $(date) on $(hostname) ==="
nvidia-smi | head -8 || true

module purge
module load GCC/11.3.0 OpenMPI/4.1.4
module load CUDA/11.8.0
module load Miniforge3/24.7.1-2
export CUDA_HOME="${EBROOTCUDA:?}"
export LD_LIBRARY_PATH="$CUDA_HOME/targets/x86_64-linux/lib:${LD_LIBRARY_PATH:-}"
export PATH="$CUDA_HOME/bin:$PATH"
export PYTHONNOUSERSITE=1
export TORCH_CUDA_ARCH_LIST="8.0;8.9;9.0"
export FORCE_CUDA=1
export MAX_JOBS="${SLURM_CPUS_PER_TASK:-8}"

nvcc --version | tail -1

eval "$(conda shell.bash hook)"
conda activate "$ENV_PREFIX"
python -c "import torch; print('torch', torch.__version__, '| gpu:', torch.cuda.is_available())"

pip install --no-cache-dir --no-build-isolation \
    "git+https://github.com/facebookresearch/pytorch3d.git@v0.7.6" 2>&1 | tail -2

python -c "import pytorch3d.ops; print('pytorch3d ok', pytorch3d.__version__)"
python -c "
import torch
x = torch.randn(2, 5, 3, device='cuda'); y = torch.randn(2, 8, 3, device='cuda')
import pytorch3d.ops as ops
d, i = ops.knn_points(x, y, K=2).dists, ops.knn_points(x, y, K=2).idx
print('knn_points on GPU ok', tuple(i.shape))"
echo "=== finished $(date) ==="
