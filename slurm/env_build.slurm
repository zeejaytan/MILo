#!/bin/bash
#SBATCH --job-name=milo-env
#SBATCH --account=punim2657
#SBATCH --partition=gpu-a100-short
#SBATCH --gres=gpu:1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=03:00:00
#SBATCH --output=/data/gpfs/projects/punim2657/MILo/logs/milo_env_%j.log

set -euo pipefail

# Build the MILo conda environment.
#
# On a GPU node, not the login node and not a CPU node: every one of the six rasteriser
# submodules compiles CUDA kernels, and tetra_triangulation's cmake needs a working nvcc.
# Building where there is no GPU produces an environment that imports fine and then fails
# the first time it is asked to render anything.
#
# Two things differ from the upstream README and both will break the install if ignored:
#
#   1. The README exports /usr/local/cuda-11.8 paths. That directory does not exist on
#      Spartan; CUDA comes from the module system as $EBROOTCUDA.
#   2. nvdiffrast must use its CUDA rasteriser. Compute nodes are headless, so an OpenGL
#      context cannot be created. The smoke test at the end checks exactly this, because
#      the failure otherwise appears hours later inside a training run.

MILO_ROOT=/data/gpfs/projects/punim2657/MILo
REPO_DIR=$MILO_ROOT/repo
ENV_PREFIX=$MILO_ROOT/envs/milo

echo "=== MILo environment build started $(date) on $(hostname) ==="
nvidia-smi | head -15 || true

module purge
module load GCC/11.3.0 OpenMPI/4.1.4
module load CUDA/11.8.0
module load Miniforge3/24.7.1-2

# The README's CUDA paths, corrected for the module system.
export CUDA_HOME="${EBROOTCUDA:?CUDA module did not set EBROOTCUDA}"
export CPATH="$CUDA_HOME/targets/x86_64-linux/include:${CPATH:-}"
export LD_LIBRARY_PATH="$CUDA_HOME/targets/x86_64-linux/lib:${LD_LIBRARY_PATH:-}"
export PATH="$CUDA_HOME/bin:$PATH"
echo "CUDA_HOME=$CUDA_HOME"
nvcc --version | tail -2

eval "$(conda shell.bash hook)"

if [[ ! -d "$ENV_PREFIX" ]]; then
    conda create -y -p "$ENV_PREFIX" python=3.9
fi
conda activate "$ENV_PREFIX"

cd "$REPO_DIR"

# install.py drives conda/pip for torch, the requirements, the six vendored rasteriser
# and utility submodules, CGAL/GMP, tetra_triangulation and nvdiffrast.
python install.py --cuda_version 11.8

# Used by scripts/compare_meshes.py, not by MILo itself.
pip install "scipy>=1.10" "pandas>=2.0"

echo
echo "=== smoke test ==="
python - <<'PY'
import sys
import torch

print("torch", torch.__version__, "| cuda", torch.version.cuda,
      "| gpu visible:", torch.cuda.is_available())
if not torch.cuda.is_available():
    sys.exit("no GPU visible to torch — the compiled extensions cannot be trusted")

failures = []

# The Delaunay triangulation MILo extracts its mesh through.
try:
    import tetranerf.utils.extension as tetra  # noqa: F401
    print("tetra_triangulation: ok")
except Exception as exc:
    failures.append(f"tetra_triangulation: {exc}")

# The rasterisers train.py selects between.
for mod in ("diff_gaussian_rasterization", "diff_gaussian_rasterization_ms",
            "fused_ssim", "simple_knn"):
    try:
        __import__(mod)
        print(f"{mod}: ok")
    except Exception as exc:
        failures.append(f"{mod}: {exc}")

# Headless rasterisation. A GL context here would fail on a compute node; the CUDA
# context is the one that must work. Rasterise one triangle rather than just importing.
try:
    import nvdiffrast.torch as dr
    ctx = dr.RasterizeCudaContext()
    v = torch.tensor([[[-0.5, -0.5, 0.0, 1.0],
                       [ 0.5, -0.5, 0.0, 1.0],
                       [ 0.0,  0.5, 0.0, 1.0]]], device="cuda")
    f = torch.tensor([[0, 1, 2]], dtype=torch.int32, device="cuda")
    rast, _ = dr.rasterize(ctx, v, f, resolution=[64, 64])
    covered = int((rast[..., 3] > 0).sum())
    print(f"nvdiffrast CUDA context: ok ({covered} pixels covered)")
    if covered == 0:
        failures.append("nvdiffrast rasterised nothing — context is broken")
except Exception as exc:
    failures.append(f"nvdiffrast: {exc}")

if failures:
    print("\nFAILED:")
    for f_ in failures:
        print("  -", f_)
    sys.exit(1)
print("\nAll components present and working on the GPU.")
PY

echo
echo "=== MILo environment build finished $(date) ==="
echo "Activate with: conda activate $ENV_PREFIX"
