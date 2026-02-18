-- Migration 006: Outreach Queue
-- Stores AI-generated outreach messages pending Mev's approval before sending
-- Integrates with Web Assist lead database

CREATE TABLE IF NOT EXISTS outreach_queue (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Lead reference
    lead_id UUID NOT NULL REFERENCES web_assist_leads(id) ON DELETE CASCADE,
    place_id TEXT NOT NULL,
    business_name TEXT NOT NULL,
    city TEXT,
    phone TEXT,
    website TEXT,
    lead_type TEXT NOT NULL,  -- no_website | revamp_candidate
    lead_score INTEGER,

    -- Generated message
    channel TEXT NOT NULL DEFAULT 'whatsapp',  -- whatsapp | email | sms
    message_subject TEXT,       -- for email
    message_body TEXT NOT NULL, -- the actual outreach message

    -- Approval workflow
    status TEXT NOT NULL DEFAULT 'pending',  -- pending | approved | rejected | sent | failed
    approved_at TIMESTAMPTZ,
    sent_at TIMESTAMPTZ,
    rejection_reason TEXT,

    -- Generation metadata
    generated_by TEXT DEFAULT 'gemini-2.0-flash',
    generation_prompt TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_outreach_status ON outreach_queue(status);
CREATE INDEX IF NOT EXISTS idx_outreach_lead_id ON outreach_queue(lead_id);
CREATE INDEX IF NOT EXISTS idx_outreach_channel ON outreach_queue(channel);
CREATE INDEX IF NOT EXISTS idx_outreach_created ON outreach_queue(created_at DESC);

-- Prevent duplicate pending messages for same lead
CREATE UNIQUE INDEX IF NOT EXISTS idx_outreach_unique_pending
    ON outreach_queue(lead_id, channel)
    WHERE status IN ('pending', 'approved');

-- Auto-update updated_at
DROP TRIGGER IF EXISTS update_outreach_queue_updated_at ON outreach_queue;
CREATE TRIGGER update_outreach_queue_updated_at
    BEFORE UPDATE ON outreach_queue
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
