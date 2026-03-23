-- Add detected_country column to athena_prospects
-- Stores the ISO 2-letter country code detected from WhatsApp phone prefix or outreach data
-- Used to auto-assign regional pricing in Athena conversations

ALTER TABLE athena_prospects
    ADD COLUMN IF NOT EXISTS detected_country TEXT,
    ADD COLUMN IF NOT EXISTS pricing_source TEXT; -- 'phone', 'outreach', 'default'

COMMENT ON COLUMN athena_prospects.detected_country IS 'ISO 2-letter country code detected from WhatsApp prefix or outreach data';
COMMENT ON COLUMN athena_prospects.pricing_source IS 'How the country was detected: phone | outreach | default';
