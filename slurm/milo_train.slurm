#!/bin/bash
#SBATCH --job-name=milo-train
#SBATCH --account=punim2657
#SBATCH --partition=gpu-a100
#SBATCH --gres=gpu:1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=128G
#SBATCH --time=12:00:00
#SBATCH --output=/data/gpfs/projects/punim2657/MILo/logs/milo_train_%j.log

set -euo pipefail

# Optimise a Gaussian Splatting scene for one sherd capture and extract its mesh.
#
# Usage:
#   ./scripts/remote/pull_and_sbatch.sh slurm/milo_train.slurm 16062025
#
# Expects scripts/colmap_to_milo.py to have built the dataset already.

CAPTURE="${1:?usage: sbatch milo_train.slurm <capture> [images_dir] [output_name]}"
# Optional 2nd argument: train on a different image set than the adapter chose --
# "images" for the unmasked views. Optional 3rd: write somewhere other than
# output/<capture>, so a second run of the same capture does not overwrite the first.
IMAGES_OVERRIDE="${2:-}"
OUT_NAME="${3:-$CAPTURE}"

MILO_ROOT=/data/gpfs/projects/punim2657/MILo
REPO_DIR=$MILO_ROOT/repo
ENV_PREFIX=$MILO_ROOT/envs/milo
DATA_DIR=$MILO_ROOT/data/$CAPTURE
OUT_DIR=$MILO_ROOT/output/$OUT_NAME

echo "=== MILo training on $CAPTURE started $(date) on $(hostname) ==="
nvidia-smi | head -15 || true

module purge
module load GCC/11.3.0 OpenMPI/4.1.4
module load CUDA/11.8.0
module load Miniforge3/24.7.1-2
export CUDA_HOME="${EBROOTCUDA:?}"
export LD_LIBRARY_PATH="$CUDA_HOME/targets/x86_64-linux/lib:${LD_LIBRARY_PATH:-}"

eval "$(conda shell.bash hook)"
conda activate "$ENV_PREFIX"

if [[ ! -f "$DATA_DIR/capture.json" ]]; then
    echo "No dataset at $DATA_DIR. Build it first:" >&2
    echo "  python scripts/colmap_to_milo.py --work <work_colmap_openmvs> --out $DATA_DIR" >&2
    exit 1
fi

# Which image directory to train on is decided by the adapter, which refuses to write a
# masked set it could not verify. Reading it back here rather than hard-coding it means a
# capture that fell back to unmasked images cannot be silently trained as if it were masked.
if [[ -n "$IMAGES_OVERRIDE" ]]; then
    IMAGES_ARG="$IMAGES_OVERRIDE"
    [[ -d "$DATA_DIR/$IMAGES_ARG" ]] || {
        echo "No image set at $DATA_DIR/$IMAGES_ARG" >&2; exit 1; }
    echo "Training on image set: $IMAGES_ARG  (OVERRIDE -- not the adapter's choice)"
else
    IMAGES_ARG=$(python -c "import json,sys; print(json.load(open('$DATA_DIR/capture.json'))['train_images_arg'])")
    echo "Training on image set: $IMAGES_ARG"
fi

# A finished run is six GPU-hours. Refuse to start on top of one rather than discover
# afterwards that the mesh being compared was overwritten halfway through.
if [[ -f "$OUT_DIR/mesh_learnable_sdf.ply" ]]; then
    echo "$OUT_DIR already holds a finished mesh." >&2
    echo "Pass a different output name as the 3rd argument, or move that run aside." >&2
    exit 1
fi
python -c "
import json
c = json.load(open('$DATA_DIR/capture.json'))
print('views registered:', c['n_images_registered'])
m = c['masks']
print('masks:', 'none — the backdrop will be reconstructed too' if not m.get('masked_images')
      else f\"{m['masked_images']} views, mean coverage {m['mask_coverage_mean']:.1%}\")
"

mkdir -p "$OUT_DIR"
cd "$REPO_DIR/milo"

# -r 1 : train at full resolution. MILo's default (-1) silently downsamples anything
#        wider than 1600 px. A fracture ridge is a fraction of a millimetre across; at
#        1600 px the reconstruction would answer a coarser question than the one asked.
# --eval : hold out every 8th view. Those views are the only honest instrument available
#        at comparison time, since no ground-truth mesh exists for an archaeological sherd.
# --imp_metric indoor : a turntable rig is a bounded, object-centric scene.
# --dense_gaussians : break surfaces are the whole point; the light configuration will
#        not resolve them.
# --decoupled_appearance : absorbs exposure and white-balance drift around the turntable.
python train.py \
    -s "$DATA_DIR" \
    -m "$OUT_DIR" \
    -i "$IMAGES_ARG" \
    -r 1 \
    --eval \
    --imp_metric indoor \
    --rasterizer radegs \
    --dense_gaussians \
    --decoupled_appearance

echo
echo "=== extracting mesh $(date) ==="
python mesh_extract_sdf.py \
    -s "$DATA_DIR" \
    -m "$OUT_DIR" \
    -i "$IMAGES_ARG" \
    -r 1 \
    --rasterizer radegs

echo
echo "=== meshes produced ==="
find "$OUT_DIR" -name '*.ply' -newermt '-1 day' -printf '%10s  %p\n' | sort -rn | head

echo
echo "=== MILo training on $CAPTURE finished $(date) ==="
echo "Next: scripts/apply_scale.py (if the capture was not scaled at the COLMAP stage),"
echo "      then slurm/milo_compare.slurm $CAPTURE"
