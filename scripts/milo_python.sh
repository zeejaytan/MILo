#!/usr/bin/env bash
# The MILo interpreter, insulated from module-provided Python packages but nothing else.
#
# WHY THIS WRAPPER EXISTS. Loading COLMAP/3.9-CUDA-11.7.0 drags in SciPy-bundle/2022.05,
# which prepends a Python 3.10 site-packages directory to PYTHONPATH. Running the MILo
# environment's Python 3.9 with that in place picks up the wrong numpy and dies with:
#
#   ImportError: Importing the numpy C-extensions failed.
#   ... No module named 'numpy.core._multiarray_umath'
#
# The message blames numpy, which is fine — it is the right numpy being shadowed by one
# built for a different Python.
#
# WHY IT FILTERS RATHER THAN CLEARS. An earlier version unset PYTHONPATH outright. That
# would have broken the photogrammetry pipeline at its first stage: run_colmap.sh sets
#   export PYTHONPATH="${PIPELINE_DIR}:${PYTHONPATH:-}"
# so that `from lib.pipeline_utils import ...` resolves, and clearing the variable throws
# that away along with the offending entries. Only paths under the module tree are
# dropped; everything the caller deliberately put there survives.
set -euo pipefail

MILO_PY="${MILO_PY:-/data/gpfs/projects/punim2657/MILo/envs/milo/bin/python}"

clean=""
if [[ -n "${PYTHONPATH:-}" ]]; then
    IFS=':' read -r -a parts <<< "$PYTHONPATH"
    for p in "${parts[@]}"; do
        [[ -z "$p" ]] && continue
        # Module-system packages are built for a different Python and must not shadow
        # this environment's. Anything else is the caller's business.
        case "$p" in
            /apps/easybuild*|/apps/*/easybuild/*) continue ;;
        esac
        clean="${clean:+$clean:}$p"
    done
fi

export PYTHONPATH="$clean"
export PYTHONNOUSERSITE=1
unset PYTHONHOME
exec "$MILO_PY" "$@"
