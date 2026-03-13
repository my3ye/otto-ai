#!/bin/bash
# Otto SessionStart hook — injects token-budgeted context into Claude's context.
# stdout from this script is added to Claude's context automatically.
set -euo pipefail

API="http://localhost:8100"

# Read hook input from stdin
INPUT=$(cat)
SOURCE=$(echo "$INPUT" | python3 -c "import json,sys; print(json.load(sys.stdin).get('source','startup'))" 2>/dev/null || echo "startup")

# Start a new session
SESSION_ID=$(curl -sf -X POST "${API}/sessions/start" \
  -H 'Content-Type: application/json' \
  -d '{"session_type": "claude_code"}' 2>/dev/null \
  | python3 -c "import json,sys; print(json.load(sys.stdin)['id'])" 2>/dev/null) || {
  echo "[Otto] Warning: Memory API unreachable"
  exit 0
}

# Save session ID for Stop hook
echo "$SESSION_ID" > /tmp/otto-session-id

# Token budget: 30% of model context window as ceiling
# Sonnet/Opus: 200k context → 30% = 60,000 tokens max
# But scale budget to content needs — no point reserving 60k for 800 tokens of memories
# Use generous defaults that grow with Otto's knowledge, capped at 30%
CONTEXT_CEILING=60000
# Heartbeat sessions get a tighter budget to leave room for actual work
OTTO_SESSION_TYPE="${OTTO_SESSION_TYPE:-}"
case "$SOURCE" in
  compact) MAX_TOKENS=5000 ;;    # Essentials after compaction
  resume)  MAX_TOKENS=12000 ;;  # Medium on resume
  *)       MAX_TOKENS=20000 ;;  # Full on startup
esac
if [ "$OTTO_SESSION_TYPE" = "heartbeat" ] || [ "$OTTO_SESSION_TYPE" = "reflection" ] || [ "$OTTO_SESSION_TYPE" = "alpha_heartbeat" ]; then
  MAX_TOKENS=10000  # Heartbeat/reflection context — enough for good decisions, leaves budget for work
fi
# Never exceed 30% ceiling
if [ "$MAX_TOKENS" -gt "$CONTEXT_CEILING" ]; then
  MAX_TOKENS=$CONTEXT_CEILING
fi

# Get token-budgeted context injection (endpoint returns JSON string, decode it)
CONTEXT=$(curl -sf "${API}/context/inject?max_tokens=${MAX_TOKENS}&source=${SOURCE}" 2>/dev/null \
  | python3 -c "import json,sys; print(json.loads(sys.stdin.read()))" 2>/dev/null) || {
  echo "[Otto] Session ${SESSION_ID} started (context injection failed)"
  exit 0
}

echo "[Otto] Session ID: ${SESSION_ID}"
echo ""
echo "$CONTEXT"

exit 0
