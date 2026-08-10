#!/usr/bin/env bash
# Move data between Mediaflux and Spartan, in either direction, without the laptop.
#
# The transfer is server-to-server: Mediaflux to Spartan storage and back. Photographs
# never pass through the laptop, which is the point.
#
# CREDENTIALS. If ~/.Arcitecta/mflux-token.cfg exists (see scripts/mediaflux_token.sh)
# this runs unattended and can be submitted as a Slurm job. Otherwise it falls back to
# ~/.Arcitecta/mflux.cfg, which has no stored credential and will prompt — meaning it
# must then be run at a real terminal on the login node, not through Slurm.
#
# Usage (on Spartan):
#   ./scripts/mediaflux_fetch.sh --list [sub-namespace]      browse the allocation
#   ./scripts/mediaflux_fetch.sh <capture> [namespace]       download a capture
#   ./scripts/mediaflux_fetch.sh --up <local-path> [namespace]   upload
#
# Examples:
#   ./scripts/mediaflux_fetch.sh --list
#   ./scripts/mediaflux_fetch.sh 16062025
#   ./scripts/mediaflux_fetch.sh --up /data/gpfs/projects/punim2657/Rabati2025/18062025
#
# Downloads land where the photogrammetry pipeline config already expects them:
#   /data/gpfs/projects/punim2657/Rabati2025/<date>/<tree>/
set -euo pipefail

# Rabati 2023 photogrammetry allocation. The layout underneath it is not assumed —
# use --list to see it, then pass a full namespace if a capture sits deeper.
MF_ROOT="${MF_ROOT:-/projects/proj-1000_rbt23photogrammetry-1128.4.1250/Rabati2025}"
PHOTO_ROOT="${PHOTO_ROOT:-/data/gpfs/projects/punim2657/Rabati2025}"
TOKEN_CFG="${TOKEN_CFG:-$HOME/.Arcitecta/mflux-token.cfg}"
BASE_CFG="${BASE_CFG:-$HOME/.Arcitecta/mflux.cfg}"
LOG_DIR="${LOG_DIR:-/data/gpfs/projects/punim2657/MILo/logs/mediaflux}"
# The university asks for no more than 4 threads on shared infrastructure.
NB_WORKERS="${NB_WORKERS:-4}"
NB_QUERIERS="${NB_QUERIERS:-4}"

if [[ -f "$TOKEN_CFG" ]]; then
    MF_CONFIG="$TOKEN_CFG"
    UNATTENDED=1
elif [[ -f "$BASE_CFG" ]]; then
    MF_CONFIG="$BASE_CFG"
    UNATTENDED=0
else
    echo "No Mediaflux config at $TOKEN_CFG or $BASE_CFG." >&2
    exit 1
fi

# Decide whether a unimelb-mf-check run found anything wrong.
#
# The client exits 0 whether or not it found differences, so the exit code proves nothing.
# The CSV is not a bare list of problems either: it always carries a header row and a
# four-line summary block, so counting lines reports 7 failures on a perfect transfer —
# which is exactly what an earlier version of this script did, on a run the client itself
# had just declared clean. The summary rows are the authority.
check_failures() {
    local csv="$1" missing mismatch
    missing=$(awk -F, '/Number of assets \(missing\)/  {gsub(/[^0-9]/,"",$4); print $4}' "$csv")
    mismatch=$(awk -F, '/Number of assets \(content mismatch\)/ {gsub(/[^0-9]/,"",$4); print $4}' "$csv")
    if [[ -z "$missing" || -z "$mismatch" ]]; then
        echo "UNPARSEABLE"
        return
    fi
    echo $(( missing + mismatch ))
}

usage() {
    echo "Usage: $0 --list [sub-namespace]" >&2
    echo "       $0 <capture> [mediaflux-namespace]" >&2
    echo "       $0 --up <local-path> [mediaflux-namespace]" >&2
    echo "Allocation root (override with \$MF_ROOT): $MF_ROOT" >&2
    exit 1
}
[[ $# -ge 1 ]] || usage

module load unimelb-mf-clients
mkdir -p "$LOG_DIR"

echo "Config: $MF_CONFIG$([[ $UNATTENDED == 1 ]] && echo ' (token — unattended)' \
      || echo ' (no stored credential — you will be prompted)')"

# --- browse -------------------------------------------------------------------------
if [[ "$1" == "--list" ]]; then
    NS="${MF_ROOT%/}${2:+/${2#/}}"
    echo "Listing $NS"
    echo
    # Enumeration goes through unimelb-mf-check against an EMPTY temporary directory:
    # every remote asset comes back as "missing locally", which is exactly the listing we
    # want, and nothing is transferred.
    #
    # Not aterm. The project role is not granted ACCESS to asset.namespace.list, and
    # Mediaflux reports that denial as "The namespace ... does not exist or is not
    # accessible" — wording indistinguishable from a wrong path, which cost a long detour
    # hunting for a namespace that was correct all along.
    PROBE_DIR=$(mktemp -d)
    LIST_CSV="${LOG_DIR}/list_$(echo "${2:-root}" | tr '/' '_').csv"
    trap 'rm -rf "$PROBE_DIR"' EXIT
    unimelb-mf-check --mf.config "$MF_CONFIG" --direction down \
        --output "$LIST_CSV" --detailed-output --no-csum-check \
        --nb-queriers "$NB_QUERIERS" --nb-workers "$NB_WORKERS" \
        "$PROBE_DIR" "$NS" 2>&1 | grep -E 'assets \[|Connected' || true

    echo
    echo "=== folders directly under $(basename "$NS") ==="
    grep -oE "${NS//./\\.}/[^\",]*" "$LIST_CSV" 2>/dev/null \
        | sed "s|^${NS}/||" | cut -d/ -f1 | sort | uniq -c | sort -rn | head -30
    echo
    echo "=== file types ==="
    grep -oE "${NS//./\\.}/[^\",]*" "$LIST_CSV" 2>/dev/null \
        | sed 's/.*\.//' | sort | uniq -c | sort -rn | head -12
    echo
    echo "Full inventory: $LIST_CSV"
    exit 0
fi

# --- upload -------------------------------------------------------------------------
if [[ "$1" == "--up" ]]; then
    SRC="${2:?Usage: $0 --up <local-path> [namespace]}"
    [[ -e "$SRC" ]] || { echo "No such path: $SRC" >&2; exit 1; }
    DEST_NS="${3:-${MF_ROOT%/}}"
    LABEL=$(basename "$SRC")

    echo "Spartan   : $SRC"
    echo "Mediaflux : $DEST_NS"
    echo

    unimelb-mf-upload \
        --mf.config "$MF_CONFIG" \
        --dest "$DEST_NS" \
        --csum-check \
        --nb-workers "$NB_WORKERS" \
        --nb-queriers "$NB_QUERIERS" \
        --log-dir "$LOG_DIR" \
        "$SRC"

    echo
    echo "=== verifying the upload ==="
    CHECK_CSV="${LOG_DIR}/check_up_${LABEL}.csv"
    unimelb-mf-check \
        --mf.config "$MF_CONFIG" \
        --direction up \
        --output "$CHECK_CSV" \
        --nb-workers "$NB_WORKERS" \
        --nb-queriers "$NB_QUERIERS" \
        "$SRC" "${DEST_NS%/}/${LABEL}"
    DIFFS=$(check_failures "$CHECK_CSV")
    if [[ "$DIFFS" == "UNPARSEABLE" ]]; then
        echo "Could not read a verification summary from $CHECK_CSV — treating as unverified." >&2
        echo "Do not delete the local copy." >&2
        exit 1
    fi
    if [[ "$DIFFS" -gt 0 ]]; then
        echo "$DIFFS file(s) missing or invalid on the server: $CHECK_CSV" >&2
        echo "Do not delete the local copy." >&2
        exit 1
    fi
    echo "Verified: every file present and intact on Mediaflux ($CHECK_CSV)"
    exit 0
fi

# --- download -----------------------------------------------------------------------
CAPTURE="$1"
SRC_NAMESPACE="${2:-${MF_ROOT%/}/${CAPTURE}}"
DEST="${PHOTO_ROOT}/${CAPTURE}"

mkdir -p "$DEST"
echo "Mediaflux : $SRC_NAMESPACE"
echo "Spartan   : $DEST"
echo

# --csum-check verifies each file's CRC32 after transfer. The photographs are the one
# irreplaceable thing in this project: the sherds are in Georgia and the capture cannot
# be repeated. A silently truncated file would surface much later as an unexplained
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
echo "=== verifying the local copy ==="
CHECK_CSV="${LOG_DIR}/check_down_${CAPTURE//\//_}.csv"
unimelb-mf-check \
    --mf.config "$MF_CONFIG" \
    --direction down \
    --output "$CHECK_CSV" \
    --nb-workers "$NB_WORKERS" \
    --nb-queriers "$NB_QUERIERS" \
    "$DEST" "${SRC_NAMESPACE%/}"

DIFFS=$(check_failures "$CHECK_CSV")
if [[ "$DIFFS" == "UNPARSEABLE" ]]; then
    echo "Could not read a verification summary from $CHECK_CSV — treating as unverified." >&2
    echo "Do NOT reconstruct from this copy." >&2
    exit 1
fi
if [[ "$DIFFS" -gt 0 ]]; then
    echo "$DIFFS file(s) missing or invalid: $CHECK_CSV" >&2
    echo "Do NOT reconstruct from this copy — re-run the download." >&2
    exit 1
fi
echo "Verified: every asset present and checksum-matched ($CHECK_CSV)"

echo
echo "=== what arrived ==="
find "$DEST" -type f | sed 's/.*\.//' | sort | uniq -c | sort -rn | head
du -sh "$DEST"

# The COLMAP pipeline reads JPEG and explicitly excludes .nef/.raw
# (pipeline_config.yaml: targets.exclude_extensions). A capture that arrives as raw only
# cannot be reconstructed until the raws are developed, and that is much better known now
# than after a failed COLMAP run.
JPEGS=$(find "$DEST" -type f \( -iname '*.jpg' -o -iname '*.jpeg' \) | wc -l)
RAWS=$(find "$DEST" -type f \( -iname '*.nef' -o -iname '*.raw' \) | wc -l)
echo
echo "JPEGs: $JPEGS    raw (NEF): $RAWS"
if [[ "$JPEGS" -eq 0 && "$RAWS" -gt 0 ]]; then
    echo
    echo "WARNING: this capture arrived as camera raw only. The photogrammetry pipeline" >&2
    echo "reads JPEG and excludes .nef by configuration, so COLMAP has nothing to work" >&2
    echo "from yet. The raws need developing to JPEG or TIFF first." >&2
fi

echo
echo "Next: run the COLMAP stage in the photogrammetry repo, then scripts/colmap_to_milo.py"
