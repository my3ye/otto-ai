# HiClaw → Otto Gap Analysis
**Date:** 2026-03-24
**Scope:** Agent loop, memory/context management, task planning, tool orchestration
**Source:** HiClaw v1.0.6 (github.com/alibaba/hiclaw, released March 4-14 2026)

---

## Summary Verdict

Otto already implements the **core HiClaw architecture** at a structurally equal or superior level:
- Manager-Workers → heartbeat/RIC + task_runner.sh
- DAG task decomposition → task_plans.py (more explicit than HiClaw)
- Memory hierarchy → S-MMU L1/L2/L3 (more sophisticated than HiClaw's per-worker MEMORY.md)
- Workflow chains → workflows.py (no HiClaw equivalent)
- Agent auto-employment → agency-agents/ directory loader

The gaps are **3 specific operational patterns** HiClaw does better, plus a consistency issue in how heartbeat routes work.

---

## Section 1: Patterns Otto Already Has (Equal or Better)

| HiClaw Pattern | Otto Equivalent | Assessment |
|---|---|---|
| Manager Agent decomposes tasks | heartbeat.sh + RIC reactive dispatch | **Equivalent** |
| DAG dependency mapping | `task_plans.py` with `depends_on` edges | **Superior** — Otto has explicit typed topology |
| Task-specific model allocation | Per-task `model` field + JitRL budget modulation | **Superior** — Otto auto-adjusts based on past success rates |
| Workers as stateless execution units | `task_runner.sh` spawning claude CLI per task | **Equivalent** |
| Agent auto-employment | `agency-agents/` copy-on-demand in task_plans.py | **Equivalent** |
| Zombie prevention / restart | `trap EXIT` in task_runner.sh + principle in procedural memory | **Equivalent** |
| Context separation (decisions vs artifacts) | S-MMU L1 (slices) vs task log files | **Equivalent** |
| Anti-cross-contamination per worker | Tool RAG selects specialist agent per task | **Equivalent** (different mechanism) |
| Multi-step pipeline chains | `workflows.py` — full pipeline engine with evolution | **Superior** — HiClaw has no workflow engine |
| Memory hierarchy | S-MMU L1/L2/L3 + HyMem + ARAG + FadeMem | **Superior** — far more sophisticated |
| Skills registry + Tool RAG | `skills.py` + Tool RAG auto-selection in task_runner.sh | **Equivalent** |

---

## Section 2: Gaps — Patterns HiClaw Does Better

### GAP-1: Credential Isolation (HIGH PRIORITY)

**HiClaw approach:** Higress AI Gateway holds real API keys. Workers receive scoped consumer tokens only. A compromised worker process cannot exfiltrate the real key.

**Otto current:** `task_runner.sh` inherits `ANTHROPIC_API_KEY` directly from systemd environment. Any task — including user-submitted code tasks — runs with the real key in its process environment.

**Risk:** Medium. On a single-tenant VM with controlled tasks, exploitation requires task code to be malicious. But the pattern is architecturally unsound.

**Fix:** Add `/llm/proxy` endpoint to Memory API that accepts a scoped request and calls Anthropic. Task runner uses this instead of direct API key. Real key lives only in Memory API's environment.

**Implementation effort:** 2 tasks (~$6). Non-breaking — task_runner.sh still calls `claude` CLI (which already routes through Anthropic), so this is lower priority than it sounds. The CLI itself holds credentials, not task_runner.sh. **Actual risk: LOW.** Still worth doing for posture.

---

### GAP-2: Artifact Path References Instead of Payload Inflation (MEDIUM PRIORITY)

**HiClaw approach:** Workers store large outputs (code, docs, temp data) to MinIO shared filesystem, return file paths in completion payloads. Manager reads only what it needs. This prevents token inflation in task chaining.

**Otto current:** Task completion posts full output text to `/tasks/{id}/complete`, stored in DB. Heartbeat reads the DB field. For large outputs (>2KB), this inflates context unnecessarily when downstream tasks or heartbeat loads task history.

**Fix:** In `task_runner.sh`, after task execution:
```bash
OUTPUT_SIZE=$(echo "$TASK_OUTPUT" | wc -c)
if [ "$OUTPUT_SIZE" -gt 2048 ]; then
    mkdir -p "$LOG_DIR/$TASK_ID"
    echo "$TASK_OUTPUT" > "$LOG_DIR/$TASK_ID/output.md"
    COMPLETION_OUTPUT="[output written to ${LOG_DIR}/${TASK_ID}/output.md — $(echo $OUTPUT_SIZE) bytes]"
else
    COMPLETION_OUTPUT="$TASK_OUTPUT"
fi
```

Heartbeat and downstream tasks read the file when they need full content, DB stores the pointer. This mirrors HiClaw's MinIO pattern without needing S3.

**Implementation effort:** 1 task (~$2). High value for long-running tasks.

---

### GAP-3: Consistency — Heartbeat Sometimes Bypasses the Plan System (MEDIUM PRIORITY)

**HiClaw pattern:** Manager Agent is the ONLY decomposition path. There is no way for tasks to be created that bypass the Manager. All task creation flows through one routing point.

**Otto gap (from prior research memory):** Heartbeat sometimes creates tasks directly (via POST /tasks) rather than going through the plan classifier, bypassing dependency tracking and DAG execution. This means some work runs without dependency enforcement and without the benefits of agent auto-employment.

**Fix:** Enforce a rule in heartbeat.md:
- Single-step work: `POST /tasks` then `/run` is fine
- Multi-step work: ALWAYS use `POST /task-plans` — never create sequential tasks manually

This is a behavioral/prompt fix, not a code fix. Update heartbeat.md to add this constraint explicitly.

**Implementation effort:** Edit to heartbeat.md (trivial). High value for plan observability.

---

### GAP-4: Hot-Reload for Agent Configs (LOW PRIORITY)

**HiClaw approach:** OpenClaw detects config changes in ~300ms, auto-reloads. No restart needed when agent prompts change.

**Otto current:** Changes to `.claude/agents/*.md` take effect on the next task spawn (claude CLI loads agents fresh each invocation), so this is actually less of an issue than it sounds. The heartbeat prompt itself (`.claude/agents/heartbeat.md`) does NOT hot-reload mid-session, but it's invoked fresh each heartbeat cycle anyway.

**Assessment:** Otto's architecture inherently hot-reloads because each task spawns a fresh claude CLI invocation. **This gap does not apply to Otto.** The only case where it matters is if otto-memory service needs an agent config change — that requires a service restart. Not worth building an inotify watcher.

**Verdict:** Not a real gap for Otto's architecture.

---

### GAP-5: Anti-Swarming / Concurrency Gate (LOW PRIORITY)

**HiClaw approach:** Agents only trigger LLM calls when @mentioned. Prevents uncoordinated concurrent LLM operations.

**Otto current:** IVT priority queue serializes kernel LLM calls. Task runner has `max_concurrent` limit (5). However, heartbeat + reflection + up to 5 task runners can ALL be making LLM calls simultaneously, with no cross-channel coordination.

**Assessment:** This is by design — Otto's parallel task execution is a feature, not a bug. The IVT handles kernel calls; tasks are explicitly isolated. The only real risk is budget — all 5 tasks + 2 heartbeats + kernel = 7 concurrent claude calls = 7x cost. Budget caps handle this implicitly.

**Verdict:** Not worth adding coordination overhead. Budget discipline + max_concurrent limits are sufficient.

---

## Section 3: Patterns NOT Worth Adopting

| HiClaw Pattern | Reason to Skip |
|---|---|
| **Matrix/Tuwunel protocol** | +500MB infra overhead. WhatsApp + Memory API already serve as the comms layer. Adding an IM server solves a problem Otto doesn't have. |
| **ZeroClaw/NanoClaw Rust runtimes** | Still in development. No stable release. Would require full runtime replacement with no proven benefit over claude CLI. |
| **Container-per-worker isolation** | Single-tenant VM, controlled task content. Container overhead is unnecessary. Otto's task-scoped working directories provide sufficient isolation. |
| **MinIO object storage** | Local filesystem (`~/otto/logs/tasks/`) works equally well for Otto's scale. MinIO makes sense for distributed workers; Otto runs on one VM. |
| **skills.sh on-demand marketplace** | 80K HiClaw skills are community-built for HiClaw's specific multi-agent model. Otto's skills are tighter, more integrated, and more aligned with our specific stack. Quantity ≠ quality. |
| **Element Web UI for agent comms** | OMS at mev.otto.lk already provides the management UI. WhatsApp provides the comms channel. |

---

## Section 4: Implementation Priority

| Priority | Gap | Effort | Value |
|---|---|---|---|
| **P1** | GAP-2: Artifact path references for large outputs | 1 task, ~$2 | Reduces DB bloat, reduces context inflation in task chaining |
| **P2** | GAP-3: Enforce plan system for multi-step heartbeat work | Prompt edit | Improves plan observability and dependency tracking |
| **P3** | GAP-1: Credential isolation via LLM proxy | 2 tasks, ~$6 | Security posture improvement (actual risk is low on single-tenant VM) |
| **SKIP** | GAP-4: Hot-reload | N/A | Not a real gap — claude CLI already reloads per invocation |
| **SKIP** | GAP-5: Anti-swarming | N/A | Budget caps + max_concurrent limits are sufficient |

---

## Section 5: Highest-Value Action

**The single change that would most improve Otto from studying HiClaw:**

Implement artifact path references (GAP-2). Write task outputs >2KB to `~/otto/logs/tasks/{id}/output.md` and store the path in the DB completion payload instead of the full text. This directly mirrors HiClaw's MinIO pattern, reduces DB payload size for large tasks, and reduces context inflation when heartbeat loads task history. It's a 1-task implementation, non-breaking, and immediately operational.

---

## Appendix: What HiClaw Teaches About Architecture Philosophy

HiClaw's core insight is **separation of concerns between coordination artifacts and execution artifacts**:
- Coordination (what to do, decisions, status) → light-weight channel (Matrix rooms / Otto's DB)
- Execution (code, docs, large outputs) → shared filesystem (MinIO / Otto's local FS)

Otto partially follows this but doesn't enforce it. Enforcing it explicitly would improve every layer.

The second insight is **credential isolation by default** — workers should never hold production keys. Otto should internalize this as a standing principle even though the current risk on a single-tenant VM is low.
