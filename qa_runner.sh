#!/bin/bash
# Otto QA Runner — reviews completed task work and auto-commits if approved.
# Called by task_runner.sh after a successful task (exit_code=0).
# Usage: qa_runner.sh <task_id> <task_cli> <log_file> [marker_file]
#
# Architecture:
#   - Detects files changed by THIS task using per-task marker file (isolation fix)
#   - Only diffs/stages the specific files changed during this task's execution window
#   - Handles untracked files (e.g. projects/) by showing content instead of git diff
#   - Spawns a DIFFERENT CLI than the one that did the work for independent review
#   - APPROVED: git add (task-scoped) + git commit, update qa_status=approved + commit_hash
#   - REJECTED: update qa_status=rejected for heartbeat to handle retry
#
# Isolation fix (2026-02-22): replaced `git diff HEAD` + `touch -d "30 minutes ago"`
# with per-task marker file passed from task_runner.sh. The marker is created JUST
# BEFORE the CLI runs, so find -newer only captures this task's changes.

set -euo pipefail

API="http://localhost:8100"
CLAUDE_CLI="/home/web3relic/.local/bin/claude"
TASK_ID="${1:?Usage: qa_runner.sh <task_id> <task_cli> <log_file> [marker_file]}"
TASK_CLI="${2:-claude}"          # CLI that ran the task (claude/gemini/kimi)
PARENT_LOG="${3:-/dev/null}"     # Parent task_runner.sh log file
TASK_MARKER_FILE="${4:-}"        # Timestamp marker created just before the CLI ran

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

# ── Detect changed files (task-scoped via marker + git) ──────────────────────
# ISOLATION FIX: Use the per-task marker file created JUST BEFORE the CLI ran.
# This isolates changes made by THIS task only, ignoring concurrent task changes.
# Fallback: use parent log file (less precise) or a 5-minute window.

REFERENCE_FILE=""
if [ -n "$TASK_MARKER_FILE" ] && [ -f "$TASK_MARKER_FILE" ]; then
    REFERENCE_FILE="$TASK_MARKER_FILE"
    qa_log "Using per-task marker file for change isolation: ${TASK_MARKER_FILE}"
elif [ -f "$PARENT_LOG" ]; then
    REFERENCE_FILE="$PARENT_LOG"
    qa_log "WARNING: No task marker file — using parent log as reference (less precise)"
else
    REFERENCE_FILE=$(mktemp /tmp/qa_fallback_marker.XXXXXX)
    touch -d "5 minutes ago" "$REFERENCE_FILE"
    qa_log "WARNING: No marker/log reference — using 5-minute window (least precise)"
fi

CHANGED_FILES=""
UNTRACKED_NEW_FILES=""  # Files under untracked dirs (e.g. projects/)

if cd "$WORK_DIR" 2>/dev/null; then
    # Primary: find files modified AFTER the marker was created (task-scoped)
    # This correctly ignores changes from other concurrently running tasks.
    NEWER_FILES=$(find . -newer "$REFERENCE_FILE" -type f \
        ! -path "./.git/*" ! -path "./logs/*" ! -name "*.log" ! -name "*.pyc" \
        ! -name "*.tmp" ! -path "./logs/tasks/*" \
        2>/dev/null | sed 's|^\./||' | sort | head -50 || echo "")

    # Secondary: git-tracked unstaged changes (belt + suspenders)
    # Filtered to only files that also appear in our find results
    GIT_MODIFIED=$(git diff --name-only HEAD 2>/dev/null || echo "")

    # Combine: use find results as primary (task-scoped), git as hint
    CHANGED_FILES=$(echo -e "${NEWER_FILES}" | grep -v "^$" | head -40 || echo "")

    # Separate out files that are under untracked directories (won't appear in git diff)
    # These need special handling — we'll show their content instead of a diff
    if [ -n "$CHANGED_FILES" ]; then
        while IFS= read -r f; do
            [ -z "$f" ] && continue
            if git ls-files --error-unmatch "$f" 2>/dev/null; then
                : # tracked — will appear in git diff
            else
                UNTRACKED_NEW_FILES="${UNTRACKED_NEW_FILES}${f}
"
            fi
        done <<< "$CHANGED_FILES"
    fi
fi

# Cleanup fallback marker if we created one
if [ -z "$TASK_MARKER_FILE" ] || [ ! -f "${TASK_MARKER_FILE:-/nonexistent}" ]; then
    rm -f "$REFERENCE_FILE" 2>/dev/null || true
fi

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
# ISOLATION FIX: Only diff the specific files changed during this task.
# Do NOT use `git diff HEAD` (shows ALL uncommitted changes from ALL tasks).
DIFF_SUMMARY=""

if cd "$WORK_DIR" 2>/dev/null; then
    DIFF_PARTS=""

    # Part 1: git diff for tracked files that were modified during this task
    if [ -n "$CHANGED_FILES" ]; then
        # Build list of git-tracked files from our task-scoped set
        TRACKED_CHANGED=$(echo "$CHANGED_FILES" | while IFS= read -r f; do
            [ -z "$f" ] && continue
            git ls-files --error-unmatch "$f" 2>/dev/null && echo "$f" || true
        done | head -20)

        if [ -n "$TRACKED_CHANGED" ]; then
            # Diff only these specific files (not the whole tree)
            DIFF_PARTS=$(echo "$TRACKED_CHANGED" | xargs git diff HEAD -- 2>/dev/null | head -300 || echo "")
        fi
    fi

    # Part 2: content excerpts of new untracked files (e.g. projects/ files)
    UNTRACKED_CONTENT=""
    if [ -n "$UNTRACKED_NEW_FILES" ]; then
        while IFS= read -r f; do
            [ -z "$f" ] && continue
            FULL_PATH="${WORK_DIR}/${f}"
            if [ -f "$FULL_PATH" ]; then
                FILE_SIZE=$(wc -c < "$FULL_PATH" 2>/dev/null || echo "?")
                FILE_LINES=$(wc -l < "$FULL_PATH" 2>/dev/null || echo "?")
                UNTRACKED_CONTENT="${UNTRACKED_CONTENT}
=== NEW FILE: ${f} (${FILE_SIZE} bytes, ${FILE_LINES} lines) ===
$(head -80 "$FULL_PATH" 2>/dev/null || echo "(binary or unreadable)")
"
            fi
        done <<< "$UNTRACKED_NEW_FILES"
    fi

    DIFF_SUMMARY="${DIFF_PARTS}"
    [ -n "$UNTRACKED_CONTENT" ] && DIFF_SUMMARY="${DIFF_SUMMARY}
--- UNTRACKED NEW FILES ---${UNTRACKED_CONTENT}"

    # Final fallback: just show file sizes
    if [ -z "$DIFF_SUMMARY" ]; then
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
4. For REJECT decisions: provide structured feedback so the task can be retried intelligently

Rules:
- APPROVE if: work is complete, changes match the request, no obvious bugs or missing pieces
- REJECT if: major missing functionality, broken code, wrong files changed, dangerous changes
- Be lenient on style/minor issues — this is a sanity check, not a full code review
- IMPORTANT: Files listed under 'UNTRACKED NEW FILES' are valid deliverables that exist on the filesystem. Do NOT reject because they are missing from git diff — git only diffs tracked files. New files in projects/ or other untracked directories are expected.
- If the task output reports creating files AND those files appear in CHANGED FILES or UNTRACKED NEW FILES, treat the deliverable as present.
- IMPORTANT: Multiple tasks run CONCURRENTLY in the same working directory. The changed files list may include files modified by OTHER parallel tasks — not this one. Only evaluate files that are directly relevant to THIS task's prompt and deliverables. If you see unrelated files (e.g. Alpha wallet files in a research sweep, or training data files in an Alpha fix), IGNORE them — they belong to a concurrent task. Do NOT reject for unrelated file changes.

Return ONLY a JSON object (no markdown, no code fences).
For APPROVE:
{\"decision\": \"APPROVE\", \"reason\": \"<1-2 sentence explanation>\", \"issues\": [], \"expected\": \"\", \"actual\": \"\", \"failure_points\": [], \"suggestions\": []}
For REJECT (fill all fields carefully — this feedback will guide the retry):
{\"decision\": \"REJECT\", \"reason\": \"<1-2 sentence summary of why rejected>\", \"issues\": [\"<issue1>\", \"<issue2>\"], \"expected\": \"<what the task was supposed to deliver based on the prompt>\", \"actual\": \"<what was actually delivered or left incomplete>\", \"failure_points\": [\"<specific missing file or broken logic>\", \"<another specific gap>\"], \"suggestions\": [\"<concrete actionable fix for retry>\", \"<another suggestion>\"]}"

qa_log "Spawning QA agent (${QA_CLI})..."

QA_RESULT=""
QA_DECISION="REJECT"  # Default safe choice
QA_CLI_USED=""
QA_CLI_STDERR_INFO=""
# Use files for inter-process state (subshell can't write to parent vars)
QA_STDERR_FILE=$(mktemp /tmp/qa_stderr_state.XXXXXX)
QA_RESULT_FILE=$(mktemp /tmp/qa_result_state.XXXXXX)

# Helper: run a single QA CLI and write stdout+stderr to shared files.
# Returns 0 if CLI succeeded with non-empty output, 1 otherwise.
_run_qa_cli() {
    local cli="$1"
    local stderr_tmp
    stderr_tmp=$(mktemp /tmp/qa_stderr.XXXXXX)
    local exit_code=0

    if [ "$cli" = "gemini" ]; then
        timeout 60 gemini -p "$QA_PROMPT" >"$QA_RESULT_FILE" 2>"$stderr_tmp" || exit_code=$?
    elif [ "$cli" = "claude" ]; then
        timeout 120 "$CLAUDE_CLI" \
            --print \
            --dangerously-skip-permissions \
            --model "claude-haiku-4-5-20251001" \
            --max-turns 3 \
            --max-budget-usd 0.20 \
            -p "$QA_PROMPT" >"$QA_RESULT_FILE" 2>"$stderr_tmp" || exit_code=$?
    elif [ "$cli" = "kimi" ]; then
        timeout 60 /home/web3relic/.local/bin/kimi \
            --quiet \
            -p "$QA_PROMPT" >"$QA_RESULT_FILE" 2>"$stderr_tmp" || exit_code=$?
    fi

    # Capture first 5 lines of stderr for diagnostics
    head -5 "$stderr_tmp" > "$QA_STDERR_FILE" 2>/dev/null || true
    rm -f "$stderr_tmp"

    local result_size
    result_size=$(wc -c < "$QA_RESULT_FILE" 2>/dev/null || echo 0)

    if [ "$exit_code" -ne 0 ] || [ "$result_size" -eq 0 ]; then
        local stderr_preview
        stderr_preview=$(cat "$QA_STDERR_FILE" 2>/dev/null | head -2 || echo "")
        qa_log "CLI ${cli} failed (exit_code=${exit_code}, output_bytes=${result_size}). Stderr: ${stderr_preview:0:200}"
        return 1
    fi

    return 0
}

# Try primary QA CLI, then fall back to claude if it fails
if _run_qa_cli "$QA_CLI"; then
    QA_CLI_USED="$QA_CLI"
    QA_RESULT=$(cat "$QA_RESULT_FILE" 2>/dev/null || echo "")
    qa_log "QA primary CLI (${QA_CLI}) succeeded"
else
    qa_log "QA primary CLI (${QA_CLI}) failed — trying fallback: claude"
    if [ "$QA_CLI" != "claude" ]; then
        if _run_qa_cli "claude"; then
            QA_CLI_USED="claude"
            QA_RESULT=$(cat "$QA_RESULT_FILE" 2>/dev/null || echo "")
            qa_log "QA fallback CLI (claude) succeeded"
        else
            qa_log "QA fallback CLI (claude) also failed — QA unavailable"
            QA_RESULT=""
            QA_CLI_USED="none"
        fi
    else
        qa_log "QA: all CLIs failed — no review possible"
        QA_RESULT=""
        QA_CLI_USED="none"
    fi
fi

# Cleanup temp files
rm -f "$QA_STDERR_FILE" "$QA_RESULT_FILE"

qa_log "QA raw result (first 300): ${QA_RESULT:0:300}"

# ── Parse QA decision ─────────────────────────────────────────────────────────
QA_PARSED=$(echo "$QA_RESULT" | python3 -c "
import json, sys, re

raw = sys.stdin.read().strip()

# Strip markdown fences (including language specifiers)
raw = re.sub(r'\`\`\`(?:json|text|bash)?\n?', '', raw).strip()

def extract_balanced_json(text):
    '''Find the first balanced {…} block, even with nested arrays/objects.'''
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

# Try balanced extraction first
blob = extract_balanced_json(raw)
if blob:
    try:
        data = json.loads(blob)
        if 'decision' in data:
            print(json.dumps({
                'decision': data['decision'].upper().strip(),
                'reason': data.get('reason', ''),
                'issues': data.get('issues', []),
                'expected': data.get('expected', ''),
                'actual': data.get('actual', ''),
                'failure_points': data.get('failure_points', []),
                'suggestions': data.get('suggestions', []),
            }))
            sys.exit(0)
    except Exception:
        pass

# Fallback: look for APPROVE/REJECT keywords anywhere in response
raw_up = raw.upper()
has_approve = 'APPROVE' in raw_up
has_reject = 'REJECT' in raw_up
if has_approve and not has_reject:
    print(json.dumps({'decision': 'APPROVE', 'reason': 'Parsed from text response (no JSON found)', 'issues': [], 'expected': '', 'actual': '', 'failure_points': [], 'suggestions': []}))
elif has_reject:
    print(json.dumps({'decision': 'REJECT', 'reason': 'Parsed from text response (no JSON found)', 'issues': [], 'expected': '', 'actual': '', 'failure_points': [], 'suggestions': []}))
else:
    print(json.dumps({'decision': 'PARSE_FAIL', 'reason': 'Could not parse QA response — no JSON or keywords found', 'issues': [], 'expected': '', 'actual': '', 'failure_points': [], 'suggestions': []}))
" 2>/dev/null || echo '{"decision": "PARSE_FAIL", "reason": "python3 error", "issues": [], "expected": "", "actual": "", "failure_points": [], "suggestions": []}')

QA_DECISION=$(echo "$QA_PARSED" | python3 -c "import json,sys; print(json.load(sys.stdin)['decision'])" 2>/dev/null || echo "PARSE_FAIL")
QA_REASON=$(echo "$QA_PARSED" | python3 -c "import json,sys; print(json.load(sys.stdin).get('reason', ''))" 2>/dev/null || echo "")
QA_ISSUES=$(echo "$QA_PARSED" | python3 -c "import json,sys; d=json.load(sys.stdin); print('; '.join(d.get('issues', [])))" 2>/dev/null || echo "")

qa_log "QA decision: ${QA_DECISION} — ${QA_REASON}"

# ── Act on decision ───────────────────────────────────────────────────────────

if [ "$QA_DECISION" = "APPROVE" ]; then
    qa_log "QA APPROVED — committing changes..."

    COMMIT_HASH=""
    if cd "$WORK_DIR" 2>/dev/null; then
        # Stage ONLY the task-scoped changed files (not ALL changes from all tasks).
        # git add -A would stage changes from concurrent tasks — wrong.
        if [ -n "$CHANGED_FILES" ]; then
            while IFS= read -r f; do
                [ -z "$f" ] && continue
                [ -f "$WORK_DIR/$f" ] && git add -- "$WORK_DIR/$f" 2>/dev/null || true
            done <<< "$CHANGED_FILES"
        fi

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
    qa_log "QA REJECTED — flagging for retry with structured feedback..."

    # RL2F Phase 1: Build structured JSON feedback for intelligent retry.
    # Stored in qa_output as JSON so task_runner.sh can inject it as context on retry.
    # Fields: expected, actual, failure_points[], suggestions[] (from RL2F paper §3)
    QA_OUTPUT_FULL=$(echo "$QA_PARSED" | python3 -c "
import json, sys
d = json.load(sys.stdin)
feedback = {
    'rl2f_feedback': {
        'reason': d.get('reason', ''),
        'issues': d.get('issues', []),
        'expected': d.get('expected', ''),
        'actual': d.get('actual', ''),
        'failure_points': d.get('failure_points', []),
        'suggestions': d.get('suggestions', []),
    }
}
# Human-readable prefix for heartbeat display, structured JSON for retry injection
print('REJECTED: ' + d.get('reason', '') + '\n' + json.dumps(feedback))
" 2>/dev/null || echo "REJECTED: ${QA_REASON}")

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

    qa_log "QA: task ${TASK_ID:0:8} REJECTED — structured RL2F feedback stored, heartbeat will handle retry"
    qa_log "RL2F failure_points: $(echo "$QA_PARSED" | python3 -c "import json,sys; d=json.load(sys.stdin); print('; '.join(d.get('failure_points', [])[:3]))" 2>/dev/null || echo "none")"

    # Log to episodic memory for heartbeat awareness
    TITLE_JSON=$(python3 -c "import json,sys; print(json.dumps(sys.argv[1]))" "$TITLE" 2>/dev/null || echo "\"$TITLE\"")
    QA_JSON=$(python3 -c "import json,sys; print(json.dumps(sys.argv[1]))" "$QA_OUTPUT_FULL" 2>/dev/null || echo "\"$QA_OUTPUT_FULL\"")
    curl -sf -X POST "${API}/episodic/events" \
        -H 'Content-Type: application/json' \
        -d "{\"type\":\"qa_rejected\",\"summary\":\"QA rejected task ${TASK_ID:0:8} (${TITLE:0:60}): ${QA_REASON:0:200}\"}" \
        >> "$PARENT_LOG" 2>&1 || true

else
    # PARSE_FAIL or CLI failure — mark as needs_manual_review instead of auto-approving.
    # Auto-approving defeats the entire purpose of the QA layer.
    if [ "$QA_CLI_USED" = "none" ]; then
        FAIL_REASON="All QA CLIs unavailable (rate limited or error). Stderr: ${QA_CLI_STDERR_INFO:0:200}"
    elif [ -z "$QA_RESULT" ]; then
        FAIL_REASON="QA CLI (${QA_CLI_USED}) returned empty response. Stderr: ${QA_CLI_STDERR_INFO:0:200}"
    else
        FAIL_REASON="QA response parse failed. Raw (first 300): ${QA_RESULT:0:300}"
    fi

    qa_log "QA parse/CLI failed — marking as needs_manual_review (NOT auto-approving)"
    qa_log "Fail reason: ${FAIL_REASON:0:200}"

    UPDATE_JSON=$(python3 -c "
import json, sys
print(json.dumps({
    'qa_status': 'needs_manual_review',
    'qa_reviewer': sys.argv[1],
    'qa_output': 'QA failed: ' + sys.argv[2][:500],
}))
" "${QA_CLI_USED:-${QA_CLI}}" "$FAIL_REASON")

    curl -sf -X POST "${API}/tasks/${TASK_ID}/qa-update" \
        -H 'Content-Type: application/json' \
        -d "$UPDATE_JSON" >> "$PARENT_LOG" 2>&1 || true

    # Log to episodic memory so heartbeat is aware
    curl -sf -X POST "${API}/episodic/events" \
        -H 'Content-Type: application/json' \
        -d "{\"type\":\"qa_parse_fail\",\"summary\":\"QA failed for task ${TASK_ID:0:8} (${TITLE:0:60}): ${FAIL_REASON:0:200}\"}" \
        >> "$PARENT_LOG" 2>&1 || true

    qa_log "QA: task ${TASK_ID:0:8} marked needs_manual_review — heartbeat will handle"
fi

qa_log "QA runner finished (decision: ${QA_DECISION})"
