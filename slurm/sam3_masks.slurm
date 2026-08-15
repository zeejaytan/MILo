#!/bin/bash
#SBATCH --job-name=sam3-masks
#SBATCH --account=punim2657
#SBATCH --partition=gpu-a100-short
#SBATCH --gres=gpu:1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=1:00:00
#SBATCH --output=/data/gpfs/projects/punim2657/MILo/logs/sam3_masks_%j.log

set -uo pipefail

# Build SAM 3 background masks for one tree. Runs before structure-from-motion.
#
# WHY THIS IS UNCONDITIONAL. On tree A02, masking was the difference between a folded
# reconstruction and a correct one -- same photographs, same mapper:
#
#     unmasked   262.1 deg camera arc, 98 deg gap   FOLDED
#     masked     348.4 deg camera arc, 12 deg gap   correct
#
# and it did so by removing only 4% of the features (median 18,502 -> 17,716). Those few
# features sit on the STATIC backdrop and are the ones asserting that the camera did not
# move, which is what lets a turntable solve fold. Tree A01 does not need masks at all --
# its tree fills more of the frame and the object signal wins. There is no way to tell
# which kind of tree you have in advance, and masking costs ~8 minutes against 4+ hours of
# reconstruction, so it is cheaper to always mask than to reconstruct twice.
#
# It does NOT make the camera-arc gate redundant. Masking is not a guarantee; the gate
# still runs after SfM and is still the thing that decides whether to proceed.
#
# Usage:
#   sbatch slurm/sam3_masks.slurm 17062025/A02

CAPTURE="${1:?usage: sbatch sam3_masks.slurm <date>/<tree>}"

MILO=/data/gpfs/projects/punim2657/MILo
IMAGES="/data/gpfs/projects/punim2657/Rabati2025/$CAPTURE"
OUT="$MILO/masks/$CAPTURE"

echo "=== SAM 3 masks for $CAPTURE started $(date) on $(hostname) ==="
[[ -d "$IMAGES" ]] || { echo "No photographs at $IMAGES" >&2; exit 1; }
N=$(find "$IMAGES" -maxdepth 1 -iname '*.jpg' | wc -l)
echo "  $N photographs"
[[ "$N" -gt 0 ]] || { echo "Nothing to mask." >&2; exit 1; }

module purge
module load Miniforge3/24.7.1-2
eval "$(conda shell.bash hook)"
conda activate /data/gpfs/projects/punim2657/tools/sam3
export PYTHONNOUSERSITE=1

python "$MILO/repo/scripts/sam3_masks.py" \
    --images "$IMAGES" --out "$OUT" --overlay-every "${OVERLAY_EVERY:-20}"
rc=$?
echo "  (exit $rc)"

NMASK=$(find "$OUT/masks_object" -name '*.png' 2>/dev/null | wc -l)
echo
echo "=== verification ==="
echo "  masks written: $NMASK for $N photographs"
[[ "$NMASK" -eq "$N" ]] || {
    echo "Mask count does not match the photographs -- refusing to hand these on." >&2
    exit 1; }

# The prompt is material-dependent and this is where a new fabric would show up. On A01
# (tan sherds) and A02 (red) "clay fragment" scores 0.88-0.93, while "pottery", "ceramic"
# and "sherd" score ZERO at every threshold. A tree whose coverage looks nothing like the
# others needs its prompt re-swept, not its masks used.
"$MILO/repo/scripts/../scripts/../scripts/check_mask_coverage.sh" 2>/dev/null || \
python - "$OUT/masks.json" <<'PY'
import json, sys, statistics as st
rows = json.load(open(sys.argv[1]))
cov = [100 * r["sherd_coverage"] for r in rows]
best = [r["sherd_best"] for r in rows]
med = st.median(cov)
print(f"  sherd coverage: median {med:.1f}%  (A01 5.2%, A02 5.2%)")
print(f"  best score    : median {st.median(best):.3f}  (A01 0.93, A02 0.93)")
if med < 1.5 or med > 15:
    print("  COVERAGE IS UNLIKE THE TREES ALREADY CHECKED.", file=sys.stderr)
    print("  Re-sweep the prompt before using these -- 'clay fragment' may not fit this",
          file=sys.stderr)
    print("  fabric, the way 'pottery' fits none of them.", file=sys.stderr)
    raise SystemExit(1)
if st.median(best) < 0.6:
    print("  CONFIDENCE IS LOW for this material; re-sweep the prompt.", file=sys.stderr)
    raise SystemExit(1)
print("  coverage and confidence are in line with the trees already checked")
PY

echo
echo "  masks_object -> $OUT/masks_object   (sherds + rig + base + turntable; for SfM)"
echo "  masks_sherds -> $OUT/masks_sherds   (sherds only; for a sherds-only dense stage)"
echo "  LOOK AT $OUT/overlays"
echo "=== finished $(date) ==="
