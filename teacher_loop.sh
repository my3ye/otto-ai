#!/bin/bash
# Otto Teacher Loop (Kalyanamitta)
# Runs after each heartbeat to send decisions to Opus for feedback.
#
# Flow:
#   1. Read the latest reasoning_chain entry
#   2. Build context from system state
#   3. Send to Claude Opus for Abhidharma-structured evaluation
#   4. Parse root condition + mental factor scores
#   5. Store in rl2f_feedback table via Memory API
#
# Usage:
#   ./teacher_loop.sh                    # evaluate latest cycle
#   ./teacher_loop.sh --heartbeat-type orchestrator
#   ./teacher_loop.sh --dry-run         # show what would be sent, don't call Opus
#
# Requires:
#   ANTHROPIC_API_KEY in environment or ~/memory/.env
#
# Cost: ~$0.05 per evaluation (Opus API)

set -euo pipefail

OTTO_DIR="/home/web3relic/otto"
MEMORY_API="http://localhost:8100"
LOG_DIR="${OTTO_DIR}/logs"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="${LOG_DIR}/teacher-${TIMESTAMP}.log"

HEARTBEAT_TYPE="${1:-orchestrator}"
DRY_RUN=false

# Parse args
while [[ $# -gt 0 ]]; do
    case $1 in
        --heartbeat-type)
            HEARTBEAT_TYPE="$2"
            shift 2
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        *)
            shift
            ;;
    esac
done

mkdir -p "$LOG_DIR"

log() {
    echo "$(date -Iseconds) $1" | tee -a "$LOG_FILE"
}

# ── Load API key ──────────────────────────────────────────────────────
if [ -z "${ANTHROPIC_API_KEY:-}" ]; then
    if [ -f "/home/web3relic/memory/.env" ]; then
        ANTHROPIC_API_KEY=$(grep "^ANTHROPIC_API_KEY=" /home/web3relic/memory/.env | cut -d= -f2)
        export ANTHROPIC_API_KEY
    fi
fi

if [ -z "${ANTHROPIC_API_KEY:-}" ]; then
    log "ERROR: ANTHROPIC_API_KEY not set. Add to ~/memory/.env or export."
    exit 1
fi

log "Teacher loop starting (heartbeat_type: ${HEARTBEAT_TYPE})"

# ── 1. Get latest reasoning chain entry ───────────────────────────────
REASONING_JSON=$(curl -sf "${MEMORY_API}/reasoning/recent?limit=1&heartbeat_type=${HEARTBEAT_TYPE}" 2>/dev/null)
if [ -z "$REASONING_JSON" ] || [ "$REASONING_JSON" = "[]" ]; then
    log "No recent reasoning chain entry found. Nothing to evaluate."
    exit 0
fi

# Extract fields
CYCLE_TS=$(echo "$REASONING_JSON" | python3 -c "import sys, json; r=json.load(sys.stdin); print(r[0]['cycle_ts'] if r else '')" 2>/dev/null)
REASONING=$(echo "$REASONING_JSON" | python3 -c "import sys, json; r=json.load(sys.stdin); print(r[0].get('reasoning','') if r else '')" 2>/dev/null)
DECISIONS=$(echo "$REASONING_JSON" | python3 -c "import sys, json; r=json.load(sys.stdin); print(r[0].get('decisions','') if r else '')" 2>/dev/null)
EXPECTED=$(echo "$REASONING_JSON" | python3 -c "import sys, json; r=json.load(sys.stdin); print(r[0].get('expected','') if r else '')" 2>/dev/null)
ACTUAL=$(echo "$REASONING_JSON" | python3 -c "import sys, json; r=json.load(sys.stdin); print(r[0].get('actual','') if r else '')" 2>/dev/null)
OUTCOME_MATCH=$(echo "$REASONING_JSON" | python3 -c "import sys, json; r=json.load(sys.stdin); print(r[0].get('outcome_match','pending') if r else 'pending')" 2>/dev/null)

if [ -z "$DECISIONS" ] || [ ${#DECISIONS} -lt 20 ]; then
    log "Decision too short to evaluate. Skipping."
    exit 0
fi

# Check if we already have feedback for this cycle
EXISTING=$(curl -sf "${MEMORY_API}/rl2f/recent?limit=5&heartbeat_type=${HEARTBEAT_TYPE}" 2>/dev/null)
ALREADY_DONE=$(echo "$EXISTING" | python3 -c "
import sys, json
entries = json.load(sys.stdin)
ts = '${CYCLE_TS}'
for e in entries:
    if e.get('cycle_ts','')[:19] == ts[:19]:
        print('yes')
        sys.exit(0)
print('no')
" 2>/dev/null)

if [ "$ALREADY_DONE" = "yes" ]; then
    log "Already evaluated cycle ${CYCLE_TS}. Skipping."
    exit 0
fi

log "Evaluating cycle: ${CYCLE_TS}"
log "Decision length: ${#DECISIONS} chars"

# ── 2. Build Opus prompt ─────────────────────────────────────────────
# Use Python to safely JSON-encode the prompt
OPUS_PAYLOAD=$(python3 << 'PYEOF'
import json, os

reasoning = os.environ.get("REASONING", "")[:2000]
decisions = os.environ.get("DECISIONS", "")[:2000]
expected = os.environ.get("EXPECTED", "(none)")[:1000]
actual = os.environ.get("ACTUAL", "(none)")[:1000]
outcome_match = os.environ.get("OUTCOME_MATCH", "pending")
cycle_ts = os.environ.get("CYCLE_TS", "")
hb_type = os.environ.get("HEARTBEAT_TYPE", "orchestrator")

system_msg = """You are the kalyanamitta (spiritual friend / teacher) for an AI orchestrator called Otto.

Otto runs hourly heartbeat cycles — observing system state, making decisions, creating/launching tasks, and messaging its human partner Mev. Evaluate this cycle using the Abhidharma framework."""

user_msg = f"""Evaluate Otto's decision-making in this heartbeat cycle.

CYCLE: {cycle_ts} ({hb_type})

REASONING:
{reasoning}

DECISIONS:
{decisions}

EXPECTED OUTCOME: {expected}
ACTUAL OUTCOME: {actual}
OUTCOME MATCH: {outcome_match}

---

Provide your evaluation in this structure:

## ROOT CONDITION ANALYSIS
Score each (0.0-1.0):
- lobha_score: [greed/vanity metrics]
- dosa_score: [aversion/avoidance]
- moha_score: [delusion/stale assumptions]
- alobha_score: [genuine mission service]
- adosa_score: [facing difficulty directly]
- amoha_score: [clear seeing/wisdom]

## MENTAL FACTOR ASSESSMENT
Score each (0.0-1.0):
- sati_score: [mindfulness — aware vs autopilot]
- panna_score: [wisdom — root causes vs symptoms]
- viriya_score: [energy — effort calibration]
- upekkha_score: [equanimity — balance]
- ekaggata_score: [focus — directed vs scattered]

## PRACTICAL EVALUATION
1. Was priority reasoning correct?
2. Were task prompts well-scoped?
3. Did Otto anticipate or only react?
4. What would you have done differently?

Be specific and honest."""

payload = {
    "model": "claude-opus-4-20250514",
    "max_tokens": 1500,
    "system": system_msg,
    "messages": [{"role": "user", "content": user_msg}],
}

print(json.dumps(payload))
PYEOF
)

if $DRY_RUN; then
    log "DRY RUN — would send to Opus:"
    echo "$OPUS_PAYLOAD" | python3 -m json.tool >> "$LOG_FILE"
    exit 0
fi

# ── 3. Call Opus ──────────────────────────────────────────────────────
export REASONING DECISIONS EXPECTED ACTUAL OUTCOME_MATCH CYCLE_TS HEARTBEAT_TYPE

log "Calling Opus API..."
OPUS_RESPONSE=$(curl -sf https://api.anthropic.com/v1/messages \
    -H "x-api-key: ${ANTHROPIC_API_KEY}" \
    -H "anthropic-version: 2023-06-01" \
    -H "content-type: application/json" \
    -d "$OPUS_PAYLOAD" \
    --max-time 120 2>/dev/null)

if [ -z "$OPUS_RESPONSE" ]; then
    log "ERROR: Opus API returned empty response"
    exit 1
fi

FEEDBACK=$(echo "$OPUS_RESPONSE" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d['content'][0]['text'])" 2>/dev/null)

if [ -z "$FEEDBACK" ]; then
    log "ERROR: Could not parse Opus response"
    echo "$OPUS_RESPONSE" >> "$LOG_FILE"
    exit 1
fi

log "Received feedback (${#FEEDBACK} chars)"

# ── 4. Parse scores ──────────────────────────────────────────────────
SCORES=$(python3 << PYEOF
import json, re

feedback = """${FEEDBACK//\"/\\\"}"""

root_conditions = {}
for key in ["lobha_score", "dosa_score", "moha_score", "alobha_score", "adosa_score", "amoha_score"]:
    match = re.search(rf"{key}:\s*(\d+\.?\d*)", feedback)
    if match:
        root_conditions[key] = min(1.0, max(0.0, float(match.group(1))))

mental_factors = {}
for key in ["sati_score", "panna_score", "viriya_score", "upekkha_score", "ekaggata_score"]:
    match = re.search(rf"{key}:\s*(\d+\.?\d*)", feedback)
    if match:
        name = key.replace("_score", "")
        mental_factors[name] = min(1.0, max(0.0, float(match.group(1))))

print(json.dumps({"root": root_conditions, "mental": mental_factors}))
PYEOF
)

ROOT_JSON=$(echo "$SCORES" | python3 -c "import sys, json; print(json.dumps(json.load(sys.stdin)['root']))" 2>/dev/null)
MENTAL_JSON=$(echo "$SCORES" | python3 -c "import sys, json; print(json.dumps(json.load(sys.stdin)['mental']))" 2>/dev/null)

log "Root conditions: ${ROOT_JSON}"
log "Mental factors: ${MENTAL_JSON}"

# ── 5. Store in RL2F table ────────────────────────────────────────────
STORE_PAYLOAD=$(python3 -c "
import json
print(json.dumps({
    'cycle_ts': '${CYCLE_TS}',
    'heartbeat_type': '${HEARTBEAT_TYPE}',
    'system_state': '',
    'decision': '''${DECISIONS//\'/\'\\\'\'}'''[:5000],
    'teacher_feedback': '''${FEEDBACK//\'/\'\\\'\'}'''[:5000],
    'root_condition_analysis': ${ROOT_JSON:-null},
    'mental_factor_scores': ${MENTAL_JSON:-null},
    'outcome': '''${ACTUAL//\'/\'\\\'\'}'''[:2000] or None,
    'outcome_match': '${OUTCOME_MATCH}' if '${OUTCOME_MATCH}' != 'pending' else None,
}))
" 2>/dev/null)

STORE_RESULT=$(curl -sf "${MEMORY_API}/rl2f" \
    -H "content-type: application/json" \
    -d "$STORE_PAYLOAD" 2>/dev/null)

if [ -n "$STORE_RESULT" ]; then
    ENTRY_ID=$(echo "$STORE_RESULT" | python3 -c "import sys, json; print(json.load(sys.stdin).get('id',''))" 2>/dev/null)
    log "Stored feedback as: ${ENTRY_ID}"
else
    log "WARNING: Failed to store feedback in API"
fi

log "Teacher loop complete."
