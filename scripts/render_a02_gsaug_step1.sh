#!/usr/bin/env bash
# Step 1 of the GS-augment A02 cheap test (ticket: pottery-photogrammetry
# .scratch/gs-augment-a02/issues/01-cheap-test.md).
#
# Re-render the EXISTING A02 splat scene at full resolution. No retraining.
# Runs inside the held GPU allocation:
#   bash scripts/gpu_session.sh run 'bash scripts/render_a02_gsaug_step1.sh'
#
# WHY no `conda activate`: the Miniforge hook emits `cygpath` calls that do not
# exist on the compute node, so activation dies before Python starts. The env
# Python carries its own packages; CUDA comes from modules (milo_train.slurm
# pattern), hence the explicit CUDA_HOME / LD_LIBRARY_PATH below.
set -euo pipefail

unset MSYSTEM OSTYPE MSYS CYGWIN || true
export PYTHONNOUSERSITE=1
unset PYTHONHOME || true

module purge
module load GCC/11.3.0 OpenMPI/4.1.4 CUDA/11.8.0
export CUDA_HOME="${EBROOTCUDA:?EBROOTCUDA missing after module load}"
export LD_LIBRARY_PATH="$CUDA_HOME/targets/x86_64-linux/lib:${LD_LIBRARY_PATH:-}"

cd /data/gpfs/projects/punim2657/MILo/repo/milo
/data/gpfs/projects/punim2657/MILo/envs/milo/bin/python render.py \
    -s /data/gpfs/projects/punim2657/MILo/data/17062025/A02 \
    -m /data/gpfs/projects/punim2657/MILo/output/17062025/A02 \
    -i images -r 1 --rasterizer radegs
