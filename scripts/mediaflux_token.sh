#!/usr/bin/env bash
# Mint a Mediaflux secure identity token so transfers can run unattended.
#
# WHY A TOKEN AND NOT A PASSWORD. The clients read credentials from an mflux.cfg, so
# unattended transfer means putting *something* in a file. A secure identity token is the
# mechanism Mediaflux provides for exactly this: it can be revoked on its own without
# changing your account password, it can be scoped to a role rather than to you, and it
# does not expose the password that also gets you into everything else at the university.
# A password sitting in a file gets copied, committed and backed up; a token can be
# destroyed with one command the moment it is not wanted.
#
# You type your password ONCE, here. Everything afterwards — downloads, uploads, Slurm
# jobs — runs without a prompt.
#
# Usage (on the Spartan LOGIN NODE, at a real terminal):
#   ./scripts/mediaflux_token.sh              # create the token and write the config
#   ./scripts/mediaflux_token.sh --describe   # print the service's real signature
#   ./scripts/mediaflux_token.sh --list       # list tokens you already hold
#   ./scripts/mediaflux_token.sh --destroy <id>
#
# To revoke everything later:
#   ./scripts/mediaflux_token.sh --list       # find the id
#   ./scripts/mediaflux_token.sh --destroy <id>
#   rm ~/.Arcitecta/mflux-token.cfg
set -euo pipefail

BASE_CFG="${BASE_CFG:-$HOME/.Arcitecta/mflux.cfg}"
TOKEN_CFG="${TOKEN_CFG:-$HOME/.Arcitecta/mflux-token.cfg}"
# What the token is allowed to do. "read-write" for uploads as well as downloads.
TOKEN_ROLE="${TOKEN_ROLE:-read-write}"

[[ -f "$BASE_CFG" ]] || { echo "No Mediaflux config at $BASE_CFG" >&2; exit 1; }

module load unimelb-mf-clients

# aterm takes its config from $MFLUX_CFG and its command as bare arguments. It does NOT
# accept --mf.config or --command; passing those makes it try to run "--mf.config" as a
# Tcl command, which is what went wrong the first time this was attempted.
run_aterm() {
    MFLUX_CFG="$BASE_CFG" aterm "$@"
}

case "${1:-create}" in
  --describe)
    # The exact argument list for secure.identity.token.create is the one thing here that
    # could not be verified without credentials. If creation below is rejected, run this
    # and adjust TOKEN_ROLE or the command to match what the server actually expects.
    run_aterm "system.service.describe :service secure.identity.token.create"
    exit 0
    ;;
  --list)
    run_aterm "secure.identity.token.describe"
    exit 0
    ;;
  --destroy)
    [[ -n "${2:-}" ]] || { echo "Usage: $0 --destroy <token-id>" >&2; exit 1; }
    run_aterm "secure.identity.token.destroy :id $2"
    echo "Destroyed token $2. Also remove $TOKEN_CFG if it held that token."
    exit 0
    ;;
  create|"") ;;
  *) echo "Unknown option: $1" >&2; exit 1 ;;
esac

echo "Creating a Mediaflux identity token (role: $TOKEN_ROLE)."
echo "You will be prompted for your password once."
echo

OUT=$(run_aterm "secure.identity.token.create :role -type role $TOKEN_ROLE") || {
    echo >&2
    echo "Token creation was rejected. Ask the server what it expects:" >&2
    echo "  $0 --describe" >&2
    echo "then set TOKEN_ROLE, or edit the command in this script to match." >&2
    exit 1
}

echo "$OUT"

# The token comes back in the service response; pull out the long opaque string.
TOKEN=$(printf '%s\n' "$OUT" | grep -oE '[A-Za-z0-9+/=_-]{24,}' | tail -1)
if [[ -z "$TOKEN" ]]; then
    echo >&2
    echo "Could not find a token in the response above. Copy it by hand into $TOKEN_CFG" >&2
    echo "as a line reading  token=<the token>  alongside host/port/transport." >&2
    exit 1
fi

# Same server details as the interactive config, but authenticating by token instead of
# by user+password. domain/user are deliberately omitted: the token carries the identity.
umask 077
{
    grep -E '^(host|port|transport)=' "$BASE_CFG"
    echo "token=$TOKEN"
} > "$TOKEN_CFG"
chmod 600 "$TOKEN_CFG"

echo
echo "Wrote $TOKEN_CFG (permissions 600, readable only by you)."
echo "It is outside the repository and cannot be committed."
echo
echo "Transfers are now unattended. Try:"
echo "  ./scripts/mediaflux_fetch.sh --list"
echo "  sbatch slurm/mediaflux_transfer.slurm down 16062025"
