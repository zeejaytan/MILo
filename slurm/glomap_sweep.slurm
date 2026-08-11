#!/bin/bash
#SBATCH --job-name=glomap-sweep
#SBATCH --account=punim2657
#SBATCH --partition=gpu-a100-short
#SBATCH --gres=gpu:1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=120G
#SBATCH --time=2:00:00
#SBATCH --output=/data/gpfs/projects/punim2657/MILo/logs/glomap_sweep_%j.log

set -uo pipefail   # NOT -e: colmap segfaults on exit and each case is judged by output

# Why global_mapper registers every photograph and produces no structure.
#
# On A11 it does the hard part correctly and then throws the result away:
#   Established 171,902 tracks from 697,286 observations
#   Kept 53,016 tracks, discarded 2,065 due to inconsistency
#   Running global positioning        (Ceres converges, cost 3.7e6 -> 2.6e2)
#   Running iterative bundle adjustment
#     Filtering tracks by reprojection ...   x4
#   Cannot run bundle adjustment: no 3D points to optimize
#
# So 53,016 good tracks are built and every one is then filtered out on reprojection
# error. The suspects are the filtering thresholds, which are tight and which a turntable
# capture is well placed to violate: small baselines between neighbouring views, and a
# scene where a static backdrop and a rotating rig disagree about camera motion.
#
#   max_angular_reproj_error_deg = 1     one degree
#   max_normalized_reproj_error  = 0.01
#   min_tri_angle_deg            = 1     turntable baselines are small
#
# The incremental mapper on this same database produces 70,947 points, so a consistent
# solution demonstrably exists — this is about which thresholds admit it.
#
# Each case reuses the existing database, so no features or matches are recomputed and a
# run takes about 90 seconds. The question is only: how many images, and how many points.
#
# Usage:
#   sbatch slurm/glomap_sweep.slurm 16062025/A11

GROUP="${1:?usage: sbatch glomap_sweep.slurm <date>/<group>}"

TOOLS=/data/gpfs/projects/punim2657/tools
SFM_ENV=$TOOLS/sfm
PHOTO_ROOT=/data/gpfs/projects/punim2657/Rabati2025
MILO_REPO=/data/gpfs/projects/punim2657/MILo/repo
MILO_PY=$MILO_REPO/scripts/milo_python.sh

IMAGES="$PHOTO_ROOT/$GROUP"
W="$IMAGES/work_colmap_openmvs"
DB="$W/database.db"
OUT=/data/gpfs/projects/punim2657/MILo/logs/glomap_sweep/$(echo "$GROUP" | tr '/' '_')

echo "=== glomap sweep for $GROUP started $(date) on $(hostname) ==="
[[ -f "$DB" ]] || { echo "No database at $DB" >&2; exit 1; }

module purge
module load Miniforge3/24.7.1-2
eval "$(conda shell.bash hook)"
conda activate "$SFM_ENV"
export PYTHONNOUSERSITE=1
mkdir -p "$OUT"

report() {
    local d="$1"
    "$MILO_PY" - "$d" <<'PY' 2>/dev/null || echo "     (unreadable)"
import glob, os, sys, importlib.util
spec = importlib.util.spec_from_file_location(
    "cl", "/data/gpfs/projects/punim2657/MILo/repo/milo/scene/colmap_loader.py")
cl = importlib.util.module_from_spec(spec); spec.loader.exec_module(cl)
best_n, best_p = 0, 0
for m in sorted(glob.glob(os.path.join(sys.argv[1], "*"))):
    f = os.path.join(m, "images.bin")
    if not os.path.exists(f):
        continue
    n = len(cl.read_extrinsics_binary(f))
    p = 0
    pf = os.path.join(m, "points3D.bin")
    if os.path.exists(pf):
        try:
            p = len(cl.read_points3D_binary(pf)[0])
        except Exception:
            p = 0
    if n > best_n or (n == best_n and p > best_p):
        best_n, best_p = n, p
print(f"     {best_n} images, {best_p:,} 3D points")
PY
}

run_case() {
    local label="$1"; shift
    local dest="$OUT/$label"
    rm -rf "$dest"; mkdir -p "$dest"
    echo
    echo "--- $label"
    echo "    extra options: $*"
    colmap global_mapper \
        --database_path "$DB" --image_path "$IMAGES" --output_path "$dest" \
        "$@" > "$dest/glomap.log" 2>&1
    grep -m1 -oE "Kept [0-9]+ tracks" "$dest/glomap.log" | sed 's/^/     /' || true
    report "$dest"
}

# Baseline: reproduce the failure, so the comparison is against what actually ran.
run_case baseline

# Each threshold relaxed on its own, to see which one is doing the filtering.
run_case angular5   --GlobalMapper.max_angular_reproj_error_deg 5
run_case normreproj --GlobalMapper.max_normalized_reproj_error 0.05
run_case triangle   --GlobalMapper.min_tri_angle_deg 0.25

# All three together, for the case where no single one is sufficient.
run_case relaxed_all \
    --GlobalMapper.max_angular_reproj_error_deg 5 \
    --GlobalMapper.max_normalized_reproj_error 0.05 \
    --GlobalMapper.min_tri_angle_deg 0.25

# Keep the positioned structure without the retriangulation pass that discards it.
run_case no_retri   --GlobalMapper.skip_retriangulation 1

echo
echo "=== summary ==="
for d in "$OUT"/*/; do
    printf "%-14s" "$(basename "$d")"
    report "$d"
done

echo
echo "68 photographs went in, and the incremental mapper makes 70,947 points from this"
echo "same database. A case registering 68 images WITH points is the one to adopt; if"
echo "none produces points, the thresholds are not the cause."
echo "=== finished $(date) ==="
