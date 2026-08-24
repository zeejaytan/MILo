#!/usr/bin/env bash
# Print WHICH sparse model a dense workspace was undistorted from. Exits 1 if it cannot
# tell, and never guesses.
#
# WHY THIS EXISTS. A03's work directory holds two solves of the same 164 photographs:
# `sparse/0`, the bent one, and `sparse_nosherdrig/0`, the corrected one that every dense
# workspace here was actually built from. They differ in the lens: SIMPLE_RADIAL k is
# -0.00811 in the first and +0.01858 in the second -- opposite signs, not a rounding
# difference. Undistorting masks through the wrong one warps them by the wrong amount
# everywhere, and the only visible symptom was the output being one pixel shorter
# (3200x2132 against the photographs' 3200x2133). Job 29543372 was stopped by that one
# pixel; without the size check it would have carved with silently misaligned masks and
# reported a tidy number.
#
# HOW IT DECIDES. `colmap image_undistorter` copies points3D.bin through byte for byte --
# undistortion moves cameras and pixels, never the 3D points. So the input model is the
# one whose points3D.bin is identical to the dense workspace's. That is an exact identity
# test, not a heuristic: on A03 it picks sparse_nosherdrig/0 for both dense_fixed and
# dense_eroded, and rejects sparse/0.
#
# Usage:
#   MODEL=$(scripts/dense_input_model.sh <dense-dir> <work-dir>) || exit 1

set -uo pipefail

DENSE="${1:?usage: dense_input_model.sh <dense-dir> <work-dir>}"
WORK="${2:?second argument is the work directory holding the candidate sparse models}"

REF="$DENSE/sparse/points3D.bin"
[[ -f "$REF" ]] || { echo "No undistorted model at $REF" >&2; exit 1; }
WANT=$(md5sum "$REF" | cut -d' ' -f1)

# Only the ORIGINAL solves, which live in $WORK/sparse*/ -- never another dense
# workspace's sparse/, which is already undistorted and shares the same points3D.bin. A
# glob, not a recursive find: nothing here walks the project filesystem.
MATCHES=()
CANDIDATES=()
for d in "$WORK"/sparse*/ "$WORK"/sparse*/*/; do
    p="${d%/}/points3D.bin"
    [[ -f "$p" ]] || continue
    CANDIDATES+=("${d%/}")
    if [[ "$(md5sum "$p" | cut -d' ' -f1)" == "$WANT" ]]; then
        MATCHES+=("${d%/}")
    fi
done

if [[ ${#MATCHES[@]} -eq 0 ]]; then
    {
        echo "Cannot tell which model $DENSE was undistorted from."
        echo "Its points3D.bin matches none of the candidates:"
        printf '    %s\n' ${CANDIDATES[@]+"${CANDIDATES[@]}"}
        echo "Pass the model explicitly rather than letting a job pick one."
    } >&2
    exit 1
fi

if [[ ${#MATCHES[@]} -gt 1 ]]; then
    # Two solves with identical points are the same solve copied; either is correct.
    echo "  ${#MATCHES[@]} identical candidates, using the first" >&2
fi
printf '%s\n' "${MATCHES[0]}"
