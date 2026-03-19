#!/bin/bash
# Otto Model Runner
# Primary: Ollama (Otto's own model)
# Fallback: Claude Sonnet via Claude Code CLI
#
# Usage:
#   ./otto_runner.sh "Your prompt here"
#   ./otto_runner.sh --agent heartbeat "Run your heartbeat..."
#   echo "prompt" | ./otto_runner.sh --stdin
#
# Environment:
#   OTTO_MODEL        : Ollama model name (default: otto:v1)
#   OTTO_OLLAMA_PORT  : Ollama API port (default: 11434)
#   OTTO_FALLBACK     : Fallback CLI (default: claude)
#   OTTO_TIMEOUT      : Ollama timeout seconds (default: 120)

set -euo pipefail

# ── Config ────────────────────────────────────────────────────────────
OTTO_MODEL="${OTTO_MODEL:-otto:v1}"
OLLAMA_PORT="${OTTO_OLLAMA_PORT:-11434}"
OLLAMA_URL="http://localhost:${OLLAMA_PORT}"
FALLBACK_CLI="${OTTO_FALLBACK:-claude}"
TIMEOUT="${OTTO_TIMEOUT:-120}"
OTTO_DIR="/home/web3relic/otto"

# ── Parse args ────────────────────────────────────────────────────────
AGENT=""
USE_STDIN=false
PROMPT=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --agent)
            AGENT="$2"
            shift 2
            ;;
        --stdin)
            USE_STDIN=true
            shift
            ;;
        *)
            PROMPT="$1"
            shift
            ;;
    esac
done

if $USE_STDIN; then
    PROMPT=$(cat)
fi

if [ -z "$PROMPT" ]; then
    echo "ERROR: No prompt provided" >&2
    echo "Usage: otto_runner.sh \"prompt\" | otto_runner.sh --stdin" >&2
    exit 1
fi

# ── Try Ollama first ──────────────────────────────────────────────────
use_ollama() {
    # Check if Ollama is running
    if ! curl -sf "${OLLAMA_URL}/api/tags" > /dev/null 2>&1; then
        return 1
    fi

    # Check if our model exists
    if ! curl -sf "${OLLAMA_URL}/api/tags" | python3 -c "
import sys, json
tags = json.load(sys.stdin)
models = [m['name'] for m in tags.get('models', [])]
if '${OTTO_MODEL}' not in models and '${OTTO_MODEL}:latest' not in models:
    sys.exit(1)
" 2>/dev/null; then
        return 1
    fi

    return 0
}

if use_ollama; then
    # Run via Ollama API
    RESPONSE=$(timeout "${TIMEOUT}s" curl -sf "${OLLAMA_URL}/api/generate" \
        -d "$(python3 -c "
import json, sys
print(json.dumps({
    'model': '${OTTO_MODEL}',
    'prompt': '''${PROMPT//\'/\'\\\'\'}''',
    'stream': False,
    'options': {
        'temperature': 0.7,
        'top_p': 0.9,
        'num_predict': 4096,
    }
}))
")" 2>/dev/null)

    if [ $? -eq 0 ] && [ -n "$RESPONSE" ]; then
        echo "$RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('response', ''))" 2>/dev/null
        exit 0
    fi

    echo "WARNING: Ollama request failed, falling back to ${FALLBACK_CLI}" >&2
fi

# ── Fallback: Claude Sonnet ───────────────────────────────────────────
echo "Using fallback: ${FALLBACK_CLI}" >&2

FALLBACK_ARGS=(
    --print
    --model sonnet
    --dangerously-skip-permissions
)

if [ -n "$AGENT" ]; then
    FALLBACK_ARGS+=(--agent "$AGENT")
fi

cd "$OTTO_DIR"
/home/web3relic/.local/bin/${FALLBACK_CLI} \
    "${FALLBACK_ARGS[@]}" \
    -p "$PROMPT"
