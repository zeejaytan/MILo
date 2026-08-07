#!/usr/bin/env bash
# Pull one capture's photographs from Mediaflux straight onto Spartan.
#
# RUN THIS ON THE SPARTAN LOGIN NODE, not through Slurm. Two reasons:
#   * The transfer is server-to-server (Mediaflux -> Spartan storage). The photographs
#     never touch the laptop, which is the whole point.
#   * ~/.Arcitecta/mflux.cfg holds host/port/transport/domain/user but no credential, so
#     the client prompts for a password. A batch job has no terminal to prompt at. If you
#     add a secure identity token to the config, this becomes non-interactive and can be
#     batched — but there is no need, the transfer is I/O bound, not compute.
#
# Usage (on Spartan):
#   ./scripts/mediaflux_fetch.sh <mediaflux-namespace> <date>/<tree>
#
# Example:
#   ./scripts/mediaflux_fetch.sh /projects/proj-xxxx/Rabati2025/16062025 16062025
#
# The destination is the path the photogrammetry pipeline config already expects:
#   /data/gpfs/projects/punim2657/Rabati2025/<date>/<tree>/
set -euo pipefail

PHOTO_ROOT="${PHOTO_ROOT:-/data/gpfs/projects/punim2657/Rabati2025}"
MF_CONFIG="${MF_CONFIG:-$HOME/.Arcitecta/mflux.cfg}"
LOG_DIR="${LOG_DIR:-/data/gpfs/projects/punim2657/MILo/logs/mediaflux}"
# The university asks for no more than 4 threads on shared infrastructure.
NB_WORKERS="${NB_WORKERS:-4}"
NB_QUERIERS="${NB_QUERIERS:-4}"

if [[ $# -lt 2 ]]; then
  echo "Usage: $0 <mediaflux-namespace> <capture-relpath>" >&2
  echo "  e.g. $0 /projects/proj-xxxx/Rabati2025/16062025 16062025" >&2
  exit 1
fi

SRC_NAMESPACE="$1"
CAPTURE="$2"
DEST="${PHOTO_ROOT}/${CAPTURE}"

if [[ ! -f "$MF_CONFIG" ]]; then
  echo "No Mediaflux config at $MF_CONFIG." >&2
  echo "Create one with host/port/transport/domain/user before running this." >&2
  exit 1
fi

module load unimelb-mf-clients

mkdir -p "$DEST" "$LOG_DIR"

echo "Mediaflux : $SRC_NAMESPACE"
echo "Spartan   : $DEST"
echo "Config    : $MF_CONFIG (you will be prompted for your password)"
echo

# --csum-check verifies each file's CRC32 after transfer. Photographs are the one
# irreplaceable thing in this project: the sherds are in Georgia and the capture cannot
# be repeated. A silently truncated JPEG would surface much later as an unexplained
# reconstruction failure.
unimelb-mf-download \
  --mf.config "$MF_CONFIG" \
  --out "$DEST" \
  --exclude-parent \
  --csum-check \
  --preserve-modified-time \
  --nb-workers "$NB_WORKERS" \
  --nb-queriers "$NB_QUERIERS" \
  --log-dir "$LOG_DIR" \
  "${SRC_NAMESPACE%/}/"

echo
echo "=== verifying local copy against Mediaflux ==="
CHECK_CSV="${LOG_DIR}/check_${CAPTURE//\//_}.csv"
unimelb-mf-check \
  --mf.config "$MF_CONFIG" \
  --direction down \
  --output "$CHECK_CSV" \
  --nb-workers "$NB_WORKERS" \
  --nb-queriers "$NB_QUERIERS" \
  "$DEST" "${SRC_NAMESPACE%/}"

# unimelb-mf-check reports differences in the CSV and still exits 0, so the exit code
# alone proves nothing. Without --detailed-output the CSV lists only missing or invalid
# files, so anything past the header line is a real discrepancy.
DIFFS=$(($(wc -l < "$CHECK_CSV") - 1))
if [[ "$DIFFS" -gt 0 ]]; then
  echo "unimelb-mf-check found $DIFFS missing or invalid file(s): $CHECK_CSV" >&2
  echo "Do NOT reconstruct from this copy — re-run the download first." >&2
  exit 1
fi
echo "Verified: no missing or invalid files ($CHECK_CSV)"

echo
echo "=== local tally ==="
find "$DEST" -type f \( -iname '*.jpg' -o -iname '*.jpeg' \) | wc -l | xargs echo "JPEGs:"
du -sh "$DEST"
echo
echo "Next: run the COLMAP stage in the photogrammetry repo, then scripts/colmap_to_milo.py"
