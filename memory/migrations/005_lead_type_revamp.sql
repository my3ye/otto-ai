-- Migration 005: Add lead_type to web_assist_leads
-- Differentiates between "no website" new builds and "revamp" candidates (has a weak/outdated site)

ALTER TABLE web_assist_leads
    ADD COLUMN IF NOT EXISTS lead_type TEXT DEFAULT 'unknown';
-- Values: 'no_website' | 'revamp_candidate' | 'strong_web_presence' | 'unknown'

COMMENT ON COLUMN web_assist_leads.lead_type IS
    'no_website=needs site built; revamp_candidate=has site but weak (social, Wix, etc); strong_web_presence=skip';

CREATE INDEX IF NOT EXISTS idx_leads_type ON web_assist_leads(lead_type);

-- Backfill existing rows (all currently 0 anyway since API blocked)
UPDATE web_assist_leads SET lead_type =
    CASE
        WHEN website IS NULL OR website = '' THEN 'no_website'
        WHEN website ~* '(facebook\.com|instagram\.com|wix\.com|blogspot|weebly\.com|wordpress\.com|squarespace\.com)' THEN 'revamp_candidate'
        ELSE 'strong_web_presence'
    END
WHERE lead_type = 'unknown';
