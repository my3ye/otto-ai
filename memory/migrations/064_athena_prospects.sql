-- Athena WhatsApp agent: prospect tracking + conversation logging
-- Stage machine: new → qualifying → qualified | disqualified → proposal_sent → closed_won | closed_lost

CREATE TABLE IF NOT EXISTS athena_prospects (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    jid             TEXT NOT NULL UNIQUE,          -- WhatsApp JID (sender_id)
    phone           TEXT,                          -- normalized phone number
    name            TEXT,                          -- display name from WhatsApp
    stage           TEXT NOT NULL DEFAULT 'new',   -- current stage
    outreach_id     UUID,                          -- FK to outreach_queue if this was an outreach reply
    business_name   TEXT,                          -- from outreach or learned in conversation
    lead_type       TEXT,                          -- from outreach (restaurant, hotel, etc.)
    city            TEXT,                          -- from outreach or learned
    website         TEXT,                          -- from outreach or learned
    qualification_notes TEXT,                      -- running notes from LLM during qualifying
    proposal_url    TEXT,                          -- link to proposal when sent
    stage_updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS athena_conversations (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    prospect_id UUID NOT NULL REFERENCES athena_prospects(id) ON DELETE CASCADE,
    jid         TEXT NOT NULL,
    direction   TEXT NOT NULL CHECK (direction IN ('incoming', 'outgoing')),
    content     TEXT NOT NULL,
    stage_at    TEXT,   -- stage at the time of this message
    created_at  TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_athena_prospects_jid ON athena_prospects(jid);
CREATE INDEX IF NOT EXISTS idx_athena_prospects_stage ON athena_prospects(stage);
CREATE INDEX IF NOT EXISTS idx_athena_prospects_outreach ON athena_prospects(outreach_id);
CREATE INDEX IF NOT EXISTS idx_athena_conversations_prospect ON athena_conversations(prospect_id);
CREATE INDEX IF NOT EXISTS idx_athena_conversations_created ON athena_conversations(created_at DESC);
