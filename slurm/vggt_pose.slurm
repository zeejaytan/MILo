#!/bin/bash
#SBATCH --job-name=vggt-pose
#SBATCH --account=punim2657
#SBATCH --partition=gpu-a100
#SBATCH --gres=gpu:1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=06:00:00
#SBATCH --output=/data/gpfs/projects/punim2657/MILo/logs/vggt_pose_%j.log

# Ticket alt-05: VGGT judged as what it is — a pose source.
#
# Estimates cameras on the existing A03 views with the upstream demo_colmap.py
# path (feed-forward, no BA) and scores them against the COLMAP solve that the
# MILo dataset was built from. Scale anchored from the capture's own
# measurement.env — an unscaled result is refused, never measured.
#
# Usage:
#   ./scripts/remote/pull_and_sbatch.sh slurm/vggt_pose.slurm 17062025/A03_sherds images
#   ./scripts/remote/pull_and_sbatch.sh slurm/vggt_pose.slurm 17062025/A03_sherds images_masked
#
# Pins: code facebookresearch/vggt@a288dd0, checkpoint facebook/VGGT-1B (open;
# Commercial is application-gated). Checkpoints and caches live on the project
# disk, not HOME (HOME quota is nearly full and compute nodes have no outbound
# internet): HF_HOME and TORCH_HOME below must match the login-node download.

set -euo pipefail

CAPTURE="${1:?usage: sbatch vggt_pose.slurm <capture> [images_dir] [out_name] [ba]}"
IMAGES_DIR="${2:-images}"
OUT_NAME="${3:-vggt_$(basename "$CAPTURE")_${IMAGES_DIR}}"
BA_MODE="${4:-}"  # "ba" appends upstream --use_ba (track + bundle-adjust)

VGGT_ROOT=/data/gpfs/projects/punim2657/vggt
MILO_ROOT=/data/gpfs/projects/punim2657/MILo
REPO_DIR=$MILO_ROOT/repo
ENV_PREFIX=$MILO_ROOT/envs/vggt
DATA_DIR=$MILO_ROOT/data/$CAPTURE
OUT_DIR=$MILO_ROOT/output/$OUT_NAME
SCENE_DIR=$OUT_DIR/scene

echo "=== VGGT pose on $CAPTURE started $(date) on $(hostname) ==="
nvidia-smi | head -8 || true

[[ -d "$DATA_DIR/$IMAGES_DIR" ]] || { echo "No image set at $DATA_DIR/$IMAGES_DIR" >&2; exit 1; }
[[ -f "$DATA_DIR/sparse/0/images.bin" ]] || { echo "No COLMAP solve at $DATA_DIR/sparse/0" >&2; exit 1; }
[[ -d "$ENV_PREFIX" ]] || { echo "No env at $ENV_PREFIX -- build it on the login node first" >&2; exit 1; }
export HF_HOME=/data/gpfs/projects/punim2657/MILo/vggt_cache/hf
export TORCH_HOME=/data/gpfs/projects/punim2657/MILo/vggt_cache/torch
CACHED_CKPT="$TORCH_HOME/hub/checkpoints/model.pt"
[[ -f "$CACHED_CKPT" ]] || { echo "No cached checkpoint at $CACHED_CKPT -- download on the login node first" >&2; exit 1; }
ls -la "$CACHED_CKPT"
[[ -f "$VGGT_ROOT/demo_colmap.py" ]] || { echo "No VGGT code at $VGGT_ROOT" >&2; exit 1; }
cd "$VGGT_ROOT" && git rev-parse HEAD

mkdir -p "$SCENE_DIR/images" "$OUT_DIR"
# Which views VGGT sees is the trial variable (ticket 05): "images" for the
# unmasked room (world frame — static backdrop dominates and the cameras
# correctly go static), "images_masked" for sherd-on-white via the loader's
# RGBA blend (object frame — the only reading comparable to COLMAP's ring).
for f in "$DATA_DIR"/"$IMAGES_DIR"/*; do
    ln -sfn "$f" "$SCENE_DIR/images/$(basename "$f")"
done
echo "staged $(ls "$SCENE_DIR/images" | wc -l) views from $IMAGES_DIR"

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

# Feed-forward by default; "ba" as 4th arg runs the upstream accuracy path
# (LightGlue tracks + pycolmap bundle adjustment). BA refines — it is the
# terminal test here, not a second campaign: if it cannot build from the
# collapsed init, the pose track retires per M7's gate.
BA_FLAG=""
if [[ "$BA_MODE" == "ba" ]]; then
    BA_FLAG="--use_ba"
    OUT_DIR="${OUT_DIR}_ba"
    SCENE_DIR="$OUT_DIR/scene"
    mkdir -p "$SCENE_DIR/images" "$OUT_DIR"
    for f in "$DATA_DIR"/"$IMAGES_DIR"/*; do
        ln -sfn "$f" "$SCENE_DIR/images/$(basename "$f")"
    done
fi
python -u demo_colmap.py --scene_dir "$SCENE_DIR" $BA_FLAG 2>&1 | tee "$OUT_DIR/log_vggt.txt"

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
