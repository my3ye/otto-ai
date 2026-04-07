---
name: context_loss_triple_bug
description: Three bugs causing Otto to lose conversation context and repeat confirmed info — streaming handler missing history, persistence race condition, lost-in-middle prompt structure
type: project
---

Three root causes found for "Otto loses context of recent messages":

**BUG 1 (CRITICAL): Streaming handler had ZERO conversation history**
- File: `memory/kernel/ric.py`, `_handle_admin_message_stream()`
- Non-streaming handler loaded 16 history messages as multi-turn
- Streaming handler only sent `[system, user]` — completely missing conversation history
- Impact: Web interface (mev.otto.lk WebSocket chat) had no prior conversation context
- Fix: Added same history loading logic as non-streaming handler

**BUG 2 (HIGH): Persistence race condition for rapid messages**
- File: `memory/kernel/ric.py`, Phase 5 runs as `asyncio.create_task()`
- Both incoming AND outgoing messages persisted only in async Phase 5 after response returned
- Phase 5 needs 2 OpenAI embedding API calls before INSERT (~1-2s)
- If Mev sends Message B before Message A's Phase 5 completes, B's history query misses A
- Fix: Early-persist incoming message (without embedding) at start of processing; Phase 5 backfills embedding via UPDATE

**BUG 3 (MEDIUM): Conversation history buried in "lost in middle" zone**
- S-MMU context: up to 12,000 tokens in system prompt
- Conversation history: 16 msgs x 600 chars = ~2,400 tokens (in multi-turn messages after system)
- History sits between massive system prompt and current message — exactly the "lost in middle" zone
- Fix: Added explicit CONVERSATION CONTINUITY instruction at end of system prompt (recency anchor)

**Why:** Mev's directive says "Never ask Mev to repeat information she has already provided."
**How to apply:** When debugging context/memory issues, check (1) all handler variants have parity, (2) persistence timing vs. retrieval timing, (3) prompt position of critical information.
