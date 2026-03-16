-- Contact conversations: per-contact message history between Otto and contacts
-- This is separate from whatsapp_messages (which is Mev-only)

CREATE TABLE IF NOT EXISTS contact_conversations (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    contact_id  UUID NOT NULL REFERENCES oms_contacts(id) ON DELETE CASCADE,
    direction   TEXT NOT NULL CHECK (direction IN ('incoming', 'outgoing')),
    content     TEXT NOT NULL,
    jid         TEXT,                           -- WhatsApp JID of contact
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    metadata    JSONB DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS contact_conversations_contact_id_idx
    ON contact_conversations(contact_id, created_at DESC);

CREATE INDEX IF NOT EXISTS contact_conversations_jid_idx
    ON contact_conversations(jid);

-- Track whether Otto has introduced himself to a contact
ALTER TABLE oms_contacts
    ADD COLUMN IF NOT EXISTS introduced_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS whatsapp_jid TEXT;

CREATE INDEX IF NOT EXISTS oms_contacts_whatsapp_jid_idx
    ON oms_contacts(whatsapp_jid);
