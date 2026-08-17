#!/usr/bin/env bash
# Push a SAM 3 mask set through the same undistortion as the photographs, and write it out
# under both naming conventions the dense stages want.
#
# WHY UNDISTORT RATHER THAN RE-SEGMENT. The masks are made on the original photographs, but
# every dense stage works on undistorted ones. Running SAM 3 a second time on the
# undistorted set would give a slightly different boundary, and then no two stages would
# share a definition of the object -- any disagreement between them would be untraceable.
# Undistorting the mask instead is exact by construction: same binary, same model, same
# options as the images it has to line up with.
#
# WHICH MODEL. The ORIGINAL sparse model -- the one the photographs themselves were
# undistorted FROM -- never the undistorted model in the dense workspace. The masks are at
# the camera's full 5568 px, and the undistorted model's cameras are 3200 px wide, so
# COLMAP aborts on
#     Check failed: distorted_camera.width == distorted_bitmap.Width() (3200 vs. 5568)
# The same --max_image_size must be passed as well, or the masks come out at a different
# size from the images they are supposed to match.
#
# TWO NAMING CONVENTIONS, because the tools disagree and neither is ours to change:
#   COLMAP   feature_extractor and stereo_fusion:  A21_0891.JPG.png   (extension KEPT)
#   OpenMVS  DensifyPointCloud --mask-path:        A21_0891.mask.png  (extension STRIPPED)
# OpenMVS strips it in Util::getFileName, checked in the pinned 2.4.0 headers rather than
# taken from a summary that said the opposite. Getting either wrong is silent in both
# tools: the mask is simply never found and the stage runs unmasked, successfully.
#
# Usage:
#   undistort_masks.sh <src-mask-dir> <sparse-model> <dense-dir> <out-root> [max-image-size]
#
# Writes <out-root>/colmap/ and <out-root>/openmvs/, and verifies both against the
# undistorted images before returning.

set -uo pipefail

SRC="${1:?usage: undistort_masks.sh <src-masks> <sparse-model> <dense-dir> <out-root> [max-size]}"
MODEL="${2:?second argument is the ORIGINAL sparse model, e.g. <work>/sparse/0}"
DENSE="${3:?third argument is the dense workspace (containing images/)}"
OUT="${4:?fourth argument is where to write colmap/ and openmvs/}"
MAXSIZE="${5:-3200}"

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

[[ -d "$SRC" ]]          || { echo "No masks at $SRC" >&2; exit 1; }
[[ -d "$MODEL" ]]        || { echo "No sparse model at $MODEL" >&2; exit 1; }
[[ -d "$DENSE/images" ]] || { echo "No undistorted images at $DENSE/images" >&2; exit 1; }

NSRC=$(find "$SRC" -maxdepth 1 -name '*.png' | wc -l)
NIMG=$(find "$DENSE/images" -maxdepth 1 -type f | wc -l)
echo "  $NSRC source masks, $NIMG undistorted images, model $MODEL"
[[ "$NSRC" -gt 0 ]] || { echo "No .png masks in $SRC" >&2; exit 1; }

# Scratch space on the PROJECT filesystem, not /tmp. On a shared CPU node /tmp is small,
# and image_undistorter does not fail when it runs out: it writes what fits, exits 0, and
# says nothing. That is how the MILo job produced 20 masks for 164 images while the dense
# job, on a GPU node with a roomier /tmp, produced all 164 from the same input.
SCRATCH="$OUT/.undistort_work"
rm -rf "$SCRATCH"
STAGE="$SCRATCH/stage"; UND="$SCRATCH/und"; ERR="$SCRATCH/colmap.log"
mkdir -p "$STAGE" "$UND"
trap 'rm -rf "$SCRATCH"' EXIT

# image_undistorter looks images up by the name held in the model, so stage each mask under
# its image's name first: A21_0891.JPG.png -> A21_0891.JPG
for f in "$SRC"/*.png; do
    cp "$f" "$STAGE/$(basename "$f" .png)"
done

# Stderr goes to a file and is SHOWN if this fails. Sending it to /dev/null cost an hour
# here: the undistorter aborted with a one-line explanation of exactly what was wrong and
# the job printed only "Undistorted 0 masks".
colmap image_undistorter --image_path "$STAGE" --input_path "$MODEL" \
    --output_path "$UND" --max_image_size "$MAXSIZE" >"$ERR" 2>&1
rc=$?

NUND=$(find "$UND/images" -maxdepth 1 -type f 2>/dev/null | wc -l)
if [[ "$NUND" -ne "$NIMG" ]]; then
    echo "Undistorted $NUND masks for $NIMG images -- refusing a partly masked run." >&2
    echo "colmap exited $rc (0 means it thought it had finished; it writes what fits" >&2
    echo "and does not report running out of room). Free space where it was working:" >&2
    df -h "$SCRATCH" /tmp 2>&1 | sed 's/^/    /' >&2
    echo "colmap's last output:" >&2
    tail -15 "$ERR" >&2
    exit 1
fi

rm -rf "$OUT/colmap" "$OUT/openmvs"
mkdir -p "$OUT/colmap" "$OUT/openmvs"
for f in "$UND"/images/*; do
    b=$(basename "$f")
    cp "$f" "$OUT/colmap/$b.png"            # A21_0891.JPG  -> A21_0891.JPG.png
    cp "$f" "$OUT/openmvs/${b%.*}.mask.png" # A21_0891.JPG  -> A21_0891.mask.png
done
echo "  wrote $NUND masks to $OUT/colmap (COLMAP) and $OUT/openmvs (OpenMVS)"

# Prove BOTH sets before anything spends hours on either. No database at this point, so
# this is the precondition half: naming, count, dimensions, and not blank.
#
# Checking both matters more than it looks. The two tools want different filenames, the
# OpenMVS one is the counter-intuitive of the two, and NEITHER tool reports a mask it
# cannot find -- it just runs unmasked and exits 0. Validating only the COLMAP set would
# leave the riskier half of this script unguarded.
python "$REPO/scripts/check_masks.py" --naming colmap \
    --images "$DENSE/images" --masks "$OUT/colmap" || exit 1
python "$REPO/scripts/check_masks.py" --naming openmvs \
    --images "$DENSE/images" --masks "$OUT/openmvs" || exit 1
