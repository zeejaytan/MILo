#!/bin/bash
#SBATCH --job-name=goris-convert
#SBATCH --account=punim2657
#SBATCH --partition=sapphire
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=16G
#SBATCH --time=00:30:00
#SBATCH --output=/data/gpfs/projects/punim2657/MILo/logs/goris_convert_%j.log

# Ticket gor-is-mesh/01: finish the A03 -> GOR-IS conversion on a CPU node.
# 164 full-res PNG writes outlast one login ssh window; the script resumes
# (skips masks already on disk). CPU-only, no GPU.
#
# Usage:
#   ./scripts/remote/pull_and_sbatch.sh slurm/goris_convert.slurm

set -euo pipefail

MILO_ROOT=/data/gpfs/projects/punim2657/MILo

echo "=== GOR-IS convert started $(date) on $(hostname) ==="
"$MILO_ROOT/envs/milo/bin/python" "$MILO_ROOT/repo/scripts/goris_convert_A03.py" "$@"
echo "=== GOR-IS convert finished $(date) ==="
ls "$MILO_ROOT/data/goris_A03/object_mask" | wc -l
