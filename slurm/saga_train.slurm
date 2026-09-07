#!/bin/bash
#SBATCH --job-name=saga-train
#SBATCH --account=punim2657
#SBATCH --partition=gpu-a100-short
#SBATCH --gres=gpu:1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
# 64G, not 128G: asking 128G silently reroutes the job to gpu-a100
# (verified 2026-09-07 by bisection — short keeps jobs only below that).
# Feature training is VRAM-bound (GPU); host RAM just holds batches.
#SBATCH --mem=64G
#SBATCH --time=02:00:00
#SBATCH --output=/data/gpfs/projects/punim2657/MILo/logs/saga_train_%j.log

# Ticket alt-09: SAGA post-hoc filter, stage 1 — distil features.
#
# Freezes the full-scene MILo Gaussians (A03_nomask, 222,678 — geometry
# untouched by construction) and trains only the 32-dim contrastive head
# against OUR adapter-verified sherd masks (not SAGA's SAM extraction).
# Query + fusion ride in a second job so the renders can be looked at first.
#
# Pins: Jumpat/SegAnyGAussians@v2@2d4c5d7 (cloned to punim2657/saga),
# envs/saga (torch 2.3.1+cu118, rasterizers + pytorch3d 0.7.6 compiled).
#
# Usage:
#   ./scripts/remote/pull_and_sbatch.sh slurm/saga_train.slurm

set -euo pipefail

SAGA_ROOT=/data/gpfs/projects/punim2657/saga
MILO_ROOT=/data/gpfs/projects/punim2657/MILo
REPO_DIR=$MILO_ROOT/repo
ENV_PREFIX=$MILO_ROOT/envs/saga
CAPTURE=17062025/A03_sherds
DATA_DIR=$MILO_ROOT/data/$CAPTURE
FROZEN=$MILO_ROOT/output/17062025/A03_nomask/point_cloud/iteration_18000/point_cloud.ply
SRC_DIR=$MILO_ROOT/saga_data/A03
MODEL_DIR=$MILO_ROOT/output/saga_A03

echo "=== SAGA feature training started $(date) on $(hostname) ==="
nvidia-smi | head -8 || true

[[ -f "$FROZEN" ]] || { echo "No frozen Gaussians at $FROZEN" >&2; exit 1; }
[[ -d "$DATA_DIR/images_masked" ]] || { echo "No masked set" >&2; exit 1; }
[[ -d "$ENV_PREFIX" ]] || { echo "No env at $ENV_PREFIX" >&2; exit 1; }
cd "$SAGA_ROOT" && git rev-parse HEAD

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

# ---- stage 0: source layout SAGA expects, our masks in its format ----
mkdir -p "$SRC_DIR" "$MODEL_DIR/point_cloud/iteration_18000"
[[ -e "$SRC_DIR/images" ]] || ln -s "$DATA_DIR/images" "$SRC_DIR/images"
[[ -d "$SRC_DIR/sparse/0" ]] || { mkdir -p "$SRC_DIR/sparse"; cp -r "$DATA_DIR/sparse/0" "$SRC_DIR/sparse/0"; }
[[ -f "$MODEL_DIR/point_cloud/iteration_18000/scene_point_cloud.ply" ]] || \
    cp "$FROZEN" "$MODEL_DIR/point_cloud/iteration_18000/scene_point_cloud.ply"
mkdir -p "$SRC_DIR/sam_masks"
# SAGA's arg loader merges a previous step's config file with the flags, and a
# fresh model dir (we skip scene training: the MILo scene is already trained
# and frozen) has none. Seed both configs from SAGA's OWN param classes, so
# every default is upstream's, not ours — only paths/iterations are job-set.
# (An earlier empty-string seed broke extraction the other way: keys the
# loader expects were missing entirely.)
python - "$MODEL_DIR" "$SRC_DIR" <<'PY'
import os
import sys
sys.path.insert(0, "/data/gpfs/projects/punim2657/saga")
from argparse import ArgumentParser, Namespace
from arguments import ModelParams, PipelineParams, OptimizationParams
model_dir, src_dir = sys.argv[1], sys.argv[2]
p = ArgumentParser()
groups = (ModelParams(p), PipelineParams(p), OptimizationParams(p))
d = {}
for g in groups:
    for k, v in vars(g).items():
        d[k[1:] if k.startswith("_") else k] = v
d.update({"source_path": src_dir, "model_path": model_dir,
          "images": "images", "target": "contrastive_feature",
          "iterations": 10000, "image_root": src_dir})
for name in ("cfg_args", "feature_cfg_args"):
    path = os.path.join(model_dir, name)
    cur = open(path).read().strip() if os.path.exists(path) else ""
    if not cur.startswith("Namespace(") or cur == "Namespace()":
        open(path, "w").write(str(Namespace(**d)))
        print("seeded", path)
    else:
        print("kept", path)
PY
python - <<'PY' 2>&1 | tail -2
# Mask stack per view: [sherd, background]. The two-stack is load-bearing,
# twice over: (1) get_scale.py `.squeeze()`s the stack and a single mask
# collapses [1,H,W] -> [H,W], so mask[0] indexed a ROW (crashed 30169966 —
# upstream never sees this, SAM always returns N>1); (2) the contrastive loss
# pulls same-mask pixels together AND pushes different masks apart, so one
# mask alone is pull-only, degenerate. Sherd-vs-background is our filter.
import os
import torch
from PIL import Image
import numpy as np
src = "/data/gpfs/projects/punim2657/MILo/data/17062025/A03_sherds/images_masked"
dst = "/data/gpfs/projects/punim2657/MILo/saga_data/A03/sam_masks"
n = 0
for f in sorted(os.listdir(src)):
    img = Image.open(os.path.join(src, f))
    sherd = np.asarray(img)[..., 3] > 128
    assert sherd.any() and (~sherd).any(), f
    stack = torch.stack([torch.from_numpy(sherd), torch.from_numpy(~sherd)])
    stem = f.split(".")[0]
    torch.save(stack, os.path.join(dst, stem + ".pt"))
    n += 1
print(f"converted {n} two-stack masks")
PY
[[ -f "$SRC_DIR/sam_masks/A31_1100.pt" ]] || { echo "mask conversion failed" >&2; exit 1; }

# ---- stage 1: per-mask 3D scales on the frozen scene ----
python -u get_scale.py -s "$SRC_DIR" -m "$MODEL_DIR" --image_root "$SRC_DIR" 2>&1 | tail -3
[[ -f "$SRC_DIR/mask_scales/A31_1100.pt" ]] || { echo "get_scale wrote nothing" >&2; exit 1; }

# ---- stage 2: contrastive head only; scene stays frozen ----
# Ray count follows upstream's own recipe (training_scripts/train_spin.sh:
# --iterations 10000 --feature_lr 0.0025 --num_sampled_rays 1000 on ~1MP
# views), scaled 8x for our 6.8MP full-res views: at 2.3% sherd coverage,
# 1000 rays land ~23 on clay per view/iter — too thin to learn from.
# 8000 rays land ~180 on clay; VRAM cost is per-ray, not per-pixel.
python -u train_contrastive_feature.py -s "$SRC_DIR" -m "$MODEL_DIR" \
    --iterations 10000 --feature_lr 0.0025 --num_sampled_rays 8000 2>&1 | tee "$MODEL_DIR/log_train_feature.txt"

echo "=== files ==="
find "$MODEL_DIR" -name '*.pth' -newermt '-1 day' | head
echo "=== finished $(date) ==="
echo "Next (separate job after looking): headless mask-prompt query -> keep idx -> filtered ply -> DTU fusion."
