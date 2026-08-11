#!/bin/bash
#SBATCH --job-name=mapper-cmp
#SBATCH --account=punim2657
#SBATCH --partition=gpu-a100-short
#SBATCH --gres=gpu:1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=120G
#SBATCH --time=4:00:00
#SBATCH --output=/data/gpfs/projects/punim2657/MILo/logs/mapper_cmp_%j.log

set -uo pipefail   # not -e: colmap segfaults on exit; steps are judged by their output

# Incremental mapper against the SAME database GLOMAP used, for a like-for-like comparison.
#
# Runs the mapper ONLY. The full pipeline would `rm -rf` the sparse and dense directories,
# which would destroy the GLOMAP model and break the dense job running from it. Output
# goes to its own directory so both models survive side by side.
#
# GLOMAP on this database (177 photographs of tree A01, TwoViewGeometry.max_error 10):
#   177 of 177 registered, 64,027 points, mean reprojection error 0.703 px (median 0.537)
#
# Usage:
#   sbatch slurm/mapper_compare.slurm 16062025

GROUP="${1:?usage: sbatch mapper_compare.slurm <date>[/<tree>]}"

TOOLS=/data/gpfs/projects/punim2657/tools
SFM_ENV=$TOOLS/sfm
PHOTO_ROOT=/data/gpfs/projects/punim2657/Rabati2025
MILO_REPO=/data/gpfs/projects/punim2657/MILo/repo
MILO_PY=$MILO_REPO/scripts/milo_python.sh

IMAGES="$PHOTO_ROOT/$GROUP"
W="$IMAGES/work_colmap_openmvs"
DB="$W/database.db"
OUT="$W/sparse_incremental"

echo "=== incremental mapper on $GROUP started $(date) on $(hostname) ==="
[[ -f "$DB" ]] || { echo "No database at $DB — run the COLMAP stage first" >&2; exit 1; }

module purge
module load Miniforge3/24.7.1-2
eval "$(conda shell.bash hook)"
conda activate "$SFM_ENV"
export PYTHONNOUSERSITE=1

N=$(find "$IMAGES" -maxdepth 1 -type f \( -iname '*.jpg' -o -iname '*.jpeg' \) | wc -l)
echo "photographs: $N"

# Read the same tuned thresholds the pipeline uses, from the conservator's config.
read -r TRI_ANGLE MIN_INLIERS MIN_RATIO <<< "$(
    "$MILO_PY" - "/data/gpfs/projects/punim2657/Photogrammetry/pipeline/config/pipeline_config.yaml" <<'PY'
import sys, yaml
mp = yaml.safe_load(open(sys.argv[1]))["colmap"]["mapper"]
print(mp.get("init_min_tri_angle",2.0), mp.get("abs_pose_min_num_inliers",15),
      mp.get("abs_pose_min_inlier_ratio",0.18))
PY
)"
echo "mapper thresholds from your config: tri=$TRI_ANGLE inliers=$MIN_INLIERS ratio=$MIN_RATIO"

rm -rf "$OUT"; mkdir -p "$OUT"
echo
echo "=== running incremental mapper ($(date +%H:%M:%S)) ==="
colmap mapper \
    --database_path "$DB" --image_path "$IMAGES" --output_path "$OUT" \
    --Mapper.multiple_models 1 \
    --Mapper.init_min_tri_angle "$TRI_ANGLE" \
    --Mapper.abs_pose_min_num_inliers "$MIN_INLIERS" \
    --Mapper.abs_pose_min_inlier_ratio "$MIN_RATIO" \
    --Mapper.ba_refine_principal_point 0 \
    --Mapper.num_threads "${SLURM_CPUS_PER_TASK:-8}"
echo "  (mapper exited $? — judged by output below, not by exit code)"

echo
echo "=== comparison ==="
"$MILO_PY" - "$W" "$N" <<'PY'
import glob, os, sys, importlib.util, numpy as np
spec = importlib.util.spec_from_file_location(
    "cl", "/data/gpfs/projects/punim2657/MILo/repo/milo/scene/colmap_loader.py")
cl = importlib.util.module_from_spec(spec); spec.loader.exec_module(cl)
W, N = sys.argv[1], int(sys.argv[2])

def describe(label, d):
    f = os.path.join(d, "images.bin")
    if not os.path.exists(f):
        print(f"  {label:24s} no model"); return
    n = len(cl.read_extrinsics_binary(f))
    xyz, rgb, err = cl.read_points3D_binary(os.path.join(d, "points3D.bin"))
    if len(xyz) == 0:
        print(f"  {label:24s} {n:>3} of {N} images, no points"); return
    print(f"  {label:24s} {n:>3} of {N} images, {len(xyz):>7,} points, "
          f"reproj {err.mean():.3f} px mean / {np.median(err):.3f} median")

describe("glomap", os.path.join(W, "sparse", "0"))
for d in sorted(glob.glob(os.path.join(W, "sparse_incremental", "*"))):
    if os.path.isdir(d):
        describe(f"incremental model {os.path.basename(d)}", d)
PY

echo
echo "More points is not automatically better: reprojection error says whether they are"
echo "real. Judge on both, and on the mesh that follows."
echo "=== finished $(date) ==="
