#!/bin/bash
#SBATCH --job-name=milo-prep
#SBATCH --account=punim2657
#SBATCH --partition=sapphire
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=1:00:00
#SBATCH --output=/data/gpfs/projects/punim2657/MILo/logs/milo_prep_%j.log

set -uo pipefail

# Build the MILo dataset from an undistorted COLMAP workspace, then queue training.
#
# Split out from the training job so the dataset is validated on a cheap CPU node rather
# than while holding a GPU: the adapter checks that every registered view resolves to a
# file, which is the failure that would otherwise surface hours into training.
#
# Usage:
#   sbatch --dependency=afterany:<dense-job> slurm/milo_prepare.slurm 16062025 dense_incremental

CAPTURE="${1:?usage: sbatch milo_prepare.slurm <capture> [dense-subdir]}"
DENSE_DIR="${2:-dense_incremental}"
SUBMIT_TRAINING="${SUBMIT_TRAINING:-1}"

MILO_ROOT=/data/gpfs/projects/punim2657/MILo
REPO_DIR=$MILO_ROOT/repo
PHOTO_ROOT=/data/gpfs/projects/punim2657/Rabati2025
WORK="$PHOTO_ROOT/$CAPTURE/work_colmap_openmvs"
DATA_DIR="$MILO_ROOT/data/$CAPTURE"

echo "=== preparing MILo dataset for $CAPTURE from $DENSE_DIR ($(date)) ==="

module purge
module load Miniforge3/24.7.1-2
eval "$(conda shell.bash hook)"
conda activate /data/gpfs/projects/punim2657/tools/sfm
export PYTHONNOUSERSITE=1

# Which model this came from decides everything downstream, so record it and refuse a
# model that collapsed the turntable. MILo would otherwise reproduce the duplicated sherds
# faithfully and we would be comparing two renderings of the same wrong geometry.
SRC_MODEL="$WORK/$DENSE_DIR/sparse"
echo
python "$REPO_DIR/scripts/check_turntable.py" "$SRC_MODEL" | tee /tmp/milo_prep_$$.txt
if grep -q "COLLAPSED" /tmp/milo_prep_$$.txt; then
    echo "This workspace collapsed the turntable rotation; not training on it." >&2
    exit 1
fi

echo
rm -rf "$DATA_DIR"
python "$REPO_DIR/scripts/colmap_to_milo.py" \
    --work "$WORK" --dense-dir "$DENSE_DIR" --out "$DATA_DIR" --no-masks
rc=$?
echo "  (adapter exited $rc)"
[[ -f "$DATA_DIR/capture.json" ]] || {
    echo "No capture.json -- the dataset was not built." >&2; exit 1; }

echo
echo "=== dataset ==="
ls -la "$DATA_DIR"
python - "$DATA_DIR/capture.json" <<'PY'
import json, sys
c = json.load(open(sys.argv[1]))
for k in ("n_images", "n_train", "n_holdout", "train_images_arg", "source_work", "masks"):
    if k in c:
        print(f"  {k}: {c[k]}")
PY

if [[ "$SUBMIT_TRAINING" == "1" ]]; then
    echo
    echo "=== queueing training ==="
    sbatch "$REPO_DIR/slurm/milo_train.slurm" "$CAPTURE"
else
    echo
    echo "Dataset ready. Train with:  sbatch slurm/milo_train.slurm $CAPTURE"
fi
echo "=== finished $(date) ==="
