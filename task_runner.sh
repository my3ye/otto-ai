#!/usr/bin/env bash
# Otto AI — Task Runner
#
# Runs a task from the queue using Claude Code CLI.
# Called by the Memory API when POST /tasks/{id}/run is invoked.
#
# Usage: ./task_runner.sh <task_id>
#
# The runner:
#   1. Fetches the task from the Memory API
#   2. Runs the prompt via claude CLI (or any LLM tool you prefer)
#   3. Reports success/failure back via POST /tasks/{id}/complete

set -euo pipefail

TASK_ID="${1:?Usage: task_runner.sh <task_id>}"
API_URL="${MEMORY_API_URL:-http://localhost:8100}"
LOG_DIR="${LOG_DIR:-./logs/tasks}"

mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/${TASK_ID}.log"

log() { echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] $*" | tee -a "$LOG_FILE"; }

trap 'on_exit' EXIT
on_exit() {
    local exit_code=$?
    if [[ $exit_code -ne 0 ]]; then
        log "ERROR: Task runner exited unexpectedly (code=$exit_code)"
        curl -s -X POST "$API_URL/tasks/$TASK_ID/complete" \
            --data-urlencode "output=Task runner crashed (exit $exit_code)" \
            --data-urlencode "exit_code=$exit_code" > /dev/null 2>&1 || true
    fi
}

# ── 1. Fetch task from API ────────────────────────────────────────────────────
log "Fetching task $TASK_ID..."
TASK_JSON=$(curl -sf "$API_URL/tasks/$TASK_ID") || {
    log "ERROR: Failed to fetch task from API"
    exit 1
}

TITLE=$(echo "$TASK_JSON" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['title'])")
PROMPT=$(echo "$TASK_JSON" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['prompt'])")
BUDGET=$(echo "$TASK_JSON" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['budget_usd'])")
MODEL=$(echo "$TASK_JSON" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['model'])")
TIMEOUT=$(echo "$TASK_JSON" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['timeout_seconds'])")

log "Task: $TITLE"
log "Model: $MODEL | Budget: \$$BUDGET | Timeout: ${TIMEOUT}s"

# ── 2. Run the task ───────────────────────────────────────────────────────────
# Customize this section to use your preferred LLM tool:
#   - claude (Claude Code CLI)
#   - gemini (Gemini CLI)
#   - Any script that reads stdin/args and writes stdout

OUTPUT_FILE=$(mktemp /tmp/otto-task-XXXXXX.txt)

if command -v claude &> /dev/null; then
    log "Running with claude CLI..."
    # --dangerously-skip-permissions gives the Claude agent full access to your filesystem,
    # shell, and network — the same permissions as the user running this script. Only run
    # tasks whose prompts you trust. Do not expose POST /tasks to the public internet without
    # authentication, or an attacker could execute arbitrary commands on your machine.
    timeout "$TIMEOUT" claude --dangerously-skip-permissions \
        --max-turns 30 \
        -p "$PROMPT" \
        > "$OUTPUT_FILE" 2>&1
    EXIT_CODE=$?
else
    log "WARNING: claude CLI not found. Install from https://claude.ai/code"
    echo "No LLM runner configured. Install claude CLI or customize task_runner.sh." > "$OUTPUT_FILE"
    EXIT_CODE=1
fi

OUTPUT=$(cat "$OUTPUT_FILE")
rm -f "$OUTPUT_FILE"

log "Task completed. exit_code=$EXIT_CODE"
log "Output (first 500 chars): ${OUTPUT:0:500}"

# ── 3. Report back to API ─────────────────────────────────────────────────────
curl -s -X POST "$API_URL/tasks/$TASK_ID/complete" \
    --data-urlencode "output=$OUTPUT" \
    --data-urlencode "exit_code=$EXIT_CODE" > /dev/null

log "Done."
