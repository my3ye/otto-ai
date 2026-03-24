# HiClaw-Derived Sprint Backlog
**Date:** 2026-03-24
**Source:** HiClaw gap analysis + research memory synthesis
**Scope:** 4 candidate improvements ranked by impact × (1/complexity) × (1/dep_risk)

---

## Scoring Matrix

| Item | Impact (1-5) | Complexity (1=easy) | Dep Risk (1=safe) | Composite Score |
|---|---|---|---|---|
| ITEM-1: Acceptance criteria in task prompts | 5 | 1 | 1 | **25.0** |
| ITEM-2: Artifact path references for large outputs | 4 | 2 | 2 | **10.0** |
| ITEM-3: Enforce plan system in heartbeat | 3 | 1 | 1 | **15.0** |
| ITEM-4: Credential isolation via LLM proxy | 2 | 4 | 3 | **1.7** |

**Reranked by composite score:**
1. ITEM-1 (25.0) — Acceptance criteria
2. ITEM-3 (15.0) — Plan system enforcement
3. ITEM-2 (10.0) — Artifact path references
4. ITEM-4 (1.7) — Credential proxy

---

## Sprint Backlog

---

### 🔴 ITEM-1 [IMMEDIATE] — Acceptance Criteria in Every Task Prompt
**Source:** HiClaw research memory (not in gap analysis doc — discovered separately)
**Priority:** HIGHEST — directly addresses QA rejection rate

**Problem:**
HiClaw Workers only accept tasks with clear success/failure criteria embedded in the task spec. Otto tasks often lack explicit criteria, causing QA to reject tasks with "unable to verify deliverable." This is the root cause of QA rejection spikes.

**Change required:**
Edit `~/otto/.claude/agents/heartbeat.md` to add a mandatory `[ACCEPTANCE CRITERIA]` block to every task creation prompt. The block must specify:
1. What file/endpoint/output to verify
2. What constitutes pass (e.g., HTTP 200, file exists with >N bytes, specific content present)
3. What constitutes fail

**Acceptance Criteria (for this task itself):**
- [ ] `heartbeat.md` task creation section contains a `[ACCEPTANCE CRITERIA]` template
- [ ] Template has 3 fields: verify target, pass condition, fail condition
- [ ] Applied to both `POST /tasks` direct creation AND `POST /task-plans` plan items
- [ ] One example task prompt in the file demonstrates the format
- [ ] QA reviewer can verify by reading heartbeat.md (no runtime test needed)

**Estimated effort:** 1 task, $1 budget, 15 min
**Risk:** Zero — additive prompt change, no code touched
**Breaking:** No

---

### ITEM-2 — Enforce Plan System for Multi-Step Heartbeat Work
**Source:** GAP-3 from gap analysis
**Priority:** High — behavioral, zero-cost

**Problem:**
Heartbeat sometimes creates tasks directly via `POST /tasks` for work that spans multiple dependent steps, bypassing the `POST /task-plans` DAG system. This loses dependency tracking, agent auto-employment, and plan observability in OMS.

**Change required:**
Edit `~/otto/.claude/agents/heartbeat.md` to add an explicit routing rule:
- **1 step:** `POST /tasks` + `/run` — fine
- **2+ steps with dependencies:** ALWAYS `POST /task-plans` — never create sequential tasks manually
- Add: "If you're about to create Task B that depends on Task A's output, stop — use task plans."

**Acceptance Criteria:**
- [ ] `heartbeat.md` contains an explicit routing rule section (clearly labeled)
- [ ] Rule distinguishes single-step vs multi-step with concrete example
- [ ] Rule warns against manually sequencing tasks
- [ ] No code changes required — prompt-only

**Estimated effort:** 1 task, $0.50 budget, 10 min
**Risk:** Zero — prompt change only
**Breaking:** No

---

### ITEM-3 — Artifact Path References for Large Task Outputs
**Source:** GAP-2 from gap analysis
**Priority:** Medium — code change, meaningful DB/context benefit

**Problem:**
Task outputs >2KB are stored as full text in the DB completion payload (`task_output` field). When heartbeat reviews tasks or downstream tasks read prior outputs, these inflate context. At scale (100+ task history), this becomes a real problem.

**HiClaw pattern:** Workers write large outputs to shared filesystem, return file paths. Coordinator reads only what it needs.

**Change required:**
In `~/otto/task_runner.sh`, add output size check before the `/tasks/{id}/complete` API call:
```bash
OUTPUT_BYTE_SIZE=$(echo "$TASK_OUTPUT" | wc -c)
if [ "$OUTPUT_BYTE_SIZE" -gt 2048 ]; then
    OUTPUT_FILE="$LOG_DIR/$TASK_ID/output.md"
    mkdir -p "$LOG_DIR/$TASK_ID"
    printf '%s' "$TASK_OUTPUT" > "$OUTPUT_FILE"
    COMPLETION_OUTPUT="[output written to ${OUTPUT_FILE} — ${OUTPUT_BYTE_SIZE} bytes]"
else
    COMPLETION_OUTPUT="$TASK_OUTPUT"
fi
# Use $COMPLETION_OUTPUT in the /complete API call instead of $TASK_OUTPUT
```

**Acceptance Criteria:**
- [ ] `task_runner.sh` contains size-check logic (grep for `OUTPUT_BYTE_SIZE` or `2048`)
- [ ] Test: run a task with >2KB output, verify DB stores path reference not full text
- [ ] Test: run a task with <2KB output, verify DB stores full text (unchanged behavior)
- [ ] `~/otto/logs/tasks/{task_id}/output.md` exists after large-output task completes
- [ ] No existing tasks broken — grep confirms `/tasks/complete` call uses new variable

**Estimated effort:** 1 task, $2 budget, 30 min
**Risk:** Low — changes task completion flow, needs careful testing
**Breaking:** Potentially — any code reading `task.task_output` from DB expecting full text must handle path references. QA runner reads task output for review — must be verified.

**Dependency:** None. Can implement standalone.

---

### ITEM-4 [DEFERRED] — Credential Isolation via LLM Proxy
**Source:** GAP-1 from gap analysis
**Priority:** Low — security posture only, actual risk is minimal on single-tenant VM

**Problem:**
`task_runner.sh` inherits `ANTHROPIC_API_KEY` from systemd environment. Architecturally, workers should not hold production keys. HiClaw addresses this via Higress AI Gateway — workers get scoped consumer tokens, real keys never leave the gateway.

**Deferred because:**
- Otto runs as single-tenant on a controlled VM
- `claude` CLI already abstracts the key — it's not exposed in bash env by task_runner.sh itself
- $6 implementation cost for low actual risk
- Would require new Memory API endpoint + task_runner.sh refactor

**When to unblock:** When Otto moves to multi-tenant, distributed workers, or community-submitted tasks.

**Estimated effort:** 2 tasks, ~$6 budget
**Risk:** Medium — changes authentication flow for all tasks

---

## Immediate Implementation Target

**→ ITEM-1: Acceptance criteria in task prompts**

Rationale:
- Highest composite score (25.0 vs next-best 15.0)
- Directly addresses QA rejection rate — the most visible quality problem
- Zero cost (prompt edit only)
- Zero risk (no code touched)
- Compounds immediately — every task created after this change benefits
- Can be done in a single $1 task

**Recommended task prompt:**
```
Edit ~/otto/.claude/agents/heartbeat.md to add a mandatory [ACCEPTANCE CRITERIA]
block template to the task creation section. Template fields: (1) verify_target:
what file/endpoint/output to check, (2) pass_condition: what must be true for
success, (3) fail_condition: what indicates failure. Apply to both POST /tasks
and POST /task-plans creation flows. Add one worked example. Keep change surgical
— edit only the task creation section, do not restructure the file.
```

---

## Notes on TrustGraph Cross-Reference

The TrustGraph analysis task is still running as of this sprint backlog. No TrustGraph patterns are included here. If TrustGraph produces additional improvement candidates, a follow-up backlog item may be warranted. Key watch: TrustGraph's knowledge graph patterns may complement Otto's existing Graphiti/Neo4j layer — worth checking for query patterns or entity resolution techniques.
