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

# Write lock
echo $$ > "$LOCK_FILE"
trap 'rm -f "$LOCK_FILE"' EXIT

echo "$(date -Iseconds) Otto reflection starting..." >> "$LOG_FILE"

# Run Claude Code CLI as Otto's reflection engine
# Timeout after 10 minutes to prevent hangs from blocking future cycles
cd "$OTTO_DIR"
export OTTO_SESSION_TYPE=reflection
timeout 600s /home/web3relic/.local/bin/claude \
    --print \
    --agent reflection \
    --dangerously-skip-permissions \
    --model opus \
    -p "Run your reflection cycle. MARS_ENABLED=${MARS_ENABLED}. Reconcile working memory against reality, consolidate memories, evaluate recent performance, identify and fix root causes, create improvement tasks if needed. Do NOT message Mev — the orchestrator handles communication." \
    >> "$LOG_FILE" 2>&1
EXIT_CODE=$?
if [ $EXIT_CODE -eq 124 ]; then
    echo "$(date -Iseconds) Reflection TIMED OUT after 600s" >> "$LOG_FILE"
elif [ $EXIT_CODE -ne 0 ]; then
    echo "$(date -Iseconds) Reflection failed with exit code $EXIT_CODE" >> "$LOG_FILE"
fi

echo "$(date -Iseconds) Otto reflection completed." >> "$LOG_FILE"

# Clean up old logs (keep last 7 days)
find "$LOG_DIR" -name "reflection-*.log" -mtime +7 -delete 2>/dev/null || true
