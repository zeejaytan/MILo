#!/usr/bin/env bash
# Score the four A02 meshes against held-out photographs -- SHERDS ONLY.
#
# WHY A SHELL WRAPPER AND NOT JUST THE PYTHON. nvdiffrast does not ship a binary: it
# JIT-compiles a CUDA plugin on first use, so it needs a real toolkit at run time, not
# just a working torch. Without CUDA_HOME it fails at RasterizeCudaContext() with
#   OSError: CUDA_HOME environment variable is not set
# while torch.cuda.is_available() reports True and the GPU name prints fine. The
# misleading part is that everything looks healthy right up to the raster call.
#
# CUDA/11.8.0 specifically: this environment's torch is 2.3.1+cu118, and a toolkit from
# a different major version would build a plugin that will not load against it.
#
# Runs under the held allocation as
#   ./scripts/gpu_session.sh run ./scripts/run_silhouette_A02.sh
# and is equally valid inside an sbatch script, which is why the env setup lives here
# rather than in a job file.
set -euo pipefail

MILO_ROOT=/data/gpfs/projects/punim2657/MILo
REPO_DIR="$MILO_ROOT/repo"
ENV_PREFIX="$MILO_ROOT/envs/milo"
WORK=/data/gpfs/projects/punim2657/Rabati2025/17062025/A02/work_colmap_openmvs
DENSE="$WORK/dense_masked"
MASKS="${MASKS:-$MILO_ROOT/masks_A02_und_sherds/colmap}"
CAPTURE="$MILO_ROOT/data/17062025/A02/capture.json"
OUT="${OUT:-$MILO_ROOT/output/17062025/A02/silhouette_sherds}"

module purge
module load GCC/11.3.0 OpenMPI/4.1.4
module load CUDA/11.8.0
module load Miniforge3/24.7.1-2
export CUDA_HOME="${EBROOTCUDA:?CUDA module did not set EBROOTCUDA}"
export LD_LIBRARY_PATH="$CUDA_HOME/targets/x86_64-linux/lib:${LD_LIBRARY_PATH:-}"

eval "$(conda shell.bash hook)"
conda activate "$ENV_PREFIX"

echo "=== silhouette comparison, A02 SHERDS ONLY, $(date) on $(hostname) ==="
echo "  CUDA_HOME=$CUDA_HOME"
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader || true

# The UNSCALED meshes. The *_mm.ply copies have been multiplied by mm-per-unit and no
# longer sit in the cameras' frame; rendering one of those produces a confident number
# that means nothing. silhouette_compare.py also warns if the extents disagree.
cd "$REPO_DIR"
python scripts/silhouette_compare.py \
    --dense   "$DENSE" \
    --masks   "$MASKS" \
    --capture "$CAPTURE" \
    --out     "$OUT" \
    --mesh openmvs="$DENSE/scene_refined_mesh.ply" \
    --mesh delaunay="$DENSE/colmap_delaunay_mesh.ply" \
    --mesh poisson="$DENSE/colmap_poisson_mesh.ply" \
    --mesh milo="$MILO_ROOT/output/17062025/A02/mesh_learnable_sdf.ply" \
    --boxes "$REPO_DIR/scripts/A02_sherd_boxes.json"
