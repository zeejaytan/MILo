#!/bin/bash
#SBATCH --job-name=vggt-pose
#SBATCH --account=punim2657
#SBATCH --partition=gpu-a100
#SBATCH --gres=gpu:1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=02:00:00
#SBATCH --output=/data/gpfs/projects/punim2657/MILo/logs/vggt_pose_%j.log

# Ticket alt-05: VGGT judged as what it is — a pose source.
#
# Estimates cameras on the existing A03 views with the upstream demo_colmap.py
# path (feed-forward, no BA) and scores them against the COLMAP solve that the
# MILo dataset was built from. Scale anchored from the capture's own
# measurement.env — an unscaled result is refused, never measured.
#
# Usage:
#   ./scripts/remote/pull_and_sbatch.sh slurm/vggt_pose.slurm 17062025/A03_sherds
#
# Pins: code facebookresearch/vggt@a288dd0, checkpoint facebook/VGGT-1B (open;
# Commercial is application-gated). The checkpoint is pre-downloaded to the
# torch hub cache on the login node — compute nodes have no outbound internet.

set -euo pipefail

CAPTURE="${1:?usage: sbatch vggt_pose.slurm <capture> [out_name]}"
OUT_NAME="${2:-vggt_$(basename "$CAPTURE")}"

VGGT_ROOT=/data/gpfs/projects/punim2657/vggt
MILO_ROOT=/data/gpfs/projects/punim2657/MILo
REPO_DIR=$MILO_ROOT/repo
ENV_PREFIX=$MILO_ROOT/envs/vggt
DATA_DIR=$MILO_ROOT/data/$CAPTURE
OUT_DIR=$MILO_ROOT/output/$OUT_NAME
SCENE_DIR=$OUT_DIR/scene

echo "=== VGGT pose on $CAPTURE started $(date) on $(hostname) ==="
nvidia-smi | head -8 || true

[[ -d "$DATA_DIR/images" ]] || { echo "No image set at $DATA_DIR/images" >&2; exit 1; }
[[ -f "$DATA_DIR/sparse/0/images.bin" ]] || { echo "No COLMAP solve at $DATA_DIR/sparse/0" >&2; exit 1; }
[[ -d "$ENV_PREFIX" ]] || { echo "No env at $ENV_PREFIX -- build it on the login node first" >&2; exit 1; }
CACHED_CKPT="$HOME/.cache/torch/hub/checkpoints/model.pt"
[[ -f "$CACHED_CKPT" ]] || { echo "No cached checkpoint at $CACHED_CKPT -- download on the login node first" >&2; exit 1; }
ls -la "$CACHED_CKPT"
[[ -f "$VGGT_ROOT/demo_colmap.py" ]] || { echo "No VGGT code at $VGGT_ROOT" >&2; exit 1; }
cd "$VGGT_ROOT" && git rev-parse HEAD

mkdir -p "$SCENE_DIR/images" "$OUT_DIR"
# Unmasked originals: VGGT carries no mask, and the COLMAP solve it is scored
# against was built from these views. Masking here would change the question.
for f in "$DATA_DIR"/images/*; do
    ln -sfn "$f" "$SCENE_DIR/images/$(basename "$f")"
done
echo "staged $(ls "$SCENE_DIR/images" | wc -l) views"

module purge
module load GCC/11.3.0 OpenMPI/4.1.4
module load CUDA/11.8.0
module load Miniforge3/24.7.1-2
export CUDA_HOME="${EBROOTCUDA:?}"
export LD_LIBRARY_PATH="$CUDA_HOME/targets/x86_64-linux/lib:${LD_LIBRARY_PATH:-}"
export PYTHONNOUSERSITE=1
export OMP_NUM_THREADS="${SLURM_CPUS_PER_TASK:-8}"

eval "$(conda shell.bash hook)"
conda activate "$ENV_PREFIX"

# Feed-forward only (no --use_ba): the honest pose-source reading. BA is a
# second ticket if this lands close.
python -u demo_colmap.py --scene_dir "$SCENE_DIR" 2>&1 | tee "$OUT_DIR/log_vggt.txt"

[[ -f "$SCENE_DIR/sparse/images.bin" ]] || { echo "VGGT wrote no sparse model" >&2; exit 1; }

WORK=$(python3 -c "import json;print(json.load(open('$DATA_DIR/capture.json'))['work_dir'])")
FACTOR=$(python3 - "$WORK/measurement.env" <<'PY'
import sys
env = dict(l.strip().split("=", 1) for l in open(sys.argv[1]) if "=" in l)
f1 = float(env["d1_real_m"]) / float(env["d1_rec_units"])
f2 = float(env["d2_real_m"]) / float(env["d2_rec_units"])
print(f"{(f1 + f2) / 2:.9f}")
PY
)
MM_PER_UNIT=$(python3 -c "print(f'{$FACTOR * 1000.0:.4f}')")
echo "scale: $MM_PER_UNIT mm per scene unit"

python3 "$REPO_DIR/scripts/compare_vggt_poses.py" \
    --colmap "$DATA_DIR/sparse/0" --vggt "$SCENE_DIR/sparse" \
    --mm_per_unit "$MM_PER_UNIT" --out "$OUT_DIR/pose_report.json" \
    2>&1 | tee "$OUT_DIR/log_pose_compare.txt"

echo "=== finished $(date) ==="
echo "Read pose_report.json against the COLMAP solve: rotation error (deg),"
echo "translation error (mm), registration rate. Verdict belongs in ticket 05."
