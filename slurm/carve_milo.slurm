#!/bin/bash
#SBATCH --job-name=milo-carve
#SBATCH --account=punim2657
#SBATCH --partition=sapphire
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=2:00:00
#SBATCH --output=/data/gpfs/projects/punim2657/MILo/logs/milo_carve_%j.log

set -euo pipefail

# Cut the sherds out of a MILo mesh that was trained WITHOUT masks.
#
# Unmasked training reconstructs the studio, so the raw mesh is a room with the sherd rig
# somewhere inside it. ONE cut does the whole job: carve the mesh against the SHERD-ONLY
# SAM 3 masks, which outline the ten sherds and nothing else -- not the clamp, not the
# dial, not the scale bar.
#
# WHY NOT THE COLOUR CUT THIS SCRIPT USED TO DO. It carved against the object mask (rig
# included) and then tried to drop the grey rig by keeping only terracotta-coloured
# vertices. That destroyed the result: sweeping the redness threshold over the carved A03
# body gives 12 sherd-sized pieces at a threshold of 5 and only 5 at the threshold that
# ran, and across the whole body the redness spread is -62 to +47 with a median of -2.
# The sherds are barely redder than the rig, so no threshold separates them cleanly.
# Colour was the wrong instrument; the sherd masks are the right one and already exist.
#
# WHY THE DILATED MASK VARIANT. This cut is subtractive -- a vertex outside the outline is
# deleted -- so a mask that is slightly too tight removes real sherd, and the surface it
# removes first is the break edge, which sits near the silhouette in most views. Erosion
# is for the photometric side of the pipeline ("grow for solving, shrink for building");
# for carving, grow.
#
# --tol stays at its default 0.40 for the same reason: colouring a carved A03 sherd by
# silhouette support showed the marginal 0.60-0.90 band covers the ENTIRE fracture
# surface (docs/notes/A03_BENT_SOLVE_AND_CLAMP_ARTEFACTS.md).
#
# Usage:
#   ./scripts/remote/pull_and_sbatch.sh slurm/carve_milo.slurm 17062025/A03 17062025/A03_nomask
#   ./scripts/remote/pull_and_sbatch.sh slurm/carve_milo.slurm 17062025/A03 17062025/A03_nomask A03_erode0

CAPTURE="${1:?usage: sbatch carve_milo.slurm <capture> [output_name] [mask_variant]}"
OUT_NAME="${2:-$CAPTURE}"

MILO_ROOT=/data/gpfs/projects/punim2657/MILo
REPO_DIR=$MILO_ROOT/repo
ENV_PREFIX=$MILO_ROOT/envs/milo
DATA_DIR=$MILO_ROOT/data/$CAPTURE
OUT_DIR=$MILO_ROOT/output/$OUT_NAME

CAP_DATE=${CAPTURE%%/*}
CAP_TREE=${CAPTURE##*/}
VARIANT="${3:-${CAP_TREE}_dilated}"

WORK=$(python3 -c "import json;print(json.load(open('$DATA_DIR/capture.json'))['work_dir'])")
DENSE="$WORK/dense_fixed"
MASK_SRC="$MILO_ROOT/masks/$CAP_DATE/$VARIANT/masks_sherds"
UND_ROOT="$MILO_ROOT/masks_und/${CAP_DATE}_${VARIANT}_sherds"

MESH="$OUT_DIR/mesh_learnable_sdf.ply"
CARVED="$OUT_DIR/mesh_sherds.ply"

echo "=== carving sherds out of $OUT_NAME started $(date) on $(hostname) ==="
echo "  mesh        : $MESH"
echo "  dense       : $DENSE"
echo "  sherd masks : $MASK_SRC"

[[ -f "$MESH" ]]     || { echo "No mesh at $MESH" >&2; exit 1; }
[[ -d "$MASK_SRC" ]] || { echo "No sherd masks at $MASK_SRC" >&2; exit 1; }

module purge
module load Miniforge3/24.7.1-2
eval "$(conda shell.bash hook)"
conda activate "$ENV_PREFIX"

cd "$REPO_DIR"

# --- Undistort the sherd masks, once per (capture, variant) ---
# The masks are drawn on the original 5568 px photographs; every stage downstream works on
# COLMAP's undistorted 3200 px views. Re-segmenting the undistorted set would give a
# slightly different boundary and no two stages would then share a definition of "sherd".
NIMG=$(find "$DENSE/images" -maxdepth 1 -type f | wc -l)
# Ask whether the directory exists BEFORE counting in it. `find` on a missing path exits 1,
# and under `set -euo pipefail` that kills the job -- silently, because the 2>/dev/null
# that hides find's complaint hides the only clue. Job 29543316 died here in four seconds
# with an empty log.
if [[ -d "$UND_ROOT/colmap" ]]; then
    NUND=$(find "$UND_ROOT/colmap" -maxdepth 1 -name '*.png' | wc -l)
else
    NUND=0
fi
if [[ "$NUND" -eq "$NIMG" ]]; then
    echo "  undistorted sherd masks already present ($NUND) -- reusing $UND_ROOT/colmap"
else
    echo "=== undistorting sherd masks $(date) ==="
    mkdir -p "$UND_ROOT"
    ./scripts/undistort_masks.sh "$MASK_SRC" "$WORK/sparse/0" "$DENSE" "$UND_ROOT" 3200
fi

echo
echo "=== carving $(date) ==="
python scripts/silhouette_filter.py \
    --mesh "$MESH" --out "$CARVED" \
    --dense "$DENSE" --masks "$UND_ROOT/colmap" \
    --every 2 --min-piece 200

echo
echo "=== millimetres $(date) ==="
# capture.json records no scale factor for this capture, so take it from the two scale bars
# the capture actually measured rather than from a number remembered in a chat. They
# disagree slightly; the mean is used and the disagreement is printed, because it is the
# floor on any millimetre figure quoted from this mesh.
FACTOR=$(python3 - "$WORK/measurement.env" <<'PY'
import sys
env = dict(l.strip().split("=", 1) for l in open(sys.argv[1]) if "=" in l)
f1 = float(env["d1_real_m"]) / float(env["d1_rec_units"])
f2 = float(env["d2_real_m"]) / float(env["d2_rec_units"])
print(f"{(f1 + f2) / 2:.9f}")
print(f"  scale bar 1: {f1*1000:.2f} mm/unit", file=sys.stderr)
print(f"  scale bar 2: {f2*1000:.2f} mm/unit", file=sys.stderr)
print(f"  they disagree by {abs(f1-f2)/((f1+f2)/2)*100:.1f}% -- every millimetre figure "
      f"from this mesh carries at least that", file=sys.stderr)
PY
)

python scripts/apply_scale.py \
    --capture "$DATA_DIR/capture.json" \
    --mesh "$CARVED" \
    --out "$OUT_DIR/mesh_sherds_mm.ply" \
    --force-factor "$FACTOR"

python - "$OUT_DIR/mesh_sherds_mm.ply" <<'PY'
"""Say how many sherd-sized pieces came out, and how big each one is.

A03 holds TEN sherds -- masks.json reports 10 instances in every frame -- so a piece count
far from ten is the headline result of this job, not a footnote. It does not replace
looking at the mesh; it just makes an obvious failure obvious from the log."""
import sys
import numpy as np
import trimesh

m = trimesh.load(sys.argv[1], process=False)
if isinstance(m, trimesh.Scene):
    m = trimesh.util.concatenate(list(m.geometry.values()))
pieces = sorted(m.split(only_watertight=False), key=lambda p: -len(p.vertices))
print(f"  {len(m.vertices):,} vertices in {len(pieces)} connected pieces")
print("     span(mm)  vertices   per cm2   sample every")
sherdish = 0
for p in pieces:
    span = (p.vertices.max(0) - p.vertices.min(0)).max()
    if span < 15:
        continue
    sherdish += 1
    area = max(p.area / 100.0, 1e-6)
    dens = len(p.vertices) / area
    print(f"     {span:8.1f}  {len(p.vertices):8,}  {dens:8.0f}   {10/np.sqrt(dens):.2f} mm")
print(f"  {sherdish} piece(s) at least 15 mm across")
if sherdish != 10:
    print(f"  NOTE: A03 has ten sherds. {sherdish} is not ten -- look at the mesh before")
    print("        drawing any conclusion from the densities above.")
PY

echo
echo "=== produced ==="
ls -la "$OUT_DIR"/mesh_sherds*.ply
echo "=== finished $(date) ==="
echo "LOOK AT IT before believing any number above."
