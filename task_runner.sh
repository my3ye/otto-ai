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
CLI_BACKEND=$(echo "$TASK_JSON" | python3 -c "import json,sys; print(json.load(sys.stdin).get('cli','claude'))")
BUDGET=$(echo "$TASK_JSON" | python3 -c "import json,sys; print(json.load(sys.stdin)['max_budget_usd'])")
MAX_TURNS=$(echo "$TASK_JSON" | python3 -c "import json,sys; print(json.load(sys.stdin)['max_turns'])")
TIMEOUT=$(echo "$TASK_JSON" | python3 -c "import json,sys; print(json.load(sys.stdin)['timeout_seconds'])")
WORK_DIR=$(echo "$TASK_JSON" | python3 -c "import json,sys; print(json.load(sys.stdin)['working_directory'])")
CONTEXT=$(echo "$TASK_JSON" | python3 -c "import json,sys; print(json.load(sys.stdin).get('context') or '')")

# Validate CLI backend (default to claude for unknown values)
case "$CLI_BACKEND" in
    claude|gemini|kimi) ;;
    *) CLI_BACKEND="claude" ;;
esac

log "Task: ${TITLE}"
log "CLI: ${CLI_BACKEND}, Model: ${MODEL}, Budget: \$${BUDGET}, Timeout: ${TIMEOUT}s, Turns: ${MAX_TURNS}"

# AdaptOrch routing — call /tasks/route with apply=true to get optimal strategy
# The API will update the task record in DB (if still pending) and return recommended params.
ROUTE_JSON=$(curl -sf -X POST "${API}/tasks/route" \
    -H 'Content-Type: application/json' \
    -d "{\"task_id\": \"${TASK_ID}\", \"apply\": true}" 2>/dev/null || echo "")

if [ -n "$ROUTE_JSON" ]; then
    STRATEGY=$(echo "$ROUTE_JSON" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['strategy']['strategy'])" 2>/dev/null || echo "")
    ROUTE_REASONING=$(echo "$ROUTE_JSON" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['strategy']['reasoning'])" 2>/dev/null || echo "")
    REC_MODEL=$(echo "$ROUTE_JSON" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['strategy']['recommended_model'])" 2>/dev/null || echo "")
    REC_TURNS=$(echo "$ROUTE_JSON" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['strategy']['recommended_max_turns'])" 2>/dev/null || echo "")
    REC_TIMEOUT=$(echo "$ROUTE_JSON" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['strategy']['recommended_timeout_seconds'])" 2>/dev/null || echo "")
    REC_BUDGET=$(echo "$ROUTE_JSON" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['strategy']['recommended_max_budget_usd'])" 2>/dev/null || echo "")
    LATS_PROMPT=$(echo "$ROUTE_JSON" | python3 -c "import json,sys; d=json.load(sys.stdin); p=d['strategy'].get('lats_fallback_prompt'); print(p if p else '')" 2>/dev/null || echo "")

    if [ -n "$STRATEGY" ]; then
        log "AdaptOrch strategy: ${STRATEGY} — ${ROUTE_REASONING}"

        # Override execution params with routing recommendations
        [ -n "$REC_MODEL" ]   && MODEL="$REC_MODEL"
        [ -n "$REC_TURNS" ]   && MAX_TURNS="$REC_TURNS"
        [ -n "$REC_TIMEOUT" ] && TIMEOUT="$REC_TIMEOUT"
        [ -n "$REC_BUDGET" ]  && BUDGET="$REC_BUDGET"
        log "AdaptOrch overrides applied — Model: ${MODEL}, Budget: \$${BUDGET}, Timeout: ${TIMEOUT}s, Turns: ${MAX_TURNS}"

        # lats_fallback: swap in the alternative LATS prompt if available
        if [ "$STRATEGY" = "lats_fallback" ] && [ -n "$LATS_PROMPT" ]; then
            PROMPT="$LATS_PROMPT"
            log "AdaptOrch lats_fallback: using LATS alternative prompt"
        fi
    else
        log "AdaptOrch routing returned no strategy — using original task params"
    fi
else
    log "AdaptOrch routing unavailable — using original task params"
fi

# ── RL2F Phase 1: Inject feedback from previous QA rejection ─────────────────
# When the heartbeat creates a retry task, it sets metadata.retry_feedback (structured
# JSON from qa_runner.sh) and metadata.retry_count so we know this is an attempt N retry.
# The feedback is prepended to the prompt so the agent learns from the specific failure.
RETRY_COUNT=$(echo "$TASK_JSON" | python3 -c "import json,sys; print(json.load(sys.stdin).get('metadata', {}).get('retry_count', 0))" 2>/dev/null || echo "0")
RETRY_FEEDBACK_RAW=$(echo "$TASK_JSON" | python3 -c "import json,sys; m=json.load(sys.stdin).get('metadata', {}); fb=m.get('retry_feedback', ''); print(fb if isinstance(fb, str) else '')" 2>/dev/null || echo "")

RL2F_BLOCK=""
if [ "$RETRY_COUNT" != "0" ] && [ -n "$RETRY_FEEDBACK_RAW" ]; then
    RL2F_BLOCK=$(python3 -c "
import json, sys, re

raw = sys.argv[1].strip()
retry_count = sys.argv[2]

# Try to parse structured RL2F feedback from the qa_output format:
# 'REJECTED: <reason>\n{\"rl2f_feedback\": {...}}'
fb_data = {}
json_match = re.search(r'\{\"rl2f_feedback\":.+\}', raw, re.DOTALL)
if json_match:
    try:
        fb_data = json.loads(json_match.group()).get('rl2f_feedback', {})
    except Exception:
        pass

if fb_data:
    lines = [f'=== RL2F FEEDBACK (Attempt #{retry_count} — previous attempt was rejected) ===']
    if fb_data.get('expected'):
        lines.append(f'EXPECTED: {fb_data[\"expected\"]}')
    if fb_data.get('actual'):
        lines.append(f'ACTUAL: {fb_data[\"actual\"]}')
    if fb_data.get('failure_points'):
        lines.append('FAILURE POINTS (must address in this retry):')
        for fp in fb_data['failure_points']:
            lines.append(f'  - {fp}')
    if fb_data.get('suggestions'):
        lines.append('SUGGESTIONS:')
        for s in fb_data['suggestions']:
            lines.append(f'  - {s}')
    if fb_data.get('issues'):
        lines.append(f'QA ISSUES: {chr(10).join(\"  - \" + i for i in fb_data[\"issues\"])}')
    lines.append('=== Address ALL failure points above before considering the task complete ===')
    print(chr(10).join(lines))
else:
    # Plain text fallback: just show the raw rejection message
    reason_line = raw.split(chr(10))[0] if chr(10) in raw else raw
    reason_line = reason_line[:300]
    print(f'=== RL2F FEEDBACK (Attempt #{retry_count} — previous attempt was rejected) ===')
    print(f'Previous rejection reason: {reason_line}')
    print('=== Address this feedback before considering the task complete ===')
" "$RETRY_FEEDBACK_RAW" "$RETRY_COUNT" 2>/dev/null || echo "")

    if [ -n "$RL2F_BLOCK" ]; then
        log "RL2F: retry attempt #${RETRY_COUNT} — injecting QA rejection feedback into prompt"
    fi
fi
# ── End RL2F Feedback Injection ────────────────────────────────────────────────

# Chain-of-Hindsight: fetch similar past task outcomes before building prompt
TITLE_ENCODED=$(python3 -c "import urllib.parse,sys; print(urllib.parse.quote(sys.argv[1]))" "$TITLE" 2>/dev/null || echo "")
HINDSIGHT_BLOCK=""
if [ -n "$TITLE_ENCODED" ]; then
    HINDSIGHT_JSON=$(curl -sf "${API}/tasks/hindsight?query=${TITLE_ENCODED}&limit=3" 2>/dev/null || echo '{"count":0,"hindsight":[]}')
    HINDSIGHT_BLOCK=$(echo "$HINDSIGHT_JSON" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    items = data.get('hindsight', [])
    if not items:
        sys.exit(0)
    lines = ['--- Hindsight from similar past tasks ---']
    for item in items:
        mark = 'SUCCEEDED' if item['outcome'] == 'succeeded' else 'FAILED'
        lines.append(f\"[{mark}] {item['title']}\")
        if item.get('lesson'):
            lesson = item['lesson'][:300].replace('\n', ' ')
            lines.append(f\"  Lesson: {lesson}\")
    lines.append('--- End hindsight ---')
    print('\n'.join(lines))
except Exception:
    pass
" 2>/dev/null || echo "")
    if [ -n "$HINDSIGHT_BLOCK" ]; then
        HINDSIGHT_COUNT=$(echo "$HINDSIGHT_JSON" | python3 -c "import json,sys; print(json.load(sys.stdin).get('count',0))" 2>/dev/null || echo "?")
        log "Chain-of-Hindsight: injected ${HINDSIGHT_COUNT} past task(s) into prompt"
    fi
fi

# Build the full prompt with context
FULL_PROMPT="You are Otto, executing a task from the task queue.

Task: ${TITLE}

${PROMPT}"

# RL2F: Inject rejection feedback at the top if this is a retry
if [ -n "$RL2F_BLOCK" ]; then
    FULL_PROMPT="You are Otto, executing a task from the task queue.

${RL2F_BLOCK}

Task: ${TITLE}

${PROMPT}"
fi

if [ -n "$HINDSIGHT_BLOCK" ]; then
    FULL_PROMPT="${FULL_PROMPT}

${HINDSIGHT_BLOCK}"
fi

if [ -n "$CONTEXT" ]; then
    FULL_PROMPT="${FULL_PROMPT}

Context:
${CONTEXT}"
fi

FULL_PROMPT="${FULL_PROMPT}

Instructions:
- Complete the task thoroughly.
- Be concise in your output — the heartbeat will review it.
- IMPORTANT: You MUST end with a text summary of what you accomplished. Do not end on a tool call — your final response must be plain text. This is required for output capture.
- If you cannot complete the task, explain what is blocking you.
- Do NOT message Mev via WhatsApp — the heartbeat handles communication."

# Run the appropriate CLI with timeout
log "Starting ${CLI_BACKEND} CLI..."
cd "$WORK_DIR"
TASK_START_TS=$(date +%s)

# Create a per-task filesystem timestamp marker immediately before the CLI runs.
# qa_runner.sh uses this to isolate changes made by THIS task specifically,
# ignoring changes from concurrently running tasks.
TASK_MARKER_FILE=$(mktemp /tmp/otto_task_marker_XXXXXX)
log "QA marker file: ${TASK_MARKER_FILE}"

set +e
case "$CLI_BACKEND" in
    claude)
        OUTPUT=$(timeout "${TIMEOUT}s" "$CLAUDE_CLI" \
            --print \
            --dangerously-skip-permissions \
            --model "$MODEL" \
            --max-turns "$MAX_TURNS" \
            --max-budget-usd "$BUDGET" \
            -p "$FULL_PROMPT" \
            2>"${LOG_FILE}.stderr")
        EXIT_CODE=$?
        ;;
    gemini)
        # Gemini CLI: no --max-turns or --budget flags. Use --yolo for auto-approval.
        # Output format json then extract .response for clean text capture.
        GEMINI_RAW=$(timeout "${TIMEOUT}s" gemini \
            --yolo \
            --output-format json \
            --include-directories "$WORK_DIR" \
            -p "$FULL_PROMPT" \
            2>"${LOG_FILE}.stderr")
        EXIT_CODE=$?
        # Extract clean response text from JSON envelope
        OUTPUT=$(echo "$GEMINI_RAW" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    print(data.get('response') or data.get('text') or str(data))
except Exception:
    print(sys.stdin.read())
" 2>/dev/null || echo "$GEMINI_RAW")
        ;;
    kimi)
        # Kimi CLI: --quiet = --print --output-format text --final-message-only
        # --yolo implied by --quiet/--print. --max-steps-per-turn instead of --max-turns.
        OUTPUT=$(timeout "${TIMEOUT}s" /home/web3relic/.local/bin/kimi \
            --quiet \
            --yolo \
            --work-dir "$WORK_DIR" \
            --max-steps-per-turn "$MAX_TURNS" \
            -p "$FULL_PROMPT" \
            2>"${LOG_FILE}.stderr")
        EXIT_CODE=$?
        ;;
    *)
        log "ERROR: Unknown CLI backend '${CLI_BACKEND}' — falling back to claude"
        OUTPUT=$(timeout "${TIMEOUT}s" "$CLAUDE_CLI" \
            --print \
            --dangerously-skip-permissions \
            --model "$MODEL" \
            --max-turns "$MAX_TURNS" \
            --max-budget-usd "$BUDGET" \
            -p "$FULL_PROMPT" \
            2>"${LOG_FILE}.stderr")
        EXIT_CODE=$?
        ;;
esac
set -e

STDERR=$(cat "${LOG_FILE}.stderr" 2>/dev/null || echo "")
rm -f "${LOG_FILE}.stderr"

log "${CLI_BACKEND} CLI exited with code ${EXIT_CODE}"

# ── CLI Quota Fallback ────────────────────────────────────────────────────────
# If gemini/kimi failed with 429 (quota exhausted), retry on claude as fallback.
# This prevents tasks from failing purely due to API quota limits on non-Claude CLIs.
if [ "$EXIT_CODE" -ne 0 ] && [ "$CLI_BACKEND" != "claude" ]; then
    if echo "$STDERR$OUTPUT" | grep -qiE "429|RESOURCE_EXHAUSTED|quota|rate.limit"; then
        log "QUOTA FALLBACK: ${CLI_BACKEND} hit quota limit — retrying on claude..."
        CLI_BACKEND="claude"
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
        log "Fallback claude CLI exited with code ${EXIT_CODE}"
    fi
fi

# Detect max-turns/max-steps hit
# Claude: "Error: Reached max turns" | Kimi: may vary | Gemini: no turn limit
if echo "$OUTPUT" | grep -qE "^Error: Reached max turns|^Error: max.steps reached"; then
    log "WARNING: Task hit turn/step limit. Work may have been done but output lost."
    OUTPUT="[INCOMPLETE — hit max_turns/max_steps limit. Task may have partially completed. Verify by checking the codebase directly.]"
fi

# Truncate output if too large
MAX_OUTPUT_LEN=50000
if [ ${#OUTPUT} -gt $MAX_OUTPUT_LEN ]; then
    OUTPUT="${OUTPUT:0:$MAX_OUTPUT_LEN}

[TRUNCATED — output exceeded ${MAX_OUTPUT_LEN} chars]"
    log "Output truncated to ${MAX_OUTPUT_LEN} chars"
fi

# ── SOFAI-LM Metacognitive Self-Check ────────────────────────────────────────
# Dual-system metacognition: Gemini rates the Claude output before we declare done.
# Enabled by default; disable with OTTO_METACOGNITION=0
OTTO_METACOGNITION="${OTTO_METACOGNITION:-1}"
META_PAYLOAD="{}"

if [ "$OTTO_METACOGNITION" = "1" ] && [ -n "$OUTPUT" ] && [ "$EXIT_CODE" -eq 0 ]; then
    log "SOFAI-LM: running metacognitive self-check..."

    # Build rating prompt — truncate output to 3000 chars to stay within token budget
    OUTPUT_EXCERPT="${OUTPUT:0:3000}"
    META_PROMPT="You are a quality evaluator for an AI agent. Rate the following task output on 3 dimensions, each scored 1-10. Return ONLY a JSON object, no explanation, no markdown.

Task title: ${TITLE}

Output to evaluate:
${OUTPUT_EXCERPT}

Score these dimensions (1=poor, 10=excellent):
- accuracy: factual correctness and logical consistency
- completeness: whether all task goals were fully addressed
- coherence: clarity, no contradictions, no hallucination indicators

Return ONLY: {\"accuracy\":N,\"completeness\":N,\"coherence\":N}"

    META_RAW=$(timeout 30 gemini -m gemini-2.0-flash -p "$META_PROMPT" 2>/dev/null || echo "")

    # Parse JSON from response (handle markdown code block wrapping)
    META_JSON=$(echo "$META_RAW" | python3 -c "
import json, sys, re
raw = sys.stdin.read()
# Strip markdown code block if present
raw = re.sub(r'\`\`\`[a-z]*\n?', '', raw).strip()
# Extract first JSON object
match = re.search(r'\{[^}]+\}', raw, re.DOTALL)
if match:
    try:
        data = json.loads(match.group())
        required = {'accuracy', 'completeness', 'coherence'}
        if required.issubset(data.keys()):
            print(json.dumps(data))
            sys.exit(0)
    except Exception:
        pass
print('{}')
" 2>/dev/null || echo "{}")

    if [ "$META_JSON" != "{}" ]; then
        META_AVG=$(echo "$META_JSON" | python3 -c "
import json, sys
data = json.load(sys.stdin)
scores = [data.get('accuracy', 0), data.get('completeness', 0), data.get('coherence', 0)]
avg = sum(scores) / len(scores)
print(f'{avg:.2f}')
" 2>/dev/null || echo "0")

        RETRY_NEEDED=$(python3 -c "import sys; print('true' if float('${META_AVG}') < 7.0 else 'false')" 2>/dev/null || echo "false")
        ESCALATE=$(python3 -c "import sys; print('true' if float('${META_AVG}') < 5.0 else 'false')" 2>/dev/null || echo "false")

        log "SOFAI-LM: accuracy=$(echo "$META_JSON" | python3 -c "import json,sys;print(json.load(sys.stdin).get('accuracy','?'))" 2>/dev/null), completeness=$(echo "$META_JSON" | python3 -c "import json,sys;print(json.load(sys.stdin).get('completeness','?'))" 2>/dev/null), coherence=$(echo "$META_JSON" | python3 -c "import json,sys;print(json.load(sys.stdin).get('coherence','?'))" 2>/dev/null), avg=${META_AVG}, retry_needed=${RETRY_NEEDED}"

        META_PAYLOAD=$(python3 -c "
import json, sys
scores = json.loads(sys.argv[1])
avg = float(sys.argv[2])
result = {
    'sofai_lm': {
        **scores,
        'average': avg,
        'retry_needed': avg < 7.0,
        'escalation_needed': avg < 5.0,
    }
}
print(json.dumps(result))
" "$META_JSON" "$META_AVG" 2>/dev/null || echo "{}")

        # Log low-quality outputs to episodic memory
        if [ "$RETRY_NEEDED" = "true" ]; then
            SEVERITY="low_quality"
            [ "$ESCALATE" = "true" ] && SEVERITY="escalation_needed"
            TITLE_ESCAPED=$(echo "$TITLE" | python3 -c "import json,sys; print(json.dumps(sys.stdin.read().strip()))" 2>/dev/null || echo "\"${TITLE}\"")
            curl -sf -X POST "${API}/episodic/events" \
                -H 'Content-Type: application/json' \
                -d "{\"type\":\"metacognitive_${SEVERITY}\",\"summary\":\"SOFAI-LM: task ${TITLE_ESCAPED} scored ${META_AVG}/10 (below 7.0 threshold). retry_needed=${RETRY_NEEDED}, escalation_needed=${ESCALATE}.\"}" \
                >> "$LOG_FILE" 2>&1 || true
            log "SOFAI-LM: ⚠ quality below threshold (avg=${META_AVG}) — flagged as ${SEVERITY}"
        else
            log "SOFAI-LM: ✓ quality check passed (avg=${META_AVG}/10)"
        fi
    else
        log "SOFAI-LM: could not parse metacognitive scores — skipping (non-fatal)"
    fi
fi
# ── End Metacognitive Check ───────────────────────────────────────────────────

# ── Auto-restart memory API if task modified its code ─────────────────────────
if [ "$EXIT_CODE" -eq 0 ]; then
    MEMORY_DIR="/home/web3relic/otto/memory"
    # Check if any memory API files were modified during this task
    MEMORY_CHANGED=$(find "$MEMORY_DIR" -name '*.py' -newer "$LOG_FILE" 2>/dev/null | head -1)
    if [ -n "$MEMORY_CHANGED" ]; then
        log "Detected memory API code changes — restarting otto-memory.service..."
        sudo systemctl restart otto-memory 2>/dev/null && \
            log "otto-memory restarted successfully." || \
            log "WARNING: Failed to restart otto-memory — new endpoints may 404."
    fi
fi
# ── End Auto-restart ──────────────────────────────────────────────────────────

# Report result back to API using python3 for safe JSON encoding
RESULT_JSON=$(python3 -c "
import json, sys
print(json.dumps({
    'output': sys.argv[1] if sys.argv[1] else None,
    'error': sys.argv[2] if sys.argv[2] else None,
    'exit_code': int(sys.argv[3]),
    'metadata': json.loads(sys.argv[4]),
}))
" "$OUTPUT" "$STDERR" "$EXIT_CODE" "$META_PAYLOAD")

curl -sf -X POST "${API}/tasks/${TASK_ID}/complete" \
    -H 'Content-Type: application/json' \
    -d "$RESULT_JSON" >> "$LOG_FILE" 2>&1 || {
    log "WARNING: Failed to report task completion to API"
}

# ── QA Runner — review and auto-commit if task succeeded ──────────────────────
QA_RUNNER="/home/web3relic/otto/qa_runner.sh"
OTTO_QA="${OTTO_QA:-1}"   # Disable with OTTO_QA=0

if [ "$OTTO_QA" = "1" ] && [ "$EXIT_CODE" -eq 0 ] && [ -x "$QA_RUNNER" ]; then
    log "QA: launching qa_runner for task ${TASK_ID}..."
    # Determine which CLI ran this task (read from task JSON cli field, default claude)
    TASK_CLI=$(echo "$TASK_JSON" | python3 -c "import json,sys; print(json.load(sys.stdin).get('cli', 'claude'))" 2>/dev/null || echo "claude")
    # Pass TASK_MARKER_FILE as 4th arg so QA can isolate this task's changes
    bash "$QA_RUNNER" "$TASK_ID" "$TASK_CLI" "$LOG_FILE" "$TASK_MARKER_FILE" 2>>"$LOG_FILE" || \
        log "QA: qa_runner exited with error (non-fatal, task still marked complete)"
    rm -f "$TASK_MARKER_FILE"
else
    if [ "$OTTO_QA" != "1" ]; then
        log "QA: disabled (OTTO_QA=0)"
    elif [ "$EXIT_CODE" -ne 0 ]; then
        log "QA: skipped (task failed, exit_code=${EXIT_CODE})"
    fi
    rm -f "$TASK_MARKER_FILE" 2>/dev/null || true
fi
# ── End QA Runner ──────────────────────────────────────────────────────────────

# APC Plan Cache — store successful plans for future reuse
if [ "$EXIT_CODE" -eq 0 ]; then
    EXEC_TIME=$(( $(date +%s) - TASK_START_TS ))
    APC_JSON=$(python3 -c "
import json, sys
print(json.dumps({
    'task_id': sys.argv[1],
    'task_title': sys.argv[2],
    'task_prompt': sys.argv[3],
    'selected_plan': sys.argv[3][:2000],
    'success': True,
    'execution_time_s': int(sys.argv[4]),
}))
" "$TASK_ID" "$TITLE" "$PROMPT" "$EXEC_TIME")
    curl -sf -X POST "${API}/plans/cache" \
        -H 'Content-Type: application/json' \
        -d "$APC_JSON" >> "$LOG_FILE" 2>&1 && \
        log "APC: plan cached (exec_time=${EXEC_TIME}s)" || \
        log "APC: cache store failed (non-fatal)"
fi

log "Task runner finished."
