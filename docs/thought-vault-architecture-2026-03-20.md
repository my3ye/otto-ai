# Thought Vault — Architecture Design
_2026-03-20_

## Design: Thought Vault

### Problem

Mev sends voice and text thought-dumps via WhatsApp that contain strategic ideas, philosophical reflections, and directional insights. These are currently processed by the kernel as conversation turns, logged as episodic events, and then lost to time. There is no dedicated place to:
- Store them as first-class objects separate from task/memory noise
- Tag, browse, and search them
- Let Otto surface patterns and connections across entries
- Give Mev a clean OMS view to review and annotate

### Approach

Three-layer system: **Capture → Store → Synthesize**

**Layer 1: Capture** — WhatsApp voice and long-text messages from Mev are automatically stored in the vault via a Phase 5 post-processing hook in ric.py. Manual entry also available via API.

**Layer 2: Store** — Dedicated PostgreSQL tables (`thought_vault`, `thought_synthesis`). Separate from content system because thoughts are raw, unstructured, and belong to Mev's internal thinking — not publishable content.

**Layer 3: Synthesize** — `/thought-vault/synthesize` endpoint that Otto calls (via heartbeat or reflection agent) to group recent entries by theme, extract patterns, and produce synthesis records. LLM-based, on-demand or scheduled.

### Key Decisions

- **New tables vs reusing `content`**: New tables. The content system is for publishable material (articles, social posts, landing copy). Thoughts are raw input — private, messy, often directive. Different access patterns, different lifecycle. Alternative: add `thought_dump` type to content — rejected because it muddies the content model and makes synthesis harder to scope.

- **Synthesis model**: On-demand endpoint (Otto calls it, not a daemon). Keeps the system simple. Otto's heartbeat can trigger it once a day or when N new entries have accumulated. Alternative: APScheduler job — rejected because it adds complexity and the heartbeat already runs every 30 min.

- **Auto-capture hook**: Phase 5 ric.py post-processor checks if incoming message is `[Voice]` or long-form text (>300 chars) from Mev, then calls the thought-vault ingest endpoint. Otto still responds normally — the vault is a side-effect, not a replacement for the response. Alternative: separate WhatsApp webhook — rejected, ric.py is already the right integration point.

- **Tags**: Dual-source. Auto-tags from Otto (topic extraction via LLM during synthesis), manual tags Mev can add via OMS. Stored as `TEXT[]` in Postgres.

- **Synthesis storage**: Separate `thought_synthesis` table (not semantic memory). Synthesis records are structured, linkable to source entries, and need their own UI surface. They can optionally be promoted to semantic memory when Otto deems them high-value.

### API / Interface

#### Backend — `/thought-vault` (new FastAPI router)

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/thought-vault/entries` | Create entry (auto or manual) |
| GET | `/thought-vault/entries` | List entries (filter: source, tags, date range, archived) |
| GET | `/thought-vault/entries/{id}` | Single entry detail |
| PUT | `/thought-vault/entries/{id}` | Update tags, notes, importance |
| DELETE | `/thought-vault/entries/{id}` | Soft delete (archived=TRUE) |
| POST | `/thought-vault/synthesize` | Run synthesis over recent entries, create synthesis records |
| GET | `/thought-vault/synthesis` | List synthesis records |
| GET | `/thought-vault/synthesis/{id}` | Single synthesis detail |
| GET | `/thought-vault/stats` | Entry count, themes, recency |

#### DB Schema (migration 063)

```sql
-- thought_vault: raw thought entries
CREATE TABLE thought_vault (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source          TEXT NOT NULL DEFAULT 'manual',  -- 'whatsapp_voice', 'whatsapp_text', 'manual'
    raw_content     TEXT NOT NULL,                   -- original transcription or text
    cleaned_content TEXT,                            -- Otto-edited clean version (optional)
    tags            TEXT[] NOT NULL DEFAULT '{}',    -- Mev + Otto assigned tags
    themes          TEXT[] NOT NULL DEFAULT '{}',    -- Otto-extracted theme labels
    sentiment       TEXT,                            -- 'exploratory', 'directive', 'reflective', 'strategic', 'creative'
    importance      INT CHECK (importance BETWEEN 1 AND 10),
    source_message_id TEXT,                          -- WhatsApp message ID for dedup
    archived        BOOLEAN NOT NULL DEFAULT FALSE,
    deleted_at      TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- thought_synthesis: Otto's synthesized patterns and connections
CREATE TABLE thought_synthesis (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    synthesis_type  TEXT NOT NULL DEFAULT 'pattern',  -- 'pattern', 'connection', 'theme_cluster', 'action_item', 'contradiction'
    title           TEXT NOT NULL,
    content         TEXT NOT NULL,
    source_ids      UUID[] NOT NULL DEFAULT '{}',     -- which thought entries contributed
    confidence      FLOAT NOT NULL DEFAULT 0.7 CHECK (confidence BETWEEN 0.0 AND 1.0),
    promoted_to_memory BOOLEAN NOT NULL DEFAULT FALSE, -- TRUE if pushed to semantic memory
    archived        BOOLEAN NOT NULL DEFAULT FALSE,
    deleted_at      TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_thought_vault_created ON thought_vault(created_at DESC) WHERE deleted_at IS NULL;
CREATE INDEX idx_thought_vault_tags ON thought_vault USING gin(tags) WHERE deleted_at IS NULL;
CREATE INDEX idx_thought_vault_themes ON thought_vault USING gin(themes) WHERE deleted_at IS NULL;
CREATE INDEX idx_thought_synthesis_created ON thought_synthesis(created_at DESC) WHERE deleted_at IS NULL;
CREATE INDEX idx_thought_synthesis_source_ids ON thought_synthesis USING gin(source_ids);
```

#### OMS Page — `/thought-vault`

Three-tab layout:
1. **Entries** — chronological list. Each card shows: timestamp, source badge (🎤 Voice / ✏️ Text / Manual), raw content excerpt, tags, importance dot. Click → full detail drawer with raw + cleaned content, tags editor.
2. **Synthesis** — list of synthesis records grouped by type. Badge for type (Pattern / Connection / Cluster). Links back to source entries.
3. **Stats** — entry count by source, top themes, recency chart, unprocessed count.

#### WhatsApp Auto-Capture Hook

In `ric.py` Phase 5 post-processor:
```python
# After kernel processes message, store in thought vault if:
# - message starts with "[Voice]"
# - OR message from Mev is >300 chars and not a command/question
async def _thought_vault_hook(interrupt, response):
    if interrupt.source != "whatsapp":
        return
    content = interrupt.content
    is_voice = content.startswith("[Voice]")
    is_long_text = len(content) > 300 and not content.startswith("/")
    if is_voice or is_long_text:
        source = "whatsapp_voice" if is_voice else "whatsapp_text"
        await _post_to_thought_vault(content, source, interrupt.message_id)
```

### Implementation Plan

#### Step 1 — DB Migration (30 min, ~$2)
Create `memory/migrations/063_thought_vault.sql` with thought_vault + thought_synthesis tables and indexes.

#### Step 2 — Backend Route (45 min, ~$3)
Create `memory/routes/thought_vault.py`:
- CRUD endpoints for entries and synthesis
- `/synthesize` endpoint: loads last N unprocessed entries, calls LLM (via kernel provider), creates synthesis records
- Register in `memory/api.py` import line

#### Step 3 — WhatsApp Hook (30 min, ~$2)
Add thought vault auto-capture to `memory/kernel/ric.py` Phase 5 post-processors. Dedup by `source_message_id`.

#### Step 4 — OMS Page (60 min, ~$4)
Create `interfaces/web-next/src/app/thought-vault/page.tsx`:
- 3-tab layout (Entries / Synthesis / Stats)
- Entry card with expandable detail
- Tags editor
- "Run Synthesis" button → calls `/thought-vault/synthesize`

#### Step 5 — Sidebar (5 min, ~$0.50)
Add `{ title: "Thought Vault", href: "/thought-vault", icon: Lightbulb }` to Content group in `app-sidebar.tsx`.

**Total estimated cost: ~$11.50 across 4 implementation tasks**

### Risks

- **LLM cost for synthesis**: Synthesizing many thoughts at once can be expensive. Mitigation: limit to 20 entries per synthesis run, skip if <5 new entries since last run.
- **Voice transcription quality**: WhatsApp sends audio files; transcription may already be done by the kernel (using OpenAI Whisper or similar) or may be the raw `[Voice] <file>` marker. Mitigation: store whatever is available — cleaned content field can be filled in later by a task.
- **Dedup on retries**: If the hook fires twice for the same message (kernel retry), we'd get duplicate entries. Mitigation: UNIQUE constraint on `source_message_id` (when non-null).
