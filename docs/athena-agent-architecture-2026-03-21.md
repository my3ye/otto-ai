## Design: Athena WhatsApp Agent — Prospect & Client Communication

### Problem
WebAssist outreach generates 2273+ pending messages targeting local businesses. When they reply to Athena (+94743768830), there's no intelligence — the current gateway routes them to the generic `contact_handler.py` which just does unstructured conversation. We need a purpose-built agent that qualifies inbound prospects, answers WebAssist questions, and escalates hot leads to Mev.

### Current State (what exists)
- **Athena service**: LIVE at port 3002, connected, +94743768830
- **Already sends** `metadata.account = "athena"` to `/gateway/incoming`
- **Gateway handler.py**: routes non-admin WhatsApp to `contact_handler.py` — generic, no qualification
- **DB**: `outreach_queue` (2273 rows), `web_assist_leads`, `oms_contacts`, `contact_conversations` exist
- **Gap**: gateway doesn't branch on `account=athena`, no prospect state, no qualification logic

### Approach

**Routing**: `handler.py` already receives the `account: "athena"` flag in metadata. Add a single branch: if `msg.metadata.get("account") == "athena"` → route to new `athena_handler.py`. Zero risk to the existing Otto/Mev WhatsApp path.

**Prospect model**: New `athena_prospects` table tracks each contact's qualification stage. On first message, check if sender phone matches an `outreach_queue` entry (i.e., they're replying to a cold outreach). If yes, preload their business context. If no, treat as inbound cold inquiry.

**Stage machine** (LLM-guided, not rigid state logic):
```
new → qualifying → qualified | disqualified → proposal_sent → closed_won | closed_lost
```
After each exchange, a lightweight LLM call re-evaluates the stage based on conversation history. Stage only advances, never regresses.

**Qualification goals** (woven naturally into conversation — never an interrogation):
- Business need: do they have a website gap?
- Decision authority: are they the owner/decision maker?
- Budget signal: price range awareness (~$2,995 one-time)?
- Timeline: when do they want to move?

**When qualified**: log a high-importance episodic event so Mev sees it at next OMS check. Reply with a clear CTA (schedule call with Mev, or Mev will reach out).

### Key Decisions

- **Routing via metadata, not new endpoint**: `account: "athena"` already in every Athena message → branch in `handler.py`. Alternative was a separate `/gateway/athena/incoming` endpoint. Rejected: unnecessary duplication, extra endpoint to maintain.

- **Separate `athena_prospects` table, not reuse `oms_contacts`**: Athena prospects have sales-specific fields (stage, budget_signal, timeline, qualification_notes) that don't belong on a general contacts table. Clean separation. Alternative: add columns to `oms_contacts`. Rejected: muddies general contact model with WebAssist-specific funnel state.

- **LLM-guided stage transitions, not rigid state machine**: Prospect conversations are messy. A rule-based state machine breaks on non-linear replies. The LLM reads the full history and classifies the stage. Simple, accurate, easy to adjust by changing the system prompt. Alternative: hardcoded keyword triggers. Rejected: too brittle.

- **Single system prompt per stage, not multi-turn orchestration**: Keep it simple — one LLM call per message with a rich system prompt that includes stage, context, and goals. The LLM handles everything. Alternative: separate LLM calls for response + stage classification + context update. Rejected: 3x cost for same outcome.

- **Unknown numbers get a soft hold**: If the JID doesn't match any outreach entry and it's not a known contact, Athena responds politely ("Hi! You've reached the WebAssist team...") and creates a new prospect record. Alternative: ignore unknown numbers. Rejected: misses inbound organic inquiries.

### API / Interface

**Gateway change (handler.py)**:
```python
if msg.channel == "whatsapp":
    if msg.metadata.get("account") == "athena":
        from .athena_handler import handle_athena_message
        return await handle_athena_message(msg)
    from .contact_handler import handle_contact_message
    return await handle_contact_message(msg)
```

**New endpoints (routes/athena.py)**:
- `GET /athena/prospects` — list all prospects with stage + last message time
- `GET /athena/prospects/{id}/conversation` — full conversation history
- `POST /athena/prospects/{id}/stage` — manual stage override by Mev
- `GET /athena/stats` — funnel stats (prospects per stage, conversion rate)

**DB tables (migration 064)**:
```sql
athena_prospects: id, jid, phone, name, outreach_id (FK→outreach_queue nullable),
    stage, business_name, business_type, has_website, budget_signal,
    timeline, qualification_notes, otto_context, created_at, updated_at

athena_conversations: id, prospect_id, jid, direction, content, created_at
```

### Implementation Plan

1. **Migration 064** — Create `athena_prospects` + `athena_conversations` tables. Apply immediately.

2. **`athena_handler.py`** — Core handler module:
   - `find_or_create_prospect(jid, name)` — lookup by JID, create if new, check outreach_queue for context
   - `load_conversation(prospect_id, limit=16)` — recent turns as OpenAI messages
   - `log_exchange(prospect_id, jid, direction, content)` — persist to athena_conversations
   - `build_system_prompt(prospect, outreach_context)` — stage-aware Athena system prompt
   - `classify_stage(prospect, conversation_history)` — lightweight LLM call to update stage
   - `handle_athena_message(msg)` — main entry point

3. **`handler.py` patch** — 3-line branch to route Athena messages. Import `athena_handler` conditionally (same pattern as `contact_handler`).

4. **`routes/athena.py`** — REST endpoints for OMS visibility. Register in `api.py`.

5. **Episodic logging** — When stage advances to `qualified`, fire `POST /episodic/events` with high importance so heartbeat surfaces it to Mev.

6. **OMS page** (separate task, lower priority) — `/webassist/athena` with prospect table, stage filters, conversation drill-down.

### Athena System Prompt Design

```
You are Athena — a friendly, professional AI assistant for WebAssist (a web design service).
You're talking to {prospect_name} via WhatsApp.

WebAssist offers: professional websites for local businesses. One-time fee ~$2,995.
Target: businesses without a website or with a poor one.

About this contact:
{context_section}

Current stage: {stage}

Goals based on stage:
- new: Warm greeting, confirm who they are and their business.
- qualifying: Understand their website situation, decision-making role, rough timeline.
- qualified: Confirm interest, offer to connect them with the team for next steps.
- disqualified: Politely acknowledge they're not a fit, wish them well.
- proposal_sent: Answer questions, address objections, reinforce value.

Rules:
- WhatsApp: short messages (2-3 sentences max). Never write essays.
- Warm, human, professional. Not salesy.
- Never make up prices beyond "starting around $2,995".
- If they ask complex technical questions, say the team will follow up.
- Never impersonate a human — you're an AI assistant for the WebAssist team.
```

### Risks

- **Stage classification cost**: Each message fires a stage-check LLM call. Mitigation: only call if conversation count > 2 and stage is `qualifying`. Skip for `new` and terminal stages.
- **Outreach_queue phone matching**: Phone numbers in outreach_queue may have different formats (+94 vs 0 prefix). Mitigation: normalize both sides with `phone_variants()` logic already in `contact_handler.py`.
- **Athena replies to its own messages**: Baileys may echo back outgoing messages. Mitigation: the `direction === 'IN'` check in `service.mjs` already filters outgoing messages before they hit the gateway. Safe.
- **Unknown numbers becoming noise**: Many businesses may forward Athena's number around. Mitigation: auto-create prospect records with `stage=new` for all unknowns — low cost, captures all inquiry.

### Files to Create/Modify

| File | Action | Size |
|------|--------|------|
| `otto/memory/migrations/064_athena_prospects.sql` | CREATE | ~30 lines |
| `otto/memory/gateway/athena_handler.py` | CREATE | ~200 lines |
| `otto/memory/gateway/handler.py` | MODIFY | +5 lines |
| `otto/memory/routes/athena.py` | CREATE | ~80 lines |
| `otto/memory/api.py` | MODIFY | +2 lines (register router) |

No changes needed to `interfaces/athena-whatsapp/service.mjs` — it already sends the right metadata.

### Total Effort Estimate

- Implementation: 1 task, coder agent, $5-8 budget, sonnet model, 900s timeout
- OMS page: separate task after core is live
