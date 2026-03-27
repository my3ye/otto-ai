# STEM Gap Implementations — Sign-off Review
**Date**: 2026-03-28
**Reviewer**: reviewer agent (65103a87)
**Implementations reviewed**: Dynamic Tool Composition, MCP Externalization, A2A Protocol
**Reference**: `~/otto/docs/stem-agent-gap-analysis-2026-03-28.md`

---

## Review Summary

**NEEDS_CHANGES** — One critical functional bug renders the composition engine practically non-functional. One strategic-level misalignment against the gap analysis. Five warnings. Two are pre-existing carryovers from prior reviews that need final verification.

---

## Critical Issues (must fix)

### 1. Composition engine returns zero chains in all practical cases
`memory/composition.py:142–189`

**What's broken**: The backward-chaining algorithm uses task-description relevance scores (`_score_agent`) to decide whether an intermediate agent may appear in a chain. But intermediate agents are relevant to *intermediate outputs*, not to the *user task*. Result: no chains are ever produced.

**Verified live**:
```
GET /skills/suggest?task=research+and+build+a+defi+integration&compose=true
→ compositions: []

GET /skills/suggest?task=write+an+article+about+defi&compose=true
→ compositions: []
```

**Root cause**: When `_build_chains` runs for content-creator (needs `research_report` from researcher), researcher's score for "write an article" ≈ 0 — it shares no keywords with "write", "article". `0 < threshold(0.1)` → researcher rejected → no chain formed.

Same pattern kills every potential chain: architect scores 0 for "build a feature" (no keywords overlap), researcher scores 0 for content tasks, etc. The only chains that can form require intermediate agents to be independently relevant to the top-level user task, which is rarely true.

**Fix required**: Score intermediate agents by their ability to satisfy the *next agent's* inputs, not by task relevance. Task relevance should only gate the terminal (output-producing) agent. Alternatively, set `relevance_threshold = 0.0` for intermediate agents and filter only on whether the agent produces the needed type.

---

### 2. Strategic priority misalignment
*Gap analysis vs implemented set*

The gap analysis (`stem-agent-gap-analysis-2026-03-28.md`, §3) prescribed:

| Priority | Item | Status |
|---|---|---|
| **P2** | Skills Maturation | ❌ Not implemented |
| **P3** | Caller Profiler (highest novelty, zero equivalent in Otto) | ❌ Not implemented |
| **P4** | Self-Adaptation / failure-branch | ⚠️ Separate task running |
| P5 | A2A Protocol | ✅ Implemented |
| P6 | MCP Externalization | ✅ Implemented |
| P7 | Dynamic Tool Composition | ✅ Implemented |

All three implemented items were rated **LOW priority** or medium-low in the gap analysis. The two highest-impact items (Caller Profiler — "genuinely novel, zero equivalent"; Skills Maturation — "highest compound-leverage") were skipped entirely.

This is not a code defect but it means the STEM sprint delivers less RL2F impact than the gap analysis projected. Flag for Mev's awareness. Self-Adaptation (P4) is being addressed in the concurrent RL2F research task — that's the right move.

---

## Warnings (should fix)

### 3. `in_reply_to` FK has no ON DELETE action
`memory/migrations/078_a2a_messages.sql`, `a2a.py:cleanup_expired_messages`

```sql
in_reply_to UUID REFERENCES a2a_messages(id)  -- no ON DELETE behavior
```

Default is RESTRICT. When the nightly cleanup runs `DELETE FROM a2a_messages WHERE channel_id = X` on a channel with reply threads, PostgreSQL may raise an FK violation on self-referential rows if deletion ordering hits a reply before its parent. Risk is low at current message volume but non-zero. Fix: `ON DELETE SET NULL`.

### 4. MCP `skill_suggest` tool doesn't expose `compose` parameter
`memory/mcp_server.py:287–296`

```python
async def skill_suggest(task_description: str) -> str:
    result = await suggest_skills(task=task_description)  # compose missing
```

The REST endpoint supports `?compose=true` and returns composition chains, but the MCP wrapper hardcodes no-compose. External MCP clients can't access chains. Add `compose: bool = False` parameter to the tool and pass it through.

### 5. MCP `whatsapp_send` has no rate limit
`memory/mcp_server.py:227–246`

Any holder of the MCP token can call `whatsapp_send` without limit. Since MCP is currently internal (localhost:8100), real risk is low. If the MCP token leaks, this becomes a spam vector. Worth adding a simple cooldown check (e.g., max 5 messages/minute) at the tool level.

### 6. Composition intermediate agent scoring uses wrong signal
*(Related to Critical #1, but a design warning regardless of threshold adjustment)*

`composition.py:178` — `if agent_scores.get(producer["name"], 0) < relevance_threshold: continue`

Even if threshold is lowered to 0.0, this line will correctly pass all agents, but the root issue is that `total_relevance` (used for sorting) will be misleadingly low for otherwise-valid chains. The scoring function should be redesigned for multi-step contexts.

### 7. A2A rate limit is not atomic
`a2a.py:75–82`

```python
recent_count = await pool.fetchval("SELECT COUNT(*) ...")  # step 1
...
await pool.fetchrow("INSERT ...")  # step 2
```

Two concurrent senders at exactly 20 messages could both pass the check. At 20 msg/hr/agent, this is a theoretical concern only but worth noting for completeness.

---

## Suggestions (nice to have)

- **`memory/mcp_auth.py:25`**: The `if not request.url.path.startswith("/mcp")` guard is dead code — this middleware only runs inside the MCP sub-app, so all requests reaching it are already `/mcp/*`. Not a bug, just unnecessary.

- **`a2a.py:227`**: `POST /a2a/channel` returns `A2AMessage` but semantically callers want channel metadata. The seed message returned isn't the same type as the channel. Consider adding a `POST /a2a/channel` response that wraps the channel_id + created message.

- **`composition.py:18–47`**: `_OUTPUT_HINTS` ordering: "investigate security" → `research_report` wins (11 chars) over `security_report` (8 chars for "security"). Security investigation tasks get the wrong output type. Multi-keyword matching would fix this.

- **`memory/mcp_server.py:148–182`**: `task_create` sets `created_by="mcp"` hardcoded. No identity for which external system/user triggered the task. Fine for now; would help audit if MCP use grows.

---

## What's Good

- **CTE cleanup SQL correct**: All three `DELETE ... RETURNING count(*)` bugs from the prior review are properly fixed. The CTE pattern works against live PostgreSQL (verified).
- **`hmac.compare_digest` in MCP auth**: Constant-time comparison prevents timing attacks on token validation.
- **A2A task_runner.sh injection**: Variable expansion happens at `A2A_BLOCK` build time. Agents receive resolved UUIDs, not shell expressions. The peers URL is pre-computed correctly.
- **Migration + indexes**: Table schema is clean. Three indexes cover the primary query patterns (channel+time, recipient, unread). Check constraint on `message_type` matches Python-side validation.
- **All UUID path params typed**: `channel_id: UUID` on all endpoints, no str→UUID injection surface.
- **Fire-and-forget completion signals**: `asyncio.create_task(_a2a_completion_signal(...))` wraps in try/except — A2A errors never block task completion.
- **MCP mount is non-fatal**: Wrapped in try/except with warning. API continues if MCP SDK fails.
- **`read_by` idempotency**: `NOT ($1 = ANY(read_by))` guard in the update correctly prevents double-counting reads.
- **Composition `incomplete` flag**: Good signal for callers when max depth was hit with unsatisfied inputs.
- **Circular import handled correctly**: `composition.py ↔ routes/skills.py` mutual dependency is lazy (function-level imports only). No load-time cycle.

---

## Integration Conflicts

None detected. The three implementations are independent:
- A2A: infra-level (DB mailbox + task_runner injection)
- MCP: gateway-level (SSE sub-app mount)
- Composition: routing-level (plan classifier hint injection)

No shared state or conflicting endpoints. All three are live and `/health` returns `{"status":"healthy","db":true}`.

---

## Test Coverage

No automated tests exist for any of the three implementations. Manual verification was done live:
- `POST /a2a/send` → message created ✓
- `GET /a2a/poll` → message returned, read_by updated ✓
- `GET /mcp/sse` with token → SSE stream ✓, without token → 401 ✓
- `GET /skills/suggest?compose=true` → skills returned, compositions = 0 (the bug) ✓
- Cleanup SQL CTEs → verified against live DB ✓

---

## Verdict by Implementation

| Implementation | Verdict | Reason |
|---|---|---|
| **A2A Protocol** | APPROVE | API, migration, task_runner injection all correct. Prior SQL critical fixed. 2 warnings (FK, rate limit) are low-risk at current scale. |
| **MCP Externalization** | APPROVE | Auth correct (hmac, 401 verified). 15 tools functional. Non-fatal mount. Warning: whatsapp_send rate limit, skill_suggest compose gap. |
| **Dynamic Tool Composition** | NEEDS_CHANGES | Core algorithm is correct but returns empty in all practical cases (Critical #1). Needs threshold redesign before it delivers any value. |

---

## Required Actions Before Full Sign-off

1. **Fix composition intermediate-agent scoring** (Critical #1): Either remove relevance filter for non-terminal agents, or pass `required_output` for each intermediate input rather than filtering by user-task relevance. Verify with live test that "research+build" and "write+article" return ≥1 chain.

2. **Add `ON DELETE SET NULL` to `in_reply_to` FK** (Warning #3): Migrate the constraint to prevent potential cleanup failures on reply chains.

3. **Expose `compose` in MCP tool** (Warning #4): Pass `compose: bool = False` through to `suggest_skills`.

Items 2 and 3 are fast fixes (single-line each). Item 1 is the meaningful change.

---

*Report generated by reviewer agent. Read-only — no code modified.*
