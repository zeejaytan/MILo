#!/bin/bash
#SBATCH --job-name=render-meshes
#SBATCH --account=punim2657
#SBATCH --partition=sapphire
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=0:30:00
#SBATCH --output=/data/gpfs/projects/punim2657/MILo/logs/render_meshes_%j.log

set -uo pipefail

# Render every mesh a capture has produced, in one place, so that the workspace rule
# "render geometry before reporting any result about it" has a job behind it rather than a
# paragraph. Until now render_mesh.py had no caller anywhere in the repo: it was run by
# hand each time, which meant the environment it needs was recorded nowhere and had to be
# rediscovered. It was rediscovered the expensive way -- a job submitted against tools/sfm,
# which has no trimesh, and four identical ModuleNotFoundErrors.
#
# THE ENVIRONMENT IS THE POINT OF THIS FILE. render_mesh.py needs trimesh; of the three
# environments on this project only MILo/envs/milo has it (4.6.8). Checked, not assumed.
#
# No GPU. render_mesh.py is a z-buffered splat of the vertices -- a few seconds per mesh
# even at 2.8M vertices, which is why this asks for half an hour and not two.
#
# Usage:
#   sbatch slurm/render_meshes.slurm 03072025/N01 [dense-subdir]

CAPTURE="${1:?usage: sbatch render_meshes.slurm <date>/<tree> [dense-subdir]}"
DENSE_DIR="${2:-dense_masked}"

MILO=/data/gpfs/projects/punim2657/MILo
REPO=$MILO/repo
D="/data/gpfs/projects/punim2657/Rabati2025/$CAPTURE/work_colmap_openmvs/$DENSE_DIR"
M="$MILO/output/$CAPTURE"
OUT="$MILO/renders/$CAPTURE"

echo "=== rendering $CAPTURE ($DENSE_DIR) started $(date) ==="

module purge
module load Miniforge3/24.7.1-2
eval "$(conda shell.bash hook)"
conda activate "$MILO/envs/milo"
export PYTHONNOUSERSITE=1
export OMP_NUM_THREADS="${SLURM_CPUS_PER_TASK:-8}"

mkdir -p "$OUT"
cd "$REPO"

# The four surface methods, labelled by what a reader needs to know about each one rather
# than by its filename. Prefer the millimetre copy where one exists: it is the same
# geometry, and rendering the scaled mesh keeps the printed measurements in real units.
render() {
    local base="$1" label="$2"
    local mesh="$base"
    [[ -s "${base%.ply}_mm.ply" ]] && mesh="${base%.ply}_mm.ply"
    if [[ ! -s "$mesh" ]]; then
        echo "  MISSING: $(basename "$base") -- not built yet, skipping"
        return 1
    fi
    echo
    echo "--- $label: $(basename "$mesh") ---"
    python scripts/render_mesh.py --mesh "$mesh" --out "$OUT" --label "$label"
}

n=0
render "$D/scene_refined_mesh.ply"   "OpenMVS refined"    && n=$((n+1))
render "$D/colmap_delaunay_mesh.ply" "COLMAP Delaunay"    && n=$((n+1))
render "$D/colmap_poisson_mesh.ply"  "COLMAP Poisson"     && n=$((n+1))
render "$M/mesh_learnable_sdf.ply"   "MILo learnable SDF" && n=$((n+1))

echo
echo "=== $n of 4 surfaces rendered into $OUT ==="
if [[ "$n" -lt 4 ]]; then
    echo "Fewer than four is not necessarily a failure -- it usually means a stage has not"
    echo "run yet. It IS a reason not to compare methods on this capture: a missing surface"
    echo "reads as agreement between the ones that are present."
fi
echo "LOOK AT THEM. The connected-component count printed on each picture is the honest"
echo "inventory: the sherds should come out as separate objects, and a large slab that is"
echo "the room rather than the tray shows up there first."
echo "=== finished $(date) ==="
exit 0
