#!/bin/bash
#SBATCH --job-name=sam3-erode0
#SBATCH --account=punim2657
#SBATCH --partition=gpu-a100-short
#SBATCH --gres=gpu:1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=1:00:00
#SBATCH --output=/data/gpfs/projects/punim2657/MILo/logs/sam3_erode0_%j.log
#
# One-shot: unshrunk surface masks for the A03 fracture-overlay test.
# Writes to A03_erode0. Production masks/17062025/A03 is not touched.
# See docs/notes/2026-08-20-erosion-fracture-overlay-design.md
#
# Usage: sbatch slurm/sam3_erode0_A03.slurm

set -uo pipefail

MILO=/data/gpfs/projects/punim2657/MILo
CAPTURE=17062025/A03
IMAGES="/data/gpfs/projects/punim2657/Rabati2025/$CAPTURE"
OUT="$MILO/masks/${CAPTURE}_erode0"

echo "=== SAM 3 unshrunk masks for $CAPTURE started $(date) on $(hostname) ==="
echo "  images: $IMAGES"
echo "  out   : $OUT  (--erode-surface 0)"

[[ -d "$IMAGES" ]] || { echo "No photographs at $IMAGES" >&2; exit 1; }
if [[ -d "$OUT/masks_sherds" ]]; then
    N=$(find "$OUT/masks_sherds" -maxdepth 1 -name '*.png' | wc -l)
    echo "Refusing to overwrite $OUT (already has $N sherd masks)." >&2
    echo "Delete that folder on purpose if this run should replace it." >&2
    exit 1
fi

N=$(find "$IMAGES" -maxdepth 1 -iname '*.jpg' | wc -l)
echo "  $N photographs"
[[ "$N" -gt 0 ]] || { echo "Nothing to mask." >&2; exit 1; }

module purge
module load Miniforge3/24.7.1-2
eval "$(conda shell.bash hook)"
conda activate /data/gpfs/projects/punim2657/tools/sam3
export PYTHONNOUSERSITE=1

mkdir -p "$OUT"
python "$MILO/repo/scripts/sam3_masks.py" \
    --images "$IMAGES" --out "$OUT" --erode-surface 0 --overlay-every 20
rc=$?
echo "  (exit $rc)"
[[ "$rc" -eq 0 ]] || exit "$rc"

NMASK=$(find "$OUT/masks_sherds" -name '*.png' 2>/dev/null | wc -l)
echo
echo "=== verification ==="
echo "  sherd masks written: $NMASK for $N photographs"
[[ "$NMASK" -eq "$N" ]] || {
    echo "Mask count does not match the photographs." >&2
    exit 1
}
echo "  LOOK AT $OUT/overlays"
echo "=== finished $(date) ==="
