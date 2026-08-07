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

case "$DIRECTION" in
  down) ./scripts/mediaflux_fetch.sh "$TARGET" ${NAMESPACE:+"$NAMESPACE"} ;;
  up)   ./scripts/mediaflux_fetch.sh --up "$TARGET" ${NAMESPACE:+"$NAMESPACE"} ;;
  *)    echo "Direction must be 'down' or 'up', got '$DIRECTION'" >&2; exit 1 ;;
esac

echo
echo "=== Mediaflux $DIRECTION finished $(date) ==="
