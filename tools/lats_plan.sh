#!/bin/bash
# Otto LATS Planner — calls POST /tasks/plan to get the best approach for a goal.
#
# Usage:
#   lats_plan.sh --goal "..." [--priority <1-10>] [--context "..."] [--n <2-5>]
#
# Output (stdout): JSON with keys:
#   selected_title    — short name of the best approach
#   selected_prompt   — full task prompt to use
#   selected_score    — composite score (0-1)
#   fallback_prompt   — next-best approach prompt (for task metadata)
#   all_approaches    — full JSON array from LATS
#
# Exit codes: 0=success, 1=error (check stderr)
#
# The heartbeat uses this to fill in task.prompt before POST /tasks.
# Store all_approaches in task metadata.lats_plan for retry fallback.

set -euo pipefail

API="http://localhost:8100"

GOAL=""
PRIORITY=5
CONTEXT=""
N_APPROACHES=3

# Parse arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --goal)      GOAL="$2";       shift 2 ;;
        --priority)  PRIORITY="$2";   shift 2 ;;
        --context)   CONTEXT="$2";    shift 2 ;;
        --n)         N_APPROACHES="$2"; shift 2 ;;
        *) echo "Unknown arg: $1" >&2; exit 1 ;;
    esac
done

if [ -z "$GOAL" ]; then
    echo "Error: --goal is required" >&2
    exit 1
fi

# Build request JSON safely using python3
REQUEST_JSON=$(python3 -c "
import json, sys
print(json.dumps({
    'goal': sys.argv[1],
    'priority': int(sys.argv[2]),
    'context': sys.argv[3],
    'n_approaches': int(sys.argv[4]),
}))
" "$GOAL" "$PRIORITY" "$CONTEXT" "$N_APPROACHES")

# Call LATS endpoint
RESPONSE=$(curl -sf -X POST "${API}/tasks/plan" \
    -H 'Content-Type: application/json' \
    -d "$REQUEST_JSON" 2>/dev/null) || {
    echo "Error: POST /tasks/plan failed — LATS endpoint unavailable" >&2
    exit 1
}

# Parse and reformat output
python3 -c "
import json, sys

data = json.loads(sys.argv[1])
approaches = data.get('approaches', [])
selected_idx = data.get('selected_index', 0)

if not approaches:
    print(json.dumps({'error': 'No approaches returned'}))
    sys.exit(1)

selected = approaches[selected_idx]
fallback_idx = None
fallback_prompt = None

# Find next-best approach for fallback
sorted_others = sorted(
    [(i, a) for i, a in enumerate(approaches) if i != selected_idx],
    key=lambda x: x[1].get('composite_score', 0),
    reverse=True
)
if sorted_others:
    fallback_idx, fallback = sorted_others[0]
    fallback_prompt = fallback.get('prompt', '')

result = {
    'selected_title':  selected.get('title', ''),
    'selected_prompt': selected.get('prompt', ''),
    'selected_score':  selected.get('composite_score', 0),
    'selected_reasoning': selected.get('reasoning', ''),
    'failure_fallback': selected.get('failure_fallback'),
    'fallback_prompt': fallback_prompt,
    'fallback_title':  sorted_others[0][1].get('title', '') if sorted_others else None,
    'n_approaches':    len(approaches),
    'all_approaches':  approaches,
}
print(json.dumps(result))
" "$RESPONSE" 2>/dev/null || {
    echo "Error: Failed to parse LATS response" >&2
    exit 1
}
