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

# Write lock
echo $$ > "$LOCK_FILE"
trap 'rm -f "$LOCK_FILE"' EXIT

echo "$(date -Iseconds) Otto heartbeat starting..." >> "$LOG_FILE"

# Run Claude Code CLI as Otto's autonomous brain
cd "$OTTO_DIR"
/home/web3relic/.local/bin/claude \
    --print \
    --agent heartbeat \
    --dangerously-skip-permissions \
    --model sonnet \
    --max-budget-usd 2.00 \
    -p "Run your heartbeat. Drive the mission forward. Ask Mev about his brands and projects, research, build, propose plans. Do as much as you can. Message Mev." \
    >> "$LOG_FILE" 2>&1 || {
    echo "$(date -Iseconds) Heartbeat failed with exit code $?" >> "$LOG_FILE"
}

echo "$(date -Iseconds) Otto heartbeat completed." >> "$LOG_FILE"

# Clean up old logs (keep last 7 days)
find "$LOG_DIR" -name "heartbeat-*.log" -mtime +7 -delete 2>/dev/null || true
