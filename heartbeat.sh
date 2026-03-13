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

# ── Self-healing: ensure sibling timers are enabled ──────────────────────────
for TIMER in otto-reflection.timer otto-maintenance.timer; do
    if ! systemctl is-active "$TIMER" &>/dev/null; then
        echo "$(date -Iseconds) HEAL: $TIMER was inactive — re-enabling" >> "$LOG_FILE"
        sudo systemctl enable --now "$TIMER" 2>/dev/null || true
    fi
done

# ── Rate limit awareness: check API endpoint first, fall back to sentinel ──────
API="http://localhost:8100"
RATE_LIMITED=$(curl -sf "${API}/kernel/providers/rate-limited" 2>/dev/null | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('rate_limited','false'))" 2>/dev/null || echo "false")
if [ "$RATE_LIMITED" = "True" ] || [ "$RATE_LIMITED" = "true" ]; then
    REMAINING=$(curl -sf "${API}/kernel/providers/rate-limited" 2>/dev/null | python3 -c "import json,sys; print(json.load(sys.stdin).get('remaining_seconds',0))" 2>/dev/null || echo "?")
    echo "$(date -Iseconds) SKIP: Rate limit backoff active — ${REMAINING}s remaining. Cycle suppressed." >> "$LOG_FILE"
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
        echo "$(date -Iseconds) SKIP: Rate limit backoff active — hit ${ELAPSED}s ago, ${REMAINING}s remaining. Cycle suppressed." >> "$LOG_FILE"
        exit 0
    fi
fi

# Write lock
echo $$ > "$LOCK_FILE"
trap 'rm -f "$LOCK_FILE"' EXIT

echo "$(date -Iseconds) Otto heartbeat starting..." >> "$LOG_FILE"

# Report start to kernel
curl -sf -X POST "${API}/kernel/agents/orchestrator/started" >> "$LOG_FILE" 2>&1 || \
    echo "$(date -Iseconds) WARNING: Could not report agent start to kernel" >> "$LOG_FILE"

# Run Claude Code CLI as Otto's autonomous brain
# Timeout after 10 minutes to prevent hangs from blocking future cycles
cd "$OTTO_DIR"
export OTTO_SESSION_TYPE=heartbeat

# ── Unified context: fetch S-MMU quality context from kernel ─────────────
# Same context pipeline as WhatsApp — purpose, priorities, directives, relevant memories,
# position bias mitigation. This is the "unified brain" approach.
UNIFIED_CONTEXT=""
UNIFIED_CONTEXT_JSON=$(curl -sf "${API}/kernel/context?role=orchestrator&max_tokens=10000" 2>/dev/null || echo "")
if [ -n "$UNIFIED_CONTEXT_JSON" ]; then
    UNIFIED_CONTEXT=$(echo "$UNIFIED_CONTEXT_JSON" | python3 -c "
import json, sys
try:
    d = json.load(sys.stdin)
    ctx = d.get('context_text', '')
    tokens = d.get('token_count', 0)
    if ctx:
        print(ctx)
        print(f'', file=sys.stderr)
        print(f'[Unified context loaded: {tokens} tokens]', file=sys.stderr)
except: pass
" 2>>"$LOG_FILE" || echo "")
fi

# Build prompt — inject unified context + rate limit alert
HEARTBEAT_PROMPT=""
if [ -n "$UNIFIED_CONTEXT" ]; then
    HEARTBEAT_PROMPT="[UNIFIED BRAIN CONTEXT — same memory pipeline as all Otto interfaces]
${UNIFIED_CONTEXT}
[END UNIFIED CONTEXT]

"
fi
HEARTBEAT_PROMPT="${HEARTBEAT_PROMPT}Run your heartbeat. You are the orchestrator: review completed tasks, process cross-brain notes, create new tasks, launch pending tasks, message Mev with updates. Do NOT do heavy work yourself — delegate to tasks."
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
    --fallback-model sonnet \
    --no-session-persistence \
    --effort high \
    -p "$HEARTBEAT_PROMPT" \
    >> "$LOG_FILE" 2>&1
EXIT_CODE=$?
if [ $EXIT_CODE -eq 124 ]; then
    echo "$(date -Iseconds) Heartbeat TIMED OUT after 600s" >> "$LOG_FILE"
elif [ $EXIT_CODE -ne 0 ]; then
    echo "$(date -Iseconds) Heartbeat failed with exit code $EXIT_CODE" >> "$LOG_FILE"
fi

# Detect rate limit in output — write sentinel to suppress next cycle
# Pattern must match actual API errors, NOT the agent's own status reports like "Rate limit | expired"
if grep -qE "HTTP 429|RateLimitError|overloaded_error|too_many_requests|rate_limit_exceeded|\"error\".*rate" "$LOG_FILE" 2>/dev/null; then
    date +%s > "$RATE_LIMIT_FILE"
    echo "$(date -Iseconds) Rate limit detected — sentinel written to ${RATE_LIMIT_FILE}. Next heartbeat cycle will be skipped." >> "$LOG_FILE"
fi

# ── Auto-repair: detect repeat error patterns and spawn fix tasks ─────────────
# Runs deterministically every cycle — no LLM judgment needed.
# If a notification/error content appears 3+ times in the last 6h, spawn a debugger task.
echo "$(date -Iseconds) Running auto-repair scan..." >> "$LOG_FILE"
python3 "${OTTO_DIR}/tools/auto_repair.py" >> "$LOG_FILE" 2>&1 || \
    echo "$(date -Iseconds) WARNING: auto_repair.py failed — continuing." >> "$LOG_FILE"

# ── Unified post-processing: same Phase 5 pipeline as WhatsApp ───────────────
# Extracts lessons, logs episodic event, measures drift — unified brain.
echo "$(date -Iseconds) Running unified post-processing..." >> "$LOG_FILE"
# Extract last ~50 lines of agent output as summary for post-processing
HB_SUMMARY=$(tail -50 "$LOG_FILE" 2>/dev/null | head -40 || echo "heartbeat cycle completed")
curl -sf -X POST "${API}/kernel/post-process" \
    -H "Content-Type: application/json" \
    -d "$(python3 -c "
import json, sys
summary = sys.stdin.read()[:2000]
print(json.dumps({'agent_id': 'orchestrator', 'summary': summary, 'source': 'heartbeat'}))
" <<< "$HB_SUMMARY")" >> "$LOG_FILE" 2>&1 || \
    echo "$(date -Iseconds) WARNING: Unified post-processing failed — continuing." >> "$LOG_FILE"

# Report completion to kernel
HB_SUCCESS="true"
[ $EXIT_CODE -ne 0 ] && HB_SUCCESS="false"
curl -sf -X POST "${API}/kernel/agents/orchestrator/completed?success=${HB_SUCCESS}" >> "$LOG_FILE" 2>&1 || \
    echo "$(date -Iseconds) WARNING: Could not report agent completion to kernel" >> "$LOG_FILE"

echo "$(date -Iseconds) Otto heartbeat completed." >> "$LOG_FILE"

# Clean up old logs (keep last 7 days)
find "$LOG_DIR" -name "heartbeat-*.log" -mtime +7 -delete 2>/dev/null || true
find "$LOG_DIR/tasks" -name "*.log" -mtime +7 -delete 2>/dev/null || true
