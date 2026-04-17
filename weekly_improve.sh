#!/usr/bin/env bash
# weekly_improve.sh — Weekly auto-improvement cycle for all registered Live Systems
# Called by otto-weekly-improve.timer (every Sunday 03:00 UTC)
#
# Distinction: Tasks have a done state. Live Systems have a weekly improvement loop.
# This script calls POST /live-systems/weekly-run which:
#   1. Assesses each system (health + evals)
#   2. Creates a git checkpoint
#   3. Identifies top improvement via LLM
#   4. Creates improvement records for follow-up
#   5. Schedules implementation tasks

set -euo pipefail

LOG_DIR="/home/web3relic/otto/logs"
LOG_FILE="$LOG_DIR/weekly-improve-$(date +%Y%m%d-%H%M%S).log"
API="http://localhost:8100"

mkdir -p "$LOG_DIR"

log() {
    echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] $*" | tee -a "$LOG_FILE"
}

log "=== Weekly Live System Improvement Cycle Starting ==="

# Check memory API is up
if ! curl -sf "$API/health" > /dev/null 2>&1; then
    log "ERROR: Memory API not responding at $API/health"
    exit 1
fi

# Trigger weekly improvement run for all due systems
log "Calling POST $API/live-systems/weekly-run..."
RESULT=$(curl -sf -X POST "$API/live-systems/weekly-run" -H 'Content-Type: application/json' -d '{}')
EXIT_CODE=$?

if [ $EXIT_CODE -ne 0 ]; then
    log "ERROR: weekly-run request failed (exit $EXIT_CODE)"
    exit 1
fi

# Parse and log results
SYSTEMS_DUE=$(echo "$RESULT" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('systems_due',0))")
TRIGGERED=$(echo "$RESULT" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('triggered',0))")
ERRORS=$(echo "$RESULT" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('errors',0))")

log "Systems due: $SYSTEMS_DUE | Triggered: $TRIGGERED | Errors: $ERRORS"

# Log per-system results
echo "$RESULT" | python3 -c "
import json, sys
d = json.load(sys.stdin)
for r in d.get('results', []):
    status = r.get('status', 'unknown')
    name = r.get('system', 'unknown')
    cycle = r.get('cycle', '?')
    health = r.get('health_ok')
    evals = r.get('evals_passed')
    improvement = r.get('improvement_identified', '')[:120]
    checkpoint = r.get('checkpoint', 'none')
    if status == 'triggered':
        print(f'  [OK] {name} cycle={cycle} health={health} evals={evals}')
        print(f'       checkpoint: {checkpoint}')
        print(f'       improvement: {improvement}')
    else:
        print(f'  [ERROR] {name}: {r.get(\"error\", \"unknown error\")}')
" 2>&1 | tee -a "$LOG_FILE"

# Log to episodic memory
curl -sf -X POST "$API/episodic/events" \
  -H 'Content-Type: application/json' \
  -d "{
    \"content\": \"Weekly live system improvement cycle: $SYSTEMS_DUE due, $TRIGGERED triggered, $ERRORS errors.\",
    \"event_type\": \"weekly_improve\",
    \"importance\": 7
  }" > /dev/null 2>&1 || true

# If improvements were triggered, create implementation tasks via heartbeat
# (heartbeat will pick up running improvements on next cycle)
if [ "$TRIGGERED" -gt 0 ]; then
    log "✓ $TRIGGERED improvement cycles started. Heartbeat will create implementation tasks."
fi

if [ "$ERRORS" -gt 0 ]; then
    log "⚠ $ERRORS systems had errors — check logs above"
fi

log "=== Weekly Improvement Cycle Complete ==="
log "Full results written to: $LOG_FILE"
