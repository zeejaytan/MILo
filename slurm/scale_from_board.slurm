#!/bin/bash
#SBATCH --job-name=scale-board
#SBATCH --account=punim2657
#SBATCH --partition=sapphire
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=1:00:00
#SBATCH --output=/data/gpfs/projects/punim2657/MILo/logs/scale_board_%j.log

set -uo pipefail

# Put a capture into millimetres using the TURNTABLE MARKER BOARD, and check that reading
# against the blue base plate in the same mesh.
#
# WHY THE BOARD RATHER THAN THE PLATE. The plate is four mouse clicks on a face declared to
# be 190 x 130 mm; the board is 16 coded targets on a printed square lattice, each a
# genuine detection in 28-46 views, fitted over every registered camera. The lattice pitch
# comes back to +/-0.036%, roughly sixty times tighter than the plate's own internal
# disagreement. Two further things are now known about the plate and neither is small: it
# is a shallow TRAY WITH A RAISED RIM, so its reconstructed outer envelope is not the
# 190 x 130 face and reads about 5% large, and one of the four Metashape points sits about
# 4.5 mm from where it was declared. See docs/notes/2026-08-22-turntable-markers.md.
#
# WHAT THIS JOB REFUSES TO DO. scale_mesh.py stops rather than scale when the model
# disagrees with its own board, when the reference cannot be applied to this model (wrong
# capture, renamed frames), or when the reference carries no correction_factor. A solve
# that put frames in the wrong place has no trustworthy scale either, and a millimetre
# figure written into a PLY header outlives the warning that should have accompanied it.
#
# THE CROSS-CHECK IS RIM-INDEPENDENT. Comparing the board against the plate's long edge
# would compare it against a rim. The DIFFERENCE of the two edges cancels the rim exactly
# -- it adds the same amount to both -- and 190 - 130 = 60 mm needs no assumption about how
# wide the rim is. On N01 that route gives 390.4 mm/unit against the board's 388.40: 0.5%.
# Note it amplifies noise about tenfold, so agreement at the percent level is a genuine
# confirmation but a coarse one. The check never overrides the board; it only reports.
#
# Usage:
#   sbatch slurm/scale_from_board.slurm 03072025/N01 dense_incremental

CAPTURE="${1:?usage: sbatch scale_from_board.slurm <date>/<tree> [dense-subdir]}"
DENSE_DIR="${2:-dense_masked}"

MILO=/data/gpfs/projects/punim2657/MILo
REPO=$MILO/repo
W="/data/gpfs/projects/punim2657/Rabati2025/$CAPTURE/work_colmap_openmvs"
D="$W/$DENSE_DIR"
REF="$REPO/docs/reference/turntable-board-${CAPTURE//\//-}.json"

echo "=== board scale for $CAPTURE ($DENSE_DIR) started $(date) ==="
echo "  reference: $REF"

[[ -f "$REF" ]]      || { echo "No board reference at $REF." >&2
                          echo "This capture has no marker board; use measure_base.slurm." >&2; exit 1; }
[[ -d "$D/sparse" ]] || { echo "No undistorted model at $D/sparse" >&2; exit 1; }

module purge
module load Miniforge3/24.7.1-2
eval "$(conda shell.bash hook)"
conda activate /data/gpfs/projects/punim2657/tools/sfm
export PYTHONNOUSERSITE=1
export OMP_NUM_THREADS="${SLURM_CPUS_PER_TASK:-8}"

cd "$REPO"

# Scale every mesh this workspace has produced so far. The COLMAP and MILo meshes usually
# do not exist yet when this job runs -- it is deliberately not made to wait for them,
# because the scale is a property of the SOLVE, not of any one surface, and holding a
# metric reading hostage to a four-hour patch-match run helps nobody. Re-run this job
# after the others land, or scale them directly: the same factor applies to all four, and
# scale_mesh.py refuses any mesh that already carries a units comment, so a second run
# cannot double-scale the ones it did the first time.
rc_any=0
scaled=0
for MESH in "$D/scene_refined_mesh.ply" "$D/scene_dense_mesh.ply" \
            "$D/colmap_delaunay_mesh.ply" "$D/colmap_poisson_mesh.ply"; do
    [[ -s "$MESH" ]] || continue
    OUT="${MESH%.ply}_mm.ply"
    if [[ -s "$OUT" ]]; then
        echo "  $(basename "$OUT") already exists -- leaving it alone"
        continue
    fi
    echo
    echo "--- $(basename "$MESH") ---"
    python scripts/scale_mesh.py \
        --mesh "$MESH" --out "$OUT" \
        --board-reference "$REF" --model "$D/sparse" \
        --capture "$CAPTURE" --method "$(basename "${MESH%.ply}")"
    rc=$?
    [[ "$rc" -eq 0 ]] && scaled=$((scaled + 1)) || rc_any=$rc
done

echo
if [[ "$scaled" -eq 0 ]]; then
    echo "  NOTHING SCALED. Either there are no meshes in $D yet, or scale_mesh.py refused."
    echo "  A refusal is a valid result, not a job failure: read the reason above. The usual"
    echo "  ones are a solve that disagrees with its board (the geometry is wrong, so the"
    echo "  scale would be too) and a reference belonging to a different capture."
else
    echo "  $scaled mesh(es) written in millimetres, with the factor and its provenance in"
    echo "  the PLY header and in a .scale.json beside each one."
fi

# ---- the independent check -----------------------------------------------------------
# Rim-independent, so it does not need the plate's absolute size to be right -- only the
# 60 mm difference between its two nominal edges. Reported, never applied.
echo
echo "=== cross-check against the blue base plate (rim-independent) ==="
if [[ -s "$D/scene_dense.ply" ]]; then
    # measure_base.py runs ~16 SAM 3 inferences to find the plate, so it needs the sam3
    # environment, not the sfm one scale_mesh.py ran in. Swapping here rather than at the
    # top keeps each tool in the environment it was built against.
    conda activate /data/gpfs/projects/punim2657/tools/sam3
    python scripts/measure_base.py \
        --dense "$D" --cloud "$D/scene_dense.ply" --out "$MILO/base/$CAPTURE" \
        --views "${VIEWS:-16}" || {
        echo "  the plate measurement refused or failed -- that does NOT invalidate the"
        echo "  board reading above. It is the coarser of the two rulers and it is the one"
        echo "  with a known rim problem. Look at $MILO/base/$CAPTURE/base_dense_*.png."; }
else
    echo "  no dense cloud at $D/scene_dense.ply -- cross-check skipped."
    echo "  The board reading stands on its own; it just has nothing to disagree with."
fi

echo
echo "=== finished $(date) ==="
# A refusal is a valid result and the chain continues unscaled, exactly as measure_base
# does. Exiting non-zero here would cancel downstream jobs over a ruler, not over geometry.
exit 0
