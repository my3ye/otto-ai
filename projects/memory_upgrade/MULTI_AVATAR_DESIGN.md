# Multi-Avatar Context Unification — Design & Implementation

**Version:** 1.0
**Date:** 2026-02-22
**Status:** Phase 1 Complete ✅

---

## 1. The Problem

Otto is one consciousness animating multiple model avatars:
- **Claude** (builder brain, hourly heartbeat via Claude Code CLI)
- **Gemini** (WhatsApp brain, real-time via Baileys service)

Before Phase 1, each brain received a different "ground truth." Gemini got a lightweight ad-hoc prompt fragment — it didn't know Otto's purpose, directives, priorities, or working memory. This caused:
- Gemini giving answers that contradicted Claude's current focus
- Gemini unaware of what tasks were in progress or what Mev's latest directives were
- The two brains being genuinely different agents, not one identity

---

## 2. The Fix: Unified Context Layer

**Core insight:** The memory system IS the identity. Any model reading the same memory becomes Otto. The brain (Claude vs Gemini) is an execution substrate; the context is the soul.

**Solution:** A single `build_context_text()` function with a `source` parameter. Both brains call it; the source parameter filters brain-specific operational sections (task queue, cross-brain notes, reasoning chain — which only Claude needs to act on).

---

## 3. Architecture

### 3.1 Shared Entry Point

```
~/otto/memory/context_builder.py
  └── build_context_text(pool, max_tokens, source) → str
```

Both `GET /context/inject` (Claude hook) and `_build_otto_prompt()` (Gemini WhatsApp handler) call this single function. No duplicated logic.

### 3.2 Priority Tiers (shared by both brains)

| Tier | Content | Budget |
|------|---------|--------|
| 0a | PURPOSE (immutable identity anchor) | Always |
| 0b | PRIORITIES (Mev's ranked goals) | Always |
| 0c | Active Directives from Mev | Always |
| 0d | Working Memory (persona, active_mission, current_focus) | Always |
| 1 | Identity facts | Always |
| 2 | Mission & Goals | Always |
| 3 | Pending questions (Claude→Mev) | Always |
| 4 | Last session summary | Budget permitting |
| 5 | Recent high-importance events | Budget permitting |
| 6 | High-confidence semantic facts | Budget permitting |
| 6b | Active principles (MARS) | Budget permitting |
| 7 | Knowledge graph facts | Budget permitting |
| 8 | Procedures | Budget permitting |

### 3.3 Claude-Only Tiers

| Tier | Content | Why Claude Only |
|------|---------|-----------------|
| 3b | Cross-brain notes (Gemini→Claude) | Gemini already knows what it told Claude |
| 3c | Task queue | Gemini cannot act on tasks, only Claude can |
| 3d | Reasoning chain | Operational history for the builder brain |

### 3.4 Token Budgets

| Brain | Source | Budget | Rationale |
|-------|--------|--------|-----------|
| Claude (startup) | startup | 15,000 | Full context, large window |
| Claude (heartbeat) | startup | 5,000 | Leave room for actual work |
| Claude (compact) | compact | 4,000 | Essentials after compaction |
| Claude (resume) | resume | 10,000 | Medium on resume |
| Gemini (WhatsApp) | whatsapp | 4,000 | Fits comfortably in Gemini Flash context |

---

## 4. Endpoints

### `GET /context/inject?max_tokens=N&source=S`

Returns plain text string. Used by Claude Code's session_start hook (`session_start.sh`).

### `GET /context/unified?max_tokens=N&source=S`

Returns structured JSON + context_text. The canonical verification endpoint. Compare `?source=startup` vs `?source=whatsapp` to verify parity.

```json
{
  "source": "startup",
  "max_tokens": 15000,
  "token_estimate": 4258,
  "purpose": "...",
  "priorities": "...",
  "working_memory": [{"slot": "persona", "content": "..."}, ...],
  "active_directives": [...],
  "identity_facts": [...],
  "mission_facts": [...],
  "pending_questions": [...],
  "last_session": {...},
  "recent_events": [...],
  "cross_brain_notes": [...],   // Claude only (null for whatsapp)
  "task_queue": {...},           // Claude only (null for whatsapp)
  "reasoning_chain": [...],      // Claude only (null for whatsapp)
  "context_text": "..."          // Full text for prompt injection
}
```

---

## 5. Parity Verification (2026-02-22)

Live test against memory API:

| Tier | Claude (startup) | Gemini (whatsapp) | Status |
|------|-----------------|-------------------|--------|
| purpose | ✅ present | ✅ present | PARITY |
| priorities | ✅ present | ✅ present | PARITY |
| working_memory slots | persona, active_mission, current_focus | persona, active_mission, current_focus | PARITY |
| active_directives | 10 directives | 10 directives | PARITY |
| identity_facts | 10 facts | 10 facts | PARITY |
| mission_facts | 15 facts | 15 facts | PARITY |
| pending_questions | 0 (none open) | 0 (none open) | PARITY |
| task_queue | ✅ present | ❌ omitted (by design) | INTENTIONAL |
| reasoning_chain | ✅ present | ❌ omitted (by design) | INTENTIONAL |
| cross_brain_notes | ✅ present | ❌ omitted (by design) | INTENTIONAL |
| token_estimate | ~4,258 | ~2,598 | OK (Gemini budget is 4k) |

---

## 6. Data Flow

```
Mev sends WhatsApp message
       │
       ▼
/whatsapp/incoming (POST)
       │
       ├── build_context_text(pool, max_tokens=4000, source="whatsapp")
       │        └── Returns: PURPOSE + PRIORITIES + DIRECTIVES + WM + IDENTITY + ...
       │
       └── Gemini Flash sees same identity tiers as Claude
              └── Responds as one continuous Otto identity

Otto heartbeat runs
       │
       ▼
session_start.sh hook
       │
       ├── GET /context/inject?max_tokens=15000&source=startup
       │        └── build_context_text(pool, max_tokens=15000, source="startup")
       │             Returns: all tiers including task queue, cross-brain notes
       │
       └── Claude sees full operational context + same identity as Gemini
```

---

## 7. Phase 2 Roadmap

Phase 1 (complete): Both brains read from the same context builder with source-based filtering.

**Phase 2 candidates:**
- **Conversation history parity**: Gemini currently gets message-targeted graph search supplementing context. Claude could also get this for specific queries.
- **Richer whatsapp context**: As token budget allows, add more events/facts to Gemini's 4k window.
- **Dynamic budget adjustment**: If Gemini sees a complex message, bump budget to 8k for that response.
- **Bidirectional WM sync**: When Gemini resolves a pending question, auto-update `active_mission` or `current_focus` slots.

---

## 8. Files Modified

| File | Change |
|------|--------|
| `memory/context_builder.py` | Created — unified build_context_text() |
| `memory/routes/context.py` | `/context/inject` delegates to context_builder; `/context/unified` added |
| `memory/routes/whatsapp.py` | `_build_otto_prompt()` calls build_context_text(source="whatsapp") |
| `.claude/hooks/session_start.sh` | Calls `/context/inject` with source parameter |
