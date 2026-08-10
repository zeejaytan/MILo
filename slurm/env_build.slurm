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
# This does NOT use the repo's install.py. That script drives everything through
# os.system() and never checks a return code, so when its first step failed (job
# 28888989) it printed "[INFO] ... installed." for all nine remaining steps and exited 0.
# The failure only surfaced in the smoke test. Each step below is checked.
#
# Four things differ from the upstream README, each of which broke the first attempt:
#
#   1. conda's pytorch-cuda=11.8 is no longer installable. The nvidia channel has moved
#      on and the solver cannot satisfy it against this driver:
#        "pytorch-cuda 11.8 is not installable because there are no viable options".
#      Torch comes from the PyTorch cu118 wheel index instead — same version, same CUDA.
#   2. The README exports /usr/local/cuda-11.8 paths. That directory does not exist here;
#      CUDA comes from the module system as $EBROOTCUDA.
#   3. ~/.local/lib/python3.9/site-packages leaks into the environment (the first attempt
#      picked scipy up from there, alongside a corrupt "-ympy" distribution).
#      PYTHONNOUSERSITE keeps the environment self-contained.
#   4. Installing CGAL pulls numpy 2.x, which torch 2.3.1 was not built against. numpy is
#      pinned below 2 at the end, after everything that might drag it forward.
#
# nvdiffrast must use its CUDA rasteriser: compute nodes are headless and an OpenGL
# context cannot be created. The smoke test checks that specifically.

MILO_ROOT=/data/gpfs/projects/punim2657/MILo
REPO_DIR=$MILO_ROOT/repo
ENV_PREFIX=$MILO_ROOT/envs/milo

echo "=== MILo environment build started $(date) on $(hostname) ==="
nvidia-smi | head -15 || true

module purge
module load GCC/11.3.0 OpenMPI/4.1.4
module load CUDA/11.8.0
module load Miniforge3/24.7.1-2

export CUDA_HOME="${EBROOTCUDA:?CUDA module did not set EBROOTCUDA}"
export CPATH="$CUDA_HOME/targets/x86_64-linux/include:${CPATH:-}"
export LD_LIBRARY_PATH="$CUDA_HOME/targets/x86_64-linux/lib:${LD_LIBRARY_PATH:-}"
export PATH="$CUDA_HOME/bin:$PATH"
# Keep ~/.local out of this environment entirely.
export PYTHONNOUSERSITE=1
# Compile for the GPUs actually in this cluster: A100 (8.0), L40S/H100 (8.9, 9.0).
export TORCH_CUDA_ARCH_LIST="${TORCH_CUDA_ARCH_LIST:-8.0;8.9;9.0}"

echo "CUDA_HOME=$CUDA_HOME"
nvcc --version | tail -2

eval "$(conda shell.bash hook)"

if [[ "${REBUILD:-0}" == "1" && -d "$ENV_PREFIX" ]]; then
    echo "REBUILD=1 — removing $ENV_PREFIX"
    conda env remove -y -p "$ENV_PREFIX" || rm -rf "$ENV_PREFIX"
fi
if [[ ! -d "$ENV_PREFIX" ]]; then
    conda create -y -p "$ENV_PREFIX" python=3.9
fi
conda activate "$ENV_PREFIX"
echo "python: $(which python)"

cd "$REPO_DIR"

step() { echo; echo "=== $* ==="; }

# CGAL/GMP/cmake first: they are the packages that drag numpy around, so let conda have
# its way before torch is installed rather than after.
#
# cmake is pinned below 4. conda-forge's current default is 4.4, which has removed
# compatibility with cmake_minimum_required(VERSION <3.5), and the pybind11 that
# tetra_triangulation fetches still declares one. That is what stopped job 28891642:
#   "CMake Error at _deps/pybind11-src/CMakeLists.txt:8: Compatibility with
#    CMake < 3.5 has been removed from CMake."
step "CGAL, GMP, cmake (conda-forge)"
conda install -y -c conda-forge "cmake<4" gmp cgal
cmake --version | head -1

step "torch 2.3.1 + cu118 (pip wheels, not conda)"
pip install --no-cache-dir \
    torch==2.3.1 torchvision==0.18.1 torchaudio==2.3.1 \
    --index-url https://download.pytorch.org/whl/cu118
python -c "import torch; print('torch', torch.__version__, 'cuda', torch.version.cuda)"

step "MILo requirements"
pip install --no-cache-dir -r requirements.txt

step "Gaussian rasterisers and utilities"
for mod in diff-gaussian-rasterization_ms diff-gaussian-rasterization \
           diff-gaussian-rasterization_gof simple-knn fused-ssim; do
    echo "--- submodules/$mod"
    pip install --no-cache-dir "submodules/$mod"
done

step "tetra_triangulation (Delaunay, from Tetra-NeRF)"
(
    cd submodules/tetra_triangulation
    # cmake finds torch through python; CUDA through the exports above.
    # CMAKE_POLICY_VERSION_MINIMUM is a no-op on cmake 3.x (just an unused-variable
    # warning) and keeps this working if the pin above ever slips to cmake 4.
    cmake . \
        -DCMAKE_PREFIX_PATH="$(python -c 'import torch,os;print(os.path.dirname(torch.__file__))')" \
        -DCMAKE_POLICY_VERSION_MINIMUM=3.5
    make -j"${SLURM_CPUS_PER_TASK:-8}"
    pip install --no-cache-dir -e .
)

step "nvdiffrast"
pip install --no-cache-dir -e submodules/nvdiffrast

step "comparison-script dependencies"
pip install --no-cache-dir "scipy>=1.10,<1.14" "pandas>=2.0,<2.3"

# Last, so nothing above can drag numpy forward again. torch 2.3.1 predates numpy 2.
step "pin numpy below 2"
pip install --no-cache-dir "numpy<2"

step "smoke test"
python - <<'PY'
import sys
import numpy as np
import torch

print("numpy", np.__version__)
print("torch", torch.__version__, "| cuda", torch.version.cuda,
      "| gpu visible:", torch.cuda.is_available())
if np.__version__.startswith("2."):
    sys.exit("numpy 2.x with torch 2.3.1 — the pin did not hold")
if not torch.cuda.is_available():
    sys.exit("no GPU visible to torch — the compiled extensions cannot be trusted")

failures = []

# The Delaunay triangulation MILo extracts its mesh through.
try:
    import tetranerf.utils.extension as tetra  # noqa: F401
    print("tetra_triangulation: ok")
except Exception as exc:
    failures.append(f"tetra_triangulation: {exc}")

# The rasterisers train.py selects between, plus the loss and kNN helpers.
for mod in ("diff_gaussian_rasterization", "diff_gaussian_rasterization_ms",
            "fused_ssim", "simple_knn"):
    try:
        __import__(mod)
        print(f"{mod}: ok")
    except Exception as exc:
        failures.append(f"{mod}: {exc}")

# Headless rasterisation. A GL context would fail on a compute node; the CUDA context is
# the one that must work. Rasterise a triangle rather than merely importing.
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

# Used by the adapter and the comparison.
for mod in ("trimesh", "scipy", "PIL", "open3d"):
    try:
        __import__(mod)
        print(f"{mod}: ok")
    except Exception as exc:
        failures.append(f"{mod}: {exc}")

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
