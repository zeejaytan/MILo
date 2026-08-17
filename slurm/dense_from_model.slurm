#!/bin/bash
#SBATCH --job-name=dense-inc
#SBATCH --account=punim2657
#SBATCH --partition=gpu-a100-short
#SBATCH --gres=gpu:1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=120G
#SBATCH --time=4:00:00
#SBATCH --output=/data/gpfs/projects/punim2657/MILo/logs/dense_inc_%j.log

set -uo pipefail   # NOT -e: colmap segfaults in its exit handlers after finishing the work

# Dense reconstruction from a NAMED sparse model, written to its own directory.
#
# The existing dense/ workspace was undistorted from GLOMAP's model, which collapsed the
# turntable: its cameras occupy a 67-degree arc around the tree instead of going round it,
# so the rig was rebuilt once per turntable position. The incremental model on the SAME
# database covers 347.7 degrees. This job rebuilds from that model without touching the
# GLOMAP outputs, so the two can be compared rather than one overwriting the other.
#
# Both OpenMVS 2.4.0 defaults that damaged the first mesh are overridden here:
#   --crop-to-roi 0   2.4.0 estimates a scene box and discards everything outside it
#   --decimate 1      RefineMesh's "auto" threw away 63% of the faces before refining
#
# Usage:
#   sbatch slurm/dense_from_model.slurm 16062025 sparse_incremental/0

GROUP="${1:?usage: sbatch dense_from_model.slurm <date>[/<tree>] <model-relpath>}"
MODEL_REL="${2:?second argument is the model path relative to the work directory}"
TAG="${TAG:-incremental}"

TOOLS=/data/gpfs/projects/punim2657/tools
SFM_ENV=$TOOLS/sfm
OPENMVS_BIN=$TOOLS/openmvs-2.4.0/bin/OpenMVS
PHOTO_ROOT=/data/gpfs/projects/punim2657/Rabati2025
MILO=/data/gpfs/projects/punim2657/MILo

IMAGES="$PHOTO_ROOT/$GROUP"
W="$IMAGES/work_colmap_openmvs"
MODEL="$W/$MODEL_REL"
DENSE="$W/dense_$TAG"

echo "=== dense reconstruction of $GROUP from $MODEL_REL started $(date) on $(hostname) ==="
[[ -d "$MODEL" ]] || { echo "No model at $MODEL" >&2; exit 1; }

# Check the tools exist BEFORE doing anything expensive. The first run of this job had the
# OpenMVS path wrong, so every stage printed "No such file or directory", nothing was
# built, and Slurm still recorded the job as COMPLETED with exit 0 -- because the stages
# are deliberately not run under `set -e` (colmap segfaults in its exit handlers). A job
# that does nothing must not report success.
for tool in InterfaceCOLMAP DensifyPointCloud ReconstructMesh RefineMesh; do
    [[ -x "$OPENMVS_BIN/$tool" ]] || {
        echo "Missing $OPENMVS_BIN/$tool -- check OPENMVS_BIN" >&2; exit 1; }
done

module purge
module load Miniforge3/24.7.1-2
eval "$(conda shell.bash hook)"
conda activate "$SFM_ENV"
export PYTHONNOUSERSITE=1
export LD_LIBRARY_PATH="$SFM_ENV/lib:${LD_LIBRARY_PATH:-}"

step() { echo; echo "=== $* ($(date +%H:%M:%S)) ==="; }

# The gate. Reprojection error cannot tell a correct turntable solve from a collapsed one
# -- the collapsed GLOMAP model scored BETTER (0.537 vs 0.635 px median). The camera arc
# can. Refuse to spend two hours meshing a model that has already failed it.
step "turntable check"
python "$MILO/repo/scripts/check_turntable.py" "$MODEL" | tee /tmp/turntable_$$.txt
if grep -q "COLLAPSED" /tmp/turntable_$$.txt; then
    if [[ "${ALLOW_COLLAPSED:-0}" == "1" ]]; then
        echo
        echo ">>> This model FAILED the turntable check, and ALLOW_COLLAPSED=1 was set."
        echo ">>> Proceeding deliberately, to mesh it as a comparison against a model that"
        echo ">>> passed. Expect duplicated sherds and a round base -- that is the point."
    else
        echo
        echo "This model collapsed the turntable rotation. Meshing it would reproduce the" >&2
        echo "duplicated-sherd result. Set ALLOW_COLLAPSED=1 to do it anyway, deliberately," >&2
        echo "e.g. to compare mappers under identical OpenMVS settings. Stopping." >&2
        exit 1
    fi
fi

step "undistort from $MODEL_REL"
rm -rf "$DENSE"
colmap image_undistorter --image_path "$IMAGES" --input_path "$MODEL" \
    --output_path "$DENSE" --max_image_size "${UNDIST_MAX:-3200}"
echo "  (exit $? -- judged by the files below, not by the exit code)"
ls "$DENSE/images" 2>/dev/null | wc -l | xargs echo "  undistorted images:"

# SURFACE MASKS. A different mask from the one that solved the cameras, and deliberately:
# the cameras were solved with the whole rig visible because the rod and clamps turn WITH
# the sherds and are excellent features, but the clamps must not end up in the surface.
# A clamp jaw resting on a sherd fuses to it, so no amount of connected-component work
# separates them afterwards -- 2D, before any geometry exists, is the only clean cut.
# masks_measure keeps the sherds and the blue base (the scale reference) and drops the
# clamps, rod and dial. Set SURFACE_MASKS=0 to build the old way, rig and all.
SURFACE_MASKS="${SURFACE_MASKS:-1}"
MVS_MASK_ARGS=()
COLMAP_MASK_DIR=""
SRC_MASKS="$MILO/masks/$GROUP/${MASK_SET:-masks_measure}"
if [[ "$SURFACE_MASKS" == "1" && -d "$SRC_MASKS" ]]; then
    step "undistorting the surface masks (${MASK_SET:-masks_measure})"
    # $MODEL, not $DENSE/sparse: the masks are at the camera's full resolution, so they
    # must go through the ORIGINAL model with the SAME --max_image_size the photographs
    # used. Passing the already-undistorted model aborts the undistorter outright --
    # "distorted_camera.width == distorted_bitmap.Width() (3200 vs. 5568)".
    "$MILO/repo/scripts/undistort_masks.sh" "$SRC_MASKS" "$MODEL" "$DENSE" \
        "$DENSE/masks" "${UNDIST_MAX:-3200}" || exit 1
    # --ignore-mask-label 0: in these masks 0 is black, which is the region to ignore.
    # The TRAILING SLASH is load-bearing. OpenMVS builds the mask filename by string
    # concatenation -- strMaskPath + getFileName(image) + ".mask.png" -- so without it the
    # path runs together into ".../openmvsA21_0891.mask.png", which simply does not exist,
    # and a mask it cannot open is a mask it ignores without a word.
    MVS_MASK_ARGS=(--mask-path "$DENSE/masks/openmvs/" --ignore-mask-label 0)
    COLMAP_MASK_DIR="$DENSE/masks/colmap"
    echo "  the surface will be built from sherds + base only"
elif [[ "$SURFACE_MASKS" == "1" ]]; then
    echo
    echo "SURFACE_MASKS=1 but there are no masks at $SRC_MASKS." >&2
    echo "Run slurm/sam3_masks.slurm first, or set SURFACE_MASKS=0 to build with the" >&2
    echo "clamps and rod included. Refusing to quietly build the thing you asked to" >&2
    echo "have removed." >&2
    exit 1
else
    echo "  SURFACE_MASKS=0 -- building the whole rig into the surface"
fi

step "OpenMVS: interface"
"$OPENMVS_BIN/InterfaceCOLMAP" -w "$DENSE" -i "$DENSE" -o "$DENSE/scene.mvs" \
    --image-folder "$DENSE/images"

step "OpenMVS: dense point cloud (ROI cropping OFF)"
"$OPENMVS_BIN/DensifyPointCloud" -w "$DENSE" -i "$DENSE/scene.mvs" \
    -o "$DENSE/scene_dense.mvs" --cuda-device 0 \
    --resolution-level "${DENS_LEVEL:-0}" --number-views "${DENS_VIEWS:-8}" \
    --number-views-fuse "${DENS_FUSE:-5}" --crop-to-roi 0 \
    "${MVS_MASK_ARGS[@]}"

step "OpenMVS: mesh"
"$OPENMVS_BIN/ReconstructMesh" -w "$DENSE" -i "$DENSE/scene_dense.mvs" \
    -p "$DENSE/scene_dense.ply" -o "$DENSE/scene_dense_mesh.ply" \
    --target-face-num "${TARGET_FACES:-10000000}" --crop-to-roi 0

# Refinement is the step most likely to run out of memory now that decimation is off:
# 3.8M faces instead of 1.4M. The unrefined mesh above is already written, so a failure
# here costs the refinement only -- it does not cost the run.
step "OpenMVS: refine (decimation DISABLED)"
"$OPENMVS_BIN/RefineMesh" -w "$DENSE" -i "$DENSE/scene_dense.mvs" \
    -m "$DENSE/scene_dense_mesh.ply" -o "$DENSE/scene_refined_mesh.ply" \
    --scales "${REFINE_SCALES:-2}" --cuda-device 0 --decimate 1 \
    || echo "  (refinement failed -- the unrefined mesh is still there and is usable)"

step "done"
ls -lh "$DENSE"/*.ply 2>/dev/null | awk '{print $5, $9}'

# Judge by artefact, not by exit code -- and make a run that produced nothing fail loudly.
[[ -s "$DENSE/scene_dense_mesh.ply" ]] || {
    echo; echo "No mesh was produced. See the stage output above." >&2; exit 1; }

echo
echo "Open scene_dense_mesh.ply and scene_refined_mesh.ply and look at them:"
echo "  is the base square rather than round, and does each sherd appear once?"
echo "=== finished $(date) ==="
