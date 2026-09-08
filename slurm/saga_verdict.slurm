#!/bin/bash
#SBATCH --job-name=saga-verdict
#SBATCH --account=punim2657
#SBATCH --partition=gpu-a100-short
#SBATCH --gres=gpu:1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=02:00:00
#SBATCH --output=/data/gpfs/projects/punim2657/MILo/logs/saga_verdict_%j.log

# Ticket alt-09: SAGA post-hoc filter, stage 4 — verdict pictures + number.
#
# Same-ruler comparison of the filtered mesh (primary: threshold 0.1) against
# the OpenMVS fixed-frame refined mesh, plus whole-mesh renders for the eye.
# Render/compare need the card (nvdiffrast); nothing else here does.
# Steel evidence is the mesh_report redness column (fired clay reads +7..+28,
# steel ~-5) plus the eye on these renders — the M4/M5 precedent.
#
# Usage:
#   ./scripts/remote/pull_and_sbatch.sh slurm/saga_verdict.slurm

set -euo pipefail

MILO_ROOT=/data/gpfs/projects/punim2657/MILo
REPO_DIR=$MILO_ROOT/repo
ENV_PREFIX=$MILO_ROOT/envs/milo
DATA_DIR=$MILO_ROOT/data/17062025/A03_sherds
SAGA_MESH=$MILO_ROOT/output/saga_A03_filt_01/mesh_saga_filt_t0.1_mm.ply
OPENMVS_MESH=/data/gpfs/projects/punim2657/Rabati2025/17062025/A03/work_colmap_openmvs/dense_fixed/scene_refined_mm.ply
OUT_DIR=$MILO_ROOT/output/saga_verdict

echo "=== SAGA verdict started $(date) on $(hostname) ==="
nvidia-smi | head -5 || true

[[ -f "$SAGA_MESH" ]] || { echo "No SAGA mesh — run slurm/saga_fuse.slurm first" >&2; exit 1; }
[[ -f "$OPENMVS_MESH" ]] || { echo "No OpenMVS mesh" >&2; exit 1; }

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

mkdir -p "$OUT_DIR"
cd "$REPO_DIR"

# Sidecar: same ruler as every other A03 millimetre (measurement.env factor),
# stated not smuggled. Compare refuses meshes without one — and wants the
# scale_mesh.py name form (<stem>.scale.json, suffix REPLACED, not appended;
# the appended form cost job 30234537 its comparison).
python - "$SAGA_MESH" <<'PY'
import json, sys, datetime
from pathlib import Path
mesh = Path(sys.argv[1])
env = dict(l.strip().split("=", 1) for l in open(
    "/data/gpfs/projects/punim2657/Rabati2025/17062025/A03/"
    "work_colmap_openmvs/measurement.env") if "=" in l)
f = ((float(env["d1_real_m"]) / float(env["d1_rec_units"]) +
      float(env["d2_real_m"]) / float(env["d2_rec_units"])) / 2) * 1000.0
sidecar = {"units": "millimetres", "mm_per_unit": f,
           "capture": "17062025/A03", "method": "SAGA-filtered DTU rung 0",
           "scaled_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),
           "source": "blue base top face 190x130 mm (same measurement.env as OpenMVS sidecar)",
           "caveat": "same ~1% precision caveat as the OpenMVS sidecar it is compared against"}
open(mesh.with_suffix(".scale.json"), "w").write(json.dumps(sidecar, indent=2))
print(f"sidecar: {f:.4f} mm/unit")
PY

echo "--- renders (whole mesh, both routes) ---"
python -u scripts/render_mesh.py \
    --mesh "$SAGA_MESH" --mesh "$OPENMVS_MESH" --out "$OUT_DIR/renders"

echo "--- same-ruler compare, SAGA primary vs OpenMVS ---"
python -u scripts/compare_meshes.py \
    --capture "$DATA_DIR/capture.json" --milo "$SAGA_MESH" --openmvs "$OPENMVS_MESH" \
    --out "$OUT_DIR/compare_01" 2>&1 | tee "$OUT_DIR/log_compare_01.txt"

echo "=== finished $(date) ==="
echo "Fetch $OUT_DIR/renders + compare_01 and LOOK before any verdict."
