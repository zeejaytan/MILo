#!/bin/bash
#SBATCH --job-name=milo-probe
#SBATCH --account=punim2657
#SBATCH --partition=gpu-a100
#SBATCH --gres=gpu:1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=06:00:00
#SBATCH --output=/data/gpfs/projects/punim2657/MILo/logs/milo_probe_%j.log

# Masked-training probe pair (intent M2, ticket masked-training/02): two ~8k
# runs on the SAME capture, config and data, differing ONLY in --masked-training.
# Past depth re-init (2000), into densification, before the 15k cutoff.
#
# Contact-face hand-marking was skipped at the conservator's call (recorded on
# the ticket): arc scoring later reads contact-zone gaps as missing surface,
# never as wrong surface.
#
# No seed flag exists in train.py, so "identical seed" is honest as "identical
# code path and data, differing only in the patch flag" -- GPU training is
# nondeterministic either way, and the stop rule pairs every number with a rim
# render for exactly this reason.
#
# Usage:
#   ./scripts/remote/pull_and_sbatch.sh slurm/milo_probe.slurm \
#        17062025/A03_sherds 17062025/A03_probe_ctrl 17062025/A03_probe_masked

set -euo pipefail

CAPTURE="${1:?usage: sbatch milo_probe.slurm <capture> <ctrl_out> <masked_out>}"
CTRL_NAME="${2:?second argument is the control output name}"
MASKED_NAME="${3:?third argument is the patched output name}"

MILO_ROOT=/data/gpfs/projects/punim2657/MILo
REPO_DIR=$MILO_ROOT/repo
ENV_PREFIX=$MILO_ROOT/envs/milo
DATA_DIR=$MILO_ROOT/data/$CAPTURE
CTRL_DIR=$MILO_ROOT/output/$CTRL_NAME
MASKED_DIR=$MILO_ROOT/output/$MASKED_NAME

echo "=== masked-training probe started $(date) on $(hostname) ==="
nvidia-smi | head -8 || true

[[ -f "$DATA_DIR/capture.json" ]] || { echo "No dataset at $DATA_DIR" >&2; exit 1; }
for d in "$CTRL_DIR" "$MASKED_DIR"; do
    [[ -e "$d/point_cloud/iteration_8000/point_cloud.ply" ]] && {
        echo "$d already holds an 8k probe -- move it aside first." >&2; exit 1; }
    mkdir -p "$d"
done

module purge
module load GCC/11.3.0 OpenMPI/4.1.4
module load CUDA/11.8.0
module load Miniforge3/24.7.1-2
export CUDA_HOME="${EBROOTCUDA:?}"
export LD_LIBRARY_PATH="$CUDA_HOME/targets/x86_64-linux/lib:${LD_LIBRARY_PATH:-}"
export OMP_NUM_THREADS="${SLURM_CPUS_PER_TASK:-8}"

eval "$(conda shell.bash hook)"
conda activate "$ENV_PREFIX"
cd "$REPO_DIR/milo"

run_probe() {  # $1 = out dir, $2... = extra train flags
    local out="$1"; shift
    python -u train.py \
        -s "$DATA_DIR" \
        -m "$out" \
        -i images_masked \
        -r 1 \
        --eval \
        --imp_metric indoor \
        --rasterizer radegs \
        --dense_gaussians \
        --decoupled_appearance \
        --iterations 8000 \
        "$@" 2>&1 | tee "$out/probe_train.log"
}

echo
echo "--- probe A: control (unpatched) $(date) ---"
run_probe "$CTRL_DIR"

echo
echo "--- probe B: masked training (both sides + background loss) $(date) ---"
run_probe "$MASKED_DIR" --masked-training

echo
echo "--- held-out renders for rim crops $(date) ---"
for d in "$CTRL_DIR" "$MASKED_DIR"; do
    python -u render.py -m "$d" --iteration 8000 --skip_train \
        --rasterizer radegs 2>&1 | tail -2
done

echo
echo "=== eroded-band alpha summary (masked run) ==="
grep -h "masked-train alpha" "$MASKED_DIR/probe_train.log" | tail -8 || true

echo
ls -la "$CTRL_DIR/point_cloud/iteration_8000/" "$MASKED_DIR/point_cloud/iteration_8000/"
echo "=== probe finished $(date) ==="
echo "Verdict needs rim close-ups at 0.10 mm/px beside these curves (ticket 02)."
