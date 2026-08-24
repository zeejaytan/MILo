#!/bin/bash
#SBATCH --job-name=milo-maskcull
#SBATCH --account=punim2657
#SBATCH --partition=gpu-a100
#SBATCH --gres=gpu:1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=128G
#SBATCH --time=6:00:00
#SBATCH --output=/data/gpfs/projects/punim2657/MILo/logs/milo_maskcull_%j.log

set -euo pipefail

# Re-extract a mesh from ALREADY-TRAINED Gaussians, with the object mask applied at the
# geometry stage instead of the photometric one. No retraining: this reads the same
# point_cloud.ply the unmasked run produced.
#
# WHY THIS STAGE IS THE SAFE ONE. Upstream MILo loads the PNG alpha channel into
# `view.gt_mask` and deliberately does NOT multiply the photograph by it -- the line that
# would is commented out in milo/scene/cameras.py. The mask is used in exactly one place,
# regularization/sdf/integration.py, where a point that falls outside the outline is not
# counted as occupied. That is a visual-hull cull of the SDF field: it decides what is
# solid, and never touches how the Gaussians learned to look. Applying the mask to the
# training loss instead (which this fork used to do) tells the model to paint background
# over the sherd rim in every view, and the rim is the fracture surface.
#
# That mask-aware path is reached ONLY with `--init integration`. Our runs default to
# `--init learnable`, which never calls it -- which is why the unmasked A03 mesh came out
# as an entire room.
#
# WHICH IMAGE SET. `-i images_masked` at EXTRACTION time, while the Gaussians came from
# `-i images`. The two are independent: the adapter writes images_masked with
# `rgba.putalpha(mask)`, RGB untouched, so the photograph stays whole and only the alpha
# channel is new. Vertex colours are still computed from the full photograph.
#
# WHAT TO WATCH. The refinement loop that runs after initialisation optimises against
# depth and normal losses computed from Gaussian renders, which know nothing about masks,
# so it can regrow surface the cull removed. --refine_iter is the lever; pass 0 to skip
# refinement entirely and keep the culled initialisation as-is.
#
# Usage:
#   ./scripts/remote/pull_and_sbatch.sh slurm/milo_extract_maskcull.slurm \
#        17062025/A03 17062025/A03_nomask 17062025/A03_maskcull [refine_iter]

CAPTURE="${1:?usage: sbatch milo_extract_maskcull.slurm <capture> <trained_run> <out_name> [refine_iter]}"
TRAINED="${2:?second argument is the finished run to read Gaussians from}"
OUT_NAME="${3:?third argument is where to write the new mesh}"
REFINE_ITER="${4:-1000}"

MILO_ROOT=/data/gpfs/projects/punim2657/MILo
REPO_DIR=$MILO_ROOT/repo
ENV_PREFIX=$MILO_ROOT/envs/milo
DATA_DIR=$MILO_ROOT/data/$CAPTURE
SRC_DIR=$MILO_ROOT/output/$TRAINED
OUT_DIR=$MILO_ROOT/output/$OUT_NAME

echo "=== mask-culled extraction started $(date) on $(hostname) ==="
echo "  Gaussians from : $SRC_DIR"
echo "  writing to     : $OUT_DIR"
echo "  refine_iter    : $REFINE_ITER"
nvidia-smi | head -15 || true

[[ -f "$SRC_DIR/point_cloud/iteration_18000/point_cloud.ply" ]] || {
    echo "No trained Gaussians at $SRC_DIR/point_cloud/iteration_18000/" >&2; exit 1; }
[[ -d "$DATA_DIR/images_masked" ]] || {
    echo "No RGBA image set at $DATA_DIR/images_masked -- rerun colmap_to_milo.py" >&2; exit 1; }

# Refuse to start on top of a finished mesh. The whole point of a separate output name is
# that the good unmasked mesh in $SRC_DIR stays untouched; silently overwriting a second
# result would defeat it.
if [[ -f "$OUT_DIR/mesh_learnable_sdf.ply" ]]; then
    echo "$OUT_DIR already holds a finished mesh. Move it aside or pick another name." >&2
    exit 1
fi

module purge
module load GCC/11.3.0 OpenMPI/4.1.4
module load CUDA/11.8.0
module load Miniforge3/24.7.1-2
export CUDA_HOME="${EBROOTCUDA:?}"
export LD_LIBRARY_PATH="$CUDA_HOME/targets/x86_64-linux/lib:${LD_LIBRARY_PATH:-}"

eval "$(conda shell.bash hook)"
conda activate "$ENV_PREFIX"

# Build a sibling model directory that SHARES the trained Gaussians by symlink. The
# extractor writes its mesh into the model directory it is given, so pointing it at the
# original run would overwrite the 111 MB unmasked mesh we want to compare against.
mkdir -p "$OUT_DIR"
for f in point_cloud cameras.json input.ply; do
    [[ -e "$SRC_DIR/$f" ]] && ln -sfn "$SRC_DIR/$f" "$OUT_DIR/$f"
done
# cfg_args is read from the model directory and merged with the command line, command line
# winning. Copy it so this directory stands on its own, then let -i and -m override.
cp -f "$SRC_DIR/cfg_args" "$OUT_DIR/cfg_args"

cd "$REPO_DIR/milo"

# --n_binary_steps_to_reset_sdf 0 : match configs/mesh/default.yaml, which the training run
#     used. The argparse default is 8, and each step re-integrates over every training
#     view -- eight times the cost for an initialisation the config says not to refine.
python mesh_extract_sdf.py \
    -s "$DATA_DIR" \
    -m "$OUT_DIR" \
    -i images_masked \
    -r 1 \
    --eval \
    --rasterizer radegs \
    --imp_metric indoor \
    --init integration \
    --refine_iter "$REFINE_ITER" \
    --n_binary_steps_to_reset_sdf 0

echo
echo "=== millimetres $(date) ==="
WORK=$(python3 -c "import json;print(json.load(open('$DATA_DIR/capture.json'))['work_dir'])")
FACTOR=$(python3 - "$WORK/measurement.env" <<'PY'
import sys
env = dict(l.strip().split("=", 1) for l in open(sys.argv[1]) if "=" in l)
f1 = float(env["d1_real_m"]) / float(env["d1_rec_units"])
f2 = float(env["d2_real_m"]) / float(env["d2_rec_units"])
print(f"{(f1 + f2) / 2:.9f}")
print(f"  the two scale bars disagree by {abs(f1-f2)/((f1+f2)/2)*100:.1f}% -- every "
      f"millimetre figure from this mesh carries at least that", file=sys.stderr)
PY
)
cd "$REPO_DIR"
python scripts/apply_scale.py \
    --capture "$DATA_DIR/capture.json" \
    --mesh "$OUT_DIR/mesh_learnable_sdf.ply" \
    --out "$OUT_DIR/mesh_maskcull_mm.ply" \
    --force-factor "$FACTOR"

python - "$OUT_DIR/mesh_maskcull_mm.ply" <<'PY'
"""Report the piece breakdown. A03 holds TEN sherds (masks.json: 10 instances per frame).

This says nothing about whether the break edges are any good -- that needs a render at a
scale which resolves a fracture ridge, against the photograph. It only catches the two
obvious failures: the cull did nothing (a room-sized main body), or the refinement regrew
what the cull removed."""
import sys
import numpy as np
import trimesh

m = trimesh.load(sys.argv[1], process=False)
if isinstance(m, trimesh.Scene):
    m = trimesh.util.concatenate(list(m.geometry.values()))
ext = m.vertices.max(0) - m.vertices.min(0)
print(f"  {len(m.vertices):,} vertices, overall extent "
      f"{ext[0]:.0f} x {ext[1]:.0f} x {ext[2]:.0f} mm")
pieces = sorted(m.split(only_watertight=False), key=lambda p: -len(p.vertices))
print("     span(mm)  vertices   per cm2   sample every")
sherdish = 0
for p in pieces:
    span = (p.vertices.max(0) - p.vertices.min(0)).max()
    if span < 15:
        continue
    sherdish += 1
    area = max(p.area / 100.0, 1e-6)
    dens = len(p.vertices) / area
    print(f"     {span:8.1f}  {len(p.vertices):8,}  {dens:8.0f}   {10/np.sqrt(dens):.2f} mm")
print(f"  {len(pieces)} pieces total, {sherdish} at least 15 mm across")
if sherdish and (p0 := (pieces[0].vertices.max(0) - pieces[0].vertices.min(0)).max()) > 400:
    print(f"  NOTE: largest piece spans {p0:.0f} mm. The mask cull did not bite -- check")
    print("        that images_masked really carries an alpha channel and that --init")
    print("        integration was honoured (the log says which init ran).")
PY

echo
echo "=== produced ==="
ls -la "$OUT_DIR"/*.ply
echo "=== finished $(date) ==="
echo "LOOK AT IT before believing any number above."
