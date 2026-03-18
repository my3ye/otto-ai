#!/bin/bash
# Git Identity Enforcer
# Sets the correct git user.name and user.email for a given repo path.
# Looks up the correct owner from ~/otto/tools/repo_owners.json.
#
# Usage: git_identity_enforcer.sh <repo_path>
# Exit codes:
#   0 = identity set successfully
#   1 = unknown repo (no mapping found in config) — caller decides whether to reject
#   2 = usage/config error

REPO_PATH="${1:?Usage: git_identity_enforcer.sh <repo_path>}"
CONFIG_FILE="/home/web3relic/otto/tools/repo_owners.json"

if [ ! -f "$CONFIG_FILE" ]; then
    echo "ERROR: repo_owners.json not found at $CONFIG_FILE" >&2
    exit 2
fi

# Find the git repo root from the given path
GIT_ROOT=$(git -C "$REPO_PATH" rev-parse --show-toplevel 2>/dev/null) || {
    echo "WARNING: '$REPO_PATH' is not inside a git repo — skipping identity enforcement" >&2
    exit 0
}

# Look up owner config for this repo root
OWNER_JSON=$(python3 -c "
import json, sys
try:
    config = json.load(open(sys.argv[1]))
    root = sys.argv[2]
    # Exact match first
    if root in config:
        print(json.dumps(config[root]))
        sys.exit(0)
    # Prefix match (for worktrees or nested paths)
    for k, v in config.items():
        if root.startswith(k + '/') or root == k:
            print(json.dumps(v))
            sys.exit(0)
    sys.exit(1)
except Exception as e:
    print(str(e), file=sys.stderr)
    sys.exit(2)
" "$CONFIG_FILE" "$GIT_ROOT" 2>/dev/null)

if [ -z "$OWNER_JSON" ]; then
    echo "WARNING: No owner mapping found for git root '$GIT_ROOT' — identity not changed" >&2
    exit 1
fi

# Extract name and email
GIT_NAME=$(echo "$OWNER_JSON" | python3 -c "import json,sys; print(json.load(sys.stdin)['name'])" 2>/dev/null)
GIT_EMAIL=$(echo "$OWNER_JSON" | python3 -c "import json,sys; print(json.load(sys.stdin)['email'])" 2>/dev/null)

if [ -z "$GIT_NAME" ] || [ -z "$GIT_EMAIL" ]; then
    echo "ERROR: Invalid owner config for '$GIT_ROOT' (missing name or email)" >&2
    exit 2
fi

# Check current identity
CURRENT_NAME=$(git -C "$GIT_ROOT" config --local user.name 2>/dev/null || echo "")
CURRENT_EMAIL=$(git -C "$GIT_ROOT" config --local user.email 2>/dev/null || echo "")

# Set local git config identity
git -C "$GIT_ROOT" config --local user.name "$GIT_NAME"
git -C "$GIT_ROOT" config --local user.email "$GIT_EMAIL"

if [ "$CURRENT_NAME" != "$GIT_NAME" ] || [ "$CURRENT_EMAIL" != "$GIT_EMAIL" ]; then
    echo "Git identity updated for $GIT_ROOT: $GIT_NAME <$GIT_EMAIL> (was: $CURRENT_NAME <$CURRENT_EMAIL>)"
else
    echo "Git identity confirmed for $GIT_ROOT: $GIT_NAME <$GIT_EMAIL>"
fi

exit 0
