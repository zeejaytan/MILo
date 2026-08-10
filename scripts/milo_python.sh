#!/usr/bin/env bash
# The MILo interpreter, insulated from whatever the module system has put on the path.
#
# WHY THIS WRAPPER EXISTS. Loading COLMAP/3.9-CUDA-11.7.0 drags in SciPy-bundle/2022.05,
# which prepends a Python 3.10 site-packages directory to PYTHONPATH. Running the MILo
# environment's Python 3.9 with that in place picks up the wrong numpy and dies with:
#
#   ImportError: Importing the numpy C-extensions failed.
#   ... No module named 'numpy.core._multiarray_umath'
#
# The message points at numpy being broken, which it is not — it is the right numpy being
# shadowed by one built for a different Python. Anything that loads a compiler-toolchain
# module and then calls this interpreter needs this, which is both the photogrammetry
# pipeline (via $PYTHON) and the mapper sweep.
#
# Usage: same as python. Set MILO_PY to point at a different interpreter.
exec env -u PYTHONPATH -u PYTHONHOME PYTHONNOUSERSITE=1 \
     "${MILO_PY:-/data/gpfs/projects/punim2657/MILo/envs/milo/bin/python}" "$@"
