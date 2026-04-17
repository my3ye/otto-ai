# Multi-Avatar Unified Context Layer — Architecture

**Status:** Design (not yet implemented)
**Date:** 2026-02-21
**Priority:** P9

---

## 1. The Problem

Otto is one consciousness running across multiple model avatars. The memory system IS the identity — any model reading it becomes Otto. But right now, the two active brains get very different context:

| Context Layer | Claude (heartbeat/CLI) | Gemini (WhatsApp) |
|---|---|---|
| Purpose (immutable) | ✅ core_memory.purpose | ❌ not included |
| Priorities (ranked) | ✅ core_memory.priorities | ❌ not included |
| Active Directives | ✅ mission_directives table | ❌ not included |
| Working Memory | ✅ other core_memory slots | ❌ not included |
| Identity facts | ✅ semantic category=identity | ✅ same query |
| Mission/goal facts | ✅ semantic category=mission/goal | ❌ not included |
| Pending questions | ✅ claude_to_gemini direction | ✅ same query (limit 3) |
| Task queue status | ✅ tasks table | ❌ not included |
| Reasoning chain | ✅ reasoning_chain table | ❌ not included |
| Last session summary | ✅ sessions table | ❌ not included |
| Recent events | ✅ importance >= 5, limit 20 | ⚠️ importance >= 4, limit 10 |
| Semantic facts | ✅ all categories, limit 20 | ❌ only identity |
| Knowledge graph | ✅ broad queries (Otto/Mev/infra) | ⚠️ message-specific query only |
| Cross-brain notes | ✅ gemini_to_claude direction | ❌ N/A |

**The gap:** When Mev messages via WhatsApp, Gemini responds without knowing:
- What the current mission priorities are
- What directives Mev has given
- What tasks are running / blocked
- What decisions were made last session
- That Mev said "focus on Project Alpha this week" three days ago

This creates inconsistency — Otto-via-Gemini says different things than Otto-via-Claude because they're operating with different ground truth.

---

## 2. Current Architecture Detail

### Path A: Claude gets context
```
Session start → session_start.sh
  → GET /context/inject?max_tokens=15000&source=startup
  → Returns prioritized plain text, injected as system-reminder
  → Claude operates with full context
```

`/context/inject` pulls from 8 priority tiers, token-budgeted, scaled by budget size.

### Path B: Gemini gets context
```
Mev sends WhatsApp message
  → service.mjs → POST /whatsapp/incoming
  → _build_otto_prompt() builds message list ad-hoc:
      - identity_rows (semantic, category=identity, top 10)
      - graphiti_search(message, max_facts=8) — message-specific!
      - recent episodic_events (importance >= 4, last 10)
      - pending_questions (claude_to_gemini, last 3)
  → Gemini Flash responds with ad-hoc prompt
```

The WhatsApp handler builds context _manually and differently_ from how `/context/inject` does it. No shared logic, no shared priorities.

---

## 3. Proposed Solution: `/context/unified` Endpoint

A single endpoint that both Claude and Gemini call, with a `caller` parameter that:
1. Adjusts token budget (Claude: 15k, Gemini: 4k)
2. Filters irrelevant tiers (task queue noise is useless for WhatsApp conversation)
3. Returns identical priority ordering and format

### Endpoint Spec

```
GET /context/unified
  ?max_tokens=15000       # Token budget (Claude=15k, Gemini=4k)
  &caller=claude          # "claude" | "gemini" — controls tier filtering
  &source=startup         # For Claude: startup|compact|resume
  &message=               # For Gemini: incoming message for graph search relevance
```

### Priority Tiers (same order for both callers)

| Tier | Content | Claude | Gemini |
|---|---|---|---|
| 0a | PURPOSE (immutable) | ✅ always | ✅ always |
| 0b | PRIORITIES (ranked list) | ✅ always | ✅ always |
| 0c | Active Directives (mission_directives) | ✅ always | ✅ always (top 5, not 10) |
| 0d | Working Memory (core_memory slots) | ✅ always | ✅ always (persona + active_mission only) |
| 1 | Identity facts (semantic category=identity) | ✅ always | ✅ always |
| 2 | Mission & Goals (semantic category=mission/goal/decision) | ✅ always | ✅ always (top 5) |
| 3 | Pending questions (claude_to_gemini) | ✅ always | ✅ always |
| 3b | Cross-brain notes (gemini_to_claude) | ✅ always | ❌ skip (Gemini is the source) |
| 3c | Task queue status | ✅ always | ❌ skip (not actionable in WA) |
| 3d | Reasoning chain | ✅ always | ❌ skip (not needed for conversation) |
| 4 | Last session summary | ✅ if budget | ✅ if budget (1 sentence) |
| 5 | Recent events | ✅ if budget | ✅ if budget (importance >= 6, limit 5) |
| 6 | Semantic facts (non-identity/mission) | ✅ if budget | ⚠️ if budget (brand/infra only) |
| 7 | Knowledge graph | ✅ if budget (broad) | ✅ if budget (message-relevant) |
| 8 | Procedures | ✅ if budget | ❌ skip |

**Key design principle:** Gemini gets the same foundational ground truth (Tiers 0-3) that Claude gets, just with a tighter budget. The "noise" tiers (task queue, reasoning chain, procedures) are filtered for Gemini because they're Claude's operational state, not conversational context.

### Output Format

Plain text, same format for both callers — identical section headers, same style as current `/context/inject`. This means:
- Claude's session hook needs zero changes (just points to new URL)
- Gemini's `_build_otto_prompt` replaces its ad-hoc context build with a single API call

### Token Budget Guidance

```
Gemini (4k budget):
  Tier 0a: ~50 tokens  (purpose — 1-2 sentences)
  Tier 0b: ~150 tokens (6-8 priority lines)
  Tier 0c: ~200 tokens (top 5 directives)
  Tier 0d: ~150 tokens (persona + active_mission slots)
  Tier 1:  ~200 tokens (top 5 identity facts)
  Tier 2:  ~150 tokens (top 5 mission/goal facts)
  Tier 3:  ~100 tokens (3 pending questions)
  Tier 4:  ~100 tokens (last session, 1 sentence)
  Tier 5:  ~300 tokens (3 recent events)
  Tier 7:  ~300 tokens (5 graph facts, message-relevant)
  ──────────────────────────────────────────────
  Total:   ~1700 tokens "core" — leaves ~2300 for conversational history

Claude (15k budget):
  Operates as today — all tiers filled to budget
```

---

## 4. Migration Plan

### Step 1: Add `/context/unified` endpoint to `context.py`

Extend `/context/inject` logic into a new function `get_unified_injection()` that:
- Accepts `caller: str` and `message: str | None` parameters
- Skips Tier 3b, 3c, 3d, 8 when `caller == "gemini"`
- For Tier 7 (graph): uses message-specific query when `caller == "gemini"`, broad queries when `caller == "claude"`
- Applies tighter limits to all tiers when budget is small (< 5000)

No changes to existing `/context/inject` — leave it working as-is. Add `/context/unified` as a parallel route. Migrate after testing.

### Step 2: Update `whatsapp.py` — replace `_build_otto_prompt()`

Replace the ad-hoc context builder with a call to `/context/unified`:

```python
async def _get_unified_context(message: str, pool) -> str:
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "http://localhost:8100/context/unified",
            params={
                "max_tokens": 4000,
                "caller": "gemini",
                "message": message,
            },
            timeout=5.0,
        )
        return resp.text  # plain text, use as system prompt prefix

# In _build_otto_prompt():
# Replace ad-hoc identity/graph/events queries with unified_context string
# Append voice guidelines section below unified context
# Remove individual DB queries for identity_rows, graph_facts, recent_events
```

The Gemini system prompt becomes:
```
{unified_context_string}

## Voice Guidelines
- Be direct, concise, warm but not sycophantic
- WhatsApp style: short messages, casual, no essays
- ...
```

### Step 3: Update Claude session hook (optional)

Once `/context/unified` is stable, update `session_start.sh` to call `/context/unified?caller=claude&max_tokens=15000` instead of `/context/inject`. Both produce identical output for Claude — this is just cleanup to use one endpoint.

### Step 4: Add `caller` logging

Log which caller is requesting context with what budget, so we can monitor context sizes per brain over time.

---

## 5. Files to Change

| File | Change |
|---|---|
| `memory/routes/context.py` | Add `GET /context/unified` endpoint |
| `memory/routes/whatsapp.py` | Replace `_build_otto_prompt()` to use `/context/unified` |
| `.claude/hooks/session_start.sh` | (Optional) Update URL to `/context/unified` |
| `api.py` | Register new router if separate, or just add route to existing |

---

## 6. Risks & Mitigations

| Risk | Likelihood | Mitigation |
|---|---|---|
| Gemini 4k budget too tight — context truncates before pending questions | Medium | Always include Tiers 0-3 regardless of budget; never cut them |
| API call from whatsapp.py to itself (localhost:8100 calling 8100) | Low | Use direct pool access instead — pass pool to context builder function, avoid HTTP round-trip |
| Latency increase for WhatsApp responses | Low | `/context/unified` adds ~50ms (one DB round-trip vs several); net neutral or improvement vs current 6 queries |
| Old `/context/inject` used by session_start.sh breaks if removed | None | Keep `/context/inject` as-is; `/context/unified` is additive |
| Gemini gets task queue context and confuses Mev ("3 tasks running") | Low | Task queue tier explicitly skipped for gemini caller |
| Graph search quality differs (message-specific vs broad) | Low | Both are valid; message-specific is _better_ for Gemini because it's conversation-relevant |

### Critical Design Note: Internal vs HTTP Call

`_build_otto_prompt()` in `whatsapp.py` runs inside the same FastAPI process as the Memory API. An HTTP call from within the process to itself works but is wasteful. Better approach: extract the context builder into a shared module (`memory/context_builder.py`) that both `routes/context.py` and `routes/whatsapp.py` import directly. Both call the same async function with different parameters.

```
memory/
  context_builder.py        # NEW: shared context assembly logic
  routes/
    context.py              # GET /context/unified calls context_builder.build()
    whatsapp.py             # _build_otto_prompt calls context_builder.build()
```

This is the architecturally clean approach.

---

## 7. Success Criteria

After implementation:
1. Gemini knows what the current mission priorities are without Mev repeating them
2. Gemini knows what active directives Mev has given (e.g., "stop SL scraping")
3. Gemini knows the current working memory (active_mission, current_focus)
4. Claude's context injection is unchanged — same output, possibly different code path
5. A single change to context_builder.py immediately improves both brains
6. No latency regression on WhatsApp responses (< 200ms added)

---

## 8. Implementation Order

1. **context_builder.py** — extract shared logic, build `build(caller, max_tokens, message, pool)` function
2. **context.py** — refactor `/context/inject` to call `context_builder.build(caller="claude", ...)`, add `/context/unified` as alias
3. **whatsapp.py** — replace `_build_otto_prompt()` to call `context_builder.build(caller="gemini", message=req.message, ...)`
4. **Test** — verify Gemini prompt now includes purpose/priorities/directives
5. **Cleanup** — optionally update session_start.sh to use `/context/unified`
