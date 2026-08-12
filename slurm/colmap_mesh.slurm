#!/bin/bash
#SBATCH --job-name=colmap-mesh
#SBATCH --account=punim2657
#SBATCH --partition=gpu-a100-short
#SBATCH --gres=gpu:1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=120G
#SBATCH --time=4:00:00
#SBATCH --output=/data/gpfs/projects/punim2657/MILo/logs/colmap_mesh_%j.log

set -uo pipefail   # NOT -e: colmap segfaults in its exit handlers after finishing its work

# COLMAP's OWN dense pipeline, as a third method independent of OpenMVS.
#
# Same camera poses, same undistorted photographs, different machinery the whole way down:
# COLMAP computes its own depth maps, fuses its own point cloud, and extracts its own
# surface. It has no ROI estimation and no automatic decimation, which are the two
# OpenMVS 2.4.0 defaults that damaged the first mesh -- so it is also a check on whether
# those were really the whole story.
#
# Following COLMAP's own tutorial (doc/tutorial.rst, "Dense Reconstruction"):
#   image_undistorter -> patch_match_stereo -> stereo_fusion -> poisson_mesher
#                                                            -> delaunay_mesher
# Undistortion is already done by dense_from_model.slurm, so this starts at stereo.
#
# BOTH meshers are run, because they fail in opposite directions and the choice is a
# judgement about the object, not about the software:
#   poisson   watertight and smooth; rounds off sharp features -- a fracture edge included
#   delaunay  graph-cut on point visibility; keeps edges, but can leave holes
#
# From doc/faq.rst: cache_size is in GIGABYTES and is CPU memory, so it must stay well
# under the job's allocation; geom_consistency raises GPU memory but is what makes the
# depth maps trustworthy; and patch-match is RESUMABLE -- "any already processed views
# will be skipped" -- so a wall-clock timeout costs only a resubmit, not the work.
#
# Usage:
#   sbatch slurm/colmap_mesh.slurm 16062025 dense_incremental

CAPTURE="${1:?usage: sbatch colmap_mesh.slurm <capture> [dense-subdir]}"
DENSE_DIR="${2:-dense_incremental}"

TOOLS=/data/gpfs/projects/punim2657/tools
SFM_ENV=$TOOLS/sfm
MILO=/data/gpfs/projects/punim2657/MILo
W="/data/gpfs/projects/punim2657/Rabati2025/$CAPTURE/work_colmap_openmvs"
DENSE="$W/$DENSE_DIR"

# Well under --mem=120G, leaving room for the fusion's own structures (FAQ: too low a
# value only makes it slow, whereas too high gets the job killed).
CACHE_GB="${CACHE_GB:-32}"

echo "=== COLMAP dense + mesh for $CAPTURE ($DENSE_DIR) started $(date) on $(hostname) ==="
[[ -d "$DENSE/images" ]] || { echo "No undistorted workspace at $DENSE" >&2; exit 1; }

module purge
module load Miniforge3/24.7.1-2
eval "$(conda shell.bash hook)"
conda activate "$SFM_ENV"
export PYTHONNOUSERSITE=1

step() { echo; echo "=== $* ($(date +%H:%M:%S)) ==="; }

step "turntable check"
python "$MILO/repo/scripts/check_turntable.py" "$DENSE/sparse" | tee /tmp/cm_$$.txt
grep -q "COLLAPSED" /tmp/cm_$$.txt && {
    echo "Model collapsed the turntable rotation; not meshing it." >&2; exit 1; }

nvidia-smi --query-gpu=name,memory.total --format=csv,noheader 2>/dev/null | sed 's/^/  GPU: /'

step "patch match stereo (resumable: processed views are skipped)"
colmap patch_match_stereo --workspace_path "$DENSE" --workspace_format COLMAP \
    --PatchMatchStereo.geom_consistency true \
    --PatchMatchStereo.cache_size "$CACHE_GB" \
    --PatchMatchStereo.gpu_index 0
echo "  (exit $? -- judged by the depth maps below)"
find "$DENSE/stereo/depth_maps" -name "*.geometric.bin" 2>/dev/null | wc -l \
    | xargs echo "  geometric depth maps:"

NIMG=$(ls "$DENSE/images" | wc -l)
NDEPTH=$(find "$DENSE/stereo/depth_maps" -name "*.geometric.bin" 2>/dev/null | wc -l)
if [[ "$NDEPTH" -lt "$NIMG" ]]; then
    echo
    echo "Only $NDEPTH of $NIMG views have depth maps. Stereo did not finish -- most" >&2
    echo "likely the 4-hour limit. Resubmit this same job: COLMAP skips completed views." >&2
    exit 1
fi

# The fused cloud MUST be written as <workspace>/fused.ply. delaunay_mesher with
# --input_type dense takes no point-cloud path: it reads the workspace by convention and
# looks for exactly that filename. Calling it colmap_fused.ply made it abort one second
# after starting -- "Could not open .../fused.ply" -- while stereo fusion before it and
# the Poisson mesher after it both worked, so the job still reported a mesh.
step "stereo fusion"
colmap stereo_fusion --workspace_path "$DENSE" --workspace_format COLMAP \
    --input_type geometric --output_path "$DENSE/fused.ply" \
    --StereoFusion.cache_size "$CACHE_GB"
echo "  (exit $?)"
ls -lh "$DENSE/fused.ply" 2>/dev/null | awk '{print "  fused cloud:", $5}'
[[ -s "$DENSE/fused.ply" ]] || { echo "Fusion produced nothing." >&2; exit 1; }

step "delaunay mesher (keeps sharp edges)"
colmap delaunay_mesher --input_path "$DENSE" --input_type dense \
    --output_path "$DENSE/colmap_delaunay_mesh.ply"
echo "  (exit $?)"

step "poisson mesher (watertight, smoother)"
colmap poisson_mesher --input_path "$DENSE/fused.ply" \
    --output_path "$DENSE/colmap_poisson_mesh.ply"
echo "  (exit $?)"

step "done"
ls -lh "$DENSE"/colmap_*.ply 2>/dev/null | awk '{print $5, $9}'
[[ -s "$DENSE/colmap_delaunay_mesh.ply" || -s "$DENSE/colmap_poisson_mesh.ply" ]] || {
    echo "No mesh was produced." >&2; exit 1; }
echo
echo "Compare against the OpenMVS meshes in the same directory:"
echo "  scene_dense_mesh.ply / scene_refined_mesh.ply   (OpenMVS)"
echo "  colmap_delaunay_mesh.ply / colmap_poisson_mesh.ply   (COLMAP)"
echo "Same photographs, same camera poses. Any difference is the surface method."
echo "=== finished $(date) ==="
