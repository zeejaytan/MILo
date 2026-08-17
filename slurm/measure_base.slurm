#!/bin/bash
#SBATCH --job-name=measure-base
#SBATCH --account=punim2657
#SBATCH --partition=sapphire
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=16
#SBATCH --mem=128G
#SBATCH --time=3:00:00
#SBATCH --output=/data/gpfs/projects/punim2657/MILo/logs/measure_base_%j.log

set -uo pipefail

# Measure the blue base plate and put the reconstruction into millimetres.
#
# Runs on CPU deliberately. It needs only ~16 SAM 3 inferences, and queueing it behind the
# project's own GPU reconstruction jobs wasted an hour for work that does not need a GPU.
#
# BEST EFFORT, NEVER SILENT. measure_base.py refuses unless the fitted top face has the
# base's known 1.462 aspect ratio AND both edges give scale factors agreeing within 2%.
# When it refuses, this job exits 0 and the tree stays in arbitrary units with a clear
# message, because a wrong scale is far worse than no scale: nothing downstream reveals it
# and every measurement taken from all four meshes would inherit it.
#
# Usage:
#   sbatch slurm/measure_base.slurm 17062025/A02 dense_masked

CAPTURE="${1:?usage: sbatch measure_base.slurm <date>/<tree> [dense-subdir]}"
DENSE_DIR="${2:-dense_masked}"

MILO=/data/gpfs/projects/punim2657/MILo
W="/data/gpfs/projects/punim2657/Rabati2025/$CAPTURE/work_colmap_openmvs"
D="$W/$DENSE_DIR"
OUT="$MILO/base/$CAPTURE"

echo "=== base measurement for $CAPTURE ($DENSE_DIR) started $(date) ==="
[[ -d "$D/sparse" ]] || { echo "No undistorted model at $D/sparse" >&2; exit 1; }
[[ -s "$D/scene_dense.ply" ]] || { echo "No dense cloud at $D/scene_dense.ply" >&2; exit 1; }

module purge
module load Miniforge3/24.7.1-2
eval "$(conda shell.bash hook)"
conda activate /data/gpfs/projects/punim2657/tools/sam3
export PYTHONNOUSERSITE=1
export OMP_NUM_THREADS="${SLURM_CPUS_PER_TASK:-16}"

python "$MILO/repo/scripts/measure_base.py" \
    --dense "$D" --cloud "$D/scene_dense.ply" --out "$OUT" \
    --views "${VIEWS:-16}" --write-measurement-env
rc=$?

echo
if [[ "$rc" -eq 0 ]]; then
    echo "  scale accepted; measurement.env written to $W"
    echo "  apply it with the photogrammetry pipeline's scale_apply.py, which rewrites the"
    echo "  sparse model so every downstream mesh inherits the scale rather than each mesh"
    echo "  being scaled separately."
else
    echo "  MEASUREMENT REJECTED -- this tree stays in arbitrary units."
    echo "  That is the intended outcome when the checks fail, not a job failure: a scale"
    echo "  that is quietly 10% wrong would corrupt every measurement taken from all four"
    echo "  meshes and nothing downstream would ever show it."
    echo "  LOOK AT $OUT/base_dense_*.png AND $OUT/base_sparse_*.png -- comparing the"
    echo "  two shows whether the plate itself reconstructed properly, then measure the"
    echo "  base by hand if it needs doing."
fi
echo "=== finished $(date) ==="
exit 0     # a refusal is a valid result; the chain continues unscaled
