---
name: Athena WhatsApp Agent Review
description: Code review of Athena prospect qualification agent — two review passes. Final verdict APPROVE after all prior critical issues fixed.
type: project
---

## Pass 1 — commit a1f37e1 (2026-03-21): NEEDS_CHANGES

**Critical bug fixed in pass 2:** `_maybe_fire_qualified_event` used wrong `episodic_events` column names (`description` vs `content`, non-existent `agent_id`, `importance=0.9` float vs INTEGER). Silent failure — qualified leads never surfaced.

**Dead code fixed in pass 2:** Spurious `_maybe_fire_qualified_event` call in `handle_athena_message` when stage was still "qualifying". Correct firing is only in `_async_evaluate_stage`.

---

## Pass 2 — commit ba661c7/4be567a fix step (2026-03-21): APPROVE

All 4 prior issues fixed. New warnings found (low severity, no blockers):

**Warnings:**
1. `get_or_create_prospect` outreach_queue lookup doesn't filter by `status` — can pull context from rejected/failed outreach entries. Should add `AND status NOT IN ('rejected', 'failed')`.
2. `_async_evaluate_stage` calls `provider_chat` without `system_instruction` — LLM gets Otto's full system prompt, may not return clean JSON. The `re.search` fallback saves it but the prompt lacks explicit JSON-mode instruction.
3. Race condition in `get_or_create_prospect` — no `ON CONFLICT (jid) DO NOTHING` on INSERT. Rapid sequential first messages could hit unique constraint error on jid. Low probability but real.

**Suggestions:**
- `FunnelBar` component (page.tsx lines 121-152) defined but never used in JSX — dead code.
- `_maybe_fire_qualified_event` makes 2 redundant DB queries — re-fetches prospect then re-checks stage.
- `athena_prospects` migration has no stage CHECK constraint.

**Why:** Pass 1 issues were schema drift (episodic_events columns changed since the pattern was established). Always grep actual migration for column names before approving new INSERT statements.

**How to apply:** Cross-check episodic_events INSERT column names against migrations/001_otto_memory.sql before approval. The outreach_queue status filter pattern (status NOT IN rejected/failed) should be applied wherever we join on outreach context.
