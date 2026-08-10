#!/usr/bin/env bash
# Run the COLMAP + OpenMVS pipeline on ONE photo group, working around three problems
# in the current Spartan environment without editing the pottery-photogrammetry repo.
#
# Usage (on Spartan):
#   ./scripts/run_photogrammetry.sh 16062025/A11
#   ./scripts/run_photogrammetry.sh 16062025/A11 --dry-run
#
# WHAT IT WORKS AROUND. All three are environment drift since the pipeline last ran in
# November 2025; none is a fault in the pipeline's logic.
#
#   1. pipeline_main.sh runs a Python snippet to discover WHICH MODULES TO LOAD, and that
#      snippet imports yaml — but the modules providing yaml are only loaded thirty lines
#      later. It worked while the default python3 happened to have PyYAML. It no longer
#      does: /usr/bin/env python3 now resolves to the `graphify` conda environment.
#      Fixed by pointing PYTHON at the MILo environment, which pipeline_main.sh honours
#      for every stage, including split_and_validate.py's trimesh and pandas.
#
#   2. The module list loads Python/3.10.4 BEFORE GCC/11.3.0. Under Lmod that Python only
#      exists underneath GCC, so the load fails outright. Since the interpreter now comes
#      from PYTHON, the module is redundant and is dropped.
#
#   3. validation.min_vertices is 100000. On 16062025 that kept only the clamp rig
#      (232k vertices) and the backdrop (227k) and discarded every actual sherd, which
#      came out between 18k and 82k. Vertex count measures how well something was
#      photographed, not whether it is pottery. Lowered here; judge the components with
#      scripts/extract_sherds.py afterwards.
#
# The pipeline's own config is never modified. A patched copy is generated from it at
# submit time, so any change made upstream is picked up automatically.
set -euo pipefail

GROUP="${1:?usage: $0 <date>/<group>   e.g. 16062025/A11}"
shift || true
DRY_RUN=0
[[ "${1:-}" == "--dry-run" ]] && DRY_RUN=1

PHOTOGRAMMETRY="${PHOTOGRAMMETRY:-/data/gpfs/projects/punim2657/Photogrammetry}"
MILO_ROOT="${MILO_ROOT:-/data/gpfs/projects/punim2657/MILo}"
MILO_PY="${MILO_PY:-$MILO_ROOT/envs/milo/bin/python}"
PHOTO_ROOT="${PHOTO_ROOT:-/data/gpfs/projects/punim2657/Rabati2025}"
MIN_VERTICES="${MIN_VERTICES:-2000}"

SRC_CONFIG="$PHOTOGRAMMETRY/pipeline/config/pipeline_config.yaml"
OUT_CONFIG="$MILO_ROOT/config/pipeline_config_group.yaml"

[[ -x "$MILO_PY" ]] || { echo "No MILo interpreter at $MILO_PY" >&2; exit 1; }
[[ -f "$SRC_CONFIG" ]] || { echo "No pipeline config at $SRC_CONFIG" >&2; exit 1; }

PHOTOS="$PHOTO_ROOT/$GROUP"
N=$(find "$PHOTOS" -maxdepth 1 -type f \( -iname '*.jpg' -o -iname '*.jpeg' \) 2>/dev/null | wc -l)
if [[ "$N" -lt 10 ]]; then
    echo "Only $N JPEGs in $PHOTOS — is that the right group?" >&2
    exit 1
fi
echo "Group  : $GROUP ($N photographs)"

mkdir -p "$(dirname "$OUT_CONFIG")"
"$MILO_PY" - "$SRC_CONFIG" "$OUT_CONFIG" "$MIN_VERTICES" <<'PY'
import sys, yaml
src, dst, min_vertices = sys.argv[1], sys.argv[2], int(sys.argv[3])
cfg = yaml.safe_load(open(src))

env = cfg.setdefault("environment", {})
# Drop the Python module: it is loaded before GCC and cannot resolve, and the
# interpreter is supplied through $PYTHON instead.
env["python_module"] = ""
# Make sure the compiler hierarchy is loaded before anything that lives under it.
wanted = ["GCC/11.3.0", "OpenMPI/4.1.4", "ICU/71.1", "COLMAP/3.9-CUDA-11.7.0"]
extra = [m for m in wanted if m in env.get("extra_modules", [])] or wanted
env["extra_modules"] = extra

old = cfg.get("validation", {}).get("min_vertices")
cfg.setdefault("validation", {})["min_vertices"] = min_vertices

yaml.safe_dump(cfg, open(dst, "w"), sort_keys=False)
print(f"Config : {dst}")
print(f"         python_module dropped; modules {extra}")
print(f"         validation.min_vertices {old} -> {min_vertices}")
PY

if [[ "$DRY_RUN" == "1" ]]; then
    echo "(dry run — not submitting)"
    exit 0
fi

cd "$PHOTOGRAMMETRY"
sbatch --export=ALL,PYTHON="$MILO_PY",PYTHONNOUSERSITE=1,CONFIG_PATH="$OUT_CONFIG" \
       pipeline/bin/submit_single.sh "$GROUP"
