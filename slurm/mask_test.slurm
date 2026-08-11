#!/bin/bash
#SBATCH --job-name=mask-test
#SBATCH --account=punim2657
#SBATCH --partition=gpu-a100-short
#SBATCH --gres=gpu:1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=120G
#SBATCH --time=4:00:00
#SBATCH --output=/data/gpfs/projects/punim2657/MILo/logs/mask_test_%j.log

set -uo pipefail   # NOT -e: colmap segfaults in its exit handlers after finishing its work

# Does masking the background fix the global mapper on a turntable capture?
#
# The claim under test: the view graph contains two contradictory accounts of how much the
# view turned between two photographs -- one from the sherds, which turn with the
# turntable, and one from the static backdrop, which does not. Rotation averaging cannot
# tell them apart, fits the majority, and discards the rest. On the unmasked database it
# discarded 8,990 of 14,067 pairs.
#
# Masking removes the backdrop's account entirely. If the claim is right, the global
# mapper should stop collapsing: far fewer pairs invalidated, and a camera arc that opens
# from 67 degrees towards the full circle. If the arc stays shut, the claim is wrong and
# the cause is somewhere else.
#
# The conservator's own Metashape reconstruction of these photographs is correct WITHOUT
# masks, so masking is not required to solve this scene. That makes this a test of the
# explanation, not a proposed fix.
#
# Everything except the masks is identical to the unmasked run -- same feature settings,
# same matcher, same thresholds -- so any difference is attributable to the masks.
#
# Usage:
#   sbatch slurm/mask_test.slurm 16062025

CAPTURE="${1:?usage: sbatch mask_test.slurm <capture>}"

TOOLS=/data/gpfs/projects/punim2657/tools
SFM_ENV=$TOOLS/sfm
MILO=/data/gpfs/projects/punim2657/MILo
IMAGES="/data/gpfs/projects/punim2657/Rabati2025/$CAPTURE"
W="$IMAGES/work_colmap_openmvs"
MASKS="$W/masks"
DB="$W/database_masked.db"
OUT="$W/sparse_masked"

# Identical to the unmasked run.
MAX_IMG="${MAX_IMG:--1}"
MAX_FEAT="${MAX_FEAT:-16000}"
DSP="${DSP:-1}"
AFFINE_SHAPE="${AFFINE_SHAPE:-1}"
EPIPOLAR_ERROR="${EPIPOLAR_ERROR:-10}"

echo "=== mask test for $CAPTURE started $(date) on $(hostname) ==="

module purge
module load Miniforge3/24.7.1-2
eval "$(conda shell.bash hook)"
conda activate "$SFM_ENV"
export PYTHONNOUSERSITE=1

step() { echo; echo "=== $* ($(date +%H:%M:%S)) ==="; }

step "build masks"
# Skippable: masks are deterministic and take minutes, but a resubmit after a timeout
# should not repeat them.
NIMG=$(find "$IMAGES" -maxdepth 1 -type f \( -iname '*.jpg' -o -iname '*.jpeg' \) | wc -l)
NMASK=$(find "$MASKS" -maxdepth 1 -name '*.png' 2>/dev/null | wc -l)
if [[ "$NMASK" -eq "$NIMG" && "$NIMG" -gt 0 ]]; then
    echo "  $NMASK masks already present for $NIMG photographs -- reusing"
else
    python "$MILO/repo/scripts/build_masks.py" \
        --images "$IMAGES" --out "$MASKS" --overlays "$W/mask_overlays"
    echo "  (exit $?)"
fi
NMASK=$(find "$MASKS" -maxdepth 1 -name '*.png' 2>/dev/null | wc -l)
echo "  masks: $NMASK for $NIMG photographs"
[[ "$NMASK" -eq "$NIMG" ]] || { echo "Mask count does not match." >&2; exit 1; }

step "feature extraction WITH masks"
rm -f "$DB"
colmap feature_extractor \
    --database_path "$DB" --image_path "$IMAGES" \
    --ImageReader.mask_path "$MASKS" \
    --ImageReader.single_camera 1 \
    --FeatureExtraction.use_gpu 1 \
    --FeatureExtraction.max_image_size "$MAX_IMG" \
    --SiftExtraction.max_num_features "$MAX_FEAT" \
    --SiftExtraction.domain_size_pooling "$DSP" \
    --SiftExtraction.estimate_affine_shape "$AFFINE_SHAPE"
echo "  (exit $? -- judged by the counts below)"

# Masking must actually have removed features. If the counts match the unmasked run, the
# masks were not applied -- a wrong filename convention fails exactly this quietly.
python - "$DB" "$W/database.db" <<'PY'
import sqlite3, sys, numpy as np
def counts(p):
    try:
        db = sqlite3.connect(p)
        n = [r[0] for r in db.execute("SELECT rows FROM keypoints")]
        db.close()
        return np.array(n)
    except Exception as e:
        return None
m, u = counts(sys.argv[1]), counts(sys.argv[2])
if m is None or len(m) == 0:
    print("  masked database has no keypoints"); raise SystemExit(1)
print(f"  masked   : {len(m)} images, median {np.median(m):,.0f} features/image")
if u is not None and len(u):
    print(f"  unmasked : {len(u)} images, median {np.median(u):,.0f} features/image")
    drop = 1 - np.median(m) / np.median(u)
    print(f"  -> masking removed {100*drop:.0f}% of the features")
    if drop < 0.02:
        print("  WARNING: essentially nothing was removed. The masks are probably not")
        print("  being applied -- check the <image>.JPG.png naming and the orientation.")
PY

step "exhaustive matching"
colmap exhaustive_matcher \
    --database_path "$DB" \
    --FeatureMatching.use_gpu 1 \
    --TwoViewGeometry.max_error "$EPIPOLAR_ERROR" \
    --TwoViewGeometry.compute_relative_pose 1
echo "  (exit $?)"
python - "$DB" <<'PY'
import sqlite3, sys
db = sqlite3.connect(sys.argv[1])
print("  verified image pairs:",
      db.execute("SELECT COUNT(*) FROM two_view_geometries WHERE rows>0").fetchone()[0],
      "   (unmasked run had 14,067)")
db.close()
PY

step "global mapper on the masked database"
rm -rf "$OUT/global"; mkdir -p "$OUT/global"
colmap global_mapper --database_path "$DB" --image_path "$IMAGES" \
    --output_path "$OUT/global" --GlobalMapper.random_seed 0 \
    > "$OUT/global/glomap.log" 2>&1
echo "  (exit $?)"
echo "  pairs invalidated at rotation averaging (unmasked run: 8,990 of 14,067):"
grep -oE "Marked [0-9]+ image pairs as invalid" "$OUT/global/glomap.log" | sed 's/^/    /'

step "incremental mapper on the masked database (control)"
rm -rf "$OUT/incremental"; mkdir -p "$OUT/incremental"
colmap mapper --database_path "$DB" --image_path "$IMAGES" \
    --output_path "$OUT/incremental" --Mapper.multiple_models 1 \
    --Mapper.ba_refine_principal_point 0 \
    --Mapper.num_threads "${SLURM_CPUS_PER_TASK:-8}" \
    > "$OUT/incremental/mapper.log" 2>&1
echo "  (exit $?)"

step "the only measure that separates these"
for kind in global incremental; do
    for m in "$OUT/$kind"/*/; do
        [[ -f "$m/images.bin" ]] || continue
        echo "  --- masked $kind"
        python "$MILO/repo/scripts/check_turntable.py" "$m" 2>/dev/null | sed 's/^/  /'
    done
done

echo
echo "=================================================================="
echo "For comparison, on the UNMASKED database of the same photographs:"
echo "  global mapper      66.6 deg camera arc   COLLAPSED"
echo "  incremental       347.7 deg camera arc   OK"
echo
echo "If the masked global mapper opens out towards 360, the contradictory-view-graph"
echo "explanation holds. If it stays shut, that explanation is wrong."
echo "LOOK AT $W/mask_overlays/contact_sheet.png before believing any of this."
echo "=== finished $(date) ==="
