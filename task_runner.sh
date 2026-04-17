#!/bin/bash
# Otto Task Runner — executes a single task from the queue.
# Spawned by the API as a detached process.
# Usage: task_runner.sh <task_id>

set -euo pipefail

# Clear Claude nested session detection so task_runner can spawn CLI sessions
unset CLAUDECODE CLAUDE_CODE_ENTRYPOINT 2>/dev/null || true

API="http://localhost:8100"
CLAUDE_CLI="/home/web3relic/.local/bin/claude"
LOG_DIR="/home/web3relic/otto/logs/tasks"
TASK_ID="${1:?Usage: task_runner.sh <task_id>}"

mkdir -p "$LOG_DIR"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="${LOG_DIR}/${TASK_ID:0:8}-${TIMESTAMP}.log"

log() { echo "$(date -Iseconds) $*" >> "$LOG_FILE"; }

# ── Zombie Prevention Trap ────────────────────────────────────────────────────
# With set -euo pipefail, any unguarded command failure kills the script before
# the completion callback runs, leaving the task as "running" forever (zombie).
# This trap catches unexpected exits and marks the task as failed via API.
TASK_COMPLETED=false
cleanup_on_exit() {
    local exit_code=$?
    if [ "$TASK_COMPLETED" = "false" ] && [ -n "${TASK_ID:-}" ]; then
        log "FATAL: Task runner exited unexpectedly (exit_code=${exit_code}, line=${BASH_LINENO[0]:-unknown})"
        curl -sf -X POST "${API}/tasks/${TASK_ID}/complete" \
            -H 'Content-Type: application/json' \
            -d "{\"output\": \"Task runner crashed at line ${BASH_LINENO[0]:-unknown}\", \"exit_code\": ${exit_code:-1}, \"error\": \"Process died: set -e triggered (exit_code=${exit_code})\"}" \
            >> "${LOG_FILE:-/dev/null}" 2>&1 || true
        log "Zombie prevention: marked task as failed via API"
    fi
}
trap cleanup_on_exit EXIT
# ── End Zombie Prevention Trap ────────────────────────────────────────────────

log "Task runner starting for task ${TASK_ID}"

# Report start to kernel
curl -sf -X POST "${API}/kernel/agents/task_worker/started" >> "$LOG_FILE" 2>&1 || \
    log "WARNING: Could not report agent start to kernel"

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
PRIORITY=$(echo "$TASK_JSON" | python3 -c "import json,sys; print(json.load(sys.stdin).get('priority', 5))" 2>/dev/null || echo "5")
AGENT_TYPE=$(echo "$TASK_JSON" | python3 -c "import json,sys; print(json.load(sys.stdin).get('agent_type') or '')" 2>/dev/null || echo "")

# ── A2A Channel Detection ─────────────────────────────────────────────────────
PLAN_ID=$(echo "$TASK_JSON" | python3 -c "import json,sys; print(json.load(sys.stdin).get('plan_id') or '')" 2>/dev/null || echo "")
WF_INSTANCE=$(echo "$TASK_JSON" | python3 -c "import json,sys; d=json.load(sys.stdin); print((d.get('metadata') or {}).get('workflow_instance_id',''))" 2>/dev/null || echo "")
A2A_CHANNEL=""
[[ -n "$PLAN_ID" ]] && A2A_CHANNEL="$PLAN_ID"
[[ -z "$A2A_CHANNEL" && -n "$WF_INSTANCE" ]] && A2A_CHANNEL="$WF_INSTANCE"
log "A2A channel: ${A2A_CHANNEL:-none}"

# Decomposition gate: block tasks that require decomposition before execution
REQ_DECOMP=$(echo "$TASK_JSON" | python3 -c "import json,sys; print(json.load(sys.stdin).get('requires_decomposition', False))" 2>/dev/null || echo "False")
DECOMPOSED=$(echo "$TASK_JSON" | python3 -c "import json,sys; print(json.load(sys.stdin).get('decomposed', False))" 2>/dev/null || echo "False")
if [ "$REQ_DECOMP" = "True" ] && [ "$DECOMPOSED" = "False" ]; then
    log "BLOCKED: Task requires decomposition before execution (use /tasks/${TASK_ID}/decompose first)"
    curl -sf -X POST "${API}/tasks/${TASK_ID}/complete" \
        -H 'Content-Type: application/json' \
        -d "{\"output\": \"Blocked — task requires decomposition before execution.\", \"exit_code\": 1}" >> "$LOG_FILE" 2>&1 || true
    exit 1
fi

# Tool RAG: if no explicit agent_type, query /skills/suggest to pick the best specialist
# Only suggest for claude CLI tasks (specialists are Claude agents)
if [ -z "$AGENT_TYPE" ] && [ "$CLI_BACKEND" = "claude" ]; then
    SKILL_TASK_QUERY=$(echo "${TITLE} ${PROMPT}" | python3 -c "import sys,urllib.parse; print(urllib.parse.quote(sys.stdin.read()[:200]))" 2>/dev/null || echo "")
    if [ -n "$SKILL_TASK_QUERY" ]; then
        SKILL_JSON=$(curl -sf "${API}/skills/suggest?task=${SKILL_TASK_QUERY}&top_n=1" 2>/dev/null || echo "")
        SKILL_NAME=$(echo "$SKILL_JSON" | python3 -c "
import json,sys
d=json.load(sys.stdin)
skills=d.get('skills',[])
if skills:
    s=skills[0]
    if s.get('relevance_score',0)>=0.6 and s.get('skill_type')=='agent':
        print(s['name'])
" 2>/dev/null || echo "")
        if [ -n "$SKILL_NAME" ]; then
            # Check project-level agents first, then user-level
            if [ -f "/home/web3relic/otto/.claude/agents/${SKILL_NAME}.md" ]; then
                AGENT_TYPE="$SKILL_NAME"
                log "Tool RAG: auto-selected agent '${AGENT_TYPE}' (project-level, relevance>=0.6)"
            elif [ -f "/home/web3relic/.claude/agents/${SKILL_NAME}.md" ]; then
                AGENT_TYPE="$SKILL_NAME"
                log "Tool RAG: auto-selected agent '${AGENT_TYPE}' (user-level, relevance>=0.6)"
            fi
        fi
    fi
fi

# Map priority to effort level (low=1-4, medium=5-7, high=8-10)
if [ "$PRIORITY" -ge 8 ] 2>/dev/null; then
    EFFORT="high"
elif [ "$PRIORITY" -ge 5 ] 2>/dev/null; then
    EFFORT="medium"
else
    EFFORT="low"
fi

# ── Progressive Loading: tiered injection limits by effort ──────────────────
# Inspired by OpenViking's progressive skill loading pattern.
# Low-effort tasks get minimal context injection (~1500 tokens vs ~5000).
# Prevents "lost in the middle" where injected boilerplate drowns the task.
case "$EFFORT" in
    low)    HINDSIGHT_LIMIT=0; PROC_ENABLED=0; SEMANTIC_LIMIT=4; SEMANTIC_CONFIDENCE=0.5; GIT_PREFLIGHT=0 ;;
    medium) HINDSIGHT_LIMIT=2; PROC_ENABLED=1; SEMANTIC_LIMIT=8; SEMANTIC_CONFIDENCE=0.3; GIT_PREFLIGHT=1 ;;
    high)   HINDSIGHT_LIMIT=3; PROC_ENABLED=1; SEMANTIC_LIMIT=12; SEMANTIC_CONFIDENCE=0.3; GIT_PREFLIGHT=1 ;;
esac
log "Progressive loading: effort=${EFFORT} hindsight=${HINDSIGHT_LIMIT} proc=${PROC_ENABLED} semantic=${SEMANTIC_LIMIT}/${SEMANTIC_CONFIDENCE} git_preflight=${GIT_PREFLIGHT}"

# Validate CLI backend (default to claude for unknown values)
case "$CLI_BACKEND" in
    claude|gemini|kimi) ;;
    *) CLI_BACKEND="claude" ;;
esac

log "Task: ${TITLE}"
log "CLI: ${CLI_BACKEND}, Model: ${MODEL}, Budget: \$${BUDGET}, Timeout: ${TIMEOUT}s, Turns: ${MAX_TURNS}, Effort: ${EFFORT}, Agent: ${AGENT_TYPE:-none}"

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

RL2F_FEEDBACK_ID=$(echo "$TASK_JSON" | python3 -c "import json,sys; print(json.load(sys.stdin).get('metadata', {}).get('rl2f_feedback_id', ''))" 2>/dev/null || echo "")

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

        # ── RL2F Phase 2: Mark feedback as injected into this retry ──────────
        # This records that structured teacher feedback was used (vs blind retry).
        # Enables success rate comparison: with-feedback vs without-feedback.
        if [ -n "$RL2F_FEEDBACK_ID" ]; then
            curl -sf -X PATCH "${API}/rl2f/task-feedback/${RL2F_FEEDBACK_ID}/mark-injected?retry_task_id=${TASK_ID}" \
                >> "$LOG_FILE" 2>&1 && \
                log "RL2F Phase 2: marked feedback ${RL2F_FEEDBACK_ID:0:8} as injected (retry_task=${TASK_ID:0:8})" || \
                log "RL2F Phase 2: WARNING — could not mark feedback as injected (non-fatal)"
        fi
        # ── End RL2F Phase 2 mark-injected ────────────────────────────────────
    fi
fi
# ── End RL2F Feedback Injection ────────────────────────────────────────────────

# Chain-of-Hindsight: fetch similar past task outcomes before building prompt
# Gated by progressive loading: skipped for low-effort tasks
TITLE_ENCODED=$(python3 -c "import urllib.parse,sys; print(urllib.parse.quote(sys.argv[1]))" "$TITLE" 2>/dev/null || echo "")
HINDSIGHT_BLOCK=""
if [ -n "$TITLE_ENCODED" ] && [ "$HINDSIGHT_LIMIT" -gt 0 ]; then
    HINDSIGHT_JSON=$(curl -sf "${API}/tasks/hindsight?query=${TITLE_ENCODED}&limit=${HINDSIGHT_LIMIT}" 2>/dev/null || echo '{"count":0,"hindsight":[]}')
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

# ── Procedure Memory Lookup ───────────────────────────────────────────────────
# Query /procedural/suggest for known approaches to this task type.
# Procedures with trust_score >= 0.40 are injected into the prompt (lowered from 0.55 by AutoEvolve gen-0 experiment).
# Procedure names are saved so we can record outcomes after execution.
# Gated by progressive loading: skipped for low-effort tasks.
PROC_BLOCK=""
PROC_NAMES=""
TITLE_ENC_PROC=$(python3 -c "import urllib.parse,sys; print(urllib.parse.quote(sys.argv[1]))" "$TITLE" 2>/dev/null || echo "")
if [ -n "$TITLE_ENC_PROC" ] && [ "$PROC_ENABLED" = "1" ]; then
    PROC_JSON=$(curl -sf "${API}/procedural/suggest?task_description=${TITLE_ENC_PROC}" 2>/dev/null || echo "[]")
    PROC_BLOCK=$(echo "$PROC_JSON" | python3 -c "
import json, sys
try:
    procs = json.load(sys.stdin)
    relevant = [p for p in procs if p.get('trust_score', 0) >= 0.40 and p.get('steps')]
    if not relevant:
        sys.exit(0)
    lines = ['--- Known procedure (from procedure memory) ---']
    for p in relevant:
        lines.append(f\"Procedure: {p['name']} (trust={p['trust_score']:.2f})\")
        if p.get('description'):
            lines.append(f\"  Description: {p['description']}\")
        if p.get('steps'):
            lines.append('  Steps:')
            for s in p['steps']:
                lines.append(f'    - {s}')
    lines.append('--- Use this approach if applicable, adapt as needed ---')
    print('\n'.join(lines))
except Exception:
    pass
" 2>/dev/null || echo "")
    PROC_NAMES=$(echo "$PROC_JSON" | python3 -c "
import json, sys
try:
    procs = json.load(sys.stdin)
    relevant = [p['name'] for p in procs if p.get('trust_score', 0) >= 0.40 and p.get('steps')]
    print('\n'.join(relevant))
except Exception:
    pass
" 2>/dev/null || echo "")
    if [ -n "$PROC_BLOCK" ]; then
        PROC_COUNT=$(echo "$PROC_NAMES" | grep -c . 2>/dev/null || echo "?")
        log "Procedure memory: ${PROC_COUNT} known procedure(s) will be injected into prompt"
    else
        log "Procedure memory: no high-trust procedures matched for this task"
    fi
fi
# ── End Procedure Memory Lookup ───────────────────────────────────────────────

# ── Semantic Memory Enrichment ───────────────────────────────────────────────
# Query Otto's memory system for relevant context (directives, decisions,
# ecosystem knowledge, conventions, lessons learned). This prevents tasks
# from executing blind — they get the same knowledge Otto has.
log "Querying semantic memory for task-relevant context..."
MEMORY_QUERY="${TITLE}. ${PROMPT}"
# Truncate query to avoid overly long payloads
MEMORY_QUERY=$(echo "$MEMORY_QUERY" | head -c 500)

SEMANTIC_BLOCK=""
SEMANTIC_JSON=$(curl -s --max-time 10 -X POST "http://localhost:8100/semantic/arag_search" \
    -H "Content-Type: application/json" \
    -d "$(python3 -c "
import json, sys
q = sys.argv[1]
print(json.dumps({'query': q, 'limit': int(sys.argv[2]), 'min_confidence': float(sys.argv[3])}))
" "$MEMORY_QUERY" "$SEMANTIC_LIMIT" "$SEMANTIC_CONFIDENCE" 2>/dev/null)" 2>/dev/null || echo "")

if [ -n "$SEMANTIC_JSON" ] && echo "$SEMANTIC_JSON" | python3 -c "import json,sys; json.load(sys.stdin)" 2>/dev/null; then
    SEMANTIC_BLOCK=$(echo "$SEMANTIC_JSON" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    results = data.get('results', [])
    if not results:
        sys.exit(0)
    lines = ['## Otto\'s Relevant Memories', '']
    seen = set()
    for r in results:
        content = r.get('content', '').strip()
        if not content or content in seen:
            continue
        seen.add(content)
        cat = r.get('category', 'unknown')
        # Truncate very long memories
        if len(content) > 400:
            content = content[:400] + '...'
        lines.append(f'- [{cat}] {content}')
    if len(seen) > 0:
        print('\n'.join(lines))
except Exception:
    pass
" 2>/dev/null || echo "")
    if [ -n "$SEMANTIC_BLOCK" ]; then
        MEM_COUNT=$(echo "$SEMANTIC_BLOCK" | grep -c '^\- \[' 2>/dev/null || echo "0")
        log "Semantic memory: ${MEM_COUNT} relevant memories injected into prompt"
    else
        log "Semantic memory: no relevant memories found"
    fi
else
    log "Semantic memory: query failed or returned invalid JSON"
fi
# ── End Semantic Memory Enrichment ───────────────────────────────────────────

# ── Cross-Task Exemplar Injection (CORAL 2604.01658) ─────────────────────────
# Query top exemplars for this agent_type. 17% improvement rate from
# cross-agent parentage per CORAL paper. Capped at 1500 tokens total.
EXEMPLAR_BLOCK=""
if [ -n "$AGENT_TYPE" ]; then
    EXEMPLAR_JSON=$(curl -sf --max-time 5 "${API}/tasks/exemplars?category=${AGENT_TYPE}&limit=3" 2>/dev/null || echo "[]")
    EXEMPLAR_COUNT=$(echo "$EXEMPLAR_JSON" | python3 -c "import json,sys; d=json.load(sys.stdin); print(len(d))" 2>/dev/null || echo "0")

    if [ "$EXEMPLAR_COUNT" -gt 0 ] 2>/dev/null; then
        EXEMPLAR_BLOCK=$(echo "$EXEMPLAR_JSON" | python3 -c "
import json, sys
exemplars = json.load(sys.stdin)
lines = ['## Reference: Top Prior Outputs (quality calibration)',
         'These are reference outputs for quality calibration. Do NOT copy structure or content — use them only to understand expected quality level and approach patterns.',
         '']
total_chars = 0
for e in exemplars:
    excerpt = (e.get('output_excerpt') or '')[:500]
    if total_chars + len(excerpt) > 4500:  # ~1500 tokens
        break
    lines.append(f'### {e[\"title\"]} ({e[\"agent_type\"]})')
    signals = e.get('quality_signals', {})
    lines.append(f'Priority: {signals.get(\"priority\",\"?\")} | Output length: {signals.get(\"output_length\",0)} chars')
    lines.append(excerpt)
    lines.append('')
    total_chars += len(excerpt)
print('\n'.join(lines))
" 2>/dev/null)

        if [ -n "$EXEMPLAR_BLOCK" ]; then
            log "Exemplars: ${EXEMPLAR_COUNT} reference task(s) injected for quality calibration"
        fi
    else
        log "Exemplars: no approved exemplars found for agent_type=${AGENT_TYPE}"
    fi
fi
# ── End Cross-Task Exemplar Injection ────────────────────────────────────────

# ── Pre-flight Environment Check ────────────────────────────────────────────
# Verify baseline health before spending budget. Inspired by Anthropic's
# "init.sh" pattern: catch broken environments early instead of wasting
# the entire task budget discovering problems mid-execution.
log "Running pre-flight environment check..."
PREFLIGHT_BLOCK=""
PREFLIGHT_ISSUES=0

# Check API health
API_HEALTH=$(curl -sf --max-time 5 "${API}/health" 2>/dev/null || echo "DOWN")
if [ "$API_HEALTH" = "DOWN" ]; then
    PREFLIGHT_BLOCK="WARNING: Otto Memory API is DOWN. Memory endpoints will fail."
    PREFLIGHT_ISSUES=$((PREFLIGHT_ISSUES + 1))
    log "Pre-flight: API is DOWN"
fi

# Check working directory exists and is accessible
if [ ! -d "$WORK_DIR" ]; then
    PREFLIGHT_BLOCK="${PREFLIGHT_BLOCK}
WARNING: Working directory '${WORK_DIR}' does not exist."
    PREFLIGHT_ISSUES=$((PREFLIGHT_ISSUES + 1))
    log "Pre-flight: working directory missing: ${WORK_DIR}"
fi

# Check git status if in a git repo (gated by progressive loading)
PREFLIGHT_GIT=""
if [ "$GIT_PREFLIGHT" = "1" ] && { [ -d "${WORK_DIR}/.git" ] || git -C "$WORK_DIR" rev-parse --git-dir &>/dev/null 2>&1; }; then
    # Count dirty files without piping through head (avoids SIGPIPE with pipefail)
    DIRTY_COUNT=$(git -C "$WORK_DIR" status --porcelain 2>/dev/null | wc -l || echo "0")
    GIT_BRANCH=$(git -C "$WORK_DIR" branch --show-current 2>/dev/null || echo "unknown")
    GIT_LAST=$(git -C "$WORK_DIR" log --oneline -3 2>/dev/null || echo "no commits")
    PREFLIGHT_GIT="Git branch: ${GIT_BRANCH}
Recent commits:
${GIT_LAST}"
    if [ "$DIRTY_COUNT" -gt 0 ] 2>/dev/null; then
        # Only show first 20 files — capture to var first to avoid SIGPIPE
        GIT_DIRTY=$(git -C "$WORK_DIR" status --porcelain -uno 2>/dev/null || true)
        GIT_DIRTY=$(echo "$GIT_DIRTY" | head -20 || true)
        PREFLIGHT_GIT="${PREFLIGHT_GIT}
Uncommitted changes (${DIRTY_COUNT} files):
${GIT_DIRTY}"
        log "Pre-flight: git repo has ${DIRTY_COUNT} uncommitted changes"
    else
        log "Pre-flight: git repo clean on branch ${GIT_BRANCH}"
    fi
fi

if [ $PREFLIGHT_ISSUES -gt 0 ]; then
    log "Pre-flight: ${PREFLIGHT_ISSUES} issue(s) detected"
else
    log "Pre-flight: all checks passed"
fi
# ── End Pre-flight Environment Check ────────────────────────────────────────

# ── Task Progress File Recovery ─────────────────────────────────────────────
# Externalize progress to a file that survives context loss (timeouts, retries).
# Inspired by Anthropic's "claude-progress.txt" pattern: each attempt reads
# the previous attempt's progress, avoiding redundant work on retries.
TASK_SHORT_ID="${TASK_ID:0:8}"
PROGRESS_FILE="${WORK_DIR}/.otto-progress-${TASK_SHORT_ID}.md"
PROGRESS_BLOCK=""

if [ -f "$PROGRESS_FILE" ]; then
    PROGRESS_CONTENT=$(head -100 "$PROGRESS_FILE" 2>/dev/null || echo "")
    if [ -n "$PROGRESS_CONTENT" ]; then
        PROGRESS_BLOCK="## Previous Attempt Progress
The following progress was recorded by a previous attempt at this task.
Resume from where it left off — do NOT redo completed work.

${PROGRESS_CONTENT}
--- End previous progress ---"
        log "Progress file: found ${PROGRESS_FILE} ($(wc -l < "$PROGRESS_FILE") lines) — injecting into prompt"
    fi
else
    log "Progress file: none found (first attempt or different working dir)"
fi
# ── End Task Progress File Recovery ─────────────────────────────────────────

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

# Inject previous attempt's progress (before other context so agent sees it early)
if [ -n "$PROGRESS_BLOCK" ]; then
    FULL_PROMPT="${FULL_PROMPT}

${PROGRESS_BLOCK}"
fi

# Inject pre-flight environment state
if [ -n "$PREFLIGHT_BLOCK" ] || [ -n "$PREFLIGHT_GIT" ]; then
    FULL_PROMPT="${FULL_PROMPT}

## Environment State (pre-flight)"
    if [ -n "$PREFLIGHT_BLOCK" ]; then
        FULL_PROMPT="${FULL_PROMPT}
${PREFLIGHT_BLOCK}"
    fi
    if [ -n "$PREFLIGHT_GIT" ]; then
        FULL_PROMPT="${FULL_PROMPT}
${PREFLIGHT_GIT}"
    fi
fi

if [ -n "$HINDSIGHT_BLOCK" ]; then
    FULL_PROMPT="${FULL_PROMPT}

${HINDSIGHT_BLOCK}"
fi

if [ -n "$PROC_BLOCK" ]; then
    FULL_PROMPT="${FULL_PROMPT}

${PROC_BLOCK}"
fi

if [ -n "$SEMANTIC_BLOCK" ]; then
    FULL_PROMPT="${FULL_PROMPT}

${SEMANTIC_BLOCK}"
fi

if [ -n "$EXEMPLAR_BLOCK" ]; then
    FULL_PROMPT="${FULL_PROMPT}

${EXEMPLAR_BLOCK}"
fi

# ── A2A: Inject peer messaging instructions ──────────────────────────────────
if [ -n "$A2A_CHANNEL" ]; then
    # Fetch recent messages (max 10, 200 chars each)
    A2A_RECENT=$(curl -sf "${API}/a2a/poll?channel_id=${A2A_CHANNEL}&reader_id=${TASK_ID}&limit=10" 2>/dev/null || echo "[]")
    A2A_MSG_COUNT=$(echo "$A2A_RECENT" | python3 -c "import json,sys; msgs=json.load(sys.stdin); print(len(msgs))" 2>/dev/null || echo "0")

    A2A_BLOCK="
## Agent-to-Agent Communication (A2A)
You are part of a multi-agent collaboration. Channel: ${A2A_CHANNEL}
Your agent ID: ${TASK_ID}

### Send a message to peers:
\`\`\`bash
curl -sf -X POST ${API}/a2a/send -H 'Content-Type: application/json' \\
  -d '{\"channel_id\": \"${A2A_CHANNEL}\", \"sender_id\": \"${TASK_ID}\", \"sender_agent_type\": \"${AGENT_TYPE}\", \"content\": \"YOUR_MESSAGE\", \"message_type\": \"message\"}'
\`\`\`

### Poll for new messages:
\`\`\`bash
curl -sf '${API}/a2a/poll?channel_id=${A2A_CHANNEL}&reader_id=${TASK_ID}&limit=10'
\`\`\`

### See running peers:
\`\`\`bash
curl -sf '${API}/a2a/peers?$([ -n \"$PLAN_ID\" ] && echo \"plan_id=${PLAN_ID}\" || echo \"workflow_instance_id=${WF_INSTANCE}\")'
\`\`\`"

    if [ "$A2A_MSG_COUNT" -gt 0 ]; then
        A2A_HISTORY=$(echo "$A2A_RECENT" | python3 -c "
import json,sys
msgs=json.load(sys.stdin)
for m in msgs[-10:]:
    sender=m.get('sender_agent_type') or m['sender_id'][:8]
    content=m['content'][:200]
    mtype=m['message_type']
    print(f'- [{mtype}] {sender}: {content}')
" 2>/dev/null || echo "")
        A2A_BLOCK="${A2A_BLOCK}

### Recent channel messages:
${A2A_HISTORY}"
    fi

    FULL_PROMPT="${FULL_PROMPT}

${A2A_BLOCK}"
    log "A2A block injected (${A2A_MSG_COUNT} recent messages)"
fi

if [ -n "$CONTEXT" ]; then
    FULL_PROMPT="${FULL_PROMPT}

Context:
${CONTEXT}"
fi

# ── Progressive Loading: tiered instructions by effort level ────────────────
if [ "$EFFORT" = "low" ]; then
    FULL_PROMPT="${FULL_PROMPT}

Instructions:
- Complete the task. Be concise.
- IMPORTANT: End with a text summary of what you accomplished. Do not end on a tool call.
- If blocked, explain what's blocking you.
- Do NOT message Mev via WhatsApp.
- Commit after each meaningful change. Write progress to '${PROGRESS_FILE}' if the task is non-trivial."
else
    FULL_PROMPT="${FULL_PROMPT}

Instructions:
- Complete the task thoroughly.
- Be concise in your output — the heartbeat will review it.
- IMPORTANT: You MUST end with a text summary of what you accomplished. Do not end on a tool call — your final response must be plain text. This is required for output capture.
- If you cannot complete the task, explain what is blocking you.
- Do NOT message Mev via WhatsApp — the heartbeat handles communication.

## Progress & Commit Discipline
- **Work on ONE feature/change at a time.** Do not attempt to implement everything in a single pass.
- **Commit after each meaningful change** with a descriptive message (e.g., 'Add user auth endpoint' not 'update code').
- **Verify each change works** before moving to the next. If in a git repo, run/test before committing.
- **Maintain a progress file** at '${PROGRESS_FILE}'. Update it as you work:
  \`\`\`markdown
  # Task Progress: ${TITLE}
  ## Completed
  - [what you finished, with brief details]
  ## In Progress
  - [what you're currently working on]
  ## Remaining
  - [what's left to do]
  ## Approach
  - [what approach is working, any key decisions made]
  \`\`\`
  This file survives timeouts and retries — the next attempt will read it and resume where you left off.
  Update it after each commit or significant milestone. Keep it concise.

## Decision Escalation
- If you encounter a decision that requires Mev's input (architectural choice, unclear requirements, multiple valid approaches), output a marker block anywhere in your response:
  [NEEDS_MEV_INPUT]
  {\"question\": \"<what you need decided>\", \"options\": [\"Option A\", \"Option B\"], \"recommendation\": 0, \"context\": \"<brief background>\"}
  [/NEEDS_MEV_INPUT]
  Then continue with your best guess, noting it may need revision based on Mev's answer."
fi
# ── End Progressive Loading Instructions ──────────────────────────────────

# Run the appropriate CLI with timeout
log "Starting ${CLI_BACKEND} CLI..."
cd "$WORK_DIR"
TASK_START_TS=$(date +%s)

# Create a per-task filesystem timestamp marker immediately before the CLI runs.
# qa_runner.sh uses this to isolate changes made by THIS task specifically,
# ignoring changes from concurrently running tasks.
TASK_MARKER_FILE=$(mktemp /tmp/otto_task_marker_XXXXXX)
log "QA marker file: ${TASK_MARKER_FILE}"
OUTFILE=$(mktemp /tmp/otto_task_output_XXXXXX)
log "Output capture file: ${OUTFILE}"

set +e
case "$CLI_BACKEND" in
    claude)
        # Build claude CLI args
        # Compute fallback model (must differ from main model)
        FALLBACK_MODEL="haiku"
        [ "$MODEL" = "haiku" ] && FALLBACK_MODEL="sonnet"
        CLAUDE_ARGS=(
            --print
            --dangerously-skip-permissions
            --model "$MODEL"
            --fallback-model "$FALLBACK_MODEL"
            --max-turns "$MAX_TURNS"
            --max-budget-usd "$BUDGET"
            --effort "$EFFORT"
            --no-session-persistence
        )
        # Use specialist agent if specified (check project-level then user-level)
        if [ -n "$AGENT_TYPE" ]; then
            if [ -f "/home/web3relic/otto/.claude/agents/${AGENT_TYPE}.md" ] || \
               [ -f "/home/web3relic/.claude/agents/${AGENT_TYPE}.md" ]; then
                CLAUDE_ARGS+=(--agent "$AGENT_TYPE")
                log "Using specialist agent: ${AGENT_TYPE}"
            else
                log "WARNING: agent '${AGENT_TYPE}' specified but .md file not found — running without agent"
            fi
        fi
        timeout "${TIMEOUT}s" "$CLAUDE_CLI" \
            "${CLAUDE_ARGS[@]}" \
            -p "$FULL_PROMPT" \
            > "$OUTFILE" 2>"${LOG_FILE}.stderr" &
        CLI_PID=$!
        ;;
    gemini)
        # Gemini CLI: no --max-turns or --budget flags. Use --yolo for auto-approval.
        # Output format json then extract .response for clean text capture.
        # Raw JSON written to OUTFILE; extracted after esac.
        timeout "${TIMEOUT}s" gemini \
            --yolo \
            --output-format json \
            --include-directories "$WORK_DIR" \
            -p "$FULL_PROMPT" \
            > "$OUTFILE" 2>"${LOG_FILE}.stderr" &
        CLI_PID=$!
        ;;
    kimi)
        # Kimi CLI: --quiet = --print --output-format text --final-message-only
        # --yolo implied by --quiet/--print. --max-steps-per-turn instead of --max-turns.
        timeout "${TIMEOUT}s" /home/web3relic/.local/bin/kimi \
            --quiet \
            --yolo \
            --work-dir "$WORK_DIR" \
            --max-steps-per-turn "$MAX_TURNS" \
            -p "$FULL_PROMPT" \
            > "$OUTFILE" 2>"${LOG_FILE}.stderr" &
        CLI_PID=$!
        ;;
    *)
        log "ERROR: Unknown CLI backend '${CLI_BACKEND}' — falling back to claude"
        FALLBACK_MODEL_FB="haiku"
        [ "$MODEL" = "haiku" ] && FALLBACK_MODEL_FB="sonnet"
        timeout "${TIMEOUT}s" "$CLAUDE_CLI" \
            --print \
            --dangerously-skip-permissions \
            --model "$MODEL" \
            --fallback-model "$FALLBACK_MODEL_FB" \
            --max-turns "$MAX_TURNS" \
            --max-budget-usd "$BUDGET" \
            --effort "$EFFORT" \
            --no-session-persistence \
            -p "$FULL_PROMPT" \
            > "$OUTFILE" 2>"${LOG_FILE}.stderr" &
        CLI_PID=$!
        ;;
esac

# ── Wink Monitor (arXiv:2602.17037) ─────────────────────────────────────────
# Launch async monitor to watch CLI output for misbehavior patterns (stalls,
# error loops, reasoning loops) while the CLI runs in background.
WINK_MONITOR="/home/web3relic/otto/task_monitor.sh"
WINK_PID=""
if [ -x "$WINK_MONITOR" ]; then
    "$WINK_MONITOR" "$TASK_ID" "$OUTFILE" "$CLI_PID" &
    WINK_PID=$!
    log "Wink monitor launched (PID=$WINK_PID) watching CLI PID=$CLI_PID"
fi

# Wait for CLI to finish
wait "$CLI_PID"
EXIT_CODE=$?

# Stop Wink monitor
if [ -n "$WINK_PID" ]; then
    kill "$WINK_PID" 2>/dev/null || true
    wait "$WINK_PID" 2>/dev/null || true
    log "Wink monitor stopped"
fi
# ── End Wink Monitor ────────────────────────────────────────────────────────
set -e

STDERR=$(cat "${LOG_FILE}.stderr" 2>/dev/null || echo "")
rm -f "${LOG_FILE}.stderr"

log "${CLI_BACKEND} CLI exited with code ${EXIT_CODE}"

# ── CLI Quota Fallback ────────────────────────────────────────────────────────
# If gemini/kimi failed with 429 (quota exhausted), retry on claude as fallback.
# This prevents tasks from failing purely due to API quota limits on non-Claude CLIs.
if [ "$EXIT_CODE" -ne 0 ] && [ "$CLI_BACKEND" != "claude" ]; then
    if echo "$STDERR$(cat "$OUTFILE" 2>/dev/null)" | grep -qiE "429|RESOURCE_EXHAUSTED|quota|rate.limit"; then
        log "QUOTA FALLBACK: ${CLI_BACKEND} hit quota limit — retrying on claude..."
        CLI_BACKEND="claude"
        set +e
        FALLBACK_MODEL_QF="haiku"
        [ "$MODEL" = "haiku" ] && FALLBACK_MODEL_QF="sonnet"
        timeout "${TIMEOUT}s" "$CLAUDE_CLI" \
            --print \
            --dangerously-skip-permissions \
            --model "$MODEL" \
            --fallback-model "$FALLBACK_MODEL_QF" \
            --max-turns "$MAX_TURNS" \
            --max-budget-usd "$BUDGET" \
            --effort "$EFFORT" \
            --no-session-persistence \
            -p "$FULL_PROMPT" \
            > "$OUTFILE" 2>"${LOG_FILE}.stderr"
        EXIT_CODE=$?
        set -e
        STDERR=$(cat "${LOG_FILE}.stderr" 2>/dev/null || echo "")
        rm -f "${LOG_FILE}.stderr"
        log "Fallback claude CLI exited with code ${EXIT_CODE}"
    fi
fi

# Read output from tempfile — captures partial output even on timeout (exit 124)
OUTPUT=$(cat "$OUTFILE" 2>/dev/null || echo "")
rm -f "$OUTFILE"

# Gemini outputs JSON — extract clean response text from envelope
if [ "$CLI_BACKEND" = "gemini" ] && [ -n "$OUTPUT" ]; then
    OUTPUT=$(echo "$OUTPUT" | python3 -c "
import json, sys
raw = sys.stdin.read()
try:
    data = json.loads(raw)
    print(data.get('response') or data.get('text') or str(data))
except Exception:
    print(raw)
" 2>/dev/null || echo "$OUTPUT")
fi

# ── Rate limit sentinel ────────────────────────────────────────────────────────
# If the CLI hit a rate limit, write sentinel so heartbeat/reflection skip next cycle.
RATE_LIMIT_FILE="/tmp/otto-rate-limited"
COMBINED_OUTPUT="${STDERR}${OUTPUT}"
if echo "$COMBINED_OUTPUT" | grep -qiE "429|rate.limit|RateLimitError|overloaded_error|too_many_requests|quota_exceeded"; then
    date +%s > "$RATE_LIMIT_FILE"
    log "Rate limit detected — wrote sentinel ${RATE_LIMIT_FILE}. Heartbeat/reflection will skip next cycle."
    curl -sf -X POST "${API}/episodic/events" \
        -H 'Content-Type: application/json' \
        -d "{\"type\":\"rate_limit_hit\",\"summary\":\"Rate limit hit during task ${TASK_ID:0:8}. Sentinel written — next heartbeat/reflection cycle suppressed.\"}" \
        >> "$LOG_FILE" 2>&1 || true
fi
# ── End rate limit sentinel ────────────────────────────────────────────────────

# Exit 124 = timeout — log how much partial output was captured
if [ "$EXIT_CODE" -eq 124 ]; then
    OUTBYTES=${#OUTPUT}
    log "TIMEOUT: CLI killed after ${TIMEOUT}s — partial output captured (${OUTBYTES} bytes)"
fi

# Detect empty output with exit_code=0 — CLI succeeded but produced nothing.
# This usually indicates the agent hit budget/turns silently or the CLI had an issue.
# Override to exit_code=1 so the task is marked 'failed' rather than auto-completing.
if [ "$EXIT_CODE" -eq 0 ] && [ -z "$OUTPUT" ]; then
    log "WARNING: CLI exited 0 with empty output — overriding exit_code to 1 (task may have hit budget silently or had a startup failure)"
    EXIT_CODE=1
    OUTPUT="[NO OUTPUT — CLI exited 0 with empty output. Possible silent budget/turns exhaustion or startup failure. Verify by checking the task log: ${LOG_FILE}]"
fi

# Detect max-turns/max-steps hit
# Claude: "Error: Reached max turns" | Kimi: may vary | Gemini: no turn limit
# The CLI exits with code 0 in this case, so we override to 1 to mark the task 'failed'
# rather than 'completed'. Without this, the API default maps exit_code=0 → 'completed'.
if echo "$OUTPUT" | grep -qE "^Error: Reached max turns|^Error: max.steps reached"; then
    log "WARNING: Task hit turn/step limit — overriding exit_code to 1 (was ${EXIT_CODE}) so task is marked 'failed' not 'completed'"
    EXIT_CODE=1
    OUTPUT="[INCOMPLETE — hit max_turns/max_steps limit. Task may have partially completed. Verify by checking the codebase directly.]"
fi

# ── HiClaw GAP-2: Artifact Path References ─────────────────────────────────
# Write artifact BEFORE truncation so the file always contains the full output.
# When output > 2KB and task succeeded, write full output to a persistent
# artifact file. Store only a summary + path reference in the DB output field.
# Prevents DB bloat and context inflation when chaining tasks/workflows.
ARTIFACT_PATH=""
ARTIFACT_BYTES=0
ARTIFACT_THRESHOLD=2048
if [ ${#OUTPUT} -gt $ARTIFACT_THRESHOLD ] && [ "$EXIT_CODE" -eq 0 ]; then
    ARTIFACT_DIR="${LOG_DIR}/${TASK_ID}"
    mkdir -p "$ARTIFACT_DIR"
    ARTIFACT_PATH="${ARTIFACT_DIR}/output.md"
    printf '%s' "$OUTPUT" > "$ARTIFACT_PATH"
    ARTIFACT_BYTES=${#OUTPUT}
    ARTIFACT_SUMMARY="${OUTPUT:0:500}"
    OUTPUT="[ARTIFACT: ${ARTIFACT_PATH}]

${ARTIFACT_SUMMARY}
...[${ARTIFACT_BYTES} bytes total — full output at: ${ARTIFACT_PATH}]"
    log "GAP-2: artifact written (${ARTIFACT_BYTES} bytes) → ${ARTIFACT_PATH}"
fi
# ── End Artifact Path References ────────────────────────────────────────────

# Truncate output if too large (runs after artifact write — artifact is always full)
MAX_OUTPUT_LEN=50000
if [ ${#OUTPUT} -gt $MAX_OUTPUT_LEN ]; then
    OUTPUT="${OUTPUT:0:$MAX_OUTPUT_LEN}

[TRUNCATED — output exceeded ${MAX_OUTPUT_LEN} chars]"
    log "Output truncated to ${MAX_OUTPUT_LEN} chars"
fi

# ── NEEDS_MEV_INPUT: Task-level collaboration request ─────────────────────────
# If the task output contains [NEEDS_MEV_INPUT]...[/NEEDS_MEV_INPUT], extract the
# question and create a decision proposal so Mev can respond via WhatsApp.
if echo "$OUTPUT" | grep -q '\[NEEDS_MEV_INPUT\]'; then
    INPUT_JSON=$(echo "$OUTPUT" | python3 -c "
import sys, re, json
text = sys.stdin.read()
match = re.search(r'\[NEEDS_MEV_INPUT\]\s*(\{.*?\})\s*\[/NEEDS_MEV_INPUT\]', text, re.DOTALL)
if match:
    try:
        data = json.loads(match.group(1))
        question = data.get('question', '')
        options_raw = data.get('options', [])
        options = [{'label': o, 'description': o} if isinstance(o, str) else o for o in options_raw]
        rec = data.get('recommendation')
        context = data.get('context', '')
        print(json.dumps({
            'question': question,
            'context': context,
            'options': options,
            'recommendation': rec,
            'recommendation_reason': '',
            'source': 'task',
            'source_task_id': '${TASK_ID}',
            'urgency': 'high',
        }))
    except Exception:
        pass
" 2>/dev/null || echo "")

    if [ -n "$INPUT_JSON" ]; then
        PROPOSE_RESULT=$(curl -sf -X POST "${API}/pending/propose" \
            -H 'Content-Type: application/json' \
            -d "$INPUT_JSON" 2>/dev/null || echo "")
        if [ -n "$PROPOSE_RESULT" ]; then
            PROPOSAL_Q=$(echo "$PROPOSE_RESULT" | python3 -c "import json,sys; print(json.load(sys.stdin).get('question','')[:200])" 2>/dev/null || echo "")
            log "NEEDS_MEV_INPUT: created proposal — ${PROPOSAL_Q}"
            # Message Mev immediately
            /home/web3relic/otto/tools/whatsapp_send.sh "Hey Mev, a task needs your input: ${PROPOSAL_Q}" 2>/dev/null || true
        else
            log "NEEDS_MEV_INPUT: failed to create proposal (non-fatal)"
        fi
    fi
fi
# ── End NEEDS_MEV_INPUT ──────────────────────────────────────────────────────

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

    META_STDERR_FILE=$(mktemp /tmp/sofai_stderr.XXXXXX)
    META_RAW=$(timeout 30 gemini -m gemini-2.0-flash -p "$META_PROMPT" 2>"$META_STDERR_FILE" || echo "")
    META_GEMINI_EXIT=$?

    # Fallback: if gemini failed (rate limit / quota / timeout), try claude haiku
    if [ -z "$META_RAW" ] || [ "$META_GEMINI_EXIT" -ne 0 ]; then
        GEMINI_STDERR=$(cat "$META_STDERR_FILE" 2>/dev/null | head -3 || echo "")
        log "SOFAI-LM: gemini failed (exit=${META_GEMINI_EXIT}, stderr: ${GEMINI_STDERR:0:100}) — trying claude haiku fallback"
        META_RAW=$(timeout 30 "$CLAUDE_CLI" \
            --print \
            --dangerously-skip-permissions \
            --model "claude-haiku-4-5-20251001" \
            --max-turns 1 \
            --max-budget-usd 0.05 \
            -p "$META_PROMPT" 2>/dev/null || echo "")
    fi
    rm -f "$META_STDERR_FILE"

    # Parse JSON from response (balanced brace extractor handles multi-line + nested JSON).
    # Fixes 16% parse failure rate from the old [^}]+ regex that couldn't handle nested objects.
    META_JSON=$(echo "$META_RAW" | python3 -c "
import json, sys, re

raw = sys.stdin.read()
# Strip markdown code block fences (opening and closing)
raw = re.sub(r'\`\`\`(?:json|text|bash)?\n?', '', raw).strip()

def extract_balanced_json(text):
    '''Find the first balanced {...} block, handles nested objects.'''
    start = text.find('{')
    if start == -1:
        return None
    depth = 0
    for i, ch in enumerate(text[start:], start):
        if ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0:
                return text[start:i+1]
    return None

blob = extract_balanced_json(raw)
if blob:
    try:
        data = json.loads(blob)
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
meta = json.loads(sys.argv[4])
artifact_path = sys.argv[5]
if artifact_path:
    meta['artifact_path'] = artifact_path
    meta['artifact_bytes'] = int(sys.argv[6])
print(json.dumps({
    'output': sys.argv[1] if sys.argv[1] else None,
    'error': sys.argv[2] if sys.argv[2] else None,
    'exit_code': int(sys.argv[3]),
    'metadata': meta,
}))
" "$OUTPUT" "$STDERR" "$EXIT_CODE" "$META_PAYLOAD" "$ARTIFACT_PATH" "${ARTIFACT_BYTES:-0}")

curl -sf -X POST "${API}/tasks/${TASK_ID}/complete" \
    -H 'Content-Type: application/json' \
    -d "$RESULT_JSON" >> "$LOG_FILE" 2>&1 || {
    log "WARNING: Failed to report task completion to API"
}
TASK_COMPLETED=true  # Prevent zombie trap from double-reporting

# ── JitRL Experience Ingestion ────────────────────────────────────────────────
# Feed this task's outcome into the JitRL experience buffer so future tasks
# benefit from knowing which action types succeed in which contexts.
if [ "$EXIT_CODE" -eq 0 ] || [ "$EXIT_CODE" -eq 124 ]; then
    JITRL_RESULT=$(curl -sf -X POST "${API}/jitrl/ingest-task/${TASK_ID}" 2>/dev/null || echo "")
    if [ -n "$JITRL_RESULT" ]; then
        JITRL_ACTION=$(echo "$JITRL_RESULT" | python3 -c "import json,sys; print(json.load(sys.stdin).get('action_type','?'))" 2>/dev/null || echo "?")
        JITRL_REWARD=$(echo "$JITRL_RESULT" | python3 -c "import json,sys; print(json.load(sys.stdin).get('reward','?'))" 2>/dev/null || echo "?")
        log "JitRL: ingested experience (action_type=${JITRL_ACTION}, reward=${JITRL_REWARD})"
    else
        log "JitRL: ingestion failed (non-fatal)"
    fi
elif [ "$EXIT_CODE" -ne 0 ]; then
    # For failed tasks, still ingest so JitRL learns from failures
    JITRL_RESULT=$(curl -sf -X POST "${API}/jitrl/ingest-task/${TASK_ID}" 2>/dev/null || echo "")
    if [ -n "$JITRL_RESULT" ]; then
        log "JitRL: ingested failed experience (reward=-0.5)"
    fi
fi
# ── End JitRL Ingestion ──────────────────────────────────────────────────────

# ── Procedure Outcome Recording ───────────────────────────────────────────────
# For each procedure that was injected into the prompt, record success or failure.
# This closes the TAME learning loop: trust scores converge toward actual reliability.
if [ -n "$PROC_NAMES" ]; then
    PROC_SUCCESS="true"
    [ "$EXIT_CODE" -ne 0 ] && PROC_SUCCESS="false"
    while IFS= read -r PROC_NAME; do
        [ -z "$PROC_NAME" ] && continue
        PROC_NAME_ENC=$(python3 -c "import urllib.parse,sys; print(urllib.parse.quote(sys.argv[1]))" "$PROC_NAME" 2>/dev/null || echo "$PROC_NAME")
        curl -sf -X PUT "${API}/procedural/${PROC_NAME_ENC}/outcome" \
            -H 'Content-Type: application/json' \
            -d "{\"success\": ${PROC_SUCCESS}}" \
            >> "$LOG_FILE" 2>&1 && \
            log "Procedure outcome: ${PROC_NAME} → success=${PROC_SUCCESS}" || \
            log "WARNING: could not record outcome for procedure '${PROC_NAME}' (non-fatal)"
    done <<< "$PROC_NAMES"
fi
# ── End Procedure Outcome Recording ───────────────────────────────────────────

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
        # Timeout exit (124): explicitly mark qa_status so heartbeat knows to retry.
        # Without this, timed-out tasks have qa_status=null and may be silently ignored.
        if [ "$EXIT_CODE" -eq 124 ]; then
            curl -sf -X POST "${API}/tasks/${TASK_ID}/qa-update" \
                -H 'Content-Type: application/json' \
                -d "{\"qa_status\": \"needs_manual_review\", \"qa_reviewer\": \"system\", \"qa_output\": \"Task timed out after ${TIMEOUT}s (exit 124). Retry with higher timeout or smaller scope.\"}" \
                >> "$LOG_FILE" 2>&1 || true
            log "Timeout: marked qa_status=needs_manual_review (timeout after ${TIMEOUT}s)"
        fi
    fi
    rm -f "$TASK_MARKER_FILE" 2>/dev/null || true
fi
# ── End QA Runner ──────────────────────────────────────────────────────────────

# ── Smart Inline Retry (QA Gate + Failure Recovery) ──────────────────────────
# Runs inline retries after failed executions or QA rejections.
# Max 2 inline retries (3 total attempts). On permanent failure: diagnostic report.
#
# Failure modes:
#   timeout (124):    Increase timeout by 50%, add incremental work instruction
#   error (non-0):    Inject error message as context, add error recovery instruction
#   empty_output:     Emphasize output requirement, focus on highest-priority deliverable
#   qa_rejected:      Re-inject latest QA rejection feedback into prompt
#
# Controlled by OTTO_INLINE_RETRY=1 (default). Set to 0 to disable.
INLINE_RETRY_ENABLED="${OTTO_INLINE_RETRY:-1}"

if [ "$INLINE_RETRY_ENABLED" = "1" ]; then

# Read retry count already accumulated (external retries by heartbeat count too)
INLINE_RETRY_COUNT=$(echo "$TASK_JSON" | python3 -c "
import json, sys
m = json.load(sys.stdin).get('metadata', {})
print(int(m.get('retry_count', 0)))
" 2>/dev/null || echo "0")

# Fetch current QA status (set by qa_runner.sh above, or still pending_qa for failed tasks)
CURRENT_QA_STATUS=$(curl -sf "${API}/tasks/${TASK_ID}" 2>/dev/null | python3 -c "
import json, sys
print(json.load(sys.stdin).get('qa_status', '') or '')
" 2>/dev/null || echo "")

# Determine initial failure mode
RETRY_FAILURE_MODE="none"
if [ "$EXIT_CODE" -eq 124 ]; then
    RETRY_FAILURE_MODE="timeout"
elif [ "$EXIT_CODE" -ne 0 ]; then
    RETRY_FAILURE_MODE="error"
elif [ -z "$OUTPUT" ] || [ "${#OUTPUT}" -lt 50 ]; then
    RETRY_FAILURE_MODE="empty_output"
elif [ "$CURRENT_QA_STATUS" = "rejected" ]; then
    RETRY_FAILURE_MODE="qa_rejected"
fi

INLINE_MAX_RETRIES=2  # Max inline retries (3 total attempts counting initial)
RETRY_TIMEOUT="$TIMEOUT"
RETRY_TURNS="$MAX_TURNS"

while [ "$RETRY_FAILURE_MODE" != "none" ]; do

    if [ "$INLINE_RETRY_COUNT" -ge "$INLINE_MAX_RETRIES" ]; then
        # ── Permanent failure — generate diagnostic report ─────────────────────
        log "SMART_RETRY: permanent failure after $((INLINE_RETRY_COUNT + 1)) attempts (mode=${RETRY_FAILURE_MODE})"

        # Build structured diagnostic report
        DIAG_REPORT=$(python3 -c "
import json, sys, datetime
mode = sys.argv[1]
recs = {
    'timeout': 'Increase timeout_seconds significantly or break into smaller subtasks',
    'error': 'Review error output, fix root cause, then re-queue with corrected prompt',
    'empty_output': 'Simplify task prompt, increase budget, or use a higher-capability model',
    'qa_rejected': 'Manually review QA rejection feedback and rewrite the task prompt',
}
print(json.dumps({
    'type': 'permanent_failure_diagnostic',
    'task_id': sys.argv[2][:8],
    'total_attempts': int(sys.argv[3]) + 1,
    'final_failure_mode': mode,
    'final_exit_code': int(sys.argv[4]),
    'final_output_bytes': len(sys.argv[5]) if sys.argv[5] else 0,
    'final_qa_status': sys.argv[6],
    'timestamp': datetime.datetime.utcnow().isoformat() + 'Z',
    'recommendation': recs.get(mode, 'Manual intervention required'),
}))
" "$RETRY_FAILURE_MODE" "$TASK_ID" "$INLINE_RETRY_COUNT" "$EXIT_CODE" "$OUTPUT" "$CURRENT_QA_STATUS" 2>/dev/null || echo "{}")

        # Log to episodic memory
        curl -sf -X POST "${API}/episodic/events" \
            -H 'Content-Type: application/json' \
            -d "$(python3 -c "
import json, sys
print(json.dumps({'type': 'task_permanent_failure', 'summary': 'Task ' + sys.argv[1][:8] + ' permanently failed after ' + str(int(sys.argv[2])+1) + ' attempts. Mode: ' + sys.argv[3] + '. Exit: ' + sys.argv[4] + '.'}))
" "$TASK_ID" "$INLINE_RETRY_COUNT" "$RETRY_FAILURE_MODE" "$EXIT_CODE" 2>/dev/null)" \
            >> "$LOG_FILE" 2>&1 || true

        # Mark task as permanently failed (qa_status=failed)
        FAIL_MSG="PERMANENT FAILURE: Task failed $((INLINE_RETRY_COUNT + 1)) attempts. Mode: ${RETRY_FAILURE_MODE}. ${DIAG_REPORT:0:600}"
        curl -sf -X POST "${API}/tasks/${TASK_ID}/qa-update" \
            -H 'Content-Type: application/json' \
            -d "$(python3 -c "
import json, sys
print(json.dumps({'qa_status': 'failed', 'qa_reviewer': 'smart_retry', 'qa_output': sys.argv[1][:800]}))
" "$FAIL_MSG" 2>/dev/null)" \
            >> "$LOG_FILE" 2>&1 || true

        log "SMART_RETRY: task ${TASK_ID:0:8} marked qa_status=failed (permanent)"
        break
    fi

    # ── Prepare retry attempt ────────────────────────────────────────────────
    INLINE_RETRY_COUNT=$((INLINE_RETRY_COUNT + 1))
    log "SMART_RETRY: starting inline retry ${INLINE_RETRY_COUNT}/${INLINE_MAX_RETRIES} — failure_mode=${RETRY_FAILURE_MODE}"

    # Persist retry count in task metadata
    curl -sf -X PATCH "${API}/tasks/${TASK_ID}/metadata" \
        -H 'Content-Type: application/json' \
        -d "{\"retry_count\": ${INLINE_RETRY_COUNT}, \"last_failure_mode\": \"${RETRY_FAILURE_MODE}\"}" \
        >> "$LOG_FILE" 2>&1 || true

    # Build failure-mode-specific retry context injection
    RETRY_CONTEXT_INJECTION=""
    case "$RETRY_FAILURE_MODE" in
        timeout)
            RETRY_TIMEOUT=$(python3 -c "print(min(int(${TIMEOUT} * 1.5), 1800))" 2>/dev/null || echo "$TIMEOUT")
            RETRY_TURNS=$(python3 -c "print(max(int(${MAX_TURNS} * 8 // 10), 15))" 2>/dev/null || echo "$MAX_TURNS")
            RETRY_CONTEXT_INJECTION="=== RETRY (attempt ${INLINE_RETRY_COUNT}): Previous attempt TIMED OUT after ${TIMEOUT}s ===
Work incrementally — complete one meaningful step, commit it, then continue.
Focus on the highest-priority deliverable first. Partial completion is better than nothing.
New timeout: ${RETRY_TIMEOUT}s. Commit what you have before the timeout expires.
=== End retry context ==="
            log "SMART_RETRY: timeout mode — new timeout=${RETRY_TIMEOUT}s turns=${RETRY_TURNS}"
            ;;
        error)
            ERROR_EXCERPT=$(echo "${STDERR}${OUTPUT}" | head -c 500 | tr '\n' ' ' | sed 's/"/\\"/g')
            RETRY_CONTEXT_INJECTION="=== RETRY (attempt ${INLINE_RETRY_COUNT}): Previous attempt EXITED WITH ERROR (code ${EXIT_CODE}) ===
Error output: ${ERROR_EXCERPT:0:400}
Diagnose the root cause from the error output above. Fix it before proceeding.
If the error is environmental (missing file, wrong path), verify prerequisites first.
=== End retry context ==="
            log "SMART_RETRY: error mode — injecting error context"
            ;;
        empty_output)
            RETRY_CONTEXT_INJECTION="=== RETRY (attempt ${INLINE_RETRY_COUNT}): Previous attempt produced NO OUTPUT ===
You MUST produce a meaningful plain-text summary of what you accomplished.
End your response with a text summary — this is REQUIRED for output capture.
If the task is complex, focus on the single most critical deliverable first.
=== End retry context ==="
            log "SMART_RETRY: empty_output mode — injecting output requirement reminder"
            ;;
        qa_rejected)
            QA_REJECTION_TEXT=$(curl -sf "${API}/tasks/${TASK_ID}" 2>/dev/null | python3 -c "
import json, sys
d = json.load(sys.stdin)
print((d.get('qa_output') or '')[:500])
" 2>/dev/null || echo "")
            # IMPL-03 VISTA: Parse QA rejection into structured failure labels
            VISTA_LABELS=$(curl -sf -X POST "${API}/tasks/parse-failure" \
                -H 'Content-Type: application/json' \
                -d "$(python3 -c "
import json, sys
print(json.dumps({
    'qa_output': sys.argv[1][:800],
    'task_title': sys.argv[2][:200],
    'task_prompt_excerpt': sys.argv[3][:500]
}))
" "${QA_REJECTION_TEXT}" "${TITLE}" "${PROMPT_EXCERPT}" 2>/dev/null)" 2>/dev/null || echo "")

            if [ -n "$VISTA_LABELS" ]; then
                VISTA_TYPE=$(echo "$VISTA_LABELS" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('failure_type','unknown'))" 2>/dev/null || echo "unknown")
                VISTA_CAUSE=$(echo "$VISTA_LABELS" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('root_cause','')[:200])" 2>/dev/null || echo "")
                VISTA_ACTION=$(echo "$VISTA_LABELS" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('corrective_action','')[:200])" 2>/dev/null || echo "")
                log "SMART_RETRY: VISTA classified failure as ${VISTA_TYPE}"
                RETRY_CONTEXT_INJECTION="=== RETRY (attempt ${INLINE_RETRY_COUNT}): Previous attempt was REJECTED by QA ===
## Failure Analysis (VISTA)
Type: ${VISTA_TYPE}
Root cause: ${VISTA_CAUSE}
Corrective action: ${VISTA_ACTION}

## Original QA Feedback
${QA_REJECTION_TEXT:0:400}

Address the corrective action above FIRST, then verify all QA feedback points.
=== End retry context ==="
            else
                log "SMART_RETRY: VISTA parse-failure unavailable, using raw QA text"
                RETRY_CONTEXT_INJECTION="=== RETRY (attempt ${INLINE_RETRY_COUNT}): Previous attempt was REJECTED by QA ===
QA rejection feedback: ${QA_REJECTION_TEXT:0:400}
Address ALL points in the QA feedback above before completing the task.
=== End retry context ==="
            fi
            log "SMART_RETRY: qa_rejected mode — injecting QA feedback"
            ;;
    esac

    # Build retry prompt (context injection prepended)
    RETRY_PROMPT="${RETRY_CONTEXT_INJECTION}

${FULL_PROMPT}"

    # Create new QA isolation marker just before retry CLI runs
    TASK_MARKER_FILE=$(mktemp /tmp/otto_task_marker_XXXXXX)
    OUTFILE=$(mktemp /tmp/otto_task_output_XXXXXX)
    log "SMART_RETRY: marker=${TASK_MARKER_FILE} outfile=${OUTFILE}"

    # ── Run retry CLI ──────────────────────────────────────────────────────────
    set +e
    case "$CLI_BACKEND" in
        claude)
            FALLBACK_MODEL_R="haiku"
            [ "$MODEL" = "haiku" ] && FALLBACK_MODEL_R="sonnet"
            timeout "${RETRY_TIMEOUT}s" "$CLAUDE_CLI" \
                --print \
                --dangerously-skip-permissions \
                --model "$MODEL" \
                --fallback-model "$FALLBACK_MODEL_R" \
                --max-turns "$RETRY_TURNS" \
                --max-budget-usd "$BUDGET" \
                --effort "$EFFORT" \
                --no-session-persistence \
                -p "$RETRY_PROMPT" \
                > "$OUTFILE" 2>"${LOG_FILE}.retry_stderr" &
            CLI_PID=$!
            ;;
        gemini)
            timeout "${RETRY_TIMEOUT}s" gemini \
                --yolo \
                --output-format json \
                --include-directories "$WORK_DIR" \
                -p "$RETRY_PROMPT" \
                > "$OUTFILE" 2>"${LOG_FILE}.retry_stderr" &
            CLI_PID=$!
            ;;
        kimi)
            timeout "${RETRY_TIMEOUT}s" /home/web3relic/.local/bin/kimi \
                --quiet \
                --yolo \
                --work-dir "$WORK_DIR" \
                --max-steps-per-turn "$RETRY_TURNS" \
                -p "$RETRY_PROMPT" \
                > "$OUTFILE" 2>"${LOG_FILE}.retry_stderr" &
            CLI_PID=$!
            ;;
        *)
            timeout "${RETRY_TIMEOUT}s" "$CLAUDE_CLI" \
                --print --dangerously-skip-permissions \
                --model "$MODEL" --fallback-model "haiku" \
                --max-turns "$RETRY_TURNS" --max-budget-usd "$BUDGET" \
                --effort "$EFFORT" --no-session-persistence \
                -p "$RETRY_PROMPT" \
                > "$OUTFILE" 2>"${LOG_FILE}.retry_stderr" &
            CLI_PID=$!
            ;;
    esac
    wait "$CLI_PID"
    EXIT_CODE=$?
    set -e

    STDERR=$(cat "${LOG_FILE}.retry_stderr" 2>/dev/null || echo "")
    rm -f "${LOG_FILE}.retry_stderr"
    OUTPUT=$(cat "$OUTFILE" 2>/dev/null || echo "")
    rm -f "$OUTFILE"

    # Gemini JSON extraction for retry output
    if [ "$CLI_BACKEND" = "gemini" ] && [ -n "$OUTPUT" ]; then
        OUTPUT=$(echo "$OUTPUT" | python3 -c "
import json, sys
raw = sys.stdin.read()
try:
    data = json.loads(raw)
    print(data.get('response') or data.get('text') or str(data))
except Exception:
    print(raw)
" 2>/dev/null || echo "$OUTPUT")
    fi

    # Detect max-turns hit on retry
    if echo "$OUTPUT" | grep -qE "^Error: Reached max turns|^Error: max.steps reached"; then
        log "SMART_RETRY: retry ${INLINE_RETRY_COUNT} hit max_turns — treating as empty output"
        OUTPUT="[INCOMPLETE — hit max_turns on retry ${INLINE_RETRY_COUNT}]"
    fi

    log "SMART_RETRY: retry ${INLINE_RETRY_COUNT} exited code=${EXIT_CODE} output=${#OUTPUT}bytes"

    # Update task output in API with retry result
    RETRY_RESULT_JSON=$(python3 -c "
import json, sys
print(json.dumps({
    'output': sys.argv[1] if sys.argv[1] else None,
    'error': sys.argv[2] if sys.argv[2] else None,
    'exit_code': int(sys.argv[3]),
    'metadata': {},
}))
" "$OUTPUT" "$STDERR" "$EXIT_CODE" 2>/dev/null || echo "{}")

    curl -sf -X POST "${API}/tasks/${TASK_ID}/complete" \
        -H 'Content-Type: application/json' \
        -d "$RETRY_RESULT_JSON" >> "$LOG_FILE" 2>&1 || true

    # Run QA on successful retry
    if [ "$EXIT_CODE" -eq 0 ] && [ -x "$QA_RUNNER" ] && [ "$OTTO_QA" = "1" ]; then
        log "SMART_RETRY: running QA on retry ${INLINE_RETRY_COUNT} output..."
        bash "$QA_RUNNER" "$TASK_ID" "$CLI_BACKEND" "$LOG_FILE" "$TASK_MARKER_FILE" 2>>"$LOG_FILE" || \
            log "SMART_RETRY: QA runner exited with error (non-fatal)"
    elif [ "$EXIT_CODE" -eq 124 ]; then
        # Timeout on retry — mark qa_status for heartbeat visibility
        curl -sf -X POST "${API}/tasks/${TASK_ID}/qa-update" \
            -H 'Content-Type: application/json' \
            -d "{\"qa_status\": \"needs_manual_review\", \"qa_reviewer\": \"smart_retry\", \"qa_output\": \"Retry ${INLINE_RETRY_COUNT} timed out after ${RETRY_TIMEOUT}s (exit 124).\"}" \
            >> "$LOG_FILE" 2>&1 || true
    fi
    rm -f "$TASK_MARKER_FILE" 2>/dev/null || true

    # Check new QA status after retry
    CURRENT_QA_STATUS=$(curl -sf "${API}/tasks/${TASK_ID}" 2>/dev/null | python3 -c "
import json, sys
print(json.load(sys.stdin).get('qa_status', '') or '')
" 2>/dev/null || echo "")

    # Re-evaluate failure mode for next loop iteration
    RETRY_FAILURE_MODE="none"
    if [ "$EXIT_CODE" -eq 124 ]; then
        RETRY_FAILURE_MODE="timeout"
    elif [ "$EXIT_CODE" -ne 0 ]; then
        RETRY_FAILURE_MODE="error"
    elif [ -z "$OUTPUT" ] || [ "${#OUTPUT}" -lt 50 ]; then
        RETRY_FAILURE_MODE="empty_output"
    elif [ "$CURRENT_QA_STATUS" = "rejected" ]; then
        RETRY_FAILURE_MODE="qa_rejected"
    fi

    if [ "$RETRY_FAILURE_MODE" = "none" ]; then
        log "SMART_RETRY: retry ${INLINE_RETRY_COUNT} succeeded — no further retries needed"
    else
        log "SMART_RETRY: retry ${INLINE_RETRY_COUNT} still failing (mode=${RETRY_FAILURE_MODE}) — will retry or escalate"
    fi

done  # end retry while loop

fi  # INLINE_RETRY_ENABLED
# ── End Smart Inline Retry ────────────────────────────────────────────────────

# ── Progress File Cleanup ───────────────────────────────────────────────────
# On success: remove the progress file (task is done, no more retries needed).
# On failure/timeout: leave it so the next retry can resume from where we stopped.
if [ "$EXIT_CODE" -eq 0 ] && [ -f "$PROGRESS_FILE" ]; then
    log "Progress file: cleaning up ${PROGRESS_FILE} (task succeeded)"
    rm -f "$PROGRESS_FILE"
elif [ "$EXIT_CODE" -ne 0 ] && [ -f "$PROGRESS_FILE" ]; then
    log "Progress file: preserving ${PROGRESS_FILE} for retry (exit_code=${EXIT_CODE})"
fi
# Also clean up any stale progress files older than 7 days
find "$WORK_DIR" -maxdepth 1 -name '.otto-progress-*.md' -mtime +7 -delete 2>/dev/null || true
# ── End Progress File Cleanup ──────────────────────────────────────────────

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

# Report completion to kernel
TASK_SUCCESS="true"
[ "$EXIT_CODE" -ne 0 ] && TASK_SUCCESS="false"
curl -sf -X POST "${API}/kernel/agents/task_worker/completed?success=${TASK_SUCCESS}" >> "$LOG_FILE" 2>&1 || \
    log "WARNING: Could not report agent completion to kernel"

# ── WhatsApp Completion Notification ─────────────────────────────────────────
# Sends a concise task result to Mev via WhatsApp.
# Success: "✅ Task completed: {title}\n{one-line summary}"
# Failure: "❌ Task failed: {title}\n{error reason}"
WHATSAPP_SEND="/home/web3relic/otto/tools/whatsapp_send.sh"
if [ -x "$WHATSAPP_SEND" ]; then
    if [ "$EXIT_CODE" -eq 0 ]; then
        # Extract a one-line summary: prefer last non-empty line from output (agent puts summary at end)
        OUTPUT_SUMMARY=$(echo "$OUTPUT" | grep -v '^```' | grep -v '^---' | \
            awk 'NF > 0 { last=$0 } END { print last }' | \
            sed 's/^[#*-]* *//' | cut -c1-150 2>/dev/null || echo "")
        [ -z "$OUTPUT_SUMMARY" ] && OUTPUT_SUMMARY="Task complete"
        WA_MSG="✅ ${TITLE}
${OUTPUT_SUMMARY}"
    else
        # Extract error reason from stderr or output
        ERROR_SUMMARY=$(printf '%s\n%s' "$STDERR" "$OUTPUT" | \
            grep -iE "^(error|fatal|failed|timeout|FATAL|ERROR)" | head -1 | \
            sed 's/^[^ ]* //' | cut -c1-150 2>/dev/null || echo "")
        [ -z "$ERROR_SUMMARY" ] && ERROR_SUMMARY="exit code ${EXIT_CODE} — check logs"
        WA_MSG="❌ ${TITLE}
${ERROR_SUMMARY}"
    fi
    "$WHATSAPP_SEND" "$WA_MSG" >> "$LOG_FILE" 2>&1 && \
        log "WhatsApp completion notification sent" || \
        log "WARNING: WhatsApp notification failed (non-fatal)"
fi
# ── End WhatsApp Completion Notification ──────────────────────────────────────

log "Task runner finished."
