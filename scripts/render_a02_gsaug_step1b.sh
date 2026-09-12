#!/usr/bin/env bash
# Step 1b of the GS-augment A02 cheap test: real-vs-render crops on SH5 views.
#
# CPU-only, seconds. Runs on the login node (no holder burn):
#   /data/gpfs/projects/punim2657/MILo/envs/milo/bin/python \
#       scripts/render_a02_gsaug_step1b.py --views A23_1029.JPG A23_1030.JPG ...
#
# Maps MILo's index-named renders (sorted names, every 8th held out) back to
# photo names, projects the SH5 box into each view with the COLMAP cameras,
# and writes small side-by-side crops + PSNR. The crops (KBs) are what get
# fetched to the laptop — never the full frames.
set -euo pipefail
exec /data/gpfs/projects/punim2657/MILo/envs/milo/bin/python \
    /data/gpfs/projects/punim2657/MILo/repo/scripts/render_a02_gsaug_step1b.py "$@"
