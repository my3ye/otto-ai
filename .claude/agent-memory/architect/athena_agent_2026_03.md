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

**Implementation scope**: 5 files — migration 064, gateway/athena_handler.py, gateway/handler.py patch, routes/athena.py, api.py. ~$5-8 budget, coder agent.
