#!/usr/bin/env bash
# Mint a Mediaflux secure identity token so transfers can run unattended.
#
# WHY A TOKEN AND NOT A PASSWORD. The clients read credentials from an mflux.cfg, so
# unattended transfer means putting *something* in a file. A secure identity token is the
# mechanism Mediaflux provides for exactly this: it can be revoked on its own without
# changing your account password, and it does not expose the password that also gets you
# into everything else at the university.
#
# You type your password ONCE, here. Everything afterwards — downloads, uploads, Slurm
# jobs — runs without a prompt.
#
# TWO THINGS ABOUT ATERM THAT COST SEVERAL FAILED ATTEMPTS, recorded so they are not
# rediscovered the hard way:
#
#   1. aterm parses a QUOTED STRING AS A SINGLE TCL COMMAND NAME. `aterm "svc :arg val"`
#      fails with `invalid command name "svc :arg val"`. The service and its arguments
#      must be passed as separate shell arguments: `aterm svc :arg val`. This is why
#      a bare `secure.identity.token.create` worked while everything with arguments did
#      not. Hence the array-based invocation below.
#   2. Java offers a password prompt only when System.console() exists, which needs BOTH
#      stdin and stdout on a terminal. Capturing output with $(...) silently disables the
#      prompt ("Interactive console disabled"). script(1) gives aterm a real pty while
#      still recording what it printed.
#
# AND ONE ABOUT THE TOKEN ITSELF: a token created without :role authenticates but is
# granted nothing — every service call comes back "not granted ACCESS". The token has to
# be given the caller's own user actor as a role, which is what this does by default.
#
# Usage (on the Spartan LOGIN NODE, at a real terminal):
#   ./scripts/mediaflux_token.sh              # create the token and write the config
#   ./scripts/mediaflux_token.sh --describe   # print the service's signature
#   ./scripts/mediaflux_token.sh --list       # tokens you already hold
#   ./scripts/mediaflux_token.sh --destroy <id>
set -euo pipefail

BASE_CFG="${BASE_CFG:-$HOME/.Arcitecta/mflux.cfg}"
TOKEN_CFG="${TOKEN_CFG:-$HOME/.Arcitecta/mflux-token.cfg}"
MF_ROOT="${MF_ROOT:-/projects/proj-1000_rbt23photogrammetry-1128.4.1250}"

[[ -f "$BASE_CFG" ]] || { echo "No Mediaflux config at $BASE_CFG" >&2; exit 1; }

module load unimelb-mf-clients

cfg_get() { grep -E "^$1=" "$BASE_CFG" | head -1 | cut -d= -f2- | tr -d '\r'; }
MF_DOMAIN="$(cfg_get domain)"
MF_USER="$(cfg_get user)"

# Arguments are separate array elements, never one quoted string. See note 1 above.
run_aterm()       { MFLUX_CFG="$BASE_CFG"  aterm "$@" < /dev/null; }
run_aterm_token() { MFLUX_CFG="$TOKEN_CFG" aterm "$@" < /dev/null; }

case "${1:-create}" in
  --describe) run_aterm system.service.describe :service secure.identity.token.create; exit 0 ;;
  --list)     run_aterm secure.identity.token.describe; exit 0 ;;
  --destroy)
    [[ -n "${2:-}" ]] || { echo "Usage: $0 --destroy <token-id>" >&2; exit 1; }
    # Prefer the working token, so revoking an old one costs no password prompt.
    if [[ -f "$TOKEN_CFG" ]]; then
        run_aterm_token secure.identity.token.destroy :id "$2"
    else
        run_aterm secure.identity.token.destroy :id "$2"
    fi
    echo "Destroyed token $2."
    exit 0
    ;;
  create|"") ;;
  *) echo "Unknown option: $1" >&2; exit 1 ;;
esac

if [[ -z "$MF_DOMAIN" || -z "$MF_USER" ]]; then
    echo "Could not read domain/user from $BASE_CFG" >&2
    exit 1
fi

# Grant the token the caller's own user actor as a role. Without this it authenticates
# and can do nothing at all.
TOKEN_ARGS=(secure.identity.token.create :role -type user "${MF_DOMAIN}:${MF_USER}")

TRANSCRIPT=$(mktemp)
trap 'rm -f "$TRANSCRIPT"' EXIT

echo "Creating a Mediaflux identity token for ${MF_DOMAIN}:${MF_USER}."
echo "You will be prompted for your password once."
echo

# script(1) needs one string, so build a properly quoted command line for it.
printf -v TOKEN_CMDLINE '%q ' "${TOKEN_ARGS[@]}"
script -qec "MFLUX_CFG=$(printf '%q' "$BASE_CFG") aterm ${TOKEN_CMDLINE}" "$TRANSCRIPT" || {
    echo "aterm failed:" >&2; cat "$TRANSCRIPT" >&2; exit 1
}

# aterm exits 0 even when the server rejects the call, so the transcript decides.
if grep -qiE 'ExNotAuthorized|invalid command|Exception|error' "$TRANSCRIPT"; then
    echo >&2
    echo "The server rejected that call:" >&2
    sed 's/\r$//' "$TRANSCRIPT" >&2
    exit 1
fi

# The response line looks like:
#   :token -id "64488" -actor-type "identity" -actor-name "330180" "<the token>"
# Take the last quoted field on that line rather than pattern-matching the whole
# transcript, which also contains script(1)'s own header and footer.
TOKEN=$(tr -d '\r' < "$TRANSCRIPT" | grep ':token ' | tail -1 | sed 's/.*"\([^"]*\)"[[:space:]]*$/\1/')
TOKEN_ID=$(tr -d '\r' < "$TRANSCRIPT" | grep ':token ' | tail -1 | sed -n 's/.*-id "\([^"]*\)".*/\1/p')

if [[ -z "$TOKEN" || "$TOKEN" == *' '* ]]; then
    echo >&2
    echo "Could not read a token out of the response. It was:" >&2
    sed 's/\r$//' "$TRANSCRIPT" >&2
    exit 1
fi

# Same server details as the interactive config, authenticating by token instead of by
# user+password. domain/user are omitted deliberately: the token carries the identity.
umask 077
{
    grep -E '^(host|port|transport)=' "$BASE_CFG"
    echo "token=$TOKEN"
} > "$TOKEN_CFG"
chmod 600 "$TOKEN_CFG"

echo
echo "Wrote $TOKEN_CFG (mode 600, id ${TOKEN_ID:-unknown})."
echo "It is outside the repository and cannot be committed."

# Prove the token can do the thing it exists for, unattended. A token that authenticates
# but is granted nothing looks fine until every batch job fails on it, which is exactly
# what happened with the first one minted here.
echo
echo "=== verifying the token can list the allocation without a prompt ==="
if run_aterm_token asset.namespace.list :namespace "$MF_ROOT"; then
    echo
    echo "Verified. Transfers now run without prompts:"
    echo "  ./scripts/mediaflux_fetch.sh --list"
    echo "  sbatch slurm/mediaflux_transfer.slurm down 16062025"
else
    echo >&2
    echo "The token authenticates but is not authorised. Remove it and investigate:" >&2
    echo "  rm $TOKEN_CFG" >&2
    echo "  $0 --describe" >&2
    exit 1
fi
