#!/bin/bash
#SBATCH --job-name=delaunay-sweep
#SBATCH --account=punim2657
#SBATCH --partition=sapphire
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=32
#SBATCH --mem=500G
#SBATCH --time=12:00:00
#SBATCH --output=/data/gpfs/projects/punim2657/MILo/logs/delaunay_sweep_%j.log

set -uo pipefail

# How fine should COLMAP's Delaunay mesher be for sherd fracture faces?
#
# At the default the mesh came out at 270,576 vertices / 542,301 faces -- coarse enough
# that the sherds read as lumps. That is not a failure: the header is explicit that
#
#   max_proj_dist = 20.0   "Unify input points into one cell in the Delaunay
#                           triangulation that fall within a reprojected radius of the
#                           given pixels."
#
# Twenty PIXELS. It merged 6,918,325 fused points down to 270,576 vertices, a 25x
# reduction, before triangulating. COLMAP's FAQ and the community parameter reference both
# say the same thing and nothing more: lower it if the mesh is too coarse. Nobody
# publishes actual values, so these two are arithmetic (halving roughly quadruples the
# cells), not received wisdom.
#
# Why bother, when Poisson already gives 3M faces with colour: because the two methods
# fail in opposite directions and only one of them suits this material. COLMAP's own FAQ
# says Delaunay "is the only model that can theoretically represent sharp edges", while
# Poisson "tends to produce bubble-like objects" and needs outlier-free input. Fracture
# faces are sharp edges by definition, so the comparison is unfair until Delaunay is run
# at a resolution that lets it show what it is for.
#
# Deliberately NOT textured. For judging whether an edge is sharp, an untextured shaded
# mesh is the honest instrument -- photographic texture can make a rounded-off edge look
# crisp. Texture later, once the geometry has been judged.
#
# Sizing: the default run peaked at 11.6 GB and took 4m32s, so 500G is generous. The finer
# case is run second and each mesh is written as it completes, so a failure at 5 does not
# cost the result at 10.
#
# Usage:
#   sbatch slurm/delaunay_sweep.slurm [dense-workspace]

W="${1:-/data/gpfs/projects/punim2657/Rabati2025/16062025/work_colmap_openmvs/dense_incremental}"

module purge
module load Miniforge3/24.7.1-2
eval "$(conda shell.bash hook)"
conda activate /data/gpfs/projects/punim2657/tools/sfm
export PYTHONNOUSERSITE=1

stats() {
    [[ -s "$1" ]] || { echo "  $(basename "$1"): MISSING"; return 1; }
    local v f
    v=$(head -c 2000 "$1" | grep -a -m1 "element vertex" | awk '{print $3}')
    f=$(head -c 2000 "$1" | grep -a -m1 "element face" | awk '{print $3}')
    printf "  %-36s %12s vertices  %12s faces  %6s\n" \
        "$(basename "$1")" "${v:-?}" "${f:-?}" "$(du -h "$1" | cut -f1)"
}

echo "=== Delaunay resolution sweep on $W ==="
echo "started $(date) on $(hostname)"
[[ -f "$W/fused.ply" && -f "$W/fused.ply.vis" ]] || {
    echo "Need both fused.ply and fused.ply.vis -- delaunay_mesher reads the workspace" >&2
    echo "by convention and needs the visibility file, not just the cloud." >&2
    exit 1; }

for d in 10 5; do
    out="$W/colmap_delaunay_p${d}.ply"
    echo
    echo "=== max_proj_dist $d  ($(date +%H:%M:%S)) ==="
    if [[ -s "$out" ]]; then
        echo "  already present, skipping"; stats "$out"; continue
    fi
    /usr/bin/time -v colmap delaunay_mesher \
        --input_path "$W" --input_type dense --output_path "$out" \
        --DelaunayMeshing.max_proj_dist "$d" \
        --DelaunayMeshing.num_threads "${SLURM_CPUS_PER_TASK:-32}" \
        2> >(grep -E "Maximum resident|Elapsed \(wall" >&2)
    echo "  (exit $? -- judged by the file below)"
    stats "$out" || echo "  -> nothing written at max_proj_dist $d"
done

echo
echo "=== every Delaunay mesh, coarsest first ==="
stats "$W/colmap_delaunay_mesh.ply"   # the default, max_proj_dist 20
for d in 10 5; do stats "$W/colmap_delaunay_p${d}.ply" 2>/dev/null; done
echo
echo "For reference, the other methods on the same poses:"
stats "$W/colmap_poisson_d11_t12.ply"
stats "$W/scene_refined_mesh.ply"
echo
echo "LOOK AT THESE before choosing. The question is not which has the most faces --"
echo "it is which keeps a fracture edge as an edge."
echo "=== finished $(date) ==="
