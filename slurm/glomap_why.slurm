#!/bin/bash
#SBATCH --job-name=glomap-why
#SBATCH --account=punim2657
#SBATCH --partition=gpu-a100-short
#SBATCH --gres=gpu:1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=120G
#SBATCH --time=3:00:00
#SBATCH --output=/data/gpfs/projects/punim2657/MILo/logs/glomap_why_%j.log

set -uo pipefail   # NOT -e: each case is judged by its output, and colmap segfaults on exit

# Why does the global mapper collapse this turntable capture when the incremental mapper,
# on the SAME database, does not?
#
# Established before writing this:
#   - Not the matching threshold. Both mappers read the same database and the same
#     14,067 verified pairs. One collapsed, one did not.
#   - Not the focal length prior, which is what COLMAP's own documentation warns about
#     (doc/cli.rst, doc/faq.rst: "the global mapper depends on good focal length priors").
#     Ours came from EXIF at 11599 px and both mappers converged to ~11880, within 2.5%.
#   - The concrete symptom is in GLOMAP's own log:
#         Marked 8990 image pairs as invalid with relative rotation error > 10 degrees
#     8,990 of 14,067 pairs -- 64% of the view graph -- discarded at rotation averaging.
#     Global positioning then converged neatly on the surviving third, which is why the
#     result looks healthy by every number while the cameras sit in a 67-degree arc.
#
# Each case reuses the existing database, so nothing is re-extracted or re-matched.
# Judged ONLY by the camera arc: reprojection error rates the collapsed answer better
# (0.537 px vs the incremental mapper's 0.635), so it cannot be used here.
#
# Usage:
#   sbatch slurm/glomap_why.slurm 16062025

CAPTURE="${1:?usage: sbatch glomap_why.slurm <capture>}"

TOOLS=/data/gpfs/projects/punim2657/tools
SFM_ENV=$TOOLS/sfm
MILO=/data/gpfs/projects/punim2657/MILo
IMAGES="/data/gpfs/projects/punim2657/Rabati2025/$CAPTURE"
W="$IMAGES/work_colmap_openmvs"
DB="$W/database.db"
OUT="$MILO/logs/glomap_why/$CAPTURE"

echo "=== why does the global mapper collapse $CAPTURE? started $(date) on $(hostname) ==="
[[ -f "$DB" ]] || { echo "No database at $DB" >&2; exit 1; }

module purge
module load Miniforge3/24.7.1-2
eval "$(conda shell.bash hook)"
conda activate "$SFM_ENV"
export PYTHONNOUSERSITE=1
mkdir -p "$OUT"

run_case() {
    local label="$1"; shift
    local db="$1"; shift
    local dest="$OUT/$label"
    rm -rf "$dest"; mkdir -p "$dest"
    echo
    echo "------------------------------------------------------------------"
    echo "--- $label"
    echo "    options: $*"
    colmap global_mapper --database_path "$db" --image_path "$IMAGES" \
        --output_path "$dest" --GlobalMapper.random_seed 0 "$@" \
        > "$dest/glomap.log" 2>&1
    # How much of the view graph survived rotation averaging -- the suspected mechanism.
    local dropped
    dropped=$(grep -oE "Marked [0-9]+ image pairs as invalid" "$dest/glomap.log" 2>/dev/null \
              | grep -oE "[0-9]+" | paste -sd+ | bc 2>/dev/null)
    echo "    pairs invalidated at rotation averaging: ${dropped:-none reported}"
    grep -m1 -oE "Kept [0-9]+ tracks" "$dest/glomap.log" 2>/dev/null | sed 's/^/    /'
    for m in "$dest"/*/; do
        [[ -f "$m/images.bin" ]] || continue
        python "$MILO/repo/scripts/check_turntable.py" "$m" 2>/dev/null | sed 's/^/    /'
    done
}

# 1. Stock. This is what we already ran; included so the comparison is self-contained.
run_case stock "$DB"

# 2. The documented recommendation. COLMAP's docs say view_graph_calibrator was ALWAYS
#    the default in standalone GLOMAP but is not run automatically here. Our focal prior
#    is already good, so if this fixes it the mechanism is the two-view geometries it
#    also recalibrates, not the intrinsics. It edits the database, hence the copy.
cp "$DB" "$W/database_vgc.db"
echo
echo "=== view_graph_calibrator on a copy of the database ==="
colmap view_graph_calibrator --database_path "$W/database_vgc.db" 2>&1 | tail -5
run_case view_graph_calibrated "$W/database_vgc.db"

# 3-5. The rotation-averaging consistency threshold that discarded 64% of the pairs.
#      Tightening should keep only pairs that agree with each other; loosening should keep
#      the contradictory ones. Both directions are informative, so both are run rather
#      than only the one that suits the hypothesis.
run_case ra_tight_3   "$DB" --GlobalMapper.ra_max_rotation_error_deg 3
run_case ra_tight_5   "$DB" --GlobalMapper.ra_max_rotation_error_deg 5
run_case ra_loose_30  "$DB" --GlobalMapper.ra_max_rotation_error_deg 30

# 6. Skip rotation averaging entirely. Not a usable setting, but it isolates whether the
#    damage happens there or later in global positioning.
run_case no_rotation_averaging "$DB" --GlobalMapper.skip_rotation_averaging 1

echo
echo "=================================================================="
echo "=== summary: camera arc is the only measure that separates these ==="
for d in "$OUT"/*/; do
    printf "%-26s" "$(basename "$d")"
    found=0
    for m in "$d"*/; do
        if [[ -f "$m/images.bin" ]]; then
            python "$MILO/repo/scripts/check_turntable.py" "$m" 2>/dev/null \
                | grep -oE "cover +[0-9.]+ deg|-> [A-Z]+" | paste -sd' ' ; found=1; break
        fi
    done
    [[ "$found" == 1 ]] || echo "no model"
done
echo
echo "The incremental mapper reaches 347.7 deg on this same database."
echo "=== finished $(date) ==="
