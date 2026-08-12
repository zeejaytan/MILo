#!/bin/bash
#SBATCH --job-name=poisson-trim
#SBATCH --account=punim2657
#SBATCH --partition=sapphire
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=16
#SBATCH --mem=200G
#SBATCH --time=2:00:00
#SBATCH --output=/data/gpfs/projects/punim2657/MILo/logs/poisson_trim_%j.log

set -uo pipefail

# Make the Poisson mesh openable, two ways.
#
# The first attempt came out at 23.6M vertices / 47.2M faces / 1.2 GB. Two reasons, both
# from COLMAP's defaults rather than from the data:
#
#   depth = 13   COLMAP's default octree depth. Poisson's own default is 8, and each level
#                roughly quadruples the face count.
#   trim  = 10   The header is explicit: "The subset of the mesh with signal value less
#                than the trim value is discarded", so a HIGHER value discards more.
#                COLMAP's own FAQ says the opposite ("reduce the value ... to decrease the
#                surface area"); the source is authoritative and the FAQ is wrong.
#
# A. simplify what we already have -- faithful to the existing surface, nothing recomputed.
# B. rebuild at a sane depth and a firmer trim -- removes the shell Poisson invents over
#    empty space and the backdrop, which is wrongness rather than merely size.
#
# Usage:
#   sbatch slurm/poisson_trim.sh <dense-workspace>

W="${1:-/data/gpfs/projects/punim2657/Rabati2025/16062025/work_colmap_openmvs/dense_incremental}"

module purge
module load Miniforge3/24.7.1-2
eval "$(conda shell.bash hook)"
conda activate /data/gpfs/projects/punim2657/tools/sfm
export PYTHONNOUSERSITE=1

stats() {
    [[ -s "$1" ]] || { echo "  $(basename "$1"): MISSING"; return; }
    local v f
    v=$(head -c 2000 "$1" | grep -a -m1 "element vertex" | awk '{print $3}')
    f=$(head -c 2000 "$1" | grep -a -m1 "element face" | awk '{print $3}')
    printf "  %-34s %12s vertices  %12s faces  %6s\n" \
        "$(basename "$1")" "${v:-?}" "${f:-?}" "$(du -h "$1" | cut -f1)"
}

echo "=== A. simplify the existing mesh (no recompute) $(date +%H:%M:%S) ==="
colmap mesh_simplifier \
    --input_path "$W/colmap_poisson_mesh.ply" \
    --output_path "$W/colmap_poisson_simplified.ply" \
    --MeshSimplification.target_face_ratio 0.05
echo "  exit=$?"
stats "$W/colmap_poisson_simplified.ply"

echo
echo "=== B. rebuild at depth 11, trim 12 $(date +%H:%M:%S) ==="
colmap poisson_mesher \
    --input_path "$W/fused.ply" \
    --output_path "$W/colmap_poisson_d11_t12.ply" \
    --PoissonMeshing.depth 11 \
    --PoissonMeshing.trim 12
echo "  exit=$?"
stats "$W/colmap_poisson_d11_t12.ply"

echo
echo "=== every mesh in the workspace $(date +%H:%M:%S) ==="
for f in "$W"/*.ply; do stats "$f"; done
echo "=== finished $(date) ==="
