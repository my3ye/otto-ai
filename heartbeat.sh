#!/bin/bash
# Otto Heartbeat Runner
# Called by systemd timer every hour. Runs Claude Code CLI as Otto's brain.

set -euo pipefail

OTTO_DIR="/home/web3relic/otto"
LOCK_FILE="/tmp/otto-heartbeat.lock"
LOG_DIR="${OTTO_DIR}/logs"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="${LOG_DIR}/heartbeat-${TIMESTAMP}.log"

# Ensure log directory exists
mkdir -p "$LOG_DIR"

# Lock to prevent concurrent heartbeats
if [ -f "$LOCK_FILE" ]; then
    LOCK_PID=$(cat "$LOCK_FILE" 2>/dev/null || echo "")
    if [ -n "$LOCK_PID" ] && kill -0 "$LOCK_PID" 2>/dev/null; then
        echo "$(date -Iseconds) Another heartbeat is running (PID $LOCK_PID), skipping." >> "$LOG_FILE"
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

echo "$(date -Iseconds) Otto heartbeat starting..." >> "$LOG_FILE"

# Run Claude Code CLI as Otto's autonomous brain
# Timeout after 10 minutes to prevent hangs from blocking future cycles
cd "$OTTO_DIR"
export OTTO_SESSION_TYPE=heartbeat

# Build prompt — inject rate limit alert if recently hit (cap task creation)
HEARTBEAT_PROMPT="Run your heartbeat. You are the orchestrator: review completed tasks, process cross-brain notes, create new tasks, launch pending tasks, message Mev with updates. Do NOT do heavy work yourself — delegate to tasks."
if [ -f "$RATE_LIMIT_FILE" ]; then
    RL_TS=$(grep -oE '^[0-9]+' "$RATE_LIMIT_FILE" 2>/dev/null || echo "0")
    RL_MIN=$(( ( $(date +%s) - RL_TS ) / 60 ))
    HEARTBEAT_PROMPT="${HEARTBEAT_PROMPT} RATE LIMIT ALERT: API was rate-limited ${RL_MIN}m ago — cap new task creation at 1 task maximum this cycle to avoid cascade."
fi

timeout 600s /home/web3relic/.local/bin/claude \
    --print \
    --agent heartbeat \
    --dangerously-skip-permissions \
    --model opus \
    -p "$HEARTBEAT_PROMPT" \
    >> "$LOG_FILE" 2>&1
EXIT_CODE=$?
if [ $EXIT_CODE -eq 124 ]; then
    echo "$(date -Iseconds) Heartbeat TIMED OUT after 600s" >> "$LOG_FILE"
elif [ $EXIT_CODE -ne 0 ]; then
    echo "$(date -Iseconds) Heartbeat failed with exit code $EXIT_CODE" >> "$LOG_FILE"
fi

# Detect rate limit in output — write sentinel to suppress next cycle
if grep -qiE "429|rate.limit|RateLimitError|overloaded_error|too_many_requests" "$LOG_FILE" 2>/dev/null; then
    date +%s > "$RATE_LIMIT_FILE"
    echo "$(date -Iseconds) Rate limit detected — sentinel written to ${RATE_LIMIT_FILE}. Next heartbeat cycle will be skipped." >> "$LOG_FILE"
fi

echo "$(date -Iseconds) Otto heartbeat completed." >> "$LOG_FILE"

# Clean up old logs (keep last 7 days)
find "$LOG_DIR" -name "heartbeat-*.log" -mtime +7 -delete 2>/dev/null || true
find "$LOG_DIR/tasks" -name "*.log" -mtime +7 -delete 2>/dev/null || true
