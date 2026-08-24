#!/bin/bash
#SBATCH --job-name=milo-carve
#SBATCH --account=punim2657
#SBATCH --partition=cascade
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=1:00:00
#SBATCH --output=/data/gpfs/projects/punim2657/MILo/logs/milo_carve_%j.log

set -euo pipefail

# Turn a MILo mesh trained WITHOUT masks into something a person can open.
#
# Unmasked training reconstructs the studio, so the raw mesh is a room with the sherd tree
# somewhere inside it. Two cuts get from there to sherds, in this order and for different
# reasons:
#
#   1. SILHOUETTE CARVING removes the room. A point belonging to the object projects inside
#      the object's outline; one that falls outside view after view cannot be part of it.
#      Carved against masks_milo/colmap -- the undistorted copy of exactly what MILo trained
#      on -- so this cut cannot remove surface the model was told to keep. In particular it
#      cannot shave the fracture rim, which is the whole point of an unmasked run.
#
#      --tol stays at the default. Raising it eats the break edges: colouring a carved A03
#      sherd by silhouette support showed the marginal 0.60-0.90 band covers the ENTIRE
#      fracture surface, because a thin steeply-angled surface sits near the silhouette in
#      most views (docs/notes/A03_BENT_SOLVE_AND_CLAMP_ARTEFACTS.md).
#
#   2. COLOUR removes the clamp. The rig is grey metal and the sherds are terracotta, and
#      dropping vertices by colour takes no geometry off the edges the way a tighter mask
#      would. It cannot un-weld a surface that grew continuous where clamp touches sherd --
#      nothing at this stage can, and that is the known cost of training unmasked.
#
# Usage:
#   ./scripts/remote/pull_and_sbatch.sh slurm/carve_milo.slurm 17062025/A03 A03_nomask

CAPTURE="${1:?usage: sbatch carve_milo.slurm <capture> [output_name]}"
OUT_NAME="${2:-$CAPTURE}"

MILO_ROOT=/data/gpfs/projects/punim2657/MILo
REPO_DIR=$MILO_ROOT/repo
ENV_PREFIX=$MILO_ROOT/envs/milo
DATA_DIR=$MILO_ROOT/data/$CAPTURE
OUT_DIR=$MILO_ROOT/output/$OUT_NAME
WORK=$(python3 -c "import json;print(json.load(open('$DATA_DIR/capture.json'))['work_dir'])")
DENSE="$WORK/dense_fixed"
MASKS="$WORK/masks_milo/colmap"

MESH="$OUT_DIR/mesh_learnable_sdf.ply"
CARVED="$OUT_DIR/mesh_carved.ply"

echo "=== carving $OUT_NAME started $(date) on $(hostname) ==="
echo "  mesh : $MESH"
echo "  dense: $DENSE"
echo "  masks: $MASKS"

[[ -f "$MESH" ]] || { echo "No mesh at $MESH" >&2; exit 1; }
[[ -d "$MASKS" ]] || { echo "No undistorted masks at $MASKS" >&2; exit 1; }

module purge
module load Miniforge3/24.7.1-2
eval "$(conda shell.bash hook)"
conda activate "$ENV_PREFIX"

cd "$REPO_DIR"

python scripts/silhouette_filter.py \
    --mesh "$MESH" --out "$CARVED" \
    --dense "$DENSE" --masks "$MASKS" \
    --every 2

echo
echo "=== millimetres, and sherds only $(date) ==="
# capture.json records no scale factor for this capture, so take it from the two scale
# bars the capture actually measured rather than from a number remembered in a chat. They
# disagree slightly; the mean is used and the disagreement is printed, because it is the
# floor on any millimetre figure quoted from this mesh.
FACTOR=$(python3 - "$WORK/measurement.env" <<'PY'
import sys
env = dict(l.strip().split("=", 1) for l in open(sys.argv[1]) if "=" in l)
f1 = float(env["d1_real_m"]) / float(env["d1_rec_units"])
f2 = float(env["d2_real_m"]) / float(env["d2_rec_units"])
print(f"{(f1 + f2) / 2:.9f}")
print(f"  scale bar 1: {f1*1000:.2f} mm/unit", file=sys.stderr)
print(f"  scale bar 2: {f2*1000:.2f} mm/unit", file=sys.stderr)
print(f"  they disagree by {abs(f1-f2)/((f1+f2)/2)*100:.1f}% -- every millimetre figure "
      f"from this mesh carries at least that", file=sys.stderr)
PY
)

python scripts/apply_scale.py \
    --capture "$DATA_DIR/capture.json" \
    --mesh "$CARVED" \
    --out "$OUT_DIR/mesh_carved_mm.ply" \
    --force-factor "$FACTOR"

python - "$OUT_DIR/mesh_carved_mm.ply" "$OUT_DIR/mesh_carved_sherds_mm.ply" <<'PY'
"""Drop the grey rig, keep the terracotta. Colour, not geometry: a tighter mask would
take the fracture rim off with the clamp, and that rim is what this whole run was for."""
import sys
import numpy as np
import trimesh

src, dst = sys.argv[1], sys.argv[2]
m = trimesh.load(src, process=False)
if isinstance(m, trimesh.Scene):
    m = trimesh.util.concatenate(list(m.geometry.values()))
col = np.asarray(m.visual.vertex_colors)[:, :3].astype(int)
V = np.asarray(m.vertices)
sel = ((col[:, 0] - (col[:, 1] + col[:, 2]) / 2) > 25) & (col.mean(1) > 45)
F = np.asarray(m.faces)
Fs = F[sel[F].all(axis=1)]
used = np.unique(Fs)
remap = np.full(len(V), -1, np.int64)
remap[used] = np.arange(len(used))
s = trimesh.Trimesh(vertices=V[used], faces=remap[Fs], process=False)
s.visual.vertex_colors = np.asarray(m.visual.vertex_colors)[used]
s.export(dst)
area = s.area / 100.0
print(f"  terracotta: {len(used):,} vertices over {area:.0f} cm2 of sherd surface")
print(f"  = {len(used)/area:.0f} per cm2, a sample every {10/np.sqrt(len(used)/area):.2f} mm")
print(f"  in {len(s.split(only_watertight=False))} separate pieces")
PY

echo
echo "=== produced ==="
ls -la "$OUT_DIR"/mesh_carved*.ply
echo "=== finished $(date) ==="
echo "LOOK AT IT before believing any number above."
