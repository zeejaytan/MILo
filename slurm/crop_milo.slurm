#!/bin/bash
#SBATCH --job-name=crop-milo
#SBATCH --account=punim2657
#SBATCH --partition=sapphire
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=96G
#SBATCH --time=1:00:00
#SBATCH --output=/data/gpfs/projects/punim2657/MILo/logs/crop_milo_%j.log

set -uo pipefail

# Cut the MILo surface down to the volume the photogrammetric methods agree on, put it in
# millimetres, and look at it.
#
# WHAT QUESTION THIS ANSWERS, AND WHAT IT DOES NOT. On 03072025/N01 the MILo mesh came out
# 2.76 m across with 8,860 pieces, while OpenMVS and the two COLMAP surfaces agreed on a
# box 59 cm across holding a tray and eleven sherds. Cropping to that box asks one thing:
# are the sherds in there underneath the junk? If they are, the mask cull under-removed and
# there is a carve step to write. If they are not, MILo failed on this capture and the
# honest answer is that N01 has three surfaces, not four.
#
# It is NOT a fix. Everything outside the box is thrown away without being looked at, so a
# crop cannot tell you whether the surface out there was studio or was more of the object.
# Read the result as a picture of the box, not as a repaired mesh.
#
# TWO ENVIRONMENTS ON PURPOSE. crop_mesh.py and render_mesh.py need trimesh, which of the
# three environments on this project only MILo/envs/milo has (4.6.8). scale_mesh.py reads a
# COLMAP model and runs in tools/sfm. Checked, not assumed -- a job submitted against the
# wrong one is how the first render attempt died.
#
# Usage:
#   sbatch slurm/crop_milo.slurm 03072025/N01 [dense-subdir]

CAPTURE="${1:?usage: sbatch crop_milo.slurm <date>/<tree> [dense-subdir]}"
DENSE_DIR="${2:-dense_incremental}"

MILO=/data/gpfs/projects/punim2657/MILo
REPO=$MILO/repo
D="/data/gpfs/projects/punim2657/Rabati2025/$CAPTURE/work_colmap_openmvs/$DENSE_DIR"
M="$MILO/output/$CAPTURE"
OUT="$MILO/renders/$CAPTURE"
REF="$REPO/docs/reference/turntable-board-${CAPTURE//\//-}.json"

MESH="$M/mesh_learnable_sdf.ply"
CROP="$M/mesh_learnable_sdf_cropped.ply"
CROP_MM="$M/mesh_learnable_sdf_cropped_mm.ply"

echo "=== cropping $CAPTURE started $(date) on $(hostname) ==="

[[ -s "$MESH" ]] || { echo "No MILo mesh at $MESH" >&2; exit 1; }

# The box comes from the UNSCALED meshes, because the MILo mesh is unscaled. Mixing a
# millimetre reference with an arbitrary-unit target would put the box 388x too large,
# keep everything, and look exactly like a crop that found the object.
BOXA="$D/colmap_delaunay_mesh.ply"
BOXB="$D/scene_refined_mesh.ply"
for f in "$BOXA" "$BOXB"; do
    [[ -s "$f" ]] || { echo "Missing reference mesh $f -- cannot derive a box." >&2; exit 1; }
    if head -c 4096 "$f" | grep -q "units: millimetres"; then
        echo "$f is already in millimetres. The box must come from an UNSCALED mesh." >&2
        exit 1
    fi
done

module purge
module load Miniforge3/24.7.1-2
eval "$(conda shell.bash hook)"
export PYTHONNOUSERSITE=1
export OMP_NUM_THREADS="${SLURM_CPUS_PER_TASK:-8}"
cd "$REPO"

conda activate "$MILO/envs/milo"

echo
echo "--- crop ---"
python scripts/crop_mesh.py \
    --mesh "$MESH" --box-from "$BOXA" --box-from "$BOXB" --out "$CROP" || exit 1

echo
echo "--- scale ---"
conda activate /data/gpfs/projects/punim2657/tools/sfm
if [[ -f "$REF" && -d "$D/sparse" ]]; then
    python scripts/scale_mesh.py \
        --mesh "$CROP" --out "$CROP_MM" \
        --board-reference "$REF" --model "$D/sparse" \
        --capture "$CAPTURE" --method "mesh_learnable_sdf_cropped"
else
    echo "  no board reference or model -- leaving the crop in arbitrary units."
fi

echo
echo "--- render ---"
conda activate "$MILO/envs/milo"
TO_RENDER="$CROP"
[[ -s "$CROP_MM" ]] && TO_RENDER="$CROP_MM"
python scripts/render_mesh.py --mesh "$TO_RENDER" --out "$OUT" --label "MILo, cropped to the agreed box"

echo
echo "LOOK AT IT. The piece count is the answer: eleven-ish separate bodies of comparable"
echo "size means the sherds are there and the cull under-removed. One dominant body, or"
echo "thousands of specks, means the box is full of the same surface the wide view showed."
echo "=== finished $(date) ==="
