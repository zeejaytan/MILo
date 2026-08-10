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

# The exact argument list for secure.identity.token.create could not be verified without
# credentials, so it is overridable. The default asks for a token carrying the caller's
# own identity, which is what unattended transfers need. If the server wants a role,
# re-run as:
#   TOKEN_CMD='secure.identity.token.create :role -type role <role-name>' ./scripts/mediaflux_token.sh
TOKEN_CMD="${TOKEN_CMD:-secure.identity.token.create}"

[[ -f "$BASE_CFG" ]] || { echo "No Mediaflux config at $BASE_CFG" >&2; exit 1; }

module load unimelb-mf-clients

# aterm takes its config from $MFLUX_CFG and its command as bare arguments. It does NOT
# accept --mf.config or --command; passing those makes it try to run "--mf.config" as a
# Tcl command.
run_aterm() {
    MFLUX_CFG="$BASE_CFG" aterm "$@"
}

# Run aterm under a pty and keep a transcript.
#
# Java offers a password prompt only when System.console() is available, which requires
# BOTH stdin and stdout to be a terminal. Capturing output with $(...) redirects stdout,
# so aterm dies with "Interactive console disabled" before it ever asks — which is
# exactly what happened on the first attempt at this script. `script` gives the command
# a real pty while writing everything to a file, so the prompt still reaches you and the
# response is still readable afterwards.
run_aterm_captured() {
    local cmd="$1" out="$2"
    script -qec "MFLUX_CFG='$BASE_CFG' aterm '$cmd'" "$out"
}

case "${1:-create}" in
  --describe)
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

TRANSCRIPT=$(mktemp)
trap 'rm -f "$TRANSCRIPT"' EXIT

echo "Creating a Mediaflux identity token."
echo "Command: $TOKEN_CMD"
echo "You will be prompted for your password once."
echo

if ! run_aterm_captured "$TOKEN_CMD" "$TRANSCRIPT"; then
    echo >&2
    echo "aterm failed. Its output was:" >&2
    cat "$TRANSCRIPT" >&2
    exit 1
fi

# aterm exits 0 even when the service itself rejects the call, so the transcript is what
# decides whether this worked.
if grep -qiE 'error|exception|invalid|refused|denied' "$TRANSCRIPT"; then
    echo >&2
    cat "$TRANSCRIPT" >&2
    echo >&2
    echo "The server rejected that call. Asking it what it expects — you will be" >&2
    echo "prompted for your password again:" >&2
    echo >&2
    run_aterm "system.service.describe :service secure.identity.token.create" || true
    echo >&2
    echo "Then re-run with the argument list it wants, e.g.:" >&2
    echo "  TOKEN_CMD='secure.identity.token.create :role -type role <role>' $0" >&2
    exit 1
fi

echo
cat "$TRANSCRIPT"

# The token is the long opaque string in the service response.
TOKEN=$(grep -oE '[A-Za-z0-9+/=_-]{24,}' "$TRANSCRIPT" | tail -1 || true)
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
echo "Wrote $TOKEN_CFG (mode 600). It is outside the repository and cannot be committed."

# Prove the token actually authenticates, rather than assuming it. If this prompts for a
# password, the token is not being accepted and the config is worse than useless — it
# would make every batch job hang on a prompt it cannot answer.
echo
echo "=== verifying the token works unattended ==="
MF_ROOT="${MF_ROOT:-/projects/proj-1000_rbt23photogrammetry-1128.4.1250}"
if MFLUX_CFG="$TOKEN_CFG" aterm "asset.namespace.exists :namespace $MF_ROOT" < /dev/null; then
    echo
    echo "Token verified. Transfers now run without prompts:"
    echo "  ./scripts/mediaflux_fetch.sh --list"
    echo "  sbatch slurm/mediaflux_transfer.slurm down 16062025"
else
    echo >&2
    echo "The token did not authenticate. Remove $TOKEN_CFG and try a different role:" >&2
    echo "  rm $TOKEN_CFG" >&2
    echo "  $0 --describe" >&2
    exit 1
fi
