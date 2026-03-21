# Athena Agent Architecture
**Date:** 2026-03-21
**Status:** Design complete — ready for implementation
**Author:** Architect agent (Step 0 of Athena workflow)

---

## Design: Athena — Full-Funnel WhatsApp Sales Agent

### Problem

WebAssist's Athena WhatsApp line (+94743768830) is live and connected at :3002. When prospects reply to outreach messages (or text in cold), there is no server-side handler: messages fall into the generic `contact_handler.py` which has no concept of qualification stages, outreach context, or funnel progression. Qualified leads are invisible to Mev.

We need a handler that:
1. Receives inbound WhatsApp messages via Athena's account
2. Responds as "Athena" — professional, cool, sassy — not a generic assistant
3. Tracks qualification stage per prospect (new → qualifying → qualified → proposal_sent → closed)
4. Alerts Mev via episodic event when a prospect qualifies
5. Exposes prospect data via REST API (for OMS visibility)

---

### Approach

**The key insight:** Athena's service.mjs already sends `metadata.account='athena'` with every message. The gateway handler just needs a 3-line branch to route Athena messages to a dedicated handler instead of the generic contact_handler.

Everything else is a new, isolated module — no changes to existing working systems.

#### Message Flow

```
Prospect texts +94743768830
    │
    ▼
Athena WhatsApp Service (:3002)
  - Normalizes message (text/audio/image/doc)
  - Transcribes audio (Deepgram)
  - Sends to /gateway/incoming with metadata.account='athena'
    │
    ▼
gateway/handler.py
  [NEW BRANCH]
  if metadata.account == 'athena':
      → athena_handler.handle_athena_message()
  else:
      → contact_handler.handle_contact_message()
    │
    ▼
gateway/athena_handler.py  [NEW]
  1. find_or_create_prospect(jid, name)
     - Check athena_prospects by JID
     - If new: check outreach_queue by phone (preload business context)
     - Create record with stage='new'
  2. load_conversation_history(prospect_id, limit=16)
  3. build_system_prompt(prospect, outreach_context)  [stage-aware]
  4. LLM call → generate reply (300 token limit — WhatsApp)
  5. classify_stage(prospect, history)  [only if count>2 and stage='qualifying']
  6. log_exchange(incoming + outgoing → athena_conversations)
  7. update prospect (stage, updated_at, last_message_at)
  8. IF stage just became 'qualified': log episodic event (importance=9)
    │
    ▼
GatewayResponse(content=reply)
    │
    ▼
Athena service sends reply via WhatsApp
```

---

### Key Decisions

- **Branch at gateway/handler.py, not a new endpoint**: Athena service already sends the right metadata. 3-line patch is cleaner and safer than creating `/gateway/athena/incoming`.
  *Alternative rejected:* New endpoint requires changing service.mjs + creating new route — unnecessary.

- **Separate athena_prospects table**: Funnel-specific fields (stage, budget_signal, timeline, decision_authority) don't belong on general `oms_contacts`. Clean domain separation.
  *Alternative rejected:* Adding columns to oms_contacts pollutes the contact model with sales-specific fields.

- **LLM-guided stage transitions**: Classifier reads conversation history and returns new stage. Flexible — adjust behavior by changing prompts, not code.
  *Alternative rejected:* Keyword-based rules (e.g., "if 'budget' in message, set stage='qualifying'") are brittle and miss context.

- **Single LLM call for response; separate classifier call only when needed**: Avoids double-call on every message. Classifier only fires if `stage='qualifying' and message_count > 2`. Cost-efficient.
  *Alternative rejected:* Combined response+classification in one call increases prompt complexity and token cost.

- **Episodic event on qualification (importance=9)**: Surfaces immediately in Mev's heartbeat context. No separate notification system needed.
  *Alternative rejected:* WhatsApp notification to Mev — adds coupling; episodic events are sufficient and already read by heartbeat.

- **Phone normalization via existing logic**: contact_handler.py already has phone_variants() pattern. Reuse for outreach_queue matching.
  *Alternative rejected:* Simple equality comparison misses format differences (94743... vs +94743... vs 0743...).

---

### API / Interface

#### New DB Tables (Migration 064)

```sql
CREATE TABLE athena_prospects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    jid TEXT UNIQUE NOT NULL,           -- WhatsApp JID
    phone TEXT,
    name TEXT,
    outreach_id UUID REFERENCES outreach_queue(id) ON DELETE SET NULL,

    -- Funnel
    stage TEXT NOT NULL DEFAULT 'new',  -- new|qualifying|qualified|disqualified|proposal_sent|closed_won|closed_lost

    -- Qualification signals
    business_name TEXT,
    business_type TEXT,
    has_website BOOLEAN,
    budget_signal TEXT,
    timeline TEXT,
    decision_authority BOOLEAN,
    qualification_notes TEXT,
    otto_context JSONB DEFAULT '{}',

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    stage_updated_at TIMESTAMPTZ,
    last_message_at TIMESTAMPTZ,
    deleted_at TIMESTAMPTZ
);

CREATE TABLE athena_conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    prospect_id UUID NOT NULL REFERENCES athena_prospects(id) ON DELETE CASCADE,
    jid TEXT NOT NULL,
    direction TEXT NOT NULL CHECK (direction IN ('incoming', 'outgoing')),
    content TEXT NOT NULL,
    message_type TEXT DEFAULT 'text',
    attachment_meta JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_athena_prospects_jid ON athena_prospects(jid);
CREATE INDEX idx_athena_prospects_stage ON athena_prospects(stage);
CREATE INDEX idx_athena_prospects_updated ON athena_prospects(updated_at DESC);
CREATE INDEX idx_athena_conversations_prospect ON athena_conversations(prospect_id, created_at DESC);
```

#### New REST Endpoints (routes/athena.py)

| Endpoint | Method | Purpose |
|---|---|---|
| `/athena/prospects` | GET | List all prospects. Query: `?stage=qualified&search=restaurant` |
| `/athena/prospects/{id}` | GET | Single prospect with latest conversation |
| `/athena/prospects/{id}/conversation` | GET | Full conversation history |
| `/athena/prospects/{id}/stage` | POST | Manual stage override: `{stage: "qualified"}` |
| `/athena/stats` | GET | Funnel breakdown: count per stage, conversion rates |

#### Modified Files

| File | Change |
|---|---|
| `gateway/handler.py` | +5 lines: branch for `metadata.account == 'athena'` |
| `api.py` | +2 lines: import and register athena router |

---

### Athena Persona (System Prompt Design)

Athena has a distinct voice — professional, cool, sassy. Not a generic bot.

**Voice examples:**
```
Bad:  "Thank you for reaching out to WebAssist. I would be happy to assist you today."
Good: "Hey! Glad you reached out. Tell me about your business — what are we working with?"

Bad:  "I apologize, but I'm unable to answer that specific question."
Good: "That's a bit outside my lane, but I'll get the right person on it. 👌"

Bad:  "Our pricing starts at $2,995 for a professional website."
Good: "Pricing depends on what you need — our team'll walk you through it on a quick call. Worth 15 minutes, I promise."
```

**Stage-specific behavioral instructions:**

| Stage | Athena's Goal | Tone |
|---|---|---|
| `new` | Warm greeting, learn business type | Curious, friendly |
| `qualifying` | Uncover need, authority, timeline | Engaged, professional |
| `qualified` | Book the call with Mev's team | Confident, clear CTA |
| `proposal_sent` | Answer objections, reinforce ROI | Reassuring, factual |
| `disqualified` | Polite close, possible referral | Warm, graceful |

**WhatsApp format rules:**
- Max 2-3 sentences per reply
- No bullet points or headers (it's WhatsApp)
- Simple, direct language
- Light emoji use (1 per message max, optional)
- Never quote pricing unless asked directly

---

### Stage Classifier Design

Called separately from response generation. Only fires when `stage == 'qualifying' and message_count > 2`.

**Classifier prompt:**
```
You are a sales qualification classifier. Read this WhatsApp conversation and return the current stage.

Stages:
- new: Opening exchange only
- qualifying: Learning needs, authority, timeline — not yet confirmed
- qualified: ALL three confirmed: (1) real website need, (2) decision authority, (3) realistic timeline
- proposal_sent: Next steps / pricing discussed
- disqualified: Scope/budget mismatch, or prospect declined
- closed_won: Project started
- closed_lost: Declined after proposal

Rules:
1. Only move FORWARD. Never regress.
2. 'qualified' requires all three signals — not just one or two.
3. Complex custom dev (custom AI, large backend, impossible timelines) = disqualified.

Conversation:
{conversation_history}

Current stage: {current_stage}

Return ONLY the stage name. No explanation.
```

---

### Implementation Plan

**Phase 1 — Core Handler (primary task, ~$5-8 coder task, Sonnet, 900s)**

1. `migrations/064_athena_prospects.sql` — Create tables and indexes
2. `gateway/athena_handler.py` — Full handler module (~200 lines):
   - `find_or_create_prospect(jid, name)`
   - `load_conversation_history(prospect_id, limit=16)`
   - `build_system_prompt(prospect, outreach_context)`
   - `call_llm_for_reply(messages, system_prompt)`
   - `classify_stage(prospect, history)` — classifier call
   - `log_exchange(prospect_id, direction, content)`
   - `handle_athena_message(msg)` — orchestrator
3. `gateway/handler.py` — +5 line patch for Athena branch
4. End-to-end verification: send test message via curl to `/gateway/incoming` with `account='athena'`

**Phase 2 — REST API (~$2-3 coder task)**

5. `routes/athena.py` — 5 endpoints
6. `api.py` — register router

**Phase 3 — OMS UI (lower priority, after Phase 1+2 verified)**

7. `/athena/prospects` page in interfaces/web-next
8. Prospect detail modal with conversation thread
9. Stage override button
10. Funnel stats widget

---

### Risks

- **Phone number format mismatches** when cross-referencing outreach_queue: Use phone_variants() logic from contact_handler.py. Soft fallback — if no match, still create prospect as cold inbound.
- **LLM stage regression**: Enforced in code — only forward transitions allowed regardless of classifier output.
- **Athena systemd service status**: Verify before shipping. `/whatsapp/accounts` endpoint already tracks this.
- **Duplicate prospect records**: JID is UNIQUE in athena_prospects — upsert-safe on conflict.
- **Spam / wrong numbers**: Accept at stage='new' (cheap). Manual archive via OMS if needed.

---

### Relevant File Paths

```
/home/web3relic/otto/
├── interfaces/
│   └── athena-whatsapp/service.mjs          -- LIVE, sends account='athena'
├── memory/
│   ├── api.py                               -- MODIFY: register router
│   ├── gateway/
│   │   ├── handler.py                       -- MODIFY: branch for Athena
│   │   ├── athena_handler.py                -- CREATE: core handler (~200 lines)
│   │   ├── contact_handler.py               -- REFERENCE: similar pattern
│   │   └── models.py                        -- REFERENCE: GatewayMessage schema
│   ├── migrations/
│   │   └── 064_athena_prospects.sql         -- CREATE: DB schema
│   └── routes/
│       ├── athena.py                        -- CREATE: REST API (~80 lines)
│       └── outreach.py                      -- REFERENCE: outreach_queue structure
└── docs/
    └── athena-agent-architecture-2026-03-21.md  -- THIS FILE
```
