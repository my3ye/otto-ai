#!/bin/bash
# Otto Alpha Heartbeat Runner
# Called by systemd timer every 30 minutes. Scans Solana smart money wallets.

set -euo pipefail

OTTO_DIR="/home/web3relic/otto"
LOCK_FILE="/tmp/otto-alpha-heartbeat.lock"
LOG_DIR="${OTTO_DIR}/logs"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="${LOG_DIR}/alpha-heartbeat-${TIMESTAMP}.log"

# Ensure log directory exists
mkdir -p "$LOG_DIR"

# Lock to prevent concurrent runs
if [ -f "$LOCK_FILE" ]; then
    LOCK_PID=$(cat "$LOCK_FILE" 2>/dev/null || echo "")
    if [ -n "$LOCK_PID" ] && kill -0 "$LOCK_PID" 2>/dev/null; then
        echo "$(date -Iseconds) Alpha heartbeat already running (PID $LOCK_PID), skipping." >> "$LOG_FILE"
        exit 0
    else
        echo "$(date -Iseconds) Stale lock file found, removing." >> "$LOG_FILE"
        rm -f "$LOCK_FILE"
    fi
fi

# Write lock
echo $$ > "$LOCK_FILE"
trap 'rm -f "$LOCK_FILE"' EXIT

echo "$(date -Iseconds) Otto Alpha heartbeat starting..." >> "$LOG_FILE"

# Run Claude Code CLI with alpha heartbeat agent
cd "$OTTO_DIR"
export OTTO_SESSION_TYPE=alpha_heartbeat
/home/web3relic/.local/bin/claude \
    --print \
    --agent alpha_heartbeat \
    --dangerously-skip-permissions \
    --model sonnet \
    --max-budget-usd 0.50 \
    -p "Run your alpha heartbeat cycle. Scan Solana smart money wallets via Helius. Log signals to memory. Alert Mev via WhatsApp only for HIGH signals. Stay within budget." \
    >> "$LOG_FILE" 2>&1 || {
    echo "$(date -Iseconds) Alpha heartbeat failed with exit code $?" >> "$LOG_FILE"
}

echo "$(date -Iseconds) Otto Alpha heartbeat completed." >> "$LOG_FILE"

# Clean up old alpha logs (keep last 7 days)
find "$LOG_DIR" -name "alpha-heartbeat-*.log" -mtime +7 -delete 2>/dev/null || true
