#!/bin/bash
#SBATCH --job-name=milo-dtu
#SBATCH --account=punim2657
#SBATCH --partition=gpu-a100
#SBATCH --gres=gpu:1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=16
#SBATCH --mem=300G
#SBATCH --time=12:00:00
#SBATCH --output=/data/gpfs/projects/punim2657/MILo/logs/milo_dtu_%j.log

set -euo pipefail

# Run MILo's OWN object-isolation route -- the one its authors use for the DTU benchmark,
# which is the same situation as ours: a small object on a stand, photographed against a
# background it must be separated from. Two steps, and this job keeps the mesh from EACH so
# they can be compared rather than conflated:
#
#   step 1  milo/eval/dtu/mesh_extract_dtu.py   -> recon_tsdf_<rung>.ply
#           Renders depth from the trained Gaussians for every training view, sets depth to
#           ZERO wherever the mask is dark, and TSDF-fuses what is left. Masked pixels never
#           enter the voxel grid, so this genuinely deletes background rather than relabelling
#           it -- unlike the cull inside --init integration, which marks unseen space SOLID.
#
#   step 2  scripts/cull_dtu_mesh.py            -> recon_tsdf_<rung>_culled.ply
#           Calls evaluate_dtu_mesh.py:cull_mesh unmodified. Keeps a vertex only if it lands
#           inside a 6-pixel-dilated sherd outline in EVERY training view. That all-views rule
#           is the difference from the integration cull's at-least-one-view rule, which the
#           mounting rig walks straight through because it sits behind the sherds from many
#           angles on a turntable.
#
# RESOLUTION LADDER. The author's voxel size is 0.002 scene units, which on A03 (373.7 mm
# per unit) is 0.75 mm. That is NOT a floor set by the data: the depth maps are rendered at
# 3200x2133 from 1.41 m away with fx 6830 px, so they sample the sherds at 0.21 mm per pixel.
# The author's voxel throws away a factor of 3.6. This job climbs a ladder instead of
# asserting one answer -- the author's setting first, as the baseline everything else is
# read against, then two refinements:
#
#     rung 1   voxel 0.0020 units = 0.75 mm    the author's, unchanged
#     rung 2   voxel 0.0010 units = 0.37 mm
#     rung 3   voxel 0.0006 units = 0.22 mm    about where the photographs run out
#
# Each rung writes its own mesh before the next begins, so a wall-clock timeout on the
# fine end still leaves the coarse results usable.
#
# WHY THE MULTIPLIER MOVES WITH THE VOXEL. Open3D's TSDF truncation band is
# trunc_voxel_multiplier * voxel_size and upstream passes neither argument, leaving it at 8
# -- one block wide, which is why 8 pairs with block_resolution 16. Refine the voxel alone
# and the band shrinks with it, from ~6 mm to ~1.5 mm. Gaussian-rendered depth disagrees
# between views by more than that in places, and where it does the surfaces stop reinforcing
# and the mesh fragments into holes. The multipliers below hold the band at ~6 mm throughout,
# so the ladder varies sampling and nothing else.
#
# WHAT THIS IS AND IS NOT. Still a mechanism check, not yet a candidate production route.
# Step 1 is Open3D TSDF fusion of rendered depth -- a different extractor from the
# marching-tetrahedra-on-Gaussians that produced mesh_learnable_sdf.ply, and the GOF line of
# work this inherits from presents marching tetrahedra as the improvement OVER TSDF fusion.
# A finer voxel reveals whatever the depth maps actually contain, which at a quarter of a
# millimetre may be genuine fracture relief or may be Gaussian depth noise. The renders
# decide that, not the vertex counts.
#
# Usage:
#   ./scripts/remote/pull_and_sbatch.sh slurm/milo_extract_dtu.slurm \
#        17062025/A03 17062025/A03_nomask 17062025/A03_dtu
#   ...optional 4th argument picks the rungs, default "1 2 3":
#        17062025/A03 17062025/A03_nomask 17062025/A03_dtu "1 2"

CAPTURE="${1:?usage: sbatch milo_extract_dtu.slurm <capture> <trained_run> <out_name> [rungs]}"
TRAINED="${2:?second argument is the finished run to read Gaussians from}"
OUT_NAME="${3:?third argument is where to write the meshes}"
RUNGS="${4:-1 2 3}"

MILO_ROOT=/data/gpfs/projects/punim2657/MILo
REPO_DIR=$MILO_ROOT/repo
ENV_PREFIX=$MILO_ROOT/envs/milo
DATA_DIR=$MILO_ROOT/data/$CAPTURE
SRC_DIR=$MILO_ROOT/output/$TRAINED
OUT_DIR=$MILO_ROOT/output/$OUT_NAME

echo "=== DTU-route extraction started $(date) on $(hostname) ==="
echo "  Gaussians from : $SRC_DIR"
echo "  writing to     : $OUT_DIR"
echo "  rungs          : $RUNGS"
nvidia-smi | head -15 || true

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

# Share the trained Gaussians by symlink so the unmasked run's meshes stay untouched.
mkdir -p "$OUT_DIR"
for f in point_cloud cameras.json input.ply; do
    if [[ -e "$SRC_DIR/$f" ]]; then
        ln -sfn "$SRC_DIR/$f" "$OUT_DIR/$f"
    fi
done
cp -f "$SRC_DIR/cfg_args" "$OUT_DIR/cfg_args"

# The scale factor, read once and reused, so every rung lands in the same millimetres.
WORK=$(python3 -c "import json;print(json.load(open('$DATA_DIR/capture.json'))['work_dir'])")
FACTOR=$(python3 - "$WORK/measurement.env" <<'PY'
import sys
env = dict(l.strip().split("=", 1) for l in open(sys.argv[1]) if "=" in l)
f1 = float(env["d1_real_m"]) / float(env["d1_rec_units"])
f2 = float(env["d2_real_m"]) / float(env["d2_rec_units"])
print(f"{(f1 + f2) / 2:.9f}")
print(f"  the two scale bars disagree by {abs(f1-f2)/((f1+f2)/2)*100:.1f}% -- every "
      f"millimetre figure from these meshes carries at least that", file=sys.stderr)
PY
)
MM_PER_UNIT=$(python3 -c "print(f'{$FACTOR * 1000.0:.4f}')")
echo "  scale          : $MM_PER_UNIT mm per scene unit"

# rung -> voxel size, truncation multiplier. The multiplier holds the band near 6 mm.
voxel_for()  { case "$1" in 1) echo 0.002;;  2) echo 0.001;;  3) echo 0.0006;; esac; }
mult_for()   { case "$1" in 1) echo 8;;      2) echo 16;;     3) echo 27;;     esac; }

# Block capacity is allocated up front, so it is a RAM reservation: 80 KiB per block.
# Rung 1 runs at the author's 50000 and REPORTS how many it actually used; the finer rungs
# are then sized from that measurement rather than from a guess. Blocks scale as the square
# of the refinement, times the increase in band thickness.
BLOCKS_USED_1=""
blocks_for() {
    local rung="$1" v m
    v=$(voxel_for "$rung"); m=$(mult_for "$rung")
    if [[ "$rung" == "1" ]]; then echo 50000; return; fi
    # If rung 1 was skipped there is no measurement to scale from. 20000 is a deliberately
    # middling stand-in; the grid-full warning in mesh_extract_dtu.py is what catches it
    # being wrong, rather than a quietly incomplete mesh.
    local base="${BLOCKS_USED_1:-20000}"
    # 1,500,000 blocks is 114 GiB reserved, which is the most that leaves room for the mesh
    # extraction inside this job's 300G.
    python3 -c "
need = $base * (0.002/$v)**2 * ($m/8.0) * 1.6
print(int(min(max(need, 50000), 1_500_000)))"
}

# The installed Open3D wheel ships a CUDA build and picks it up automatically on a GPU
# node, and fusion is far faster there. The limit is memory: block_count reserves 80 KiB
# per block on whichever device. Anything under 30 GiB goes to the A100; the fine rungs
# reserve more than a GPU has and fall back to host RAM.
device_for() {
    python3 -c "
gib = $1 * 80/1024/1024
print('CUDA:0' if gib < 30 else 'CPU:0')"
}

for RUNG in $RUNGS; do
    V=$(voxel_for "$RUNG"); M=$(mult_for "$RUNG"); B=$(blocks_for "$RUNG")
    DEV=$(device_for "$B")
    TAG="v${V}"
    RAW="$OUT_DIR/recon_tsdf_${TAG}.ply"
    CULLED="$OUT_DIR/recon_tsdf_${TAG}_culled.ply"

    echo
    echo "=================================================================="
    echo "=== rung $RUNG: voxel $V units, multiplier $M, blocks $B, fusing on $DEV  $(date)"
    python3 -c "print(f'  voxel {$V * $MM_PER_UNIT:.3f} mm, band +/-{$V * $M * $MM_PER_UNIT:.2f} mm, {$B * 80/1024/1024:.1f} GiB reserved')"
    echo "=================================================================="

    if [[ -f "$RAW" ]]; then
        echo "  $RAW exists already -- skipping the fusion for this rung."
    else
        cd "$REPO_DIR/milo"
        python -u eval/dtu/mesh_extract_dtu.py \
            -s "$DATA_DIR" -m "$OUT_DIR" -i images_masked -r 1 --eval \
            --rasterizer radegs \
            --voxel_size "$V" \
            --block_count "$B" \
            --trunc_voxel_multiplier "$M" \
            --mm_per_unit "$MM_PER_UNIT" \
            --o3d_device "$DEV" \
            --ply_name "$(basename "$RAW")" 2>&1 | tee "$OUT_DIR/log_fuse_${TAG}.txt"
    fi
    [[ -f "$RAW" ]] || { echo "rung $RUNG wrote no mesh" >&2; exit 1; }

    # Feed the measured block usage forward to the finer rungs.
    if [[ "$RUNG" == "1" && -f "$OUT_DIR/log_fuse_${TAG}.txt" ]]; then
        BLOCKS_USED_1=$(grep -oP 'blocks used: \K[\d,]+' "$OUT_DIR/log_fuse_${TAG}.txt" \
                        | tr -d ',' | head -1 || true)
        echo "  measured block usage at the author's setting: ${BLOCKS_USED_1:-unknown}"
    fi

    echo
    echo "--- rung $RUNG, step 2: silhouette cull $(date) ---"
    cd "$REPO_DIR"
    python -u scripts/cull_dtu_mesh.py \
        -s "$DATA_DIR" -m "$OUT_DIR" -i images_masked -r 1 --eval \
        --mesh "$RAW" --out "$CULLED"

    echo
    echo "--- rung $RUNG: millimetres $(date) ---"
    python scripts/apply_scale.py --capture "$DATA_DIR/capture.json" \
        --mesh "$RAW"    --out "$OUT_DIR/mesh_dtufusion_${TAG}_mm.ply" --force-factor "$FACTOR"
    python scripts/apply_scale.py --capture "$DATA_DIR/capture.json" \
        --mesh "$CULLED" --out "$OUT_DIR/mesh_dtucull_${TAG}_mm.ply"   --force-factor "$FACTOR"
done

echo
echo "=== what each step and each rung produced ==="
# A03 holds TEN sherds (masks.json: 10 instances per frame). Reported for every mesh so the
# effect of the cull, and of the refinement, shows as a difference rather than an assertion.
python scripts/mesh_report.py "$OUT_DIR"/mesh_dtu*_mm.ply --expect-pieces 10

echo
ls -la "$OUT_DIR"/*.ply
echo "=== finished $(date) ==="
echo "LOOK AT THE MESHES before believing any number above. A finer voxel resolves whatever"
echo "the depth maps contain -- which at 0.22 mm may be fracture relief or may be noise."
