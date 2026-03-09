#!/bin/bash
# Otto Research Pipeline Runner
# Called by otto-research-pipeline.timer every 3 hours.
# Runs progressive research agent to compound capital growth strategies.

set -euo pipefail

OTTO_DIR="/home/web3relic/otto"
ALPHA_DIR="${OTTO_DIR}/projects/alpha"
LOCK_FILE="/tmp/otto-research-pipeline.lock"
LOG_DIR="${OTTO_DIR}/logs"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="${LOG_DIR}/research-pipeline-${TIMESTAMP}.log"

mkdir -p "$LOG_DIR"

# Lock to prevent concurrent runs
if [ -f "$LOCK_FILE" ]; then
    LOCK_PID=$(cat "$LOCK_FILE" 2>/dev/null || echo "")
    if [ -n "$LOCK_PID" ] && kill -0 "$LOCK_PID" 2>/dev/null; then
        echo "$(date -Iseconds) Research pipeline already running (PID $LOCK_PID), skipping." >> "$LOG_FILE"
        exit 0
    else
        echo "$(date -Iseconds) Stale lock found, removing." >> "$LOG_FILE"
        rm -f "$LOCK_FILE"
    fi
fi

echo $$ > "$LOCK_FILE"
trap 'rm -f "$LOCK_FILE"' EXIT

echo "$(date -Iseconds) Research pipeline starting..." >> "$LOG_FILE"

cd "$ALPHA_DIR"

# Run the pipeline
/usr/bin/python3 "${ALPHA_DIR}/research_pipeline.py" >> "$LOG_FILE" 2>&1
EXIT_CODE=$?

if [ $EXIT_CODE -ne 0 ]; then
    echo "$(date -Iseconds) Research pipeline failed with exit code $EXIT_CODE" >> "$LOG_FILE"
else
    echo "$(date -Iseconds) Research pipeline completed successfully." >> "$LOG_FILE"
fi

# Clean up old logs — keep last 7 days
find "$LOG_DIR" -name "research-pipeline-*.log" -mtime +7 -delete 2>/dev/null || true

exit $EXIT_CODE
