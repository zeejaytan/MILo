#!/usr/bin/env bash
# Step 2a of the GS-augment A02 cheap test: 15 novel SH5 close-ups from the
# existing checkpoint. GPU, minutes. Runs inside the held allocation:
#   bash scripts/gpu_session.sh run 'bash scripts/render_a02_gsaug_step2a.sh'
set -euo pipefail
unset MSYSTEM OSTYPE MSYS CYGWIN || true
export PYTHONNOUSERSITE=1
unset PYTHONHOME || true
module purge
module load GCC/11.3.0 OpenMPI/4.1.4 CUDA/11.8.0
export CUDA_HOME="${EBROOTCUDA:?EBROOTCUDA missing after module load}"
export LD_LIBRARY_PATH="$CUDA_HOME/targets/x86_64-linux/lib:${LD_LIBRARY_PATH:-}"
cd /data/gpfs/projects/punim2657/MILo/repo/milo
export PYTHONPATH="/data/gpfs/projects/punim2657/MILo/repo/milo:${PYTHONPATH:-}"
/data/gpfs/projects/punim2657/MILo/envs/milo/bin/python ../scripts/render_novel_sh5.py \
    -s /data/gpfs/projects/punim2657/MILo/data/17062025/A02 \
    -m /data/gpfs/projects/punim2657/MILo/output/17062025/A02 \
    -i images \
    --boxes /data/gpfs/projects/punim2657/MILo/repo/scripts/A02_sherd_boxes.json \
    --sherd SH5 \
    --out /data/gpfs/projects/punim2657/MILo/output/17062025/A02/gsaug_renders
