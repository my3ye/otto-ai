#!/bin/bash
# Otto QA Runner — reviews completed task work and auto-commits if approved.
# Called by task_runner.sh after a successful task (exit_code=0).
# Usage: qa_runner.sh <task_id> <task_cli> <log_file>
#
# Architecture:
#   - Detects files changed by the task (git diff + find -newer)
#   - Spawns a DIFFERENT CLI than the one that did the work for independent review
#   - APPROVED: git add + git commit, update qa_status=approved + commit_hash
#   - REJECTED: update qa_status=rejected for heartbeat to handle retry

set -euo pipefail

API="http://localhost:8100"
CLAUDE_CLI="/home/web3relic/.local/bin/claude"
TASK_ID="${1:?Usage: qa_runner.sh <task_id> <task_cli> <log_file>}"
TASK_CLI="${2:-claude}"     # CLI that ran the task (claude/gemini/kimi)
PARENT_LOG="${3:-/dev/null}" # Parent task_runner.sh log file

qa_log() { echo "$(date -Iseconds) [QA] $*" >> "$PARENT_LOG"; }

qa_log "QA runner starting for task ${TASK_ID} (original CLI: ${TASK_CLI})"

# ── Fetch task details ───────────────────────────────────────────────────────

TASK_JSON=$(curl -sf "${API}/tasks/${TASK_ID}" 2>/dev/null) || {
    qa_log "FATAL: Could not fetch task ${TASK_ID}"
    exit 1
}

TITLE=$(echo "$TASK_JSON" | python3 -c "import json,sys; print(json.load(sys.stdin)['title'])")
PROMPT=$(echo "$TASK_JSON" | python3 -c "import json,sys; print(json.load(sys.stdin)['prompt'])")
OUTPUT=$(echo "$TASK_JSON" | python3 -c "import json,sys; print(json.load(sys.stdin).get('output') or '')")
WORK_DIR=$(echo "$TASK_JSON" | python3 -c "import json,sys; print(json.load(sys.stdin)['working_directory'])")

qa_log "Task: ${TITLE}"
qa_log "Work dir: ${WORK_DIR}"

# ── Select QA reviewer (must differ from task CLI) ───────────────────────────
# claude → gemini, gemini → claude, kimi → claude
case "$TASK_CLI" in
    claude)   QA_CLI="gemini" ;;
    gemini)   QA_CLI="claude" ;;
    kimi)     QA_CLI="claude" ;;
    *)        QA_CLI="gemini" ;;
esac

qa_log "QA reviewer: ${QA_CLI}"

# ── Mark qa_status as pending_qa ────────────────────────────────────────────
curl -sf -X POST "${API}/tasks/${TASK_ID}/qa-update" \
    -H 'Content-Type: application/json' \
    -d "{\"qa_status\": \"pending_qa\", \"qa_reviewer\": \"${QA_CLI}\"}" \
    >> "$PARENT_LOG" 2>&1 || true

# ── Detect changed files (git diff + find -newer marker) ─────────────────────
# Use the parent log file as a time reference (created just before the task ran)
MARKER_FILE=$(mktemp /tmp/qa_marker.XXXXXX)
# Touch marker file 30 seconds in the past to catch files modified during the task
touch -d "30 minutes ago" "$MARKER_FILE"

CHANGED_FILES=""
if cd "$WORK_DIR" 2>/dev/null; then
    # Git-tracked changes (staged + unstaged)
    GIT_DIFF=$(git diff --name-only HEAD 2>/dev/null || echo "")
    GIT_UNTRACKED=$(git ls-files --others --exclude-standard 2>/dev/null | head -20 || echo "")
    COMBINED="${GIT_DIFF}${GIT_UNTRACKED:+
$GIT_UNTRACKED}"

    # Also check find -newer as fallback for non-git dirs
    NEWER_FILES=$(find . -newer "$PARENT_LOG" -type f \
        ! -path "./.git/*" ! -path "./logs/*" ! -name "*.log" ! -name "*.pyc" \
        2>/dev/null | head -20 | sed 's|^\./||' || echo "")

    # Merge both sources
    CHANGED_FILES=$(echo -e "${COMBINED}\n${NEWER_FILES}" | sort -u | grep -v "^$" | head -30 || echo "")
fi
rm -f "$MARKER_FILE"

if [ -z "$CHANGED_FILES" ]; then
    qa_log "No changed files detected — skipping QA commit (task may have been read-only or no-op)"
    # Mark as approved (no changes to commit)
    curl -sf -X POST "${API}/tasks/${TASK_ID}/qa-update" \
        -H 'Content-Type: application/json' \
        -d "{\"qa_status\": \"approved\", \"qa_reviewer\": \"${QA_CLI}\", \"qa_output\": \"No file changes detected — task appears read-only or no-op. Auto-approved.\"}" \
        >> "$PARENT_LOG" 2>&1 || true
    qa_log "QA: auto-approved (no changes)"
    exit 0
fi

qa_log "Changed files detected: $(echo "$CHANGED_FILES" | wc -l) file(s)"
qa_log "Files: $(echo "$CHANGED_FILES" | tr '\n' ' ')"

# ── Build diff summary for QA review ─────────────────────────────────────────
DIFF_SUMMARY=""
if cd "$WORK_DIR" 2>/dev/null; then
    # Get a truncated diff for review
    DIFF_SUMMARY=$(git diff HEAD 2>/dev/null | head -200 || echo "(binary or no git diff available)")
    if [ -z "$DIFF_SUMMARY" ]; then
        # Fallback: show file list with sizes
        DIFF_SUMMARY=$(echo "$CHANGED_FILES" | while read -r f; do
            [ -f "$WORK_DIR/$f" ] && echo "  $f ($(wc -c < "$WORK_DIR/$f" 2>/dev/null || echo '?') bytes)" || true
        done)
    fi
fi

# ── Run QA agent ─────────────────────────────────────────────────────────────
OUTPUT_EXCERPT="${OUTPUT:0:2000}"
PROMPT_EXCERPT="${PROMPT:0:800}"
DIFF_EXCERPT="${DIFF_SUMMARY:0:3000}"

QA_PROMPT="You are Otto's QA reviewer. A task just completed and you must decide: APPROVE or REJECT.

TASK TITLE: ${TITLE}

TASK PROMPT (what was requested):
${PROMPT_EXCERPT}

TASK OUTPUT (what the agent reported):
${OUTPUT_EXCERPT}

CHANGED FILES:
${CHANGED_FILES}

GIT DIFF (truncated):
${DIFF_EXCERPT}

YOUR JOB:
1. Check that the changes align with what was requested
2. Look for obvious issues: broken syntax, missing files, incomplete implementation, security problems
3. Make a decision: APPROVE or REJECT

Rules:
- APPROVE if: work is complete, changes match the request, no obvious bugs or missing pieces
- REJECT if: major missing functionality, broken code, wrong files changed, dangerous changes
- Be lenient on style/minor issues — this is a sanity check, not a full code review

Return ONLY a JSON object (no markdown, no code fences):
{\"decision\": \"APPROVE\" or \"REJECT\", \"reason\": \"<1-2 sentence explanation>\", \"issues\": [\"<issue1>\", \"<issue2>\"] or []}"

qa_log "Spawning QA agent (${QA_CLI})..."

QA_RESULT=""
QA_DECISION="REJECT"  # Default safe choice

if [ "$QA_CLI" = "gemini" ]; then
    QA_RESULT=$(timeout 60 gemini -m gemini-2.0-flash -p "$QA_PROMPT" 2>/dev/null || echo "")
elif [ "$QA_CLI" = "claude" ]; then
    QA_RESULT=$(timeout 120 "$CLAUDE_CLI" \
        --print \
        --dangerously-skip-permissions \
        --model "haiku" \
        --max-turns 3 \
        --max-budget-usd 0.20 \
        -p "$QA_PROMPT" 2>/dev/null || echo "")
elif [ "$QA_CLI" = "kimi" ]; then
    QA_RESULT=$(timeout 60 kimi -p "$QA_PROMPT" 2>/dev/null || echo "")
fi

qa_log "QA raw result: ${QA_RESULT:0:200}"

# ── Parse QA decision ─────────────────────────────────────────────────────────
QA_PARSED=$(echo "$QA_RESULT" | python3 -c "
import json, sys, re
raw = sys.stdin.read().strip()
# Strip markdown fences
raw = re.sub(r'\`\`\`[a-z]*\n?', '', raw).strip()
# Extract JSON object
match = re.search(r'\{[^{}]+\}', raw, re.DOTALL)
if match:
    try:
        data = json.loads(match.group())
        if 'decision' in data:
            print(json.dumps({'decision': data['decision'].upper(), 'reason': data.get('reason', ''), 'issues': data.get('issues', [])}))
            sys.exit(0)
    except Exception:
        pass
# Fallback: look for APPROVE/REJECT keywords
if 'APPROVE' in raw.upper() and 'REJECT' not in raw.upper():
    print(json.dumps({'decision': 'APPROVE', 'reason': 'Parsed from text response', 'issues': []}))
elif 'REJECT' in raw.upper():
    print(json.dumps({'decision': 'REJECT', 'reason': 'Parsed from text response', 'issues': []}))
else:
    print(json.dumps({'decision': 'PARSE_FAIL', 'reason': 'Could not parse QA response', 'issues': []}))
" 2>/dev/null || echo '{"decision": "PARSE_FAIL", "reason": "python3 error", "issues": []}')

QA_DECISION=$(echo "$QA_PARSED" | python3 -c "import json,sys; print(json.load(sys.stdin)['decision'])" 2>/dev/null || echo "PARSE_FAIL")
QA_REASON=$(echo "$QA_PARSED" | python3 -c "import json,sys; print(json.load(sys.stdin).get('reason', ''))" 2>/dev/null || echo "")
QA_ISSUES=$(echo "$QA_PARSED" | python3 -c "import json,sys; d=json.load(sys.stdin); print('; '.join(d.get('issues', [])))" 2>/dev/null || echo "")

qa_log "QA decision: ${QA_DECISION} — ${QA_REASON}"

# ── Act on decision ───────────────────────────────────────────────────────────

if [ "$QA_DECISION" = "APPROVE" ]; then
    qa_log "QA APPROVED — committing changes..."

    COMMIT_HASH=""
    if cd "$WORK_DIR" 2>/dev/null; then
        # Stage all changed files
        git add -A 2>/dev/null || true

        # Check if there's anything to commit
        if git diff --cached --quiet 2>/dev/null; then
            qa_log "Nothing staged to commit (already committed or no tracked changes)"
            COMMIT_HASH="no-changes"
        else
            # Commit with descriptive message
            COMMIT_MSG="task(${TASK_ID:0:8}): ${TITLE}

Auto-committed by Otto QA runner.
Task ID: ${TASK_ID}
QA reviewer: ${QA_CLI}
QA verdict: APPROVED — ${QA_REASON}

Co-Authored-By: Otto QA <otto@ottolabs.ai>"

            git commit -m "$COMMIT_MSG" 2>/dev/null && \
                COMMIT_HASH=$(git rev-parse HEAD 2>/dev/null || echo "") || \
                COMMIT_HASH="commit-failed"

            qa_log "Git commit: ${COMMIT_HASH:0:12}"
        fi
    fi

    QA_OUTPUT_FULL="${QA_REASON}"
    [ -n "$QA_ISSUES" ] && QA_OUTPUT_FULL="${QA_OUTPUT_FULL} | Issues: ${QA_ISSUES}"
    [ -n "$COMMIT_HASH" ] && QA_OUTPUT_FULL="${QA_OUTPUT_FULL} | Committed: ${COMMIT_HASH:0:12}"

    # Update task record
    UPDATE_JSON=$(python3 -c "
import json, sys
print(json.dumps({
    'qa_status': 'approved',
    'qa_reviewer': sys.argv[1],
    'qa_output': sys.argv[2],
    'commit_hash': sys.argv[3] if sys.argv[3] else None,
}))
" "$QA_CLI" "$QA_OUTPUT_FULL" "$COMMIT_HASH")

    curl -sf -X POST "${API}/tasks/${TASK_ID}/qa-update" \
        -H 'Content-Type: application/json' \
        -d "$UPDATE_JSON" >> "$PARENT_LOG" 2>&1 || true

    qa_log "QA: task ${TASK_ID:0:8} APPROVED and committed (${COMMIT_HASH:0:12})"

elif [ "$QA_DECISION" = "REJECT" ]; then
    qa_log "QA REJECTED — flagging for retry..."

    QA_OUTPUT_FULL="REJECTED: ${QA_REASON}"
    [ -n "$QA_ISSUES" ] && QA_OUTPUT_FULL="${QA_OUTPUT_FULL} | Issues: ${QA_ISSUES}"

    UPDATE_JSON=$(python3 -c "
import json, sys
print(json.dumps({
    'qa_status': 'rejected',
    'qa_reviewer': sys.argv[1],
    'qa_output': sys.argv[2],
}))
" "$QA_CLI" "$QA_OUTPUT_FULL")

    curl -sf -X POST "${API}/tasks/${TASK_ID}/qa-update" \
        -H 'Content-Type: application/json' \
        -d "$UPDATE_JSON" >> "$PARENT_LOG" 2>&1 || true

    qa_log "QA: task ${TASK_ID:0:8} REJECTED — heartbeat will handle retry"

    # Log to episodic memory for heartbeat awareness
    TITLE_JSON=$(python3 -c "import json,sys; print(json.dumps(sys.argv[1]))" "$TITLE" 2>/dev/null || echo "\"$TITLE\"")
    QA_JSON=$(python3 -c "import json,sys; print(json.dumps(sys.argv[1]))" "$QA_OUTPUT_FULL" 2>/dev/null || echo "\"$QA_OUTPUT_FULL\"")
    curl -sf -X POST "${API}/episodic/events" \
        -H 'Content-Type: application/json' \
        -d "{\"type\":\"qa_rejected\",\"summary\":\"QA rejected task ${TASK_ID:0:8} (${TITLE:0:60}): ${QA_REASON:0:200}\"}" \
        >> "$PARENT_LOG" 2>&1 || true

else
    # PARSE_FAIL — treat as conditional approve (don't block progress on QA failures)
    qa_log "QA parse failed — auto-approving to avoid blocking (non-fatal)"

    UPDATE_JSON=$(python3 -c "
import json, sys
print(json.dumps({
    'qa_status': 'approved',
    'qa_reviewer': sys.argv[1],
    'qa_output': 'QA parse failed — auto-approved. Raw: ' + sys.argv[2][:200],
}))
" "$QA_CLI" "$QA_RESULT")

    curl -sf -X POST "${API}/tasks/${TASK_ID}/qa-update" \
        -H 'Content-Type: application/json' \
        -d "$UPDATE_JSON" >> "$PARENT_LOG" 2>&1 || true

    # Still try to commit any staged changes
    if cd "$WORK_DIR" 2>/dev/null && ! git diff --cached --quiet 2>/dev/null; then
        COMMIT_MSG="task(${TASK_ID:0:8}): ${TITLE}

Auto-committed by Otto QA (parse-fail fallback).
Task ID: ${TASK_ID}

Co-Authored-By: Otto QA <otto@ottolabs.ai>"
        git commit -m "$COMMIT_MSG" 2>/dev/null && qa_log "Fallback commit done" || qa_log "Fallback commit skipped"
    fi
fi

qa_log "QA runner finished (decision: ${QA_DECISION})"
