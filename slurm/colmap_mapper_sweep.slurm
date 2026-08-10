#!/bin/bash
#SBATCH --job-name=colmap-sweep
#SBATCH --account=punim2657
#SBATCH --partition=sapphire
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=16
#SBATCH --mem=128G
#SBATCH --time=04:00:00
#SBATCH --output=/data/gpfs/projects/punim2657/MILo/logs/colmap_sweep_%j.log

set -euo pipefail

# Why only 2 of 68 photographs registered.
#
# Feature matching on A11 is healthy: 1,637 image pairs survived geometric verification
# out of 2,278 matched (72%), median 356 inliers. So the images DO see each other. The
# incremental mapper is what stopped, having registered A11_0704 and A11_0739 and no more.
#
# The suspicion is the turntable-relaxed thresholds. The pipeline sets
# init_min_tri_angle to 2.0, against COLMAP's default of 16. A low value lets the mapper
# initialise on a pair with almost no baseline; such a reconstruction is badly
# conditioned and cannot be grown, and with multiple_models 0 the mapper then stops
# rather than starting again elsewhere. That combination would fail exactly like this.
#
# This sweeps the initial triangulation angle and the multiple-models flag against the
# EXISTING database, so no feature extraction or matching is repeated. Nothing here is
# tuning for a nicer result: the question is only how many photographs each setting
# manages to register.
#
# Usage:
#   ./scripts/remote/pull_and_sbatch.sh slurm/colmap_mapper_sweep.slurm 16062025/A11

GROUP="${1:?usage: sbatch colmap_mapper_sweep.slurm <date>/<group>}"

PHOTO_ROOT=/data/gpfs/projects/punim2657/Rabati2025
W="$PHOTO_ROOT/$GROUP/work_colmap_openmvs"
IMAGES="$PHOTO_ROOT/$GROUP"
OUT=/data/gpfs/projects/punim2657/MILo/logs/mapper_sweep/$(echo "$GROUP" | tr '/' '_')
# Not the interpreter directly: the COLMAP module puts a Python 3.10 numpy on
# PYTHONPATH, which shadows this environment's numpy. See scripts/milo_python.sh.
MILO_PY=/data/gpfs/projects/punim2657/MILo/repo/scripts/milo_python.sh

echo "=== mapper sweep for $GROUP started $(date) on $(hostname) ==="
[[ -f "$W/database.db" ]] || { echo "No database at $W/database.db" >&2; exit 1; }

module purge
module load GCC/11.3.0 OpenMPI/4.1.4 ICU/71.1 COLMAP/3.9-CUDA-11.7.0

mkdir -p "$OUT"

count_registered() {
    local model_root="$1"
    "$MILO_PY" - "$model_root" <<'PY'
import importlib.util, sys, glob, os
spec = importlib.util.spec_from_file_location(
    "cl", "/data/gpfs/projects/punim2657/MILo/repo/milo/scene/colmap_loader.py")
cl = importlib.util.module_from_spec(spec); spec.loader.exec_module(cl)
root = sys.argv[1]
models = sorted(glob.glob(os.path.join(root, "*")))
if not models:
    print("0 images, 0 models")
    raise SystemExit
tot, sizes = 0, []
for m in models:
    f = os.path.join(m, "images.bin")
    if os.path.exists(f):
        n = len(cl.read_extrinsics_binary(f))
        sizes.append(n); tot += n
print(f"{max(sizes) if sizes else 0} images in largest model; "
      f"{len(sizes)} model(s), sizes {sizes}")
PY
}

run_case() {
    local label="$1" tri="$2" multi="$3"
    local dest="$OUT/$label"
    rm -rf "$dest"; mkdir -p "$dest"
    echo
    echo "--- $label : init_min_tri_angle=$tri multiple_models=$multi"
    # The mapper writes nothing and exits 0 when it fails to build a model, so the count
    # afterwards is what decides, not the exit status.
    colmap mapper \
        --database_path "$W/database.db" \
        --image_path "$IMAGES" \
        --output_path "$dest" \
        --Mapper.multiple_models "$multi" \
        --Mapper.init_min_tri_angle "$tri" \
        --Mapper.abs_pose_min_num_inliers 15 \
        --Mapper.abs_pose_min_inlier_ratio 0.18 \
        --Mapper.ba_refine_principal_point 0 \
        --Mapper.num_threads 16 \
        > "$dest/mapper.log" 2>&1 || echo "  (mapper exited non-zero)"
    printf "  result: "; count_registered "$dest"
}

# Current pipeline setting first, so the comparison is against what actually ran.
run_case "tri02_single" 2.0  0
run_case "tri02_multi"  2.0  1
run_case "tri04_multi"  4.0  1
run_case "tri08_multi"  8.0  1
run_case "tri16_multi" 16.0  1

echo
echo "=== summary ==="
for d in "$OUT"/*/; do
    printf "%-16s " "$(basename "$d")"
    count_registered "$d"
done

echo
echo "68 photographs were fed in. A setting that registers most of them is the one to"
echo "put in the pipeline config; if none does, the problem is the capture geometry and"
echo "not the thresholds."
echo "=== finished $(date) ==="
