#!/bin/bash
# Otto Daily Strategy Runner
# Called by systemd timer once daily at 05:00 IST.
# Runs 3 strategic deep-dives and dispatches tasks for the day.

set -euo pipefail

OTTO_DIR="/home/web3relic/otto"
LOCK_FILE="/tmp/otto-strategy.lock"
LOG_DIR="${OTTO_DIR}/logs"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="${LOG_DIR}/strategy-${TIMESTAMP}.log"
API="http://localhost:8100"

mkdir -p "$LOG_DIR"

# ── Lock to prevent concurrent runs ──────────────────────────────────────────
if [ -f "$LOCK_FILE" ]; then
    LOCK_PID=$(cat "$LOCK_FILE" 2>/dev/null || echo "")
    if [ -n "$LOCK_PID" ] && kill -0 "$LOCK_PID" 2>/dev/null; then
        echo "$(date -Iseconds) Strategy already running (PID $LOCK_PID), skipping." >> "$LOG_FILE"
        exit 0
    else
        echo "$(date -Iseconds) Stale lock file found, removing." >> "$LOG_FILE"
        rm -f "$LOCK_FILE"
    fi
fi

# ── Rate limit awareness: check API endpoint first, fall back to sentinel ────
RATE_LIMITED=$(curl -sf "${API}/kernel/providers/rate-limited" 2>/dev/null | \
    python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('rate_limited','false'))" 2>/dev/null || echo "false")
if [ "$RATE_LIMITED" = "True" ] || [ "$RATE_LIMITED" = "true" ]; then
    REMAINING=$(curl -sf "${API}/kernel/providers/rate-limited" 2>/dev/null | \
        python3 -c "import json,sys; print(json.load(sys.stdin).get('remaining_seconds',0))" 2>/dev/null || echo "?")
    echo "$(date -Iseconds) SKIP: Rate limit backoff active — ${REMAINING}s remaining. Strategy suppressed." >> "$LOG_FILE"
    exit 0
fi
# Fallback: sentinel file
RATE_LIMIT_FILE="/tmp/otto-rate-limited"
if [ -f "$RATE_LIMIT_FILE" ]; then
    RATE_LIMIT_TS=$(grep -oE '^[0-9]+' "$RATE_LIMIT_FILE" 2>/dev/null || echo "0")
    NOW_TS=$(date +%s)
    ELAPSED=$(( NOW_TS - RATE_LIMIT_TS ))
    if [ "$ELAPSED" -lt 3600 ]; then
        REMAINING=$(( 3600 - ELAPSED ))
        echo "$(date -Iseconds) SKIP: Rate limit backoff active — hit ${ELAPSED}s ago, ${REMAINING}s remaining. Strategy suppressed." >> "$LOG_FILE"
        exit 0
    fi
fi

# ── Write lock ───────────────────────────────────────────────────────────────
echo $$ > "$LOCK_FILE"
trap 'rm -f "$LOCK_FILE"' EXIT

echo "$(date -Iseconds) Otto daily strategy starting..." >> "$LOG_FILE"

# ── Unified context: fetch S-MMU quality context from kernel ─────────────────
UNIFIED_CONTEXT=""
UNIFIED_CONTEXT_JSON=$(curl -sf "${API}/kernel/context?role=strategist&max_tokens=10000" 2>/dev/null || echo "")
if [ -n "$UNIFIED_CONTEXT_JSON" ]; then
    UNIFIED_CONTEXT=$(echo "$UNIFIED_CONTEXT_JSON" | python3 -c "
import json, sys
try:
    d = json.load(sys.stdin)
    ctx = d.get('context_text', '')
    tokens = d.get('token_count', 0)
    if ctx:
        print(ctx)
        print(f'[Unified context loaded: {tokens} tokens]', file=sys.stderr)
except: pass
" 2>>"$LOG_FILE" || echo "")
fi

# ── Build prompt ─────────────────────────────────────────────────────────────
PROMPT=""
if [ -n "$UNIFIED_CONTEXT" ]; then
    PROMPT="[UNIFIED BRAIN CONTEXT — same memory pipeline as all Otto interfaces]
${UNIFIED_CONTEXT}
[END UNIFIED CONTEXT]

"
fi
PROMPT="${PROMPT}Run your daily strategic analysis. Answer the three questions, dispatch tasks, send the brief to Mev."

# ── Run Claude Code CLI as the strategist ────────────────────────────────────
cd "$OTTO_DIR"
export OTTO_SESSION_TYPE=strategy

timeout 900s /home/web3relic/.local/bin/claude \
    --print \
    --agent strategist \
    --dangerously-skip-permissions \
    --model sonnet \
    --fallback-model haiku \
    --max-budget-usd 2.00 \
    --effort high \
    --no-session-persistence \
    -p "$PROMPT" \
    >> "$LOG_FILE" 2>&1
EXIT_CODE=$?

if [ $EXIT_CODE -eq 124 ]; then
    echo "$(date -Iseconds) Strategy TIMED OUT after 900s" >> "$LOG_FILE"
elif [ $EXIT_CODE -ne 0 ]; then
    echo "$(date -Iseconds) Strategy failed with exit code $EXIT_CODE" >> "$LOG_FILE"
fi

# ── Rate limit detection ─────────────────────────────────────────────────────
if grep -qE "HTTP 429|RateLimitError|overloaded_error|too_many_requests|rate_limit_exceeded|\"error\".*rate" "$LOG_FILE" 2>/dev/null; then
    date +%s > /tmp/otto-rate-limited
    echo "$(date -Iseconds) Rate limit detected — sentinel written." >> "$LOG_FILE"
fi

echo "$(date -Iseconds) Otto daily strategy completed (exit=$EXIT_CODE)." >> "$LOG_FILE"

# ── Clean old logs (keep 30 days — strategic briefs are reference material) ──
find "$LOG_DIR" -name "strategy-*.log" -mtime +30 -delete 2>/dev/null || true
