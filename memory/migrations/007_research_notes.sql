-- Migration 007: Research notes table
-- Stores all research findings, papers, and notes in Postgres (per Mev's decision)
-- Replaces any JSON-based research storage

CREATE TABLE IF NOT EXISTS research_papers (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    arxiv_id        TEXT UNIQUE,
    title           TEXT NOT NULL,
    authors         TEXT,
    abstract        TEXT,
    tags            TEXT[],                        -- e.g. ['memory', 'continual-learning', 'pgvector']
    relevance_notes TEXT,                          -- how this applies to Otto/our systems
    local_pdf_path  TEXT,                          -- path on media drive
    source_url      TEXT,
    added_at        TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    added_by        TEXT NOT NULL DEFAULT 'otto'   -- 'otto' or 'mev'
);

CREATE TABLE IF NOT EXISTS research_notes (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    topic       TEXT NOT NULL,                     -- e.g. 'pgvector-0.8', 'continual-learning', 'lead-scoring'
    title       TEXT NOT NULL,
    content     TEXT NOT NULL,                     -- markdown-formatted findings
    action_items TEXT[],                           -- concrete next steps derived from research
    paper_ids   UUID[],                            -- refs to research_papers
    importance  INTEGER DEFAULT 5,                 -- 1-10
    implemented BOOLEAN DEFAULT FALSE,             -- has this been acted on?
    created_at  TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    updated_at  TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_research_notes_topic ON research_notes(topic);
CREATE INDEX IF NOT EXISTS idx_research_notes_implemented ON research_notes(implemented);
CREATE INDEX IF NOT EXISTS idx_research_papers_tags ON research_papers USING GIN(tags);

CREATE OR REPLACE FUNCTION update_research_notes_updated_at()
RETURNS TRIGGER AS $$
BEGIN NEW.updated_at = now(); RETURN NEW; END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_research_notes_updated_at
    BEFORE UPDATE ON research_notes
    FOR EACH ROW EXECUTE FUNCTION update_research_notes_updated_at();
