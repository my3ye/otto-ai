# Architecture: Heartbeat Cycle Improvements
**Date:** 2026-03-23
**Source research:** Constraint-injection synthesis (task 4354b390), Honcho evaluation (task 9e30d75a)
**Status:** FINAL — ready for implementation

---

## Overview

Three ranked improvements derived from validated research. Each is independent and can be implemented separately. Priority order: Rank 1 first, then Rank 2, then Rank 3. Honcho (Rank 4) is deferred — it targets WebAssist, not the heartbeat cycle.

---

## Improvement 1: Constraint-Injection Gates in heartbeat.md (RANK 1 — P7 IMMEDIATE)

### Problem

The heartbeat OODA loop has no abort path before task creation. The existing `COLLABORATE CHECK` fires *after* `DECIDE` — it determines whether to ask Mev, not whether to abort execution. Three mid-chain abort gates are needed, following the PG-CoT pattern from OMNIFLOW (arXiv 2603.15797), validated by LlamaFirewall, SagaLLM, and Task Shield (all 2026).

### Target File

`~/otto/.claude/agents/heartbeat.md`

### Gate Locations in OODA Loop

The ReflAct block currently has: `PURPOSE CHECK → PRIORITY SCAN → OBSERVE → ORIENT → LEARN FROM MISTAKES → ANTICIPATE → DECIDE → COLLABORATE CHECK → ACT → REFLECT`

Three gates insert between existing steps:

```
PURPOSE CHECK → PRIORITY SCAN → OBSERVE → ORIENT → LEARN FROM MISTAKES
                                                                         ↓
                                                                    [GATE A: budget/rate-limit]
                                                                         ↓
                                                                    ANTICIPATE → DECIDE
                                                                                      ↓
                                                                                 [GATE B: directive alignment]
                                                                                      ↓
                                                                              COLLABORATE CHECK → ACT
                                                                                                    ↓
                                                                                               REFLECT → EXPECTED
                                                                                                              ↓
                                                                                                         [GATE C: idle tag]
                                                                                                              ↓
                                                                                                        RL2F WRITE
```

---

### Gate A — Post-LEARN, Pre-ANTICIPATE: Budget/Rate-Limit Abort

**Position:** Insert between `LEARN FROM MISTAKES` and `ANTICIPATE` steps.

**Purpose:** Hard abort if conditions make task creation unsafe. Binary — no ambiguity, no subjective judgment.

**Implementation — text to insert in heartbeat.md:**

```markdown
GATE A — Budget & Rate-Limit Check (abort if unsafe):

Check budget remaining and rate-limit state before planning any actions:

```bash
# Check budget
BUDGET=$(curl -sf http://localhost:8100/workspace/read?key=heartbeat_budget 2>/dev/null \
  | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('value', '1.00'))" 2>/dev/null || echo "1.00")

# Check rate limit flag
RATE_LIMIT=$(curl -sf http://localhost:8100/workspace/read?key=rate_limited 2>/dev/null \
  | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('value', 'false'))" 2>/dev/null || echo "false")
```

ABORT conditions (if either is true, skip ANTICIPATE + DECIDE entirely, jump to REFLECT):
- Budget remaining < $0.10
- Rate limit flag = "true"

If aborting:
1. Log to episodic: `{"event": "gate_a_abort", "reason": "budget < 0.10 OR rate_limited"}`
2. Write to workspace handoff: note the abort reason for next cycle
3. Skip to REFLECT step

If not aborting: continue to ANTICIPATE.
```

**Existing heartbeat.md section to modify:**

The `LEARN FROM MISTAKES` section ends at approximately line 88 (after the RL2F accuracy check). Gate A text inserts immediately after, before the `ANTICIPATE` section (line 98).

---

### Gate B — Post-DECIDE, Pre-COLLABORATE CHECK: Directive Alignment

**Position:** Insert between `DECIDE` step and `COLLABORATE CHECK`.

**Purpose:** Verify each proposed action in the DECIDE list serves an active P1-P10 directive. Prevents misaligned task creation entering the queue.

**Implementation — text to insert in heartbeat.md:**

```markdown
GATE B — Directive Alignment Check (verify each DECIDE action):

Before proceeding to COLLABORATE CHECK, verify each action in your DECIDE list:

For EACH action listed in DECIDE:
1. Identify which Mev directive (from the PURPOSE + PRIORITIES block) this action serves
2. Assign a priority number: P1-P10 (must match an active directive rank)
3. Check: "If Mev's P1 has unfinished work, why am I doing this P5 action?"

ABORT rule: If an action serves NO active directive — remove it from the DECIDE list.
DEFER rule: If P1/P2 has unfinished Mev-blocked work, cap DECIDE to:
  - 1 monitoring action (check P1 status)
  - 1 communication action (if Mev has been silent 72h+)
  - NO new task creation for P5+ items while P1/P2 are blocked

Log removed actions to episodic:
```bash
curl -sf -X POST http://localhost:8100/episodic/events \
  -H 'Content-Type: application/json' \
  -d '{"event_type": "gate_b_filtered", "content": "Removed action: [action] — no directive match", "source": "heartbeat", "importance": 0.4}'
```

After filtering: proceed to COLLABORATE CHECK with the cleaned DECIDE list.
```

**Existing heartbeat.md section to modify:**

The `DECIDE` step ends around line 111 (after the 3-action list format). Gate B inserts between `DECIDE` (line ~111) and `COLLABORATE CHECK` (line ~113).

---

### Gate C — Post-REFLECT, Pre-RL2F Write: Idle Tagging

**Position:** Modify the RL2F reasoning chain write at the end of the cycle (around line 776-795).

**Purpose:** Tag predictions as `idle_cycle: true/false` before committing to reasoning_chain. Enables clean active-cycle accuracy accounting (Improvement 2 depends on this).

**Implementation — modify the existing RL2F write block in heartbeat.md:**

The existing reasoning chain write block (around line 776-795) writes:

```bash
curl -s -X POST http://localhost:8100/reasoning \
  -H 'Content-Type: application/json' \
  -d "$(python3 -c "
import json
print(json.dumps({
    'heartbeat_type': 'orchestrator',
    'reasoning': '<WHY>',
    'decisions': '<DECIDED>',
    'expected': '<EXPECTED>',
    'metadata': {}
}))")"
```

**Modify** the `metadata` field to include idle detection:

```bash
curl -s -X POST http://localhost:8100/reasoning \
  -H 'Content-Type: application/json' \
  -d "$(python3 -c "
import json
# Determine if this was an idle cycle
# Idle = queue was 0/0/0 AND no tasks created AND no message sent
tasks_created = 0  # replace with actual count from this cycle
msg_sent = False   # replace with actual bool from this cycle
queue_was_empty = True  # replace with actual queue state
idle_cycle = (tasks_created == 0 and not msg_sent and queue_was_empty)

print(json.dumps({
    'heartbeat_type': 'orchestrator',
    'reasoning': '<WHY you made the choices you did this cycle — 1-2 sentences>',
    'decisions': '<DECIDED — what you actually did>',
    'expected': '<EXPECTED — what you predict will happen next cycle>',
    'metadata': {
        'idle_cycle': idle_cycle,
        'tasks_created': tasks_created,
        'msg_sent': msg_sent,
    }
}))")"
```

**How idle is defined:**
- `idle_cycle = True` when: tasks_created == 0 AND msg_sent == False AND queue was 0/0/0 at cycle start
- `idle_cycle = False` when: any of the above is False — task created, message sent, or queue had work

---

## Improvement 2: RL2F Idle-Cycle Window Fix (RANK 2 — P6)

### Problem

`GET /reasoning/accuracy` returns 36% from a 50-entry window. Research confirms ~29 of 50 entries are idle-cycle predictions (queue=0/0/0, Mev silent, system stable) that score as "partial" by convention. They inflate the denominator without providing learning signal. The true active-cycle accuracy is unknown because the window treats all entries equally.

### Target Files

1. `~/otto/memory/routes/reasoning.py` — modify `/accuracy` endpoint
2. `~/otto/.claude/agents/heartbeat.md` — Improvement 1 Gate C provides the `idle_cycle` flag

### DB Schema

No migration needed. The `reasoning_chain.metadata` column is already a JSONB field. Gate C (Improvement 1) writes `idle_cycle: true/false` into it. The fix reads that field.

**Verify current schema:**
```bash
docker exec memory-postgres-1 psql -U otto -d memory -c "\d reasoning_chain"
```

Expected output includes: `metadata jsonb`

### API Change: `/reasoning/accuracy`

**Current query (lines 270-278 in reasoning.py):**
```python
rows = await pool.fetch(
    f"""SELECT outcome_match, cycle_ts
        FROM reasoning_chain
        WHERE outcome_match != 'pending'
        {type_filter}
        ORDER BY cycle_ts DESC
        LIMIT $1""",
    *params,
)
```

**Modified query — adds `is_idle` field:**
```python
rows = await pool.fetch(
    f"""SELECT outcome_match, cycle_ts,
               COALESCE((metadata->>'idle_cycle')::boolean, false) AS is_idle
        FROM reasoning_chain
        WHERE outcome_match != 'pending'
        {type_filter}
        ORDER BY cycle_ts DESC
        LIMIT $1""",
    *params,
)
```

**Modified `_stats()` function — adds active-cycle split:**

Replace existing `_stats()` function (lines 291-306) with:

```python
def _stats(entries):
    total = len(entries)
    if total == 0:
        return {
            "total": 0, "matched": 0, "partial": 0, "miss": 0,
            "accuracy_pct": 0.0, "active_total": 0, "active_accuracy_pct": 0.0
        }
    matched = sum(1 for r in entries if r["outcome_match"] == "matched")
    partial = sum(1 for r in entries if r["outcome_match"] == "partial")
    miss = sum(1 for r in entries if r["outcome_match"] == "miss")

    # Active-cycle split (entries where idle_cycle = False or missing)
    active = [r for r in entries if not r.get("is_idle", False)]
    active_total = len(active)
    active_matched = sum(1 for r in active if r["outcome_match"] == "matched")

    return {
        "total": total,
        "matched": matched,
        "partial": partial,
        "miss": miss,
        "accuracy_pct": round(matched / total * 100, 1),
        "partial_pct": round(partial / total * 100, 1),
        "miss_pct": round(miss / total * 100, 1),
        "active_total": active_total,
        "active_accuracy_pct": round(active_matched / active_total * 100, 1) if active_total > 0 else 0.0,
        "idle_count": total - active_total,
    }
```

**Modified return value (lines 321-325):**

```python
return {
    **curr_stats,
    "trend": trend,
    "prior_accuracy_pct": prev_stats["accuracy_pct"],
    "prior_active_accuracy_pct": prev_stats.get("active_accuracy_pct", 0.0),
    "window": window,
}
```

### Heartbeat.md Change for Improvement 2

The `LEARN FROM MISTAKES` section currently reads (line 87):
> `curl -sf http://localhost:8100/reasoning/accuracy` and read the `accuracy_pct` field.

**Add** after the existing accuracy check instruction:
```markdown
- Also read `active_accuracy_pct` from the same response — this excludes idle-cycle predictions
  (queue=0/0/0, no tasks created) which carry no learning signal.
  Use `active_accuracy_pct` as the primary signal for whether your reasoning is improving.
  `accuracy_pct` is still shown for completeness but is distorted by idle cycles.
```

---

## Improvement 3: S-MMU Similarity Threshold Gate (RANK 3 — P5)

### Problem

`_load_relevant_slices()` in `smmu.py` loads slices ordered by a composite score (similarity × 0.4 + importance × 0.25 + access × 0.15 + recency × 0.2) but applies no minimum similarity cutoff. A slice with similarity=0.1 but high importance and recency can enter L1, acting as a distractor. Context Rot research (Chroma 2026) identifies retrieval near-misses as an accuracy killer.

### Target File

`~/otto/memory/kernel/smmu.py`

### Current Code (lines 231-243)

```python
rows = await pool.fetch(
    """SELECT s.id, s.label, s.memory_ids, s.token_count, s.category,
              p.importance_score, p.access_count,
              1 - (s.centroid <=> $1::vector(1536)) AS similarity
       FROM semantic_slices s
       JOIN semantic_page_table p ON p.slice_id = s.id
       WHERE s.centroid IS NOT NULL
       ORDER BY (0.4 * (1 - (s.centroid <=> $1::vector(1536)))
               + 0.25 * COALESCE(p.importance_score, 0.5)
               + 0.15 * LEAST(p.access_count::float / 100.0, 1.0)
               + 0.2 * GREATEST(0, 1.0 - EXTRACT(EPOCH FROM NOW() - s.updated_at) / 2592000.0)
               ) DESC
       LIMIT 10""",
    embedding_str,
)
```

### Modified Code

Add `HAVING` clause after `JOIN` condition to filter low-similarity slices:

```python
rows = await pool.fetch(
    """SELECT s.id, s.label, s.memory_ids, s.token_count, s.category,
              p.importance_score, p.access_count,
              1 - (s.centroid <=> $1::vector(1536)) AS similarity
       FROM semantic_slices s
       JOIN semantic_page_table p ON p.slice_id = s.id
       WHERE s.centroid IS NOT NULL
         AND (1 - (s.centroid <=> $1::vector(1536))) >= 0.5
       ORDER BY (0.4 * (1 - (s.centroid <=> $1::vector(1536)))
               + 0.25 * COALESCE(p.importance_score, 0.5)
               + 0.15 * LEAST(p.access_count::float / 100.0, 1.0)
               + 0.2 * GREATEST(0, 1.0 - EXTRACT(EPOCH FROM NOW() - s.updated_at) / 2592000.0)
               ) DESC
       LIMIT 10""",
    embedding_str,
)
```

**Threshold decision:** Research recommended 0.7, but 0.7 is aggressive — it may drop valid slices during off-topic or ambiguous prompts (e.g., heartbeat's generic "what needs doing" prompt). **Use 0.5 as the initial value.** This filters clear near-misses while preserving borderline-relevant slices. Adjust upward to 0.65-0.7 if L1 quality improves and no regressions appear after 48h.

**Why WHERE, not HAVING:** PostgreSQL cannot reference a computed column alias in `WHERE`, but can inline the expression. The expression `(1 - (s.centroid <=> $1::vector(1536))) >= 0.5` in `WHERE` is evaluated at the same point as the ORDER BY expression and uses the index efficiently. No performance regression expected.

**Fallback behavior:** If the threshold filters ALL slices (edge case: very novel prompt), the existing fallback path at line 296 (`_load_legacy_context`) handles it. No new fallback needed.

---

## Implementation Order

| Step | Action | File | Effort |
|------|--------|------|--------|
| 1 | Add Gate A text block after LEARN FROM MISTAKES | `heartbeat.md` | ~15 lines |
| 2 | Add Gate B text block after DECIDE | `heartbeat.md` | ~20 lines |
| 3 | Modify Gate C (RL2F write block) to include idle metadata | `heartbeat.md` | ~10 lines |
| 4 | Modify `_stats()` in reasoning.py to add active-cycle split | `reasoning.py` | ~15 lines |
| 5 | Modify accuracy SQL query to fetch `is_idle` field | `reasoning.py` | ~3 lines |
| 6 | Update LEARN FROM MISTAKES instructions re: active_accuracy_pct | `heartbeat.md` | ~4 lines |
| 7 | Add similarity threshold WHERE clause to smmu.py | `smmu.py` | ~2 lines |

All changes are additive (gates add new text, functions add new return fields). No deletions. Rollback = revert the added lines.

---

## Deferred: Honcho Integration

The Honcho research (task 9e30d75a) confirms a real gap in WebAssist (no scalable per-user modeling for external users), with stack compatibility verified. However, this is a **WebAssist** improvement, not a heartbeat cycle change. Deferred to a separate task. Decision tree: Mev must first choose managed (Option D, Honcho SDK via app.honcho.dev) vs sovereign (Option C, native Deriver background job into pgvector). This is a sovereignty decision.

---

## Risk Assessment

| Improvement | Risk | Mitigation |
|-------------|------|------------|
| Gate A | Gate fires too aggressively, blocking valid work | Binary thresholds ($0.10, rate_limited) — no ambiguity |
| Gate B | Removes valid actions due to overly strict filtering | Logging all removals to episodic — review after 3 cycles |
| Gate C | Idle detection mislabels active cycles | Conservative definition (all 3 conditions must be true) |
| RL2F accuracy split | active_accuracy_pct starts at 0% (no tagged entries) | Dual reporting (both metrics shown) during ramp-up |
| S-MMU threshold 0.5 | May drop borderline-relevant slices | Threshold tunable; fallback to legacy context if all slices filtered |
