#!/bin/bash
#SBATCH --job-name=recon-group
#SBATCH --account=punim2657
#SBATCH --partition=gpu-a100
#SBATCH --gres=gpu:1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=16
#SBATCH --mem=256G
#SBATCH --time=24:00:00
#SBATCH --output=/data/gpfs/projects/punim2657/MILo/logs/recon_%j.log

set -euo pipefail

# Reconstruct ONE photo group with the current toolchain: COLMAP 4.1.1 + OpenMVS 2.4.0.
#
# WHY THIS EXISTS RATHER THAN CALLING pipeline_main.sh. Three separate faults in the
# photogrammetry pipeline block these captures, and that repo is edited on Spartan outside
# the laptop-and-push arrangement, so it is not mine to change:
#
#   1. multiple_models: 0 makes COLMAP stop after its first model. On A11 that model held
#      2 of 68 photographs. Allowing a second attempt registers all 68 (measured: sweep
#      job 29042664, init_min_tri_angle 2.0 either way).
#   2. Even allowing multiple models, run_colmap.py picks `sorted(model_dirs)[0]` while
#      logging "the first model (largest)". Sorting is by directory NAME, so it takes
#      sparse/0 — the 2-image model — and the reconstruction fails identically.
#   3. Its bootstrap imports yaml before loading the modules that provide it.
#
# The tuned CAPTURE parameters are still yours: they are read out of your
# pipeline_config.yaml rather than restated here, so anything you retune upstream is
# picked up. What this script fixes is orchestration, not photogrammetry.
#
# MAPPER CHOICE. COLMAP 4.0 absorbed GLOMAP as `global_mapper`, which solves all camera
# poses together instead of growing from a seed pair. Growing from a seed pair is exactly
# what failed here, so the global mapper is the default. MAPPER=incremental falls back to
# the classic path with multiple_models enabled and the largest model selected.
#
# Usage:
#   ./scripts/remote/pull_and_sbatch.sh slurm/reconstruct_group.slurm 16062025/A11
#   MAPPER=incremental ... slurm/reconstruct_group.slurm 16062025/A11

GROUP="${1:?usage: sbatch reconstruct_group.slurm <date>/<group>}"
MAPPER="${MAPPER:-global}"
# colmap | mvs | all. Splitting matters for scheduling, not just tidiness: gpu-a100 has
# 336 jobs queued and estimates a start ~23 hours out, while gpu-a100-short has 3 queued
# and a 4-hour limit. The COLMAP stage finishes well inside 4 hours AND carries the
# decisive result — how many photographs register — so running it alone on the short
# partition answers the question today instead of tomorrow. The dense stage, which is the
# genuinely long part, then queues separately.
#   STAGE=colmap sbatch --partition=gpu-a100-short --time=4:00:00 ...
#   STAGE=mvs    sbatch ...
STAGE="${STAGE:-all}"

TOOLS=/data/gpfs/projects/punim2657/tools
SFM_ENV=$TOOLS/sfm
OPENMVS_BIN=$TOOLS/openmvs-2.4.0/bin/OpenMVS
PHOTO_ROOT=/data/gpfs/projects/punim2657/Rabati2025
PHOTOGRAMMETRY=/data/gpfs/projects/punim2657/Photogrammetry
MILO_REPO=/data/gpfs/projects/punim2657/MILo/repo
MILO_PY=$MILO_REPO/scripts/milo_python.sh

IMAGES="$PHOTO_ROOT/$GROUP"
W="$IMAGES/work_colmap_openmvs"
NPROC="${SLURM_CPUS_PER_TASK:-16}"

echo "=== reconstruct $GROUP started $(date) on $(hostname) ==="
nvidia-smi | head -12 || true

[[ -d "$IMAGES" ]] || { echo "No photographs at $IMAGES" >&2; exit 1; }
[[ -x "$SFM_ENV/bin/colmap" ]] || { echo "No COLMAP at $SFM_ENV/bin/colmap — run slurm/build_sfm_tools.slurm first" >&2; exit 1; }
[[ -d "$OPENMVS_BIN" ]] || { echo "No OpenMVS at $OPENMVS_BIN — run slurm/build_sfm_tools.slurm first" >&2; exit 1; }

module purge
module load Miniforge3/24.7.1-2
eval "$(conda shell.bash hook)"
conda activate "$SFM_ENV"
export PYTHONNOUSERSITE=1

# Captured, not piped: `colmap -h | head` makes head close the pipe, colmap dies of
# SIGPIPE, and `set -o pipefail` would end this job before it reconstructed anything.
# The same trap cost three rounds in the build script.
echo "$(colmap -h 2>&1 | head -2 || true)"

N=$(find "$IMAGES" -maxdepth 1 -type f \( -iname '*.jpg' -o -iname '*.jpeg' \) | wc -l)
echo "photographs: $N"

# Read the capture parameters out of the pipeline's own config, so the settings tuned for
# this turntable rig stay in one place.
read -r MAX_IMG MAX_FEAT DSP GUIDED TRI_ANGLE MIN_INLIERS MIN_RATIO UNDIST_MAX \
        DENS_LEVEL DENS_VIEWS DENS_FUSE TARGET_FACES REFINE_SCALES <<< "$(
    "$MILO_PY" - "$PHOTOGRAMMETRY/pipeline/config/pipeline_config.yaml" <<'PY'
import sys, yaml
c = yaml.safe_load(open(sys.argv[1]))
fe = c["colmap"]["feature_extractor"]; mt = c["colmap"]["exhaustive_matcher"]
mp = c["colmap"]["mapper"];            un = c["colmap"]["image_undistorter"]
de = c["openmvs"]["densify"];          rc = c["openmvs"]["reconstruct"]
rf = c["openmvs"].get("refine", {})
print(fe.get("max_image_size",4096), fe.get("max_num_features",16000),
      fe.get("domain_size_pooling",1), mt.get("guided_matching",1),
      mp.get("init_min_tri_angle",2.0), mp.get("abs_pose_min_num_inliers",15),
      mp.get("abs_pose_min_inlier_ratio",0.18), un.get("max_image_size",6000),
      de.get("resolution_level",0), de.get("number_views",8),
      de.get("number_views_fuse",5), rc.get("target_face_num",10000000),
      rf.get("scales",2))
PY
)"
echo "capture settings from your config: features=$MAX_FEAT dsp=$DSP tri=$TRI_ANGLE dens_level=$DENS_LEVEL"

mkdir -p "$W"
DB="$W/database.db"

step() { echo; echo "=== $* ($(date +%H:%M:%S)) ==="; }

# COLMAP 4.1.1 segfaults in __run_exit_handlers AFTER completing its work — feature
# extraction processed all 68 images, wrote a 205 MB database with keypoints for every
# one, and then crashed on the way out. `set -e` killed the job on a step that had
# succeeded.
#
# So exit codes are not the test here; results are. That is the better instrument anyway:
# every other failure today came from a check that reported something other than what it
# claimed to measure. run_colmap tolerates the crash and the CALLER must verify the
# artefact it wanted.
COLMAP_EXIT_CRASH=0
run_colmap() {
    local rc=0
    "$@" || rc=$?
    if [[ $rc -ne 0 ]]; then
        if [[ $rc -eq 139 || $rc -eq $((128+11)) ]]; then
            echo "  [colmap exited with SIGSEGV ($rc) — known shutdown crash;" \
                 "judging by output instead]"
            COLMAP_EXIT_CRASH=1
        else
            echo "  [colmap exited $rc]" >&2
            return $rc
        fi
    fi
    return 0
}

# How many images have keypoints, straight out of the database.
db_images_with_features() {
    "$MILO_PY" - "$1" <<'PY' 2>/dev/null || echo 0
import sqlite3, sys
c = sqlite3.connect(sys.argv[1])
print(c.execute("select count(*) from keypoints where rows>0").fetchone()[0])
PY
}

db_verified_pairs() {
    "$MILO_PY" - "$1" <<'PY' 2>/dev/null || echo 0
import sqlite3, sys
c = sqlite3.connect(sys.argv[1])
print(c.execute("select count(*) from two_view_geometries where rows>0").fetchone()[0])
PY
}

# ---------------------------------------------------------------------------- features
if [[ "$STAGE" == "mvs" ]]; then
    DENSE="$W/dense"
    [[ -d "$DENSE/images" && -d "$DENSE/sparse" ]] || {
        echo "STAGE=mvs but no undistorted workspace at $DENSE." >&2
        echo "Run STAGE=colmap first." >&2; exit 1; }
    echo "STAGE=mvs: reusing the undistorted workspace from the COLMAP stage"
    echo "  views: $(ls "$DENSE/images" | wc -l)"
else

# Existence of the database is NOT evidence that it is usable. The previous run crashed
# after feature extraction and before matching, leaving a 205 MB database with keypoints
# for all 68 images and zero matches — and this check, which only looked for the file,
# skipped matching and handed global_mapper an empty correspondence graph. It crashed in
# two seconds and registered nothing. Ask the database what it actually contains.
HAVE_FEATURES=0; HAVE_PAIRS=0
if [[ -f "$DB" ]]; then
    HAVE_FEATURES=$(db_images_with_features "$DB")
    HAVE_PAIRS=$(db_verified_pairs "$DB")
    echo "existing database: $HAVE_FEATURES images with features, $HAVE_PAIRS verified pairs"
fi

if [[ "$HAVE_FEATURES" -lt "$N" ]]; then
    # COLMAP 4.x SPLIT these options: generic ones (use_gpu, max_image_size, gpu_index,
    # num_threads, type) moved to FeatureExtraction.* / FeatureMatching.*, while
    # SIFT-specific ones (max_num_features, domain_size_pooling, peak_threshold) stayed
    # under SiftExtraction.* / SiftMatching.*. Passing the 3.9 names makes 4.1.1 abort
    # with "unrecognised option '--SiftExtraction.use_gpu'" and then segfault in its exit
    # handler, which looks like a crash but is only a parse failure.
    step "feature extraction"
    run_colmap colmap feature_extractor \
        --database_path "$DB" --image_path "$IMAGES" \
        --ImageReader.single_camera 1 \
        --FeatureExtraction.use_gpu 1 \
        --FeatureExtraction.max_image_size "$MAX_IMG" \
        --SiftExtraction.max_num_features "$MAX_FEAT" \
        --SiftExtraction.domain_size_pooling "$DSP"

    FEAT_IMAGES=$(db_images_with_features "$DB")
    echo "  images with features: $FEAT_IMAGES of $N"
    [[ "$FEAT_IMAGES" -ge "$N" ]] || {
        echo "Feature extraction did not cover every photograph." >&2; exit 1; }
else
    echo "features already present for all $N photographs — skipping extraction"
fi

if [[ "$HAVE_PAIRS" -le 0 ]]; then
    step "exhaustive matching"
    run_colmap colmap exhaustive_matcher \
        --database_path "$DB" \
        --FeatureMatching.use_gpu 1 \
        --FeatureMatching.guided_matching "$GUIDED"

    PAIRS=$(db_verified_pairs "$DB")
    echo "  geometrically verified image pairs: $PAIRS"
    [[ "$PAIRS" -gt 0 ]] || { echo "Matching produced no verified pairs." >&2; exit 1; }
else
    echo "matches already present ($HAVE_PAIRS verified pairs) — skipping matching"
fi

# ----------------------------------------------------------------------------- mapping
SPARSE="$W/sparse"
rm -rf "$SPARSE"; mkdir -p "$SPARSE"

if [[ "$MAPPER" == "global" ]]; then
    step "global mapper (GLOMAP)"
    run_colmap colmap global_mapper \
        --database_path "$DB" --image_path "$IMAGES" --output_path "$SPARSE"
else
    step "incremental mapper (multiple models allowed)"
    run_colmap colmap mapper \
        --database_path "$DB" --image_path "$IMAGES" --output_path "$SPARSE" \
        --Mapper.multiple_models 1 \
        --Mapper.init_min_tri_angle "$TRI_ANGLE" \
        --Mapper.abs_pose_min_num_inliers "$MIN_INLIERS" \
        --Mapper.abs_pose_min_inlier_ratio "$MIN_RATIO" \
        --Mapper.ba_refine_principal_point 0 \
        --Mapper.num_threads "$NPROC"
fi

step "select the model with the most registered images"
# Not sorted(dirs)[0]. That is the bug in run_colmap.py: it sorts by directory name and
# calls the result "largest", so a 2-image sparse/0 wins over a 68-image sparse/1.
BEST=$("$MILO_PY" - "$SPARSE" "$N" <<'PY'
import glob, os, sys, importlib.util
spec = importlib.util.spec_from_file_location(
    "cl", "/data/gpfs/projects/punim2657/MILo/repo/milo/scene/colmap_loader.py")
cl = importlib.util.module_from_spec(spec); spec.loader.exec_module(cl)
root, total = sys.argv[1], int(sys.argv[2])
best, best_n, report = None, -1, []
for d in sorted(glob.glob(os.path.join(root, "*"))):
    f = os.path.join(d, "images.bin")
    if not os.path.exists(f):
        continue
    n = len(cl.read_extrinsics_binary(f))
    report.append(f"  {os.path.basename(d)}: {n} images")
    if n > best_n:
        best, best_n = d, n
print("\n".join(report), file=sys.stderr)
print(f"  chosen: {os.path.basename(best) if best else 'none'} "
      f"({best_n} of {total} photographs)", file=sys.stderr)
print(best or "")
PY
)
[[ -n "$BEST" ]] || { echo "No sparse model was produced." >&2; exit 1; }

REG=$("$MILO_PY" -c "
import importlib.util
spec = importlib.util.spec_from_file_location('cl','$MILO_REPO/milo/scene/colmap_loader.py')
cl = importlib.util.module_from_spec(spec); spec.loader.exec_module(cl)
print(len(cl.read_extrinsics_binary('$BEST/images.bin')))")
echo "registered $REG of $N photographs"
if [[ "$REG" -lt $(( N / 2 )) ]]; then
    echo "Fewer than half the photographs registered. Stopping: everything downstream" >&2
    echo "would be a reconstruction of a fraction of the object." >&2
    exit 1
fi

# global_mapper solves camera POSES but writes no 3D points: it left points3D.bin at 8
# bytes — an empty table — while images.bin held 33 MB of observations for all 68 views.
# OpenMVS then reported "empty point-cloud" and refused, because it seeds dense matching
# from the sparse cloud. point_triangulator fills that in from the poses and the matches
# already in the database. The incremental mapper triangulates as it goes and does not
# need this, so the step is conditional on the count rather than on the mapper.
NPOINTS=$("$MILO_PY" -c "
import importlib.util
spec = importlib.util.spec_from_file_location('cl','$MILO_REPO/milo/scene/colmap_loader.py')
cl = importlib.util.module_from_spec(spec); spec.loader.exec_module(cl)
print(len(cl.read_points3D_binary('$BEST/points3D.bin')[0]))" 2>/dev/null || echo 0)
echo "3D points in the chosen model: $NPOINTS"

if [[ "$NPOINTS" -eq 0 ]]; then
    step "triangulate points from the solved poses"
    TRI="$W/sparse/triangulated"
    rm -rf "$TRI"; mkdir -p "$TRI"
    run_colmap colmap point_triangulator \
        --database_path "$DB" --image_path "$IMAGES" \
        --input_path "$BEST" --output_path "$TRI"
    NPOINTS=$("$MILO_PY" -c "
import importlib.util
spec = importlib.util.spec_from_file_location('cl','$MILO_REPO/milo/scene/colmap_loader.py')
cl = importlib.util.module_from_spec(spec); spec.loader.exec_module(cl)
print(len(cl.read_points3D_binary('$TRI/points3D.bin')[0]))" 2>/dev/null || echo 0)
    echo "  triangulated 3D points: $NPOINTS"
    [[ "$NPOINTS" -gt 0 ]] || {
        echo "Triangulation produced no points; dense reconstruction cannot proceed." >&2
        exit 1; }
    BEST="$TRI"
fi

# Undistortion expects the chosen model; give it its own directory rather than renaming,
# so which model was used stays visible afterwards.
step "undistort"
DENSE="$W/dense"
rm -rf "$DENSE"
run_colmap colmap image_undistorter \
    --image_path "$IMAGES" --input_path "$BEST" --output_path "$DENSE" \
    --max_image_size "$UNDIST_MAX"

fi   # end of the COLMAP stage (skipped entirely when STAGE=mvs)

if [[ "$STAGE" == "colmap" ]]; then
    echo
    echo "=== STAGE=colmap: stopping after undistortion ==="
    echo "Registered $REG of $N photographs into $(basename "$BEST")."
    echo "Dense reconstruction next:"
    echo "  STAGE=mvs sbatch slurm/reconstruct_group.slurm $GROUP"
    echo "=== finished $(date) ==="
    exit 0
fi

# ----------------------------------------------------------------------------- OpenMVS
export LD_LIBRARY_PATH="$SFM_ENV/lib:${LD_LIBRARY_PATH:-}"
# -w "$W" on EVERY tool, not just the interface. The scene file stores image paths
# relative to a working directory, so without it the later tools resolve them against the
# process CWD — which is the repo — and DensifyPointCloud died looking for
# '/data/.../MILo/repo/dense/images/A11_0704.JPG'.
step "OpenMVS: interface"
"$OPENMVS_BIN/InterfaceCOLMAP" -w "$W" -i "$DENSE" -o "$W/scene.mvs" \
    --image-folder "$DENSE/images"

step "OpenMVS: dense point cloud"
"$OPENMVS_BIN/DensifyPointCloud" -w "$W" -i "$W/scene.mvs" -o "$W/scene_dense.mvs" \
    --cuda-device 0 --resolution-level "$DENS_LEVEL" \
    --number-views "$DENS_VIEWS" --number-views-fuse "$DENS_FUSE"

step "OpenMVS: mesh"
"$OPENMVS_BIN/ReconstructMesh" -w "$W" -i "$W/scene_dense.mvs" -p "$W/scene_dense.ply" \
    -o "$W/scene_dense_mesh.ply" --target-face-num "$TARGET_FACES"

step "OpenMVS: refine"
"$OPENMVS_BIN/RefineMesh" -w "$W" -i "$W/scene_dense.mvs" -m "$W/scene_dense_mesh.ply" \
    -o "$W/scene_refined_mesh.ply" --scales "$REFINE_SCALES" --cuda-device 0 \
    || echo "(refinement failed; the unrefined mesh is still usable)"

# ------------------------------------------------------------------------------ sherds
step "extract sherd-shaped components"
MESH="$W/scene_refined_mesh.ply"
[[ -f "$MESH" ]] || MESH="$W/scene_dense_mesh.ply"
"$MILO_PY" "$MILO_REPO/scripts/extract_sherds.py" \
    --mesh "$MESH" --out "$W/sherds" || echo "(extraction failed; the mesh is still there)"

step "done"
ls -lh "$W"/*.ply 2>/dev/null | awk '{print $5, $9}'
echo
echo "LOOK AT $W/sherds/contact_sheet.png before trusting the selection."
echo "=== finished $(date) ==="
