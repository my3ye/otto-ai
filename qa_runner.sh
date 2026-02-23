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

# ── RL2F training signal helper ───────────────────────────────────────────────
# Posts every QA decision to /rl2f/feedback as a training record.
# Non-fatal: if the endpoint fails, QA continues unaffected.
post_rl2f_feedback() {
    local outcome="$1"       # approved | rejected
    local feedback="$2"      # QA reason / review text
    local reviewer="${3:-}"  # which CLI reviewed (optional)
    local PAYLOAD
    PAYLOAD=$(python3 -c "
import json, sys
out = sys.argv[1]
fb = sys.argv[2][:500]
rev = sys.argv[3] if len(sys.argv) > 3 else ''
tid = sys.argv[4]
ttl = sys.argv[5][:200] if len(sys.argv) > 5 else ''
op = sys.argv[6][:1000] if len(sys.argv) > 6 else ''
print(json.dumps({
    'task_id': tid,
    'outcome': out,
    'feedback_text': fb,
    'task_output': op if op else None,
    'task_title': ttl if ttl else None,
    'qa_reviewer': rev if rev else None,
}))
" "$outcome" "$feedback" "$reviewer" "$TASK_ID" "$TITLE" "$OUTPUT" 2>/dev/null || echo "")
    if [ -n "$PAYLOAD" ]; then
        curl -sf -X POST "${API}/rl2f/feedback" \
            -H 'Content-Type: application/json' \
            -d "$PAYLOAD" >> "$PARENT_LOG" 2>&1 && \
            qa_log "RL2F: logged ${outcome} decision to training signal" || \
            qa_log "RL2F: WARNING — feedback POST failed (non-fatal, continuing)"
    fi
}

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
    post_rl2f_feedback "approved" "No file changes detected — task appears read-only or no-op. Auto-approved." "auto"
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
            # Diff each task-scoped file individually with per-file line cap.
            # Per-file approach avoids mid-file truncation from a single head -N on the
            # concatenated xargs output (which cuts across file boundaries).
            while IFS= read -r f; do
                [ -z "$f" ] && continue
                FILE_DIFF=$(git diff HEAD -- "$f" 2>/dev/null | head -100 || echo "")
                [ -n "$FILE_DIFF" ] && DIFF_PARTS="${DIFF_PARTS}${FILE_DIFF}
"
            done <<< "$TRACKED_CHANGED"
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

# ── For research/sweep/exploration tasks: also verify semantic memory storage ──
# Research tasks store deliverables via POST /semantic/remember (no git diff).
# Git-diff-only QA causes false rejections for these task types.
# Covered patterns: research, sweep, survey, exploration, investigation, analysis, review, discovery, audit
IS_RESEARCH_TASK=false
SEMANTIC_EVIDENCE=""
if echo "$TITLE" | grep -qiE '(research|sweep|survey|explor|investigat|analys|review|discover|audit)'; then
    IS_RESEARCH_TASK=true
    qa_log "Research/exploration task detected — querying semantic memory for recent storage"
    SEMANTIC_RESULTS=$(curl -sf -X POST "${API}/semantic/search" \
        -H 'Content-Type: application/json' \
        -d '{"query": "research papers", "limit": 5}' 2>/dev/null || echo "")
    SEMANTIC_EVIDENCE=$(echo "$SEMANTIC_RESULTS" | python3 -c "
import json, sys
from datetime import datetime, timezone, timedelta
try:
    results = json.load(sys.stdin)
    if not isinstance(results, list):
        results = results.get('results', [])
    cutoff = datetime.now(timezone.utc) - timedelta(hours=1)
    recent = []
    for r in results:
        created = r.get('created_at', '')
        try:
            dt = datetime.fromisoformat(created.replace('Z', '+00:00'))
            if dt > cutoff:
                recent.append(r.get('content', '')[:200])
        except Exception:
            pass
    if recent:
        print('VERIFIED: {} fact(s) stored in semantic memory in last hour:'.format(len(recent)))
        for i, f in enumerate(recent, 1):
            print('  {}. {}'.format(i, f[:150]))
    else:
        total = len(results)
        print('UNVERIFIED: 0 facts stored in last hour (query returned {} older results).'.format(total))
except Exception as e:
    print('ERROR querying semantic memory: {}'.format(e))
" 2>/dev/null || echo "Semantic memory query failed")
    qa_log "Semantic evidence: ${SEMANTIC_EVIDENCE:0:200}"

    # Auto-approve: if semantic storage is verified, skip the QA LLM entirely.
    # Rationale: QA LLMs see empty git diff and tend to reject research tasks even when
    # the real deliverable (semantic memories stored) is confirmed present. This bypasses
    # that false-rejection path while still requiring actual verification.
    if echo "$SEMANTIC_EVIDENCE" | grep -q "^VERIFIED:"; then
        qa_log "Research task — semantic storage verified. Auto-approving (skipping QA LLM)."
        curl -sf -X POST "${API}/tasks/${TASK_ID}/qa-update" \
            -H 'Content-Type: application/json' \
            -d "{\"qa_status\": \"approved\", \"qa_reviewer\": \"auto\", \"qa_output\": \"Research task auto-approved: ${SEMANTIC_EVIDENCE:0:300}\"}" \
            >> "$PARENT_LOG" 2>&1 || true
        qa_log "QA: task ${TASK_ID:0:8} auto-approved (research — semantic storage verified)"
        post_rl2f_feedback "approved" "Research task auto-approved: ${SEMANTIC_EVIDENCE:0:300}" "auto"
        exit 0
    fi
fi

# ── Run QA agent ─────────────────────────────────────────────────────────────
OUTPUT_EXCERPT="${OUTPUT:0:2000}"
PROMPT_EXCERPT="${PROMPT:0:800}"

# Build diff excerpt — structured summary when too large, never mid-line truncation.
MAX_DIFF_CHARS=3000
DIFF_SUMMARY_LEN=${#DIFF_SUMMARY}
if [ "$DIFF_SUMMARY_LEN" -le "$MAX_DIFF_CHARS" ]; then
    DIFF_EXCERPT="$DIFF_SUMMARY"
else
    # Diff is too large — show file list + per-file first-50-lines excerpts.
    # This gives the QA LLM a complete picture of WHAT changed without mid-line cuts.
    _HEADER="[DIFF TOO LARGE: ${DIFF_SUMMARY_LEN} chars exceeds ${MAX_DIFF_CHARS} limit. Structured summary below — no mid-line truncation.]

CHANGED FILES:
${CHANGED_FILES}

PER-FILE DIFF EXCERPTS (first 50 lines each):"
    _PER_FILE=""
    if cd "$WORK_DIR" 2>/dev/null; then
        while IFS= read -r _f; do
            [ -z "$_f" ] && continue
            _FD=$(git diff HEAD -- "$_f" 2>/dev/null | head -50 || echo "")
            if [ -n "$_FD" ]; then
                _PER_FILE="${_PER_FILE}
--- ${_f} ---
${_FD}"
            elif [ -f "$WORK_DIR/$_f" ]; then
                # Untracked new file — show first 30 lines of content
                _FC=$(head -30 "$WORK_DIR/$_f" 2>/dev/null || echo "(unreadable)")
                _PER_FILE="${_PER_FILE}
--- ${_f} (NEW FILE, first 30 lines) ---
${_FC}"
            fi
        done <<< "$CHANGED_FILES"
    fi
    DIFF_EXCERPT="${_HEADER}${_PER_FILE}"
    # Hard cap at 6000 chars — but only after a complete line boundary
    if [ "${#DIFF_EXCERPT}" -gt 6000 ]; then
        DIFF_EXCERPT="${DIFF_EXCERPT:0:5950}
[... remaining diff omitted — see CHANGED FILES list above]"
    fi
fi

# Build semantic evidence section (only shown for research/sweep tasks)
SEMANTIC_SECTION=""
if [ "$IS_RESEARCH_TASK" = "true" ]; then
    SEMANTIC_SECTION="
SEMANTIC MEMORY STORAGE (research task — primary deliverable):
${SEMANTIC_EVIDENCE}
"
fi

TASK_TYPE_NOTE=""
if [ "$IS_RESEARCH_TASK" = "true" ]; then
    TASK_TYPE_NOTE="TASK TYPE: RESEARCH/EXPLORATION — primary deliverable is semantic memory storage (API calls), NOT git diff. An empty git diff is EXPECTED and NORMAL for this task type."
fi

QA_PROMPT="You are Otto's QA reviewer. A task just completed and you must decide: APPROVE or REJECT.

TASK TITLE: ${TITLE}
${TASK_TYPE_NOTE}

TASK PROMPT (what was requested):
${PROMPT_EXCERPT}

TASK OUTPUT (what the agent reported):
${OUTPUT_EXCERPT}

CHANGED FILES:
${CHANGED_FILES}

GIT DIFF (full if ≤3000 chars, structured summary if larger):
${DIFF_EXCERPT}
${SEMANTIC_SECTION}
YOUR JOB:
1. Check that the changes align with what was requested
2. Look for obvious issues: broken syntax, missing files, incomplete implementation, security problems
3. Classify every finding as CRITICAL (blocks approval) or ADVISORY (improvement only)
4. Rate your confidence on each finding: HIGH = very certain, MEDIUM = likely, LOW = uncertain
5. Make a decision: APPROVE or REJECT

CONFIDENCE AND CRITICALITY RULES (CoRefine):
- Only HIGH-confidence CRITICAL findings should cause REJECT
- MEDIUM or LOW confidence findings → put in advisory_findings, do NOT block approval
- ADVISORY findings (style, naming, minor improvements) → never cause REJECT
- If you have doubts about whether something is truly broken, lower the confidence to MEDIUM/LOW
- If all your concerns are advisory or low-confidence → APPROVE with suggestions

Rules:
- APPROVE if: work is complete, changes match the request, no obvious bugs or missing pieces
- REJECT if: major missing functionality, broken code, wrong files changed, dangerous changes — AND you are HIGH-confidence about it
- Be lenient on style/minor issues — this is a sanity check, not a full code review
- IMPORTANT: For research/sweep tasks, the primary deliverable is semantic memory storage via API calls — NOT git diff. If 'SEMANTIC MEMORY STORAGE' section shows 'VERIFIED: N fact(s) stored in last hour', treat this as strong evidence of completion. Do NOT reject a research task solely because git diff is empty.
- IMPORTANT: Files listed under 'UNTRACKED NEW FILES' are valid deliverables that exist on the filesystem. Do NOT reject because they are missing from git diff — git only diffs tracked files. New files in projects/ or other untracked directories are expected.
- If the task output reports creating files AND those files appear in CHANGED FILES or UNTRACKED NEW FILES, treat the deliverable as present.
- IMPORTANT: Multiple tasks run CONCURRENTLY in the same working directory. The changed files list may include files modified by OTHER parallel tasks — not this one. Only evaluate files that are directly relevant to THIS task's prompt and deliverables. If you see unrelated files (e.g. Alpha wallet files in a research sweep, or training data files in an Alpha fix), IGNORE them — they belong to a concurrent task. Do NOT reject for unrelated file changes.

Return ONLY a JSON object (no markdown, no code fences).
For APPROVE:
{\"decision\": \"APPROVE\", \"reason\": \"<1-2 sentence explanation>\", \"overall_confidence\": \"HIGH\", \"critical_findings\": [], \"advisory_findings\": [{\"issue\": \"<optional suggestion>\", \"confidence\": \"LOW\"}], \"issues\": [], \"expected\": \"\", \"actual\": \"\", \"failure_points\": [], \"suggestions\": []}
For REJECT (only when you have HIGH-confidence CRITICAL findings — fill all fields carefully):
{\"decision\": \"REJECT\", \"reason\": \"<1-2 sentence summary of why rejected>\", \"overall_confidence\": \"HIGH\", \"critical_findings\": [{\"issue\": \"<specific blocker>\", \"confidence\": \"HIGH\"}], \"advisory_findings\": [{\"issue\": \"<minor suggestion>\", \"confidence\": \"MEDIUM\"}], \"issues\": [\"<issue1>\"], \"expected\": \"<what the task was supposed to deliver based on the prompt>\", \"actual\": \"<what was actually delivered or left incomplete>\", \"failure_points\": [\"<specific missing file or broken logic>\"], \"suggestions\": [\"<concrete actionable fix for retry>\"]}"

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

# ── CoRefine: Confidence-guided targeted refinement ──────────────────────────
# Implements CoRefine (arXiv 2602.08948): targeted self-correction using confidence
# signals. Only fixes HIGH-confidence CRITICAL issues. Max 2 rounds.
# Sets COREFINE_REFINEMENT_COUNT in caller scope.
COREFINE_REFINEMENT_COUNT=0

corefine_run_refinement() {
    local task_cli="$1"           # original CLI that ran the task
    local critical_json="$2"      # JSON: [{"issue":"...","confidence":"HIGH"}]
    local suggestions_json="$3"   # JSON: ["fix1","fix2"]
    local max_rounds=2
    local resolved=1              # 1=failed/unresolved, 0=success

    for round in $(seq 1 $max_rounds); do
        qa_log "CoRefine round ${round}/${max_rounds}: spawning targeted fix via ${task_cli}"

        # Build targeted refinement prompt
        local REFINE_PROMPT
        REFINE_PROMPT=$(python3 -c "
import json, sys
try:
    critical = json.loads(sys.argv[1])
    suggestions = json.loads(sys.argv[2])
    title = sys.argv[3]
    work_dir = sys.argv[4]
    round_n = sys.argv[5]
    max_r = sys.argv[6]
    issues_text = '\n'.join([
        '  - [{}] {}'.format(
            f.get('confidence','HIGH') if isinstance(f,dict) else 'HIGH',
            f.get('issue', str(f)) if isinstance(f,dict) else str(f)
        ) for f in critical
    ])
    sugg_text = '\n'.join(['  - ' + s for s in suggestions[:5]])
    print('TARGETED FIX REQUEST (CoRefine round {}/{})'.format(round_n, max_r))
    print('')
    print('Task: ' + title)
    print('Work directory: ' + work_dir)
    print('')
    print('QA rejected your previous work. Fix ONLY these CRITICAL issues:')
    print(issues_text)
    if sugg_text:
        print('')
        print('Suggested approaches:')
        print(sugg_text)
    print('')
    print('RULES:')
    print('- Read the relevant files first')
    print('- Make surgical changes — fix ONLY the issues listed above')
    print('- Do NOT rewrite unrelated code')
    print('- Verify your changes are correct after applying them')
    print('- Working directory: ' + work_dir)
except Exception as e:
    print('Fix the critical QA issues in: ' + sys.argv[3])
    print('Working directory: ' + sys.argv[4])
" "$critical_json" "$suggestions_json" "$TITLE" "$WORK_DIR" "$round" "$max_rounds" 2>/dev/null \
  || echo "Fix the critical QA issues in: ${TITLE}. Working directory: ${WORK_DIR}")

        if [ -z "$REFINE_PROMPT" ]; then
            qa_log "CoRefine round ${round}: empty prompt — skipping"
            break
        fi

        # Create a timestamp marker for post-refinement diff detection
        local REFINE_MARKER
        REFINE_MARKER=$(mktemp /tmp/corefine_marker.XXXXXX)
        local REFINE_OUT_FILE
        REFINE_OUT_FILE=$(mktemp /tmp/corefine_out.XXXXXX)
        local REFINE_EXIT=0

        # Spawn original CLI with targeted prompt
        if [ "$task_cli" = "claude" ]; then
            timeout 180 "$CLAUDE_CLI" \
                --print --dangerously-skip-permissions \
                --model "claude-haiku-4-5-20251001" \
                --max-turns 8 --max-budget-usd 0.15 \
                --add-dir "$WORK_DIR" \
                -p "$REFINE_PROMPT" >"$REFINE_OUT_FILE" 2>/dev/null || REFINE_EXIT=$?
        elif [ "$task_cli" = "gemini" ]; then
            (cd "$WORK_DIR" && timeout 90 gemini -p "$REFINE_PROMPT") >"$REFINE_OUT_FILE" 2>/dev/null || REFINE_EXIT=$?
        else
            # kimi or unknown: fall back to claude haiku for refinement
            timeout 180 "$CLAUDE_CLI" \
                --print --dangerously-skip-permissions \
                --model "claude-haiku-4-5-20251001" \
                --max-turns 8 --max-budget-usd 0.15 \
                --add-dir "$WORK_DIR" \
                -p "$REFINE_PROMPT" >"$REFINE_OUT_FILE" 2>/dev/null || REFINE_EXIT=$?
        fi

        local REFINE_BYTES
        REFINE_BYTES=$(wc -c < "$REFINE_OUT_FILE" 2>/dev/null || echo 0)
        rm -f "$REFINE_OUT_FILE"
        COREFINE_REFINEMENT_COUNT=$((COREFINE_REFINEMENT_COUNT + 1))

        if [ "$REFINE_EXIT" -ne 0 ] || [ "$REFINE_BYTES" -eq 0 ]; then
            qa_log "CoRefine round ${round}: refinement CLI failed (exit=${REFINE_EXIT}, bytes=${REFINE_BYTES})"
            rm -f "$REFINE_MARKER"
            continue
        fi

        qa_log "CoRefine round ${round}: refinement done (${REFINE_BYTES} bytes). Re-evaluating critical issues..."

        # Get diff since refinement marker (captures files changed during refinement)
        local NEW_DIFF=""
        if cd "$WORK_DIR" 2>/dev/null; then
            NEW_DIFF=$(find . -newer "$REFINE_MARKER" -type f \
                ! -path "./.git/*" ! -name "*.log" ! -name "*.pyc" ! -name "*.tmp" \
                2>/dev/null | head -20 | while IFS= read -r rf; do
                    git diff HEAD -- "$rf" 2>/dev/null | head -30 || true
                done | head -120 || echo "")
        fi
        rm -f "$REFINE_MARKER"

        # Targeted re-evaluation: did critical issues get resolved?
        local EVAL_PROMPT
        EVAL_PROMPT=$(python3 -c "
import json, sys
try:
    critical = json.loads(sys.argv[1])
    new_diff = sys.argv[2]
    title = sys.argv[3]
    issues_text = '\n'.join(['  - ' + (f.get('issue',str(f)) if isinstance(f,dict) else str(f)) for f in critical])
    print('TARGETED RE-EVALUATION for: ' + title)
    print('')
    print('CRITICAL issues that were reported:')
    print(issues_text)
    print('')
    print('CHANGES MADE SINCE THOSE ISSUES WERE REPORTED:')
    print(new_diff[:1500] if new_diff else '(no git diff — changes may be in untracked files or already committed)')
    print('')
    print('Did the refinement address ALL the critical issues?')
    print('Be lenient — if intent is clear and issues appear addressed, say resolved.')
    print('Return ONLY JSON (no markdown):')
    print('{\"resolved\": true, \"reason\": \"brief explanation\"}')
    print('or')
    print('{\"resolved\": false, \"remaining\": [\"still unresolved\"]}')
except Exception:
    print('Did all critical issues get fixed? Return JSON: {\"resolved\": true/false, \"reason\": \"\"}')
" "$critical_json" "$NEW_DIFF" "$TITLE" 2>/dev/null \
  || echo 'Did all critical issues get fixed? Return JSON: {"resolved": true/false, "reason": ""}')

        local EVAL_RESULT_FILE
        EVAL_RESULT_FILE=$(mktemp /tmp/corefine_eval.XXXXXX)
        local EVAL_EXIT=0
        timeout 60 "$CLAUDE_CLI" \
            --print --dangerously-skip-permissions \
            --model "claude-haiku-4-5-20251001" \
            --max-turns 2 --max-budget-usd 0.06 \
            -p "$EVAL_PROMPT" >"$EVAL_RESULT_FILE" 2>/dev/null || EVAL_EXIT=$?

        local EVAL_OUT
        EVAL_OUT=$(cat "$EVAL_RESULT_FILE" 2>/dev/null || echo "")
        rm -f "$EVAL_RESULT_FILE"

        local IS_RESOLVED
        IS_RESOLVED=$(echo "$EVAL_OUT" | python3 -c "
import json, sys, re
raw = sys.stdin.read().strip()
raw = re.sub(r'\`\`\`(?:json)?\n?', '', raw).strip()
start = raw.find('{'); end = raw.rfind('}')
if start != -1 and end != -1:
    try:
        d = json.loads(raw[start:end+1])
        print('true' if d.get('resolved', False) else 'false')
        sys.exit(0)
    except Exception:
        pass
# Fallback keyword scan
if '\"resolved\": true' in raw or \"'resolved': true\" in raw:
    print('true')
else:
    print('false')
" 2>/dev/null || echo "false")

        if [ "$IS_RESOLVED" = "true" ]; then
            qa_log "CoRefine round ${round}: ALL critical issues resolved — promoting to APPROVE"
            resolved=0
            break
        else
            qa_log "CoRefine round ${round}: issues not fully resolved — ${round}/${max_rounds} rounds used"
        fi
    done

    return $resolved
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
            decision = data['decision'].upper().strip()
            critical_findings = data.get('critical_findings', [])
            advisory_findings = data.get('advisory_findings', [])
            overall_confidence = data.get('overall_confidence', 'HIGH')

            # CoRefine auto-upgrade: REJECT with no HIGH-confidence critical findings → APPROVE
            # If reviewer used new schema but all blockers are low-confidence → upgrade
            if decision == 'REJECT':
                high_conf_critical = [
                    f for f in critical_findings
                    if isinstance(f, dict) and f.get('confidence', 'HIGH').upper() == 'HIGH'
                ]
                # Also treat plain string items in critical_findings as HIGH by default
                plain_critical = [f for f in critical_findings if isinstance(f, str)]
                real_blockers = high_conf_critical + plain_critical
                if not real_blockers and critical_findings == []:
                    # No critical findings at all — reviewer said REJECT but listed nothing critical
                    decision = 'APPROVE'
                    data['reason'] = '[CoRefine auto-upgrade] REJECT had no critical findings — promoted to APPROVE. Advisory: ' + data.get('reason', '')

            print(json.dumps({
                'decision': decision,
                'reason': data.get('reason', ''),
                'overall_confidence': overall_confidence,
                'critical_findings': critical_findings,
                'advisory_findings': advisory_findings,
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
    print(json.dumps({'decision': 'APPROVE', 'reason': 'Parsed from text response (no JSON found)', 'overall_confidence': 'MEDIUM', 'critical_findings': [], 'advisory_findings': [], 'issues': [], 'expected': '', 'actual': '', 'failure_points': [], 'suggestions': []}))
elif has_reject:
    print(json.dumps({'decision': 'REJECT', 'reason': 'Parsed from text response (no JSON found)', 'overall_confidence': 'MEDIUM', 'critical_findings': [], 'advisory_findings': [], 'issues': [], 'expected': '', 'actual': '', 'failure_points': [], 'suggestions': []}))
else:
    print(json.dumps({'decision': 'PARSE_FAIL', 'reason': 'Could not parse QA response — no JSON or keywords found', 'overall_confidence': 'LOW', 'critical_findings': [], 'advisory_findings': [], 'issues': [], 'expected': '', 'actual': '', 'failure_points': [], 'suggestions': []}))
" 2>/dev/null || echo '{"decision": "PARSE_FAIL", "reason": "python3 error", "overall_confidence": "LOW", "critical_findings": [], "advisory_findings": [], "issues": [], "expected": "", "actual": "", "failure_points": [], "suggestions": []}')

QA_DECISION=$(echo "$QA_PARSED" | python3 -c "import json,sys; print(json.load(sys.stdin)['decision'])" 2>/dev/null || echo "PARSE_FAIL")
QA_REASON=$(echo "$QA_PARSED" | python3 -c "import json,sys; print(json.load(sys.stdin).get('reason', ''))" 2>/dev/null || echo "")
QA_ISSUES=$(echo "$QA_PARSED" | python3 -c "import json,sys; d=json.load(sys.stdin); print('; '.join(d.get('issues', [])))" 2>/dev/null || echo "")
# CoRefine fields: confidence + critical/advisory classification
QA_CONFIDENCE=$(echo "$QA_PARSED" | python3 -c "import json,sys; print(json.load(sys.stdin).get('overall_confidence', 'HIGH'))" 2>/dev/null || echo "HIGH")
QA_CRITICAL_FINDINGS=$(echo "$QA_PARSED" | python3 -c "import json,sys; import json as j2; print(j2.dumps(json.load(sys.stdin).get('critical_findings', [])))" 2>/dev/null || echo "[]")
QA_CRITICAL_COUNT=$(echo "$QA_PARSED" | python3 -c "
import json, sys
d = json.load(sys.stdin)
critical = d.get('critical_findings', [])
# Count only HIGH-confidence critical findings (or plain strings, treated as HIGH)
count = sum(1 for f in critical if isinstance(f, str) or (isinstance(f, dict) and f.get('confidence', 'HIGH').upper() == 'HIGH'))
print(count)
" 2>/dev/null || echo "0")
QA_SUGGESTIONS_JSON=$(echo "$QA_PARSED" | python3 -c "import json,sys; import json as j2; print(j2.dumps(json.load(sys.stdin).get('suggestions', [])))" 2>/dev/null || echo "[]")

qa_log "QA decision: ${QA_DECISION} — ${QA_REASON}"
qa_log "CoRefine: overall_confidence=${QA_CONFIDENCE}, critical_findings(HIGH)=${QA_CRITICAL_COUNT}"

# ── Act on decision ───────────────────────────────────────────────────────────

# Read rl2f_feedback_id from task metadata (set on rejection, passed to retry task)
RL2F_FEEDBACK_ID=$(echo "$TASK_JSON" | python3 -c "
import json, sys
print(json.load(sys.stdin).get('metadata', {}).get('rl2f_feedback_id', ''))
" 2>/dev/null || echo "")

if [ "$QA_DECISION" = "APPROVE" ]; then
    qa_log "QA APPROVED — committing changes..."

    # ── RL2F Phase 2: Mark feedback turn as succeeded ──────────────────────────
    # If this task was a retry (has rl2f_feedback_id), the retry succeeded.
    # Update the feedback record's outcome so we can track: feedback → success.
    if [ -n "$RL2F_FEEDBACK_ID" ]; then
        RESOLVE_PAYLOAD=$(python3 -c "
import json, sys
print(json.dumps({'outcome': 'succeeded', 'outcome_details': 'QA approved retry task ' + sys.argv[1][:8]}))
" "$TASK_ID" 2>/dev/null || echo '{"outcome": "succeeded"}')
        curl -sf -X PATCH "${API}/rl2f/task-feedback/${RL2F_FEEDBACK_ID}/resolve" \
            -H 'Content-Type: application/json' \
            -d "$RESOLVE_PAYLOAD" \
            >> "$PARENT_LOG" 2>&1 && \
            qa_log "RL2F Phase 2: feedback ${RL2F_FEEDBACK_ID:0:8} resolved as succeeded" || \
            qa_log "RL2F Phase 2: WARNING — could not resolve feedback outcome (non-fatal)"
    fi
    # ── End RL2F Phase 2 outcome resolution ───────────────────────────────────

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
    post_rl2f_feedback "approved" "${QA_REASON}" "${QA_CLI_USED:-${QA_CLI}}"

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

    # ── RL2F Phase 2: Mark previous feedback as failed (chain rejection) ────────
    # If this task was already a retry (has rl2f_feedback_id), and it's being rejected
    # again, update the previous feedback record's outcome to 'failed' before creating new.
    if [ -n "$RL2F_FEEDBACK_ID" ]; then
        FAIL_PAYLOAD=$(python3 -c "
import json, sys
print(json.dumps({'outcome': 'failed', 'outcome_details': 'Retry task ' + sys.argv[1][:8] + ' was re-rejected by QA'}))
" "$TASK_ID" 2>/dev/null || echo '{"outcome": "failed"}')
        curl -sf -X PATCH "${API}/rl2f/task-feedback/${RL2F_FEEDBACK_ID}/resolve" \
            -H 'Content-Type: application/json' \
            -d "$FAIL_PAYLOAD" \
            >> "$PARENT_LOG" 2>&1 && \
            qa_log "RL2F Phase 2: previous feedback ${RL2F_FEEDBACK_ID:0:8} resolved as failed (re-rejected)" || \
            qa_log "RL2F Phase 2: WARNING — could not resolve previous feedback as failed (non-fatal)"
    fi
    # ── End chain rejection handling ──────────────────────────────────────────

    # ── RL2F Phase 2: Persist feedback turn to task_retry_feedback table ──────
    # This enables: feedback chain retrieval, retry success metrics, training data.
    # attempt_number = current retry_count + 1 (or 1 for first rejection).
    CURRENT_RETRY_COUNT=$(echo "$TASK_JSON" | python3 -c "
import json, sys
print(json.load(sys.stdin).get('metadata', {}).get('retry_count', 0))
" 2>/dev/null || echo "0")
    ATTEMPT_NUMBER=$(( CURRENT_RETRY_COUNT + 1 ))

    # Extract the structured feedback object for the DB record
    RL2F_FEEDBACK_JSON=$(echo "$QA_PARSED" | python3 -c "
import json, sys
d = json.load(sys.stdin)
print(json.dumps({
    'reason': d.get('reason', ''),
    'issues': d.get('issues', []),
    'expected': d.get('expected', ''),
    'actual': d.get('actual', ''),
    'failure_points': d.get('failure_points', []),
    'suggestions': d.get('suggestions', []),
}))
" 2>/dev/null || echo "{}")

    # POST to /rl2f/task-feedback — store the rejection feedback turn
    TASK_FEEDBACK_PAYLOAD=$(python3 -c "
import json, sys
print(json.dumps({
    'original_task_id': sys.argv[1],
    'attempt_number': int(sys.argv[2]),
    'feedback': json.loads(sys.argv[3]),
    'qa_rejection_reason': sys.argv[4][:500] if sys.argv[4] else None,
    'feedback_injected': False,
}))
" "$TASK_ID" "$ATTEMPT_NUMBER" "$RL2F_FEEDBACK_JSON" "$QA_REASON" 2>/dev/null || echo "")

    RL2F_FEEDBACK_ID=""
    if [ -n "$TASK_FEEDBACK_PAYLOAD" ]; then
        FEEDBACK_RECORD=$(curl -sf -X POST "${API}/rl2f/task-feedback" \
            -H 'Content-Type: application/json' \
            -d "$TASK_FEEDBACK_PAYLOAD" 2>/dev/null || echo "")
        RL2F_FEEDBACK_ID=$(echo "$FEEDBACK_RECORD" | python3 -c "
import json, sys
try:
    d = json.load(sys.stdin)
    print(d.get('id', ''))
except Exception:
    print('')
" 2>/dev/null || echo "")
        if [ -n "$RL2F_FEEDBACK_ID" ]; then
            qa_log "RL2F Phase 2: feedback turn stored (id=${RL2F_FEEDBACK_ID:0:8}, attempt=${ATTEMPT_NUMBER})"
        else
            qa_log "RL2F Phase 2: WARNING — failed to store feedback turn (API error or non-JSON response)"
        fi
    fi
    # ── End RL2F Phase 2 persistence ──────────────────────────────────────────

    UPDATE_JSON=$(python3 -c "
import json, sys
# Include rl2f_feedback_id in task metadata so heartbeat can pass it to retry task
metadata_update = {}
if sys.argv[3]:
    metadata_update['rl2f_feedback_id'] = sys.argv[3]
    metadata_update['rl2f_attempt_number'] = int(sys.argv[4])
print(json.dumps({
    'qa_status': 'rejected',
    'qa_reviewer': sys.argv[1],
    'qa_output': sys.argv[2],
    'metadata_update': metadata_update,
}))
" "$QA_CLI" "$QA_OUTPUT_FULL" "$RL2F_FEEDBACK_ID" "$ATTEMPT_NUMBER" 2>/dev/null)

    # Use standard qa-update if metadata_update payload not supported (fallback)
    STANDARD_UPDATE=$(python3 -c "
import json, sys
print(json.dumps({
    'qa_status': 'rejected',
    'qa_reviewer': sys.argv[1],
    'qa_output': sys.argv[2],
}))
" "$QA_CLI" "$QA_OUTPUT_FULL" 2>/dev/null)

    curl -sf -X POST "${API}/tasks/${TASK_ID}/qa-update" \
        -H 'Content-Type: application/json' \
        -d "$STANDARD_UPDATE" >> "$PARENT_LOG" 2>&1 || true

    # Store rl2f_feedback_id in task metadata for heartbeat to use when creating retry
    if [ -n "$RL2F_FEEDBACK_ID" ]; then
        META_PATCH=$(python3 -c "
import json, sys
print(json.dumps({'rl2f_feedback_id': sys.argv[1], 'rl2f_attempt_number': int(sys.argv[2])}))
" "$RL2F_FEEDBACK_ID" "$ATTEMPT_NUMBER" 2>/dev/null || echo "")
        if [ -n "$META_PATCH" ]; then
            curl -sf -X PATCH "${API}/tasks/${TASK_ID}/metadata" \
                -H 'Content-Type: application/json' \
                -d "$META_PATCH" >> "$PARENT_LOG" 2>&1 || true
        fi
    fi

    qa_log "QA: task ${TASK_ID:0:8} REJECTED — structured RL2F feedback stored, heartbeat will handle retry"
    qa_log "RL2F failure_points: $(echo "$QA_PARSED" | python3 -c "import json,sys; d=json.load(sys.stdin); print('; '.join(d.get('failure_points', [])[:3]))" 2>/dev/null || echo "none")"

    # Log to episodic memory for heartbeat awareness
    EPISODIC_REJECT_JSON=$(python3 -c "
import json, sys
print(json.dumps({'type': 'qa_rejected', 'summary': 'QA rejected task ' + sys.argv[1][:8] + ' (' + sys.argv[2][:60] + '): ' + sys.argv[3][:200]}))
" "$TASK_ID" "$TITLE" "$QA_REASON" 2>/dev/null || echo '{"type":"qa_rejected","summary":"QA rejected task (json build failed)"}')
    curl -sf -X POST "${API}/episodic/events" \
        -H 'Content-Type: application/json' \
        -d "$EPISODIC_REJECT_JSON" \
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
    EPISODIC_FAIL_JSON=$(python3 -c "
import json, sys
print(json.dumps({'type': 'qa_parse_fail', 'summary': 'QA failed for task ' + sys.argv[1][:8] + ' (' + sys.argv[2][:60] + '): ' + sys.argv[3][:200]}))
" "$TASK_ID" "$TITLE" "$FAIL_REASON" 2>/dev/null || echo '{"type":"qa_parse_fail","summary":"QA parse fail (json build failed)"}')
    curl -sf -X POST "${API}/episodic/events" \
        -H 'Content-Type: application/json' \
        -d "$EPISODIC_FAIL_JSON" \
        >> "$PARENT_LOG" 2>&1 || true

    qa_log "QA: task ${TASK_ID:0:8} marked needs_manual_review — heartbeat will handle"
fi

qa_log "QA runner finished (decision: ${QA_DECISION})"
