#!/usr/bin/env bash
# Reconstruct one pottery tree end to end: masks -> SfM -> three dense pipelines.
#
# Submits the whole chain with Slurm dependencies and returns immediately. Each stage
# refuses to hand on work it cannot vouch for, which matters more here than it sounds:
# nearly every failure this project has had was a stage reporting success while producing
# nothing usable.
#
#   1  sam3_masks       SAM 3 background masks. UNCONDITIONAL -- see below.
#   2  reconstruct      feature extraction + matching + incremental mapper + undistort,
#                       with the masks, then the CAMERA-ARC GATE
#   3  dense_from_model OpenMVS dense cloud + mesh + refined mesh      (1 mesh)
#   4  colmap_mesh      COLMAP patch-match + fusion + delaunay + poisson (2 meshes)
#   5  milo_prepare     MILo dataset + training + mesh extraction       (1 mesh)
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
# Usage:
#   ./scripts/run_tree.sh 17062025/A03
#   ./scripts/run_tree.sh 17062025/A03 --no-milo      (skip the long training run)
#   ./scripts/run_tree.sh 17062025/A03 --unmasked     (baseline, for comparison only)

set -euo pipefail

CAPTURE="${1:?usage: $0 <date>/<tree> [--no-milo] [--unmasked]}"; shift || true
NO_MILO=0; UNMASKED=0
for a in "$@"; do
    case "$a" in
        --no-milo) NO_MILO=1 ;;
        --unmasked) UNMASKED=1 ;;
        *) echo "unknown option: $a" >&2; exit 2 ;;
    esac
done

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
DEP=""
if [[ "$UNMASKED" == 0 ]]; then
    J_MASK=$(sbatch --parsable "$REPO/slurm/sam3_masks.slurm" "$CAPTURE")
    echo "  1. masks          $J_MASK"
    DEP="--dependency=afterok:$J_MASK"
    MASK_EXPORT=",MASK_PATH=$MASKS"
else
    echo "  1. masks          SKIPPED (--unmasked; for baseline comparison only)"
    MASK_EXPORT=""
fi

J_SFM=$(sbatch --parsable $DEP \
    --export="ALL,STAGE=colmap${MASK_EXPORT}" \
    --partition=gpu-a100-short --time=4:00:00 \
    "$REPO/slurm/reconstruct_group.slurm" "$CAPTURE")
echo "  2. SfM + arc gate $J_SFM"

J_MVS=$(sbatch --parsable --dependency=afterok:$J_SFM \
    --export="ALL,TAG=$TAG" \
    "$REPO/slurm/dense_from_model.slurm" "$CAPTURE" sparse/0)
echo "  3. OpenMVS        $J_MVS   (1 mesh)"

J_COL=$(sbatch --parsable --dependency=afterok:$J_MVS \
    "$REPO/slurm/colmap_mesh.slurm" "$CAPTURE" "dense_$TAG")
echo "  4. COLMAP meshes  $J_COL   (2 meshes)"

if [[ "$NO_MILO" == 0 ]]; then
    J_MILO=$(sbatch --parsable --dependency=afterok:$J_MVS \
        "$REPO/slurm/milo_prepare.slurm" "$CAPTURE" "dense_$TAG")
    echo "  5. MILo           $J_MILO   (1 mesh, queues training itself)"
fi

echo
echo "Four meshes when it finishes. Nothing downstream runs if the camera-arc gate fails,"
echo "which is the point: a folded solve meshes into duplicated sherds and looks plausible."
echo "Watch:  squeue -u \$USER"
