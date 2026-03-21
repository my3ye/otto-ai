---
name: Athena WhatsApp Agent Review
description: Code review of Athena prospect qualification agent (commit a1f37e1, 2026-03-21). NEEDS_CHANGES — 1 critical bug (episodic_events INSERT wrong columns), 1 dead code block, 2 warnings.
type: project
---

Review of Athena WhatsApp agent (commit a1f37e1), reviewed 2026-03-21. Verdict: NEEDS_CHANGES.

**Critical bug:** `_maybe_fire_qualified_event` in `gateway/athena_handler.py` inserts to `episodic_events` using wrong column names: `description` (should be `content`), `agent_id` (column doesn't exist), and `importance = 0.9` (column is INTEGER 1-10, should be `9`). The insert will always fail silently — wrapped in try/except that only logs at debug. Means qualified leads NEVER appear in Otto's context, defeating a stated goal.

**Dead code:** Lines 343-348 in `handle_athena_message` fire `_maybe_fire_qualified_event` when `stage == "qualifying"`, but that function immediately returns because the stage hasn't changed to "qualified" yet at that point. The correct firing happens in `_async_evaluate_stage`. This adds a spurious async task per message.

**Warnings:**
- `asyncio.create_task()` without done-callback — unhandled task exceptions silently swallowed
- No limit/offset bounds on list endpoints

**What's good:** Handler.py branch is minimal (4 lines), stage machine is well-designed, async stage eval pattern is correct, phone_variants matching, temperature choices.

**Why:** episodic_events column mismatch is a schema drift issue — the table uses `content` not `description`, and has no `agent_id` column.
**How to apply:** Always cross-check INSERT column names against actual DB schema before approving new episodic event logging code.
