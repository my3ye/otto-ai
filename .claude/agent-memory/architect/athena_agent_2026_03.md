---
name: athena_agent_2026_03
description: Athena WhatsApp agent architecture for WebAssist prospect & client communication (2026-03-21)
type: project
---

Architecture designed for Athena agent (Step 0 complete). Full doc at ~/otto/docs/athena-agent-architecture-2026-03-21.md.

**Key decisions**:
- Route via `metadata.account="athena"` already sent by Athena service.mjs — no new endpoint needed
- Branch added in `gateway/handler.py` before generic `contact_handler`
- New `athena_prospects` table (stage machine: new→qualifying→qualified→disqualified→proposal_sent→closed) + `athena_conversations` table — migration 064
- LLM-guided stage transitions (not rigid state machine) via stage-aware system prompt
- Outreach context preloaded if inbound JID matches outreach_queue phone

**Why:** Athena is already connected (+94743768830, port 3002, active) and already sends correct metadata. Only the handler-side logic is missing.

**Persona**: "Athena" — professional, cool, sassy woman. Max 2-3 sentence WhatsApp replies. Stage-aware tone (curious→engaged→confident→graceful). Never quote pricing unless asked.

**Stage classifier**: Separate LLM call, only fires when `stage='qualifying' and message_count > 2`. Qualified requires ALL THREE: (1) confirmed website need, (2) decision authority, (3) realistic timeline. Only forward transitions — no regression in code.

**Episodic event on qualification**: importance=9, surfaces in Mev's heartbeat. Content: "Athena prospect qualified: {name} ({business})".

**REST API** (routes/athena.py): GET /athena/prospects, GET /athena/prospects/{id}/conversation, POST /athena/prospects/{id}/stage, GET /athena/stats.

**Implementation scope**: 5 files — migration 064, gateway/athena_handler.py, gateway/handler.py patch, routes/athena.py, api.py. ~$5-8 budget, coder agent, Sonnet, 900s timeout.
