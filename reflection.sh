#!/bin/bash
# Otto Reflection Runner
# Called by systemd timer at :30 every hour. Runs Claude Code CLI as Otto's self-improvement engine.

set -euo pipefail

OTTO_DIR="/home/web3relic/otto"
LOCK_FILE="/tmp/otto-reflection.lock"
LOG_DIR="${OTTO_DIR}/logs"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="${LOG_DIR}/reflection-${TIMESTAMP}.log"

# MARS dual adversarial synthesis toggle (default: enabled)
# Set MARS_ENABLED=false in environment to skip the dual critic pass
MARS_ENABLED="${MARS_ENABLED:-true}"

# Ensure log directory exists
mkdir -p "$LOG_DIR"

# Lock to prevent concurrent reflections
if [ -f "$LOCK_FILE" ]; then
    LOCK_PID=$(cat "$LOCK_FILE" 2>/dev/null || echo "")
    if [ -n "$LOCK_PID" ] && kill -0 "$LOCK_PID" 2>/dev/null; then
        echo "$(date -Iseconds) Another reflection is running (PID $LOCK_PID), skipping." >> "$LOG_FILE"
        exit 0
    else
        echo "$(date -Iseconds) Stale lock file found, removing." >> "$LOG_FILE"
        rm -f "$LOCK_FILE"
    fi
fi

# ── Rate limit awareness: skip cycle if API was rate-limited recently ──────────
RATE_LIMIT_FILE="/tmp/otto-rate-limited"
if [ -f "$RATE_LIMIT_FILE" ]; then
    RATE_LIMIT_TS=$(grep -oE '^[0-9]+' "$RATE_LIMIT_FILE" 2>/dev/null || echo "0")
    NOW_TS=$(date +%s)
    ELAPSED=$(( NOW_TS - RATE_LIMIT_TS ))
    if [ "$ELAPSED" -lt 3600 ]; then
        REMAINING=$(( 3600 - ELAPSED ))
        echo "$(date -Iseconds) SKIP: Rate limit backoff active — hit ${ELAPSED}s ago, ${REMAINING}s remaining. Cycle suppressed." >> "$LOG_FILE"
        exit 0
    fi
fi

# Write lock
echo $$ > "$LOCK_FILE"
trap 'rm -f "$LOCK_FILE"' EXIT

echo "$(date -Iseconds) Otto reflection starting..." >> "$LOG_FILE"

# Run Claude Code CLI as Otto's reflection engine
# Timeout after 10 minutes to prevent hangs from blocking future cycles
cd "$OTTO_DIR"
export OTTO_SESSION_TYPE=reflection

# Build prompt — inject rate limit alert if recently hit (conservative mode)
REFLECTION_PROMPT="Run your reflection cycle. MARS_ENABLED=${MARS_ENABLED}. Reconcile working memory against reality, consolidate memories, evaluate recent performance, identify and fix root causes, create improvement tasks if needed. Do NOT message Mev — the orchestrator handles communication."
if [ -f "$RATE_LIMIT_FILE" ]; then
    RL_TS=$(grep -oE '^[0-9]+' "$RATE_LIMIT_FILE" 2>/dev/null || echo "0")
    RL_MIN=$(( ( $(date +%s) - RL_TS ) / 60 ))
    REFLECTION_PROMPT="${REFLECTION_PROMPT} RATE LIMIT ALERT: API was rate-limited ${RL_MIN}m ago — focus on memory consolidation only, do NOT create new tasks this cycle."
fi

timeout 600s /home/web3relic/.local/bin/claude \
    --print \
    --agent reflection \
    --dangerously-skip-permissions \
    --model opus \
    -p "$REFLECTION_PROMPT" \
    >> "$LOG_FILE" 2>&1
EXIT_CODE=$?
if [ $EXIT_CODE -eq 124 ]; then
    echo "$(date -Iseconds) Reflection TIMED OUT after 600s" >> "$LOG_FILE"
elif [ $EXIT_CODE -ne 0 ]; then
    echo "$(date -Iseconds) Reflection failed with exit code $EXIT_CODE" >> "$LOG_FILE"
fi

# Detect rate limit in output — write sentinel to suppress next cycle
if grep -qiE "429|rate.limit|RateLimitError|overloaded_error|too_many_requests" "$LOG_FILE" 2>/dev/null; then
    date +%s > "$RATE_LIMIT_FILE"
    echo "$(date -Iseconds) Rate limit detected — sentinel written to ${RATE_LIMIT_FILE}. Next reflection cycle will be skipped." >> "$LOG_FILE"
fi

echo "$(date -Iseconds) Otto reflection completed." >> "$LOG_FILE"

# Clean up old logs (keep last 7 days)
find "$LOG_DIR" -name "reflection-*.log" -mtime +7 -delete 2>/dev/null || true
