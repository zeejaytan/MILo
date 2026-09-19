#!/bin/bash
#SBATCH --job-name=goris-smoke
#SBATCH --account=punim2657
#SBATCH --partition=gpu-a100-short
#SBATCH --gres=gpu:1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=01:00:00
#SBATCH --output=/data/gpfs/projects/punim2657/MILo/logs/goris_smoke_%j.log

# Ticket gor-is-mesh/01: reuse smoke test for GOR-IS on envs/milo.
#
# Reuses envs/milo (python 3.9, torch 2.3.1+cu118) untouched; additive
# sidecar $MILO_ROOT/goris_pkgs via `pip install --target` + PYTHONPATH.
# Proves `from scene.gaussian_model import GaussianModel` (top-level gtracer
# import) works on a GPU node before any training is ticketed.
#
# Usage:
#   ./scripts/remote/pull_and_sbatch.sh slurm/goris_smoke.slurm
#
# Exit non-zero on any failure; the log decides reuse vs fresh envs/goris.

set -euo pipefail

MILO_ROOT=/data/gpfs/projects/punim2657/MILo
GORIS=$MILO_ROOT/gor-is
ENV_PREFIX=$MILO_ROOT/envs/milo
PKGS=$MILO_ROOT/goris_pkgs

echo "=== GOR-IS reuse smoke started $(date) on $(hostname) ==="
nvidia-smi | head -8 || true
cd "$GORIS" && git rev-parse HEAD && git submodule status | head -5

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
# OptiX SDK for the gtracer build below.
export OPTIX_HOME="${EBROOTOPTIX:?OptiX module did not set EBROOTOPTIX}"
echo "OPTIX_HOME=$OPTIX_HOME"
ls "$OPTIX_HOME/include/optix.h" || { echo "no optix.h — stop"; exit 1; }

eval "$(conda shell.bash hook)"
conda activate "$ENV_PREFIX"
python -c "import sys; print('python', sys.version.split()[0])"
python -c "import torch; assert torch.cuda.is_available(); print('torch', torch.__version__, 'gpu ok')"

mkdir -p "$PKGS"

step() { echo; echo "=== $* ==="; }

# 2026-09-18 lesson (job 30715196 FAILED 1:0): plain `pip install --target`
# resolves dependencies from PyPI and drops torch 2.8.0 + numpy 2.0.2 into
# the sidecar, shadowing the env's torch 2.3.1 (PYTHONPATH is first) and
# breaking the env-built rasterizer with an undefined-symbol ImportError.
# --no-deps: the env already carries torch/numpy/PIL/cv2. If the sidecar
# ever gains a shadowing torch/numpy, wipe it and rebuild (rm -rf $PKGS).
step "gtracer (OptiX fork, pinned checkout) into sidecar"
if python -c "import sys; sys.path.insert(0, '$PKGS'); import gtracer" 2>/dev/null; then
    echo "gtracer already importable in sidecar — skipping rebuild"
else
    (
        cd "$GORIS/submodules/gtracer"
        rm -rf ./build && mkdir build && cd build && cmake .. && make -j"${SLURM_CPUS_PER_TASK:-8}" && cd ../
        pip install --no-cache-dir --no-deps --target="$PKGS" .
    )
fi

step "pure-python gaps: mediapy (render_utils) + lpips (inpainting3D)"
for pkg in mediapy lpips; do
    if python -c "import sys; sys.path.insert(0, '$PKGS'); import $pkg" 2>/dev/null; then
        echo "$pkg already present — skipping"
    else
        # --no-deps (30715196 lesson): env carries numpy/PIL/torch/torchvision.
        # wandb/tensorboard NOT needed: log_utils.py guards them in
        # try/except ImportError and --logger none returns before use.
        pip install --no-cache-dir --no-deps --target="$PKGS" "$pkg"
    fi
done
step "simple-lama-inpainting into sidecar (needed at ticket 02 inpainting3D)"
if python -c "import sys; sys.path.insert(0, '$PKGS'); import simple_lama_inpainting" 2>/dev/null; then
    echo "simple-lama already present — skipping"
else
    pip install --no-cache-dir --no-deps --target="$PKGS" simple-lama-inpainting
fi

step "vendored rasterizer into sidecar (recon 30753265 lesson)"
# GOR-IS's rasterizer is the depth&alpha fork (NamedTuple settings incl.
# require_depth); the env's vanilla build lacks it and train.py dies in
# build_rasterizer with TypeError. Same package name, so the sidecar build
# shadows the env's for GOR-IS jobs only; the env itself is untouched.
# 2026-09-19 lesson (recon 30753265): the fallthrough import check above
# is vacuous — the env's own build also carries a require_depth annotation
# (plus a require_coord GOR-IS never passes). Decide on directory presence.
if [[ -d "$PKGS/diff_gaussian_rasterization" ]]; then
    echo "vendored rasterizer already in sidecar — skipping rebuild"
else
    pip install --no-cache-dir --no-deps --target="$PKGS" "$GORIS/submodules/diff-gaussian-rasterization"
fi

step "guard: sidecar must not shadow env torch/numpy"
if [[ -e "$PKGS/torch" || -e "$PKGS/numpy" ]]; then
    echo "sidecar shadows torch/numpy — wipe and rebuild sidecar, then stop"
    ls "$PKGS" | head -20
    exit 1
fi

step "full GOR-IS import smoke (reused rasterizer + sidecar gtracer)"
export PYTHONPATH="$PKGS:${PYTHONPATH:-}"
python - <<'PY'
import torch
import diff_gaussian_rasterization, simple_knn
import nvdiffrast.torch as dr
from gtracer import GaussianTracer
print("rasterizer + nvdiffrast + gtracer: ok")
import sys
sys.path.insert(0, "/data/gpfs/projects/punim2657/MILo/gor-is")
from scene.gaussian_model import GaussianModel
import gaussian_renderer
print("scene.gaussian_model + gaussian_renderer: ok")
import mediapy, lpips, simple_lama_inpainting
print("mediapy + lpips + simple-lama (import only): ok")
print("torch", torch.__version__, "| cuda gpu:", torch.cuda.is_available())
PY

echo
echo "=== GOR-IS reuse smoke finished $(date): envs/milo + sidecar works ==="
