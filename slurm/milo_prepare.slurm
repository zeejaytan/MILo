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
# MASKS. Run SAM 3 ONCE, on the original photographs, then push those masks through the
# SAME undistortion as the images rather than segmenting a second time. COLMAP's
# image_undistorter looks images up by the name held in the model, so the masks are staged
# under their image names first.
#
# Two reasons this beats re-segmenting the undistorted set. The geometry is exact by
# construction -- same code path, same model, same options -- where a second segmentation
# has to be trusted. And every stage then works from the SAME definition of the object;
# segmenting twice gives SfM and MILo slightly different boundaries, and any disagreement
# between them would be untraceable. Verified on A02: undistorted mask and undistorted
# image both 3200x2133, outline following the sherds with no drift at the frame edges.
# WHICH MASK SET. masks_measure -- sherds + the blue base, no clamps or rod -- so MILo's
# mesh needs the same hand-editing as the other three, which is none.
#
# WATCH FOR THIS. A mask does something different here than in the photogrammetry stages.
# There it excludes pixels from depth fusion, and the clamp simply is not reconstructed.
# Here it also removes those pixels from the TRAINING LOSS, so the region a clamp used to
# occupy becomes unconstrained rather than empty: nothing penalises the model for putting
# Gaussians there, and mesh_extract_sdf will turn whatever lands there into surface. The
# symptom is floating blobs hanging in the gaps where the clamps were, not clamps.
# Set MASK_SET=masks_object to go back to masking only the room.
SAM_MASKS="$MILO_ROOT/masks/$CAPTURE/${MASK_SET:-masks_measure}"
MASKS_USER="$WORK/masks_user"
if [[ -d "$SAM_MASKS" ]]; then
    echo "=== undistorting the SAM 3 masks to match the training images ==="
    STAGE_DIR=$(mktemp -d)
    for f in "$SAM_MASKS"/*.png; do
        cp "$f" "$STAGE_DIR/$(basename "$f" .png)"      # A21_0891.JPG.png -> A21_0891.JPG
    done
    UND=$(mktemp -d)
    colmap image_undistorter --image_path "$STAGE_DIR"         --input_path "$WORK/$DENSE_DIR/sparse" --output_path "$UND"         --max_image_size "${UNDIST_MAX:-3200}" >/dev/null 2>&1
    mkdir -p "$MASKS_USER"
    # ONE convention across the project: COLMAP's "<image filename>.png", extension kept.
    # image_undistorter writes bare image names, so the .png is appended here.
    n=0
    for f in "$UND"/images/*; do
        b=$(basename "$f"); cp "$f" "$MASKS_USER/$b.png" && n=$((n+1))
    done
    rm -rf "$STAGE_DIR" "$UND"
    echo "  $n undistorted masks -> $MASKS_USER"
    # The same gate as the SfM job. There is no database here, so this is the precondition
    # half only: one mask per undistorted image, COLMAP's naming, matching dimensions, and
    # not blank. MILo's own adapter then refuses any view whose mask it cannot resolve.
    python "$REPO_DIR/scripts/check_masks.py" \
        --images "$WORK/$DENSE_DIR/images" --masks "$MASKS_USER" || exit 1
    MASK_ARG=""
else
    echo "  no SAM 3 masks at $SAM_MASKS -- training on the backdrop as well"
    MASK_ARG="--no-masks"
fi

rm -rf "$DATA_DIR"
python "$REPO_DIR/scripts/colmap_to_milo.py" \
    --work "$WORK" --dense-dir "$DENSE_DIR" --out "$DATA_DIR" $MASK_ARG
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
