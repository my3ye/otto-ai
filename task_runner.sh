#!/bin/bash
# Otto Task Runner — executes a single task from the queue.
# Spawned by the API as a detached process.
# Usage: task_runner.sh <task_id>

set -euo pipefail

API="http://localhost:8100"
CLAUDE_CLI="/home/web3relic/.local/bin/claude"
LOG_DIR="/home/web3relic/otto/logs/tasks"
TASK_ID="${1:?Usage: task_runner.sh <task_id>}"

mkdir -p "$LOG_DIR"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="${LOG_DIR}/${TASK_ID:0:8}-${TIMESTAMP}.log"

log() { echo "$(date -Iseconds) $*" >> "$LOG_FILE"; }

log "Task runner starting for task ${TASK_ID}"

# Fetch task details from API
TASK_JSON=$(curl -sf "${API}/tasks/${TASK_ID}" 2>/dev/null) || {
    log "FATAL: Could not fetch task ${TASK_ID} from API"
    exit 1
}

# Parse task fields
TITLE=$(echo "$TASK_JSON" | python3 -c "import json,sys; print(json.load(sys.stdin)['title'])")
PROMPT=$(echo "$TASK_JSON" | python3 -c "import json,sys; print(json.load(sys.stdin)['prompt'])")
MODEL=$(echo "$TASK_JSON" | python3 -c "import json,sys; print(json.load(sys.stdin)['model'])")
BUDGET=$(echo "$TASK_JSON" | python3 -c "import json,sys; print(json.load(sys.stdin)['max_budget_usd'])")
MAX_TURNS=$(echo "$TASK_JSON" | python3 -c "import json,sys; print(json.load(sys.stdin)['max_turns'])")
TIMEOUT=$(echo "$TASK_JSON" | python3 -c "import json,sys; print(json.load(sys.stdin)['timeout_seconds'])")
WORK_DIR=$(echo "$TASK_JSON" | python3 -c "import json,sys; print(json.load(sys.stdin)['working_directory'])")
CONTEXT=$(echo "$TASK_JSON" | python3 -c "import json,sys; print(json.load(sys.stdin).get('context') or '')")

log "Task: ${TITLE}"
log "Model: ${MODEL}, Budget: \$${BUDGET}, Timeout: ${TIMEOUT}s, Turns: ${MAX_TURNS}"

# Build the full prompt with context
FULL_PROMPT="You are Otto, executing a task from the task queue.

Task: ${TITLE}

${PROMPT}"

if [ -n "$CONTEXT" ]; then
    FULL_PROMPT="${FULL_PROMPT}

Context:
${CONTEXT}"
fi

FULL_PROMPT="${FULL_PROMPT}

Instructions:
- Complete the task thoroughly.
- Be concise in your output — the heartbeat will review it.
- If you cannot complete the task, explain what is blocking you.
- Do NOT message Mev via WhatsApp — the heartbeat handles communication."

# Run Claude CLI with timeout
log "Starting Claude CLI..."
cd "$WORK_DIR"

set +e
OUTPUT=$(timeout "${TIMEOUT}s" "$CLAUDE_CLI" \
    --print \
    --dangerously-skip-permissions \
    --model "$MODEL" \
    --max-turns "$MAX_TURNS" \
    --max-budget-usd "$BUDGET" \
    -p "$FULL_PROMPT" \
    2>"${LOG_FILE}.stderr")
EXIT_CODE=$?
set -e

STDERR=$(cat "${LOG_FILE}.stderr" 2>/dev/null || echo "")
rm -f "${LOG_FILE}.stderr"

log "Claude CLI exited with code ${EXIT_CODE}"

# Truncate output if too large
MAX_OUTPUT_LEN=50000
if [ ${#OUTPUT} -gt $MAX_OUTPUT_LEN ]; then
    OUTPUT="${OUTPUT:0:$MAX_OUTPUT_LEN}

[TRUNCATED — output exceeded ${MAX_OUTPUT_LEN} chars]"
    log "Output truncated to ${MAX_OUTPUT_LEN} chars"
fi

# Report result back to API using python3 for safe JSON encoding
RESULT_JSON=$(python3 -c "
import json, sys
print(json.dumps({
    'output': sys.argv[1] if sys.argv[1] else None,
    'error': sys.argv[2] if sys.argv[2] else None,
    'exit_code': int(sys.argv[3]),
}))
" "$OUTPUT" "$STDERR" "$EXIT_CODE")

curl -sf -X POST "${API}/tasks/${TASK_ID}/complete" \
    -H 'Content-Type: application/json' \
    -d "$RESULT_JSON" >> "$LOG_FILE" 2>&1 || {
    log "WARNING: Failed to report task completion to API"
}

log "Task runner finished."
