#!/bin/bash
#SBATCH --job-name=saga-fuse
#SBATCH --account=punim2657
#SBATCH --partition=gpu-a100-short
#SBATCH --gres=gpu:1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=02:00:00
#SBATCH --output=/data/gpfs/projects/punim2657/MILo/logs/saga_fuse_%j.log

# Ticket alt-09: SAGA post-hoc filter, stage 3 — filter, fuse, scale.
#
# Filters the frozen scene to the SAGA keep set, then runs the LIVE
# fusion-time masked-depth DTU path on the survivors — the same extractor as
# the A03 DTU verdict, so the only thing that changes is the input.
# No silhouette cull: it deletes every vertex on A03 (known, measured).
#
# Thresholds (evidence-moved, see ticket): overlays keep every visible sherd
# at 0.1 with minor background the fusion masks neutralise anyway; 0.2 rides
# as sensitivity. Primary is 0.1 — NOT the prespecified 0.6, which sat above
# where the 3D similarities live and starved the scene to 1.2%.
#
# Voxel is rung 0 (0.0022 units = 0.822 mm): under the ~1 mm bar and clear of
# the 32,768-block cliff at rig-free grid sizes. The extractor's own gate
# refuses before the call if the grid is bigger than measured here.
# Renders on the card, fuses on the host (o3d CPU:0 first, CUDA retry) —
# one script because the extractor is monolithic, not two jobs.
#
# Usage:
#   ./scripts/remote/pull_and_sbatch.sh slurm/saga_fuse.slurm

set -euo pipefail

MILO_ROOT=/data/gpfs/projects/punim2657/MILo
REPO_DIR=$MILO_ROOT/repo
ENV_PREFIX=$MILO_ROOT/envs/milo
DATA_DIR=$MILO_ROOT/data/17062025/A03_sherds
SRC_DIR=$MILO_ROOT/output/17062025/A03_nomask
SAGA_MODEL=$MILO_ROOT/output/saga_A03
QUERY_DIR=$SAGA_MODEL/query

echo "=== SAGA fuse started $(date) on $(hostname) ==="
nvidia-smi | head -8 || true

[[ -f "$QUERY_DIR/keep_idx_0.1.npy" ]] || { echo "No keep sets — run slurm/saga_query.slurm first" >&2; exit 1; }
[[ -f "$SRC_DIR/point_cloud/iteration_18000/point_cloud.ply" ]] || { echo "No frozen scene" >&2; exit 1; }

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

cd "$REPO_DIR"
for THR in 0.1 0.2; do
    OUT_DIR=$MILO_ROOT/output/saga_A03_filt_${THR/./}
    TAG="t$THR"
    echo
    echo "=== threshold $THR -> $OUT_DIR $(date) ==="
    mkdir -p "$OUT_DIR/point_cloud/iteration_18000"
    python -u scripts/saga_filter_ply.py \
        --ply "$SRC_DIR/point_cloud/iteration_18000/point_cloud.ply" \
        --keep "$QUERY_DIR/keep_idx_$THR.npy" \
        --out "$OUT_DIR/point_cloud/iteration_18000/point_cloud.ply"
    for f in cameras.json input.ply cfg_args; do
        [[ -e "$SRC_DIR/$f" ]] && ln -sfn "$SRC_DIR/$f" "$OUT_DIR/$f"
    done

    RAW="$OUT_DIR/recon_tsdf_v0.0022.ply"
    FUSELOG="$OUT_DIR/log_fuse_v0.0022.txt"
    run_fuse() {
        python -u milo/eval/dtu/mesh_extract_dtu.py \
            -s "$DATA_DIR" -m "$OUT_DIR" -i images_masked -r 1 --eval \
            --rasterizer radegs \
            --voxel_size 0.0022 --block_count 40000 \
            --trunc_voxel_multiplier 8 \
            --mm_per_unit "$MM_PER_UNIT" \
            --o3d_device "$1" \
            --ply_name "$(basename "$RAW")" 2>&1 | tee "$2"
    }
    if [[ ! -f "$RAW" ]]; then
        run_fuse "CPU:0" "$FUSELOG" || true
        [[ -f "$RAW" ]] || {
            echo "--- CPU:0 produced nothing; retrying CUDA:0 ---"
            run_fuse "CUDA:0" "${FUSELOG%.txt}_retry.txt" || true; }
    fi
    [[ -f "$RAW" ]] || { echo "thr $THR wrote no mesh on either device" >&2; exit 1; }

    python scripts/apply_scale.py --capture "$DATA_DIR/capture.json" \
        --mesh "$RAW" --out "$OUT_DIR/mesh_saga_filt_${TAG}_mm.ply" \
        --force-factor "$FACTOR"
done

echo
python scripts/mesh_report.py "$MILO_ROOT"/output/saga_A03_filt_*/mesh_saga_filt_*_mm.ply --expect-pieces 10
ls -la "$MILO_ROOT"/output/saga_A03_filt_*/*.ply
echo "=== finished $(date) ==="
echo "LOOK AT THE MESHES (renders + OpenMVS compare follow in the verdict step)."
