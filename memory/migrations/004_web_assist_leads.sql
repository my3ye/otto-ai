-- Migration 004: Web Assist Lead Database
-- Stores potential web design/development clients scraped from Google Places API
-- For future integration with Web Assist outreach automation

CREATE TABLE IF NOT EXISTS web_assist_leads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Google Places identifiers
    place_id TEXT UNIQUE NOT NULL,

    -- Business info
    name TEXT NOT NULL,
    types TEXT[],                    -- e.g. ['restaurant', 'food', 'establishment']
    business_status TEXT,            -- OPERATIONAL, CLOSED_TEMPORARILY, CLOSED_PERMANENTLY

    -- Contact & location
    address TEXT,
    phone TEXT,
    website TEXT,
    google_maps_url TEXT,

    -- Location data
    city TEXT,
    country TEXT DEFAULT 'LK',
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,

    -- Qualification signals
    has_website BOOLEAN GENERATED ALWAYS AS (website IS NOT NULL AND website != '') STORED,
    rating NUMERIC(2,1),
    user_ratings_total INTEGER,
    price_level INTEGER,             -- 0-4 (free to very expensive)

    -- Lead scoring
    lead_score INTEGER DEFAULT 0,   -- computed score for outreach priority
    lead_notes TEXT,                 -- Otto's notes on why this is a good lead

    -- Outreach tracking (for future Web Assist integration)
    outreach_status TEXT DEFAULT 'new',  -- new, contacted, replied, converted, disqualified
    outreach_at TIMESTAMPTZ,

    -- Scraping metadata
    search_query TEXT,               -- what query found this lead
    scraped_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_leads_country ON web_assist_leads(country);
CREATE INDEX IF NOT EXISTS idx_leads_city ON web_assist_leads(city);
CREATE INDEX IF NOT EXISTS idx_leads_status ON web_assist_leads(outreach_status);
CREATE INDEX IF NOT EXISTS idx_leads_score ON web_assist_leads(lead_score DESC);
CREATE INDEX IF NOT EXISTS idx_leads_has_website ON web_assist_leads(has_website);
CREATE INDEX IF NOT EXISTS idx_leads_types ON web_assist_leads USING GIN(types);
CREATE INDEX IF NOT EXISTS idx_leads_scraped_at ON web_assist_leads(scraped_at DESC);

-- Auto-update updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

DROP TRIGGER IF EXISTS update_web_assist_leads_updated_at ON web_assist_leads;
CREATE TRIGGER update_web_assist_leads_updated_at
    BEFORE UPDATE ON web_assist_leads
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Lead scraping runs log
CREATE TABLE IF NOT EXISTS lead_scrape_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at TIMESTAMPTZ,
    status TEXT DEFAULT 'running',   -- running, completed, failed
    queries_run INTEGER DEFAULT 0,
    leads_found INTEGER DEFAULT 0,
    leads_new INTEGER DEFAULT 0,
    leads_updated INTEGER DEFAULT 0,
    error_message TEXT
);
