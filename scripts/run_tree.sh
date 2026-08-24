#!/usr/bin/env bash
# Reconstruct one pottery tree end to end: masks -> SfM -> three dense pipelines.
#
# Submits the whole chain with Slurm dependencies and returns immediately. Each stage
# refuses to hand on work it cannot vouch for, which matters more here than it sounds:
# nearly every failure this project has had was a stage reporting success while producing
# nothing usable.
#
#   1  masks  sam3_masks        SAM 3 background masks. UNCONDITIONAL -- see below.
#   2  sfm    reconstruct       features + matching + incremental mapper + undistort,
#                               with the masks, then the TURNTABLE GATE
#   3  mvs    dense_from_model  OpenMVS dense cloud + mesh + refined mesh    (1 mesh)
#   4  scale  scale_from_board  metric scale: marker board where one exists,
#             / measure_base    otherwise the blue base plate               (0 meshes)
#   5  mesh   colmap_mesh       COLMAP patch-match + fusion + delaunay + poisson (2)
#   6  milo   milo_prepare      MILo dataset + training + mesh extraction   (1 mesh)
#
# WHY MASKING IS UNCONDITIONAL. On A02 it was the difference between a folded solve and a
# correct one -- 262.1 deg camera arc against 348.4 deg, same photographs, same mapper --
# by removing only 4% of the features. Those few sit on the STATIC backdrop and are what
# lets a turntable solve fold. A01 does not need masks at all. Nothing tells you which
# kind of tree you have in advance, and masking costs ~8 minutes against 4+ hours of
# reconstruction, so masking always is cheaper than reconstructing twice.
#
# WHAT MASKING DOES NOT DO. It does not make the camera-arc gate redundant. The gate still
# runs after SfM and still decides whether anything downstream happens. It fired correctly
# on A02 and was talked out of once already; see docs/lessons.md.
#
# RESUMING A PART-BUILT TREE. --from <stage> starts the chain partway along and submits
# everything after it. This exists because the alternative is hand-submitting one stage,
# which is how 03072025/N01 came to have ONE of the four meshes: dense_from_model.slurm was
# run on its own, and steps 4-6 never happened because nothing was left to trigger them.
# Running a stage by hand silently drops everything downstream of it. The flag turns that
# from something to remember into something the script does.
#
# Stages, in order:  masks  sfm  mvs  scale  mesh  milo
#
# Each resume point checks its own prerequisite on disk and refuses if it is missing, so
# --from mesh on a tree with no dense cloud stops here rather than four queue-hours later.
#
# Usage:
#   ./scripts/run_tree.sh 17062025/A03
#   ./scripts/run_tree.sh 17062025/A03 --no-milo      (skip the long training run)
#   ./scripts/run_tree.sh 17062025/A03 --unmasked     (baseline, for comparison only)
#   ./scripts/run_tree.sh 17062025/A03 --skip-masks   (masks already generated and checked)
#   TAG=incremental ./scripts/run_tree.sh 03072025/N01 --from scale
#                                                     (SfM and OpenMVS already done)

set -euo pipefail

CAPTURE="${1:?usage: $0 <date>/<tree> [--no-milo] [--unmasked] [--from <stage>]}"; shift || true
NO_MILO=0; UNMASKED=0; SKIP_MASKS=0; FROM_STAGE=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --no-milo) NO_MILO=1 ;;
        --unmasked) UNMASKED=1 ;;
        --skip-masks) SKIP_MASKS=1 ;;
        --from) FROM_STAGE="${2:?--from needs a stage: masks sfm mvs scale mesh milo}"; shift ;;
        --from=*) FROM_STAGE="${1#--from=}" ;;
        *) echo "unknown option: $1" >&2; exit 2 ;;
    esac
    shift
done

# Stage numbers, so "does this stage run" is one comparison rather than six flags.
#
# The validation is inline rather than in a function that exits, because `exit` inside
# `$( )` only kills the subshell: FROM would come back EMPTY and the script would carry on
# submitting jobs with a broken comparison. That is the same shape as the bug that let
# check_turntable.py print a page of disagreeing frames and return 0 -- a check that
# reports and a check that stops are not the same thing.
FROM=1
if [[ -n "$FROM_STAGE" ]]; then
    case "$FROM_STAGE" in
        masks) FROM=1 ;; sfm) FROM=2 ;; mvs) FROM=3 ;;
        scale) FROM=4 ;; mesh) FROM=5 ;; milo) FROM=6 ;;
        *) echo "unknown stage '$FROM_STAGE' -- use one of: masks sfm mvs scale mesh milo" >&2
           exit 2 ;;
    esac
fi
[[ "$SKIP_MASKS" == 1 && "$FROM" -lt 2 ]] && FROM=2

MILO=/data/gpfs/projects/punim2657/MILo
REPO=$MILO/repo
IMAGES="/data/gpfs/projects/punim2657/Rabati2025/$CAPTURE"
MASKS="$MILO/masks/$CAPTURE/masks_object"
TAG="${TAG:-masked}"
[[ "$UNMASKED" == 1 ]] && TAG="unmasked"

[[ -d "$IMAGES" ]] || { echo "No photographs at $IMAGES" >&2; exit 1; }
N=$(find "$IMAGES" -maxdepth 1 -iname '*.jpg' | wc -l)
echo "$CAPTURE: $N photographs"
[[ "$N" -ge 20 ]] || { echo "Only $N photographs -- that is not a tree." >&2; exit 1; }

# Spartan's clone is pull-only. A dirty checkout silently blocks the pull, and a job then
# runs an OLD script while reporting success -- which is exactly how a masked run of A02
# came back with no masks applied at all.
cd "$REPO"
if [[ -n "$(git status --porcelain -- slurm scripts 2>/dev/null)" ]]; then
    echo "The Spartan checkout has local modifications under slurm/ or scripts/." >&2
    echo "It is pull-only: commit on the laptop and pull here. Refusing to submit," >&2
    echo "because a blocked pull means these jobs would run stale code." >&2
    git status --short -- slurm scripts >&2
    exit 1
fi
git pull --ff-only >/dev/null 2>&1 || { echo "git pull --ff-only failed." >&2; exit 1; }
echo "  repo at $(git log --oneline -1)"

cd "$MILO"
WORK="$IMAGES/work_colmap_openmvs"
DENSE="$WORK/dense_$TAG"

# Resuming means the prerequisite has to be on disk, because a Slurm dependency can only
# wait for a job that was submitted. Check it here, in seconds, rather than discovering it
# inside a job that has already queued for an hour.
if [[ "$FROM" -ge 3 ]]; then
    [[ -d "$WORK/sparse/0" ]] || {
        echo "--from $FROM_STAGE needs an SfM model at $WORK/sparse/0, which is not there." >&2
        echo "Run without --from, or --from sfm." >&2; exit 1; }
fi
if [[ "$FROM" -ge 4 ]]; then
    [[ -s "$DENSE/scene_dense.ply" ]] || {
        echo "--from $FROM_STAGE needs a dense cloud at $DENSE/scene_dense.ply." >&2
        echo "TAG is '$TAG'; if the workspace is named differently, set TAG=<name>." >&2
        ls -d "$WORK"/dense_* 2>/dev/null | sed 's|^|  found: |' >&2
        echo "Run --from mvs to build it." >&2; exit 1; }
    echo "  resuming from $FROM_STAGE against $DENSE"
fi

DEP=""
if [[ "$FROM" -gt 1 ]]; then
    if [[ "$SKIP_MASKS" == 1 ]]; then
        # Reuse masks already on disk. Worth having as a flag rather than a hand-written
        # sbatch chain: the masks are the stage most likely to need a second look, and
        # re-segmenting 164 frames to re-run the reconstruction wastes ten GPU minutes.
        # Both sets are checked here, because a half-present mask set fails much later.
        NOBJ=$(find "$MASKS" -maxdepth 1 -name '*.png' 2>/dev/null | wc -l)
        NMEA=$(find "$MILO/masks/$CAPTURE/masks_measure" -maxdepth 1 -name '*.png' 2>/dev/null | wc -l)
        echo "  1. masks          REUSED: $NOBJ object, $NMEA measure, for $N photographs"
        [[ "$NOBJ" -eq "$N" && "$NMEA" -eq "$N" ]] || {
            echo "Mask counts do not match the $N photographs -- rerun sam3_masks.slurm." >&2
            echo "A count mismatch usually means a photograph was added or removed since." >&2
            exit 1; }
    else
        echo "  1. masks          SKIPPED (--from $FROM_STAGE)"
    fi
    MASK_EXPORT=",MASK_PATH=$MASKS"
elif [[ "$UNMASKED" == 1 ]]; then
    echo "  1. masks          SKIPPED (--unmasked; for baseline comparison only)"
    MASK_EXPORT=""
else
    J_MASK=$(sbatch --parsable "$REPO/slurm/sam3_masks.slurm" "$CAPTURE")
    echo "  1. masks          $J_MASK"
    DEP="--dependency=afterok:$J_MASK"
    MASK_EXPORT=",MASK_PATH=$MASKS"
fi
[[ "$UNMASKED" == 1 ]] && MASK_EXPORT=""

if [[ "$FROM" -le 2 ]]; then
    J_SFM=$(sbatch --parsable $DEP \
        --export="ALL,STAGE=colmap${MASK_EXPORT}" \
        --partition=gpu-a100-short --time=4:00:00 \
        "$REPO/slurm/reconstruct_group.slurm" "$CAPTURE")
    echo "  2. SfM + arc gate $J_SFM"
    DEP_SFM="--dependency=afterok:$J_SFM"
else
    echo "  2. SfM + arc gate SKIPPED (model already at $WORK/sparse/0)"
    DEP_SFM=""
fi

if [[ "$FROM" -le 3 ]]; then
    J_MVS=$(sbatch --parsable $DEP_SFM \
        --export="ALL,TAG=$TAG" \
        "$REPO/slurm/dense_from_model.slurm" "$CAPTURE" sparse/0)
    echo "  3. OpenMVS        $J_MVS   (1 mesh)"
    DEP_MVS="--dependency=afterok:$J_MVS"
else
    echo "  3. OpenMVS        SKIPPED (dense cloud already at $DENSE)"
    DEP_MVS=""
fi

# ---- 4. metric scale ----------------------------------------------------------------
# TWO RULERS, and the better one is preferred where it exists.
#
# THE MARKER BOARD (03072025/N01 onwards). 16 coded targets on a printed 40 mm lattice,
# fitted over every registered camera. Its pitch is recovered to +/-0.036%, about sixty
# times tighter than the base plate's own internal disagreement, and every target is a
# genuine multi-view detection rather than a mouse click.
#
# THE BLUE BASE PLATE (everything before that). Four clicked corners of a 190 x 130 mm
# face. Two things are now known about it, both found by looking rather than by inferring:
# the plate is a shallow TRAY WITH A RAISED RIM, so the reconstructed outer envelope is
# not the 190 x 130 face and reads about 5% large; and one of the four Metashape points is
# ~4.5 mm out of place. It is a usable ruler and the only one most captures have -- but it
# is the fallback, not the reference. See docs/notes/2026-08-22-turntable-markers.md.
#
# BEST EFFORT, NEVER SILENT, either way. measure_base.py refuses unless the fitted top
# face has the base's 1.462 aspect ratio AND both edges agree within 2%; scale_mesh.py
# refuses a model that disagrees with its own board. A refusal leaves the tree in
# arbitrary units and says so. A wrong scale is far worse than none: nothing downstream
# reveals it, and every measurement taken from all four meshes would inherit it.
BOARD_REF="$REPO/docs/reference/turntable-board-${CAPTURE//\//-}.json"
if [[ "$FROM" -le 4 ]]; then
    if [[ -f "$BOARD_REF" ]]; then
        J_SCALE=$(sbatch --parsable $DEP_MVS \
            --job-name=scale-board --partition=sapphire --ntasks=1 --cpus-per-task=8 \
            --mem=64G --time=1:00:00 --output="$MILO/logs/scale_board_%j.log" \
            "$REPO/slurm/scale_from_board.slurm" "$CAPTURE" "dense_$TAG")
        echo "  4. scale (BOARD)  $J_SCALE   $(basename "$BOARD_REF")"
    else
        J_SCALE=$(sbatch --parsable $DEP_MVS \
            --job-name=measure-base --partition=sapphire --ntasks=1 --cpus-per-task=16 \
            --mem=128G --time=3:00:00 --output="$MILO/logs/measure_base_%j.log" \
            "$REPO/slurm/measure_base.slurm" "$CAPTURE" "dense_$TAG")
        echo "  4. scale (plate)  $J_SCALE   no board reference for $CAPTURE"
    fi
else
    echo "  4. scale          SKIPPED (--from $FROM_STAGE)"
fi

if [[ "$FROM" -le 5 ]]; then
    J_COL=$(sbatch --parsable $DEP_MVS \
        "$REPO/slurm/colmap_mesh.slurm" "$CAPTURE" "dense_$TAG")
    echo "  5. COLMAP meshes  $J_COL   (2 meshes)"
else
    echo "  5. COLMAP meshes  SKIPPED (--from $FROM_STAGE)"
fi

if [[ "$NO_MILO" == 0 && "$FROM" -le 6 ]]; then
    J_MILO=$(sbatch --parsable $DEP_MVS \
        "$REPO/slurm/milo_prepare.slurm" "$CAPTURE" "dense_$TAG")
    echo "  6. MILo           $J_MILO   (1 mesh, queues training itself)"
elif [[ "$NO_MILO" == 1 ]]; then
    echo "  6. MILo           SKIPPED (--no-milo)"
fi

echo
if [[ "$FROM" -eq 1 ]]; then
    echo "Four meshes when it finishes. Nothing downstream runs if the camera-arc gate fails,"
    echo "which is the point: a folded solve meshes into duplicated sherds and looks plausible."
else
    echo "Resumed from '$FROM_STAGE'. The stages before it were NOT re-run and NOT re-checked --"
    echo "whatever is on disk is taken as correct, the turntable gate's verdict included."
fi
echo "Watch:  squeue -u \$USER"
