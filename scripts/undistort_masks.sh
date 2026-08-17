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
# TWO NAMING CONVENTIONS, because the tools disagree and neither is ours to change:
#   COLMAP   feature_extractor and stereo_fusion:  A21_0891.JPG.png   (extension KEPT)
#   OpenMVS  DensifyPointCloud --mask-path:        A21_0891.mask.png  (extension STRIPPED)
# OpenMVS strips it in Util::getFileName, checked in the pinned 2.4.0 headers rather than
# taken from a summary that said the opposite. Getting either wrong is silent in both
# tools: the mask is simply never found and the stage runs unmasked, successfully.
#
# Usage:
#   undistort_masks.sh <src-mask-dir> <dense-dir> <out-root> [max-image-size]
#
# Writes <out-root>/colmap/ and <out-root>/openmvs/, and verifies the COLMAP set against
# the undistorted images before returning.

set -uo pipefail

SRC="${1:?usage: undistort_masks.sh <src-mask-dir> <dense-dir> <out-root> [max-size]}"
DENSE="${2:?second argument is the dense workspace (containing images/ and sparse/)}"
OUT="${3:?third argument is where to write colmap/ and openmvs/}"
MAXSIZE="${4:-3200}"

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

[[ -d "$SRC" ]]            || { echo "No masks at $SRC" >&2; exit 1; }
[[ -d "$DENSE/images" ]]   || { echo "No undistorted images at $DENSE/images" >&2; exit 1; }
[[ -d "$DENSE/sparse" ]]   || { echo "No undistorted model at $DENSE/sparse" >&2; exit 1; }

NSRC=$(find "$SRC" -maxdepth 1 -name '*.png' | wc -l)
NIMG=$(find "$DENSE/images" -maxdepth 1 -type f | wc -l)
echo "  $NSRC source masks, $NIMG undistorted images"
[[ "$NSRC" -gt 0 ]] || { echo "No .png masks in $SRC" >&2; exit 1; }

# image_undistorter looks images up by the name held in the model, so stage each mask under
# its image's name first: A21_0891.JPG.png -> A21_0891.JPG
STAGE=$(mktemp -d); UND=$(mktemp -d)
trap 'rm -rf "$STAGE" "$UND"' EXIT
for f in "$SRC"/*.png; do
    cp "$f" "$STAGE/$(basename "$f" .png)"
done

colmap image_undistorter --image_path "$STAGE" --input_path "$DENSE/sparse" \
    --output_path "$UND" --max_image_size "$MAXSIZE" >/dev/null 2>&1

NUND=$(find "$UND/images" -maxdepth 1 -type f 2>/dev/null | wc -l)
[[ "$NUND" -eq "$NIMG" ]] || {
    echo "Undistorted $NUND masks for $NIMG images -- refusing a partly masked run." >&2
    exit 1; }

rm -rf "$OUT/colmap" "$OUT/openmvs"
mkdir -p "$OUT/colmap" "$OUT/openmvs"
for f in "$UND"/images/*; do
    b=$(basename "$f")
    cp "$f" "$OUT/colmap/$b.png"            # A21_0891.JPG  -> A21_0891.JPG.png
    cp "$f" "$OUT/openmvs/${b%.*}.mask.png" # A21_0891.JPG  -> A21_0891.mask.png
done
echo "  wrote $NUND masks to $OUT/colmap (COLMAP) and $OUT/openmvs (OpenMVS)"

# Prove it before anything spends hours on it. No database at this point, so this is the
# precondition half: naming, count, dimensions, and not blank.
python "$REPO/scripts/check_masks.py" --images "$DENSE/images" --masks "$OUT/colmap" || exit 1
