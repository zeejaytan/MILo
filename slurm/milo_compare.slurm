#!/bin/bash
#SBATCH --job-name=milo-compare
#SBATCH --account=punim2657
#SBATCH --partition=gpu-a100-short
#SBATCH --gres=gpu:1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=128G
#SBATCH --time=02:00:00
#SBATCH --output=/data/gpfs/projects/punim2657/MILo/logs/milo_compare_%j.log

set -euo pipefail

# Compare the MILo mesh with the OpenMVS mesh for one capture.
#
# Usage:
#   ./scripts/remote/pull_and_sbatch.sh slurm/milo_compare.slurm 16062025 [openmvs-mesh.ply]
#
# Needs a GPU: the silhouette comparison and the raking-light renders both go through
# nvdiffrast.

CAPTURE="${1:?usage: sbatch milo_compare.slurm <capture> [openmvs-mesh]}"
OPENMVS_MESH="${2:-}"

MILO_ROOT=/data/gpfs/projects/punim2657/MILo
REPO_DIR=$MILO_ROOT/repo
ENV_PREFIX=$MILO_ROOT/envs/milo
DATA_DIR=$MILO_ROOT/data/$CAPTURE
OUT_DIR=$MILO_ROOT/output/$CAPTURE

echo "=== comparison for $CAPTURE started $(date) on $(hostname) ==="

module purge
module load GCC/11.3.0 OpenMPI/4.1.4
module load CUDA/11.8.0
module load Miniforge3/24.7.1-2
export CUDA_HOME="${EBROOTCUDA:?}"
export LD_LIBRARY_PATH="$CUDA_HOME/targets/x86_64-linux/lib:${LD_LIBRARY_PATH:-}"

eval "$(conda shell.bash hook)"
conda activate "$ENV_PREFIX"

WORK_DIR=$(python -c "import json; print(json.load(open('$DATA_DIR/capture.json'))['work_dir'])")

# Prefer the refined mesh; OpenMVS writes several stages and the refined one is what the
# pipeline treats as its output.
if [[ -z "$OPENMVS_MESH" ]]; then
    for cand in scene_dense_mesh_refine.ply scene_dense_mesh.ply; do
        if [[ -f "$WORK_DIR/$cand" ]]; then
            OPENMVS_MESH="$WORK_DIR/$cand"
            break
        fi
    done
fi
if [[ -z "$OPENMVS_MESH" || ! -f "$OPENMVS_MESH" ]]; then
    echo "No OpenMVS mesh found under $WORK_DIR — pass one explicitly as the second argument." >&2
    exit 1
fi

# Prefer a millimetre-scaled MILo mesh if apply_scale.py made one.
MILO_MESH=""
for cand in "$OUT_DIR/mesh_mm.ply" "$OUT_DIR/mesh.ply"; do
    [[ -f "$cand" ]] && { MILO_MESH="$cand"; break; }
done
if [[ -z "$MILO_MESH" ]]; then
    MILO_MESH=$(find "$OUT_DIR" -name '*.ply' -printf '%s\t%p\n' | sort -rn | head -1 | cut -f2)
fi
[[ -n "$MILO_MESH" ]] || { echo "No MILo mesh under $OUT_DIR" >&2; exit 1; }

echo "MILo mesh    : $MILO_MESH"
echo "OpenMVS mesh : $OPENMVS_MESH"

cd "$REPO_DIR"
python scripts/compare_meshes.py \
    --capture "$DATA_DIR/capture.json" \
    --milo    "$MILO_MESH" \
    --openmvs "$OPENMVS_MESH" \
    --out     "$OUT_DIR/compare"

echo
echo "=== comparison for $CAPTURE finished $(date) ==="
echo "Bring the pictures down and LOOK at them before drawing any conclusion:"
echo "  ./scripts/remote/fetch_artifacts.sh output/$CAPTURE/compare ./artifacts/"
