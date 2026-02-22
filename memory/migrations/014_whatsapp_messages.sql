-- WhatsApp Messages with Semantic Embeddings
-- Adds a dedicated table for WhatsApp messages with vector search capability.
-- Backfill from episodic_events happens via POST /whatsapp/backfill endpoint.

BEGIN;

CREATE TABLE IF NOT EXISTS whatsapp_messages (
    id                          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    direction                   TEXT NOT NULL CHECK (direction IN ('incoming', 'outgoing')),
    content                     TEXT NOT NULL,
    jid                         TEXT,              -- WhatsApp JID (sender or recipient)
    push_name                   TEXT,              -- Display name from WhatsApp
    embedding                   halfvec(1536),     -- Semantic embedding for search
    matched_pending_question_id UUID REFERENCES pending_questions(id) ON DELETE SET NULL,
    episodic_event_id           UUID REFERENCES episodic_events(id) ON DELETE SET NULL,
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT now(),
    metadata                    JSONB DEFAULT '{}'::jsonb
);

-- HNSW index for fast cosine similarity search (matches pattern in migration 008)
CREATE INDEX IF NOT EXISTS idx_whatsapp_messages_embedding
    ON whatsapp_messages USING hnsw (embedding halfvec_cosine_ops)
    WITH (m = 16, ef_construction = 64);

CREATE INDEX IF NOT EXISTS idx_whatsapp_messages_direction
    ON whatsapp_messages (direction);

CREATE INDEX IF NOT EXISTS idx_whatsapp_messages_created
    ON whatsapp_messages (created_at DESC);

CREATE INDEX IF NOT EXISTS idx_whatsapp_messages_jid
    ON whatsapp_messages (jid);

COMMIT;
