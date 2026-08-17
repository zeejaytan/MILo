#!/bin/bash
#SBATCH --job-name=mflux-xfer
#SBATCH --account=punim2657
#SBATCH --partition=cascade
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=12:00:00
#SBATCH --output=/data/gpfs/projects/punim2657/MILo/logs/mflux_xfer_%j.log

set -euo pipefail

# Unattended Mediaflux transfer, in either direction.
#
# Requires a secure identity token (scripts/mediaflux_token.sh). Without one the client
# would prompt for a password, and a batch job has no terminal to prompt at — so this
# checks for the token up front rather than hanging until the wall-clock limit.
#
# A CPU partition, not GPU: this is network and disk work. 4 threads, which is the
# university's stated ceiling on shared infrastructure, so more cores would sit idle.
#
# Usage:
#   ./scripts/remote/pull_and_sbatch.sh slurm/mediaflux_transfer.slurm down 16062025
#   ./scripts/remote/pull_and_sbatch.sh slurm/mediaflux_transfer.slurm up /data/.../18062025
#
# Several captures at once:
#   for c in 16062025 17062025/A02 18062025/B01; do
#     ./scripts/remote/pull_and_sbatch.sh slurm/mediaflux_transfer.slurm down "$c"
#   done

DIRECTION="${1:?usage: sbatch mediaflux_transfer.slurm <down|up> <capture-or-path> [namespace]}"
TARGET="${2:?usage: sbatch mediaflux_transfer.slurm <down|up> <capture-or-path> [namespace]}"
NAMESPACE="${3:-}"

REPO_DIR=/data/gpfs/projects/punim2657/MILo/repo
TOKEN_CFG="${TOKEN_CFG:-$HOME/.Arcitecta/mflux-token.cfg}"

echo "=== Mediaflux $DIRECTION : $TARGET — started $(date) on $(hostname) ==="

if [[ ! -f "$TOKEN_CFG" ]]; then
    echo "No token config at $TOKEN_CFG." >&2
    echo "A batch job cannot answer a password prompt. Create a token first, once, at a" >&2
    echo "terminal on the login node:" >&2
    echo "  cd $REPO_DIR && ./scripts/mediaflux_token.sh" >&2
    exit 1
fi

cd "$REPO_DIR"

# PHOTOGRAPHS ONLY when a single tree is named. A tree's namespace is about three quarters
# camera raws that nothing in this pipeline reads -- A03 is 165 JPG (1.41 GB) against 187
# NEF (4.21 GB) -- and unimelb-mf-download has no extension filter, so the whole-namespace
# route moves 4 GB in order to ignore it. mediaflux_fetch_tree.py enumerates first and
# passes only the photographs. Set WITH_RAWS=1 for the whole namespace, and use the plain
# whole-date form (e.g. "16062025") when that is genuinely what is wanted.
case "$DIRECTION" in
  down)
    if [[ "$TARGET" == */* && "${WITH_RAWS:-0}" != "1" ]]; then
        DEST="/data/gpfs/projects/punim2657/Rabati2025/$TARGET"
        echo "single tree: fetching photographs only -> $DEST"
        module purge
        module load Miniforge3/24.7.1-2
        eval "$(conda shell.bash hook)"
        conda activate /data/gpfs/projects/punim2657/tools/sfm
        export PYTHONNOUSERSITE=1
        python scripts/mediaflux_fetch_tree.py --capture "$TARGET" --dest "$DEST" \
            ${WITH_PROJECT:+--with-project}
        echo
        echo "  photographs on disk: $(find "$DEST" -maxdepth 1 -iname '*.jpg' | wc -l)"
        du -sh "$DEST" 2>/dev/null | awk '{print "  size:", $1}'
    else
        ./scripts/mediaflux_fetch.sh "$TARGET" ${NAMESPACE:+"$NAMESPACE"}
    fi
    ;;
  up)   ./scripts/mediaflux_fetch.sh --up "$TARGET" ${NAMESPACE:+"$NAMESPACE"} ;;
  *)    echo "Direction must be 'down' or 'up', got '$DIRECTION'" >&2; exit 1 ;;
esac

echo
echo "=== Mediaflux $DIRECTION finished $(date) ==="
