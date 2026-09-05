#!/bin/bash
#SBATCH --job-name=milo-depthdis
#SBATCH --account=punim2657
#SBATCH --partition=gpu-a100
#SBATCH --gres=gpu:1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=02:00:00
#SBATCH --output=/data/gpfs/projects/punim2657/MILo/logs/depth_disagreement_%j.log

# Ticket 02: cross-view depth disagreement in millimetres on A03.
#
# Renders median depth from the trained Gaussians for six spread views and reports
# nearest-neighbour distances between the unprojected sherd point clouds: the honest
# resolution floor M1's first box needs. No Open3D, no mesh, no fusion -- the number
# describes the rendered depth, not any grid built from it.
#
# Usage:
#   ./scripts/remote/pull_and_sbatch.sh slurm/depth_disagreement.slurm \
#        17062025/A03_sherds 17062025/A03_nomask
#
# The trained run stays 17062025/A03_nomask on purpose: the same Gaussians every other
# A03 measurement uses, so the floor belongs to the representation, not to a retrain.

set -euo pipefail

CAPTURE="${1:?usage: sbatch depth_disagreement.slurm <capture> <trained_run>}"
TRAINED="${2:?second argument is the finished run to read Gaussians from}"

MILO_ROOT=/data/gpfs/projects/punim2657/MILo
REPO_DIR=$MILO_ROOT/repo
ENV_PREFIX=$MILO_ROOT/envs/milo
DATA_DIR=$MILO_ROOT/data/$CAPTURE
SRC_DIR=$MILO_ROOT/output/$TRAINED

echo "=== depth disagreement started $(date) on $(hostname) ==="
echo "  Gaussians from : $SRC_DIR"
echo "  dataset        : $DATA_DIR"
nvidia-smi | head -8 || true

[[ -f "$SRC_DIR/point_cloud/iteration_18000/point_cloud.ply" ]] || {
    echo "No trained Gaussians at $SRC_DIR/point_cloud/iteration_18000/" >&2; exit 1; }
[[ -d "$DATA_DIR/images_masked" ]] || {
    echo "No RGBA image set at $DATA_DIR/images_masked -- rerun colmap_to_milo.py" >&2; exit 1; }

module purge
module load GCC/11.3.0 OpenMPI/4.1.4
module load CUDA/11.8.0
module load Miniforge3/24.7.1-2
export CUDA_HOME="${EBROOTCUDA:?}"
export LD_LIBRARY_PATH="$CUDA_HOME/targets/x86_64-linux/lib:${LD_LIBRARY_PATH:-}"
export OMP_NUM_THREADS="${SLURM_CPUS_PER_TASK:-8}"

eval "$(conda shell.bash hook)"
conda activate "$ENV_PREFIX"

# The scale factor, read once from the capture's own measurement -- the same source
# every other A03 millimetre figure uses. No guessed scales: --mm_per_unit is required
# because guessing one is how the last false finding happened.
WORK=$(python3 -c "import json;print(json.load(open('$DATA_DIR/capture.json'))['work_dir'])")
FACTOR=$(python3 - "$WORK/measurement.env" <<'PY'
import sys
env = dict(l.strip().split("=", 1) for l in open(sys.argv[1]) if "=" in l)
f1 = float(env["d1_real_m"]) / float(env["d1_rec_units"])
f2 = float(env["d2_real_m"]) / float(env["d2_rec_units"])
print(f"{(f1 + f2) / 2:.9f}")
print(f"  the two scale bars disagree by {abs(f1-f2)/((f1+f2)/2)*100:.1f}% -- every "
      f"millimetre figure from this probe carries at least that", file=sys.stderr)
PY
)
MM_PER_UNIT=$(python3 -c "print(f'{$FACTOR * 1000.0:.4f}')")
echo "  scale          : $MM_PER_UNIT mm per scene unit"

# -m points straight at the trained run, so the probe writes
# depth_disagreement.json beside the run it measured. Nothing in the run is altered.
OUT_DIR="$SRC_DIR"
cd "$REPO_DIR/milo"
python -u ../scripts/depth_disagreement.py \
    -s "$DATA_DIR" -m "$OUT_DIR" -i images_masked -r 1 --eval \
    --mm_per_unit "$MM_PER_UNIT" \
    --views 0 24 48 72 96 120 --subsample 20000 2>&1 | tee "$OUT_DIR/log_depth_disagreement.txt"

[[ -f "$OUT_DIR/depth_disagreement.json" ]] || {
    echo "probe wrote no depth_disagreement.json" >&2; exit 1; }
echo "=== finished $(date) ==="
echo "READ THE PAIR LINES, not just the pooled median: one bad pair is a view-dependent"
echo "failure (the chrome rig moves with viewpoint); uniform noise is the representation."
