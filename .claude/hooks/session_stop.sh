#!/bin/bash
# Otto Stop hook — auto-ends the session when Claude finishes.
# Reads the session ID saved by the SessionStart hook.
set -euo pipefail

API="http://localhost:8100"

# Read hook input
INPUT=$(cat)

# Check if stop_hook_active to prevent infinite loops
IS_ACTIVE=$(echo "$INPUT" | python3 -c "import json,sys; print(json.load(sys.stdin).get('stop_hook_active', False))" 2>/dev/null || echo "False")
if [ "$IS_ACTIVE" = "True" ]; then
  exit 0
fi

# Get session ID from file
SESSION_ID=""
if [ -f /tmp/otto-session-id ]; then
  SESSION_ID=$(cat /tmp/otto-session-id)
fi

if [ -z "$SESSION_ID" ]; then
  exit 0
fi

# End session with a generic summary (the session helper captures more detail)
curl -sf -X POST "${API}/sessions/${SESSION_ID}/end" \
  -H 'Content-Type: application/json' \
  -d '{"summary": "Session completed"}' >/dev/null 2>&1 || true

# Clean up
rm -f /tmp/otto-session-id

exit 0
