#!/usr/bin/env bash
# Mint a Mediaflux secure identity token so transfers can run unattended.
#
# WHY A TOKEN AND NOT A PASSWORD. The clients read credentials from an mflux.cfg, so
# unattended transfer means putting *something* in a file. A secure identity token is the
# mechanism Mediaflux provides for exactly this: it can be revoked on its own without
# changing your account password, it can be scoped to just the roles it needs, and it
# does not expose the password that also gets you into everything else at the university.
#
# You type your password ONCE. If a working token already exists, not even that: a token
# holding your user role can mint its replacement, so re-rolling costs no prompt.
#
# THREE THINGS THAT COST SEVERAL FAILED ATTEMPTS, recorded so they are not rediscovered:
#
#   1. aterm parses a QUOTED STRING AS A SINGLE TCL COMMAND NAME. `aterm "svc :arg val"`
#      fails with `invalid command name`. The service and each argument must be separate
#      shell arguments. A bare `secure.identity.token.create` appeared to work only
#      because it takes no arguments, which disguised the bug.
#   2. Java offers a password prompt only when System.console() exists, needing BOTH
#      stdin and stdout on a terminal. Capturing output with $(...) silently disables it
#      ("Interactive console disabled"). script(1) gives aterm a pty and a transcript.
#   3. ROLES ARE NOT INHERITED TRANSITIVELY. A token granted `:role -type user <you>`
#      authenticates as you and still cannot read your project: the project permission
#      comes from a role your user holds, and that role must be granted to the token
#      explicitly. A token with no :role at all authenticates and can do nothing.
#
# Usage (on Spartan):
#   ./scripts/mediaflux_token.sh              # create/refresh the token config
#   ./scripts/mediaflux_token.sh --roles      # show the roles your account holds
#   ./scripts/mediaflux_token.sh --list       # tokens you already hold
#   ./scripts/mediaflux_token.sh --destroy <id>
set -euo pipefail

BASE_CFG="${BASE_CFG:-$HOME/.Arcitecta/mflux.cfg}"
TOKEN_CFG="${TOKEN_CFG:-$HOME/.Arcitecta/mflux-token.cfg}"
# The allocation is what roles are named after; MF_ROOT is where the captures actually
# live inside it. They are not the same string, and conflating them makes the role lookup
# below silently find nothing.
MF_ALLOCATION="${MF_ALLOCATION:-proj-1000_rbt23photogrammetry-1128.4.1250}"
MF_ROOT="${MF_ROOT:-/projects/${MF_ALLOCATION}/Rabati2025}"

module load unimelb-mf-clients

# Arguments are always separate array elements, never one quoted string. See note 1.
aterm_with() { local cfg="$1"; shift; MFLUX_CFG="$cfg" aterm "$@" < /dev/null; }

# Prefer an existing working token: minting a replacement then costs no password prompt.
pick_source_cfg() {
    if [[ -f "$TOKEN_CFG" ]] && aterm_with "$TOKEN_CFG" actor.self.describe >/dev/null 2>&1; then
        echo "$TOKEN_CFG"
    else
        echo "$BASE_CFG"
    fi
}
SOURCE_CFG="$(pick_source_cfg)"
[[ -f "$SOURCE_CFG" ]] || { echo "No Mediaflux config at $SOURCE_CFG" >&2; exit 1; }
INTERACTIVE=0
[[ "$SOURCE_CFG" == "$BASE_CFG" ]] && INTERACTIVE=1

# Who the account is. From the token if we have one, else from the base config.
resolve_user() {
    local u
    u=$(aterm_with "$SOURCE_CFG" actor.self.describe 2>/dev/null \
        | sed -n 's/.*-type "user" "\([^"]*\)".*/\1/p' | head -1) || true
    if [[ -z "$u" ]]; then
        local d n
        d=$(grep -E '^domain=' "$BASE_CFG" | cut -d= -f2- | tr -d '\r')
        n=$(grep -E '^user='   "$BASE_CFG" | cut -d= -f2- | tr -d '\r')
        [[ -n "$d" && -n "$n" ]] && u="${d}:${n}"
    fi
    echo "$u"
}

case "${1:-create}" in
  --roles)
    MF_USER="$(resolve_user)"
    echo "Roles held by ${MF_USER:-?}:"
    aterm_with "$SOURCE_CFG" actor.describe :type user :name "$MF_USER"
    exit 0
    ;;
  --list)    aterm_with "$SOURCE_CFG" secure.identity.token.describe; exit 0 ;;
  --destroy)
    [[ -n "${2:-}" ]] || { echo "Usage: $0 --destroy <token-id>" >&2; exit 1; }
    aterm_with "$SOURCE_CFG" secure.identity.token.destroy :id "$2"
    echo "Destroyed token $2."
    exit 0
    ;;
  create|"") ;;
  *) echo "Unknown option: $1" >&2; exit 1 ;;
esac

MF_USER="$(resolve_user)"
[[ -n "$MF_USER" ]] || { echo "Could not determine the Mediaflux user" >&2; exit 1; }

echo "Account: $MF_USER"
echo "Source : $SOURCE_CFG$([[ $INTERACTIVE == 1 ]] && echo ' (you will be prompted once)' \
        || echo ' (existing token — no prompt needed)')"

# Which roles to grant. Only those covering the allocation this repo works with, plus the
# user role itself — not every role the account happens to hold. A token that can reach
# one project is a smaller thing to lose than one that can reach everything.
PROJECT="$MF_ALLOCATION"
ROLES_RAW=$(aterm_with "$SOURCE_CFG" actor.describe :type user :name "$MF_USER" 2>/dev/null \
            | sed -n 's/.*-type "role" "\([^"]*\)".*/\1/p' || true)
mapfile -t PROJECT_ROLES < <(printf '%s\n' "$ROLES_RAW" | grep -F "$PROJECT" || true)

if [[ ${#PROJECT_ROLES[@]} -eq 0 ]]; then
    echo >&2
    echo "Your account holds no role naming '$PROJECT'. Roles found:" >&2
    printf '  %s\n' $ROLES_RAW >&2
    echo "Set MF_ROOT to the right allocation, or grant the role explicitly with" >&2
    echo "  TOKEN_ROLES='role-a role-b' $0" >&2
    exit 1
fi
[[ -n "${TOKEN_ROLES:-}" ]] && read -r -a PROJECT_ROLES <<< "$TOKEN_ROLES"

echo "Granting: ${PROJECT_ROLES[*]} (+ user $MF_USER)"
echo

ARGS=(secure.identity.token.create :role -type user "$MF_USER")
for r in "${PROJECT_ROLES[@]}"; do ARGS+=(:role -type role "$r"); done

TRANSCRIPT=$(mktemp)
trap 'rm -f "$TRANSCRIPT"' EXIT
chmod 600 "$TRANSCRIPT"

if [[ $INTERACTIVE == 1 ]]; then
    # script(1) takes one string, so build a properly quoted command line for it.
    printf -v CMDLINE '%q ' "${ARGS[@]}"
    script -qec "MFLUX_CFG=$(printf '%q' "$SOURCE_CFG") aterm ${CMDLINE}" "$TRANSCRIPT" \
        || { echo "aterm failed:" >&2; cat "$TRANSCRIPT" >&2; exit 1; }
else
    aterm_with "$SOURCE_CFG" "${ARGS[@]}" > "$TRANSCRIPT" 2>&1 || true
fi

# aterm exits 0 even when the server rejects the call, so the transcript decides.
if grep -qiE 'ExNotAuthorized|invalid command|ExServiceError|Exception' "$TRANSCRIPT"; then
    echo "The server rejected that call:" >&2
    sed 's/\r$//' "$TRANSCRIPT" >&2
    exit 1
fi

# Response line looks like:
#   :token -id "64494" -actor-type "identity" -actor-name "330192" "<the token>"
# Take the last quoted field of that line specifically; the transcript also holds
# script(1)'s own header and footer.
TOKEN_LINE=$(tr -d '\r' < "$TRANSCRIPT" | grep ':token ' | tail -1)
TOKEN=$(printf '%s' "$TOKEN_LINE" | sed 's/.*"\([^"]*\)"[[:space:]]*$/\1/')
TOKEN_ID=$(printf '%s' "$TOKEN_LINE" | sed -n 's/.*-id "\([^"]*\)".*/\1/p')

if [[ -z "$TOKEN" || "$TOKEN" == *' '* ]]; then
    echo "Could not read a token out of the response:" >&2
    sed 's/\r$//' "$TRANSCRIPT" >&2
    exit 1
fi

OLD_ID=""
[[ -f "$TOKEN_CFG" ]] && OLD_ID=$(grep -E '^# token-id=' "$TOKEN_CFG" | cut -d= -f2- || true)

# Same server details as the interactive config, authenticating by token instead of by
# user+password. domain/user are omitted deliberately: the token carries the identity.
umask 077
{
    grep -E '^(host|port|transport)=' "$BASE_CFG"
    echo "token=$TOKEN"
    echo "# token-id=$TOKEN_ID"
} > "$TOKEN_CFG"
chmod 600 "$TOKEN_CFG"
echo "Wrote $TOKEN_CFG (mode 600, token id ${TOKEN_ID:-unknown})."

# Prove the token can do the thing it exists for, unattended. A token that authenticates
# but is granted nothing looks fine until every batch job fails on it — which is exactly
# what the first two attempts here produced.
#
# The check goes through unimelb-mf-check, NOT aterm. The project role is not granted
# ACCESS to asset.namespace.list, and Mediaflux reports that denial as "The namespace ...
# does not exist or is not accessible" — indistinguishable from a wrong path, and it sent
# an earlier version of this script hunting for a namespace that was correct all along.
# The transfer clients are what the workflow actually depends on, so they are what gets
# tested. An empty temporary directory means nothing is downloaded.
echo
echo "=== verifying: enumerating $MF_ROOT with the token, no prompt ==="
PROBE_DIR=$(mktemp -d); PROBE_CSV=$(mktemp)
trap 'rm -rf "$TRANSCRIPT" "$PROBE_DIR" "$PROBE_CSV"' EXIT
if unimelb-mf-check --mf.config "$TOKEN_CFG" --direction down \
       --output "$PROBE_CSV" --no-csum-check --nb-queriers 4 \
       "$PROBE_DIR" "$MF_ROOT" 2>&1 | grep -E 'assets \[(checked|missing)\]|Connected'; then
    echo
    echo "Verified. Transfers now run unattended:"
    echo "  ./scripts/mediaflux_fetch.sh --list"
    echo "  sbatch slurm/mediaflux_transfer.slurm down 16062025"
    if [[ -n "$OLD_ID" && "$OLD_ID" != "$TOKEN_ID" ]]; then
        echo
        echo "Superseded token $OLD_ID is still valid. Revoke it with:"
        echo "  $0 --destroy $OLD_ID"
    fi
else
    echo >&2
    echo "The token authenticates but cannot enumerate $MF_ROOT." >&2
    echo "Check which roles your account holds:  $0 --roles" >&2
    exit 1
fi
