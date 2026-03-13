-- Paper triage scoring system
-- Adds structured scoring to research_papers so Otto can prioritize
-- what to implement instead of blindly building everything.

-- Scoring dimensions (each 1-10):
--   relevance:   Does this solve a problem Otto actually has RIGHT NOW?
--   overlap:     How much does this duplicate existing implementations? (10 = no overlap, 1 = fully redundant)
--   impact:      If implemented, how much does Otto improve? (10 = transformative, 1 = marginal)
--   complexity:  How hard to implement on our stack? (10 = trivial, 1 = requires new infra)
--   futureproof: Is this a fundamental technique or a narrow hack? (10 = foundational, 1 = brittle trick)

ALTER TABLE research_papers
    ADD COLUMN IF NOT EXISTS score_relevance   smallint CHECK (score_relevance BETWEEN 1 AND 10),
    ADD COLUMN IF NOT EXISTS score_overlap     smallint CHECK (score_overlap BETWEEN 1 AND 10),
    ADD COLUMN IF NOT EXISTS score_impact      smallint CHECK (score_impact BETWEEN 1 AND 10),
    ADD COLUMN IF NOT EXISTS score_complexity  smallint CHECK (score_complexity BETWEEN 1 AND 10),
    ADD COLUMN IF NOT EXISTS score_futureproof smallint CHECK (score_futureproof BETWEEN 1 AND 10),
    ADD COLUMN IF NOT EXISTS composite_score   real,
    ADD COLUMN IF NOT EXISTS score_reasoning   text,
    ADD COLUMN IF NOT EXISTS scored_at         timestamptz,
    ADD COLUMN IF NOT EXISTS status            text NOT NULL DEFAULT 'unscored'
        CHECK (status IN ('unscored', 'scored', 'implement', 'skip', 'implemented', 'superseded')),
    ADD COLUMN IF NOT EXISTS overlaps_with     text[],   -- arxiv_ids or impl names this overlaps
    ADD COLUMN IF NOT EXISTS published_date    date;

-- Composite score: weighted formula favoring impact and relevance
-- impact(30%) + relevance(25%) + futureproof(20%) + overlap(15%) + complexity(10%)
CREATE OR REPLACE FUNCTION compute_paper_composite()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.score_relevance IS NOT NULL
       AND NEW.score_overlap IS NOT NULL
       AND NEW.score_impact IS NOT NULL
       AND NEW.score_complexity IS NOT NULL
       AND NEW.score_futureproof IS NOT NULL THEN
        NEW.composite_score := (
            NEW.score_impact * 0.30 +
            NEW.score_relevance * 0.25 +
            NEW.score_futureproof * 0.20 +
            NEW.score_overlap * 0.15 +
            NEW.score_complexity * 0.10
        );
        NEW.scored_at := now();
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_paper_composite ON research_papers;
CREATE TRIGGER trg_paper_composite
    BEFORE INSERT OR UPDATE ON research_papers
    FOR EACH ROW EXECUTE FUNCTION compute_paper_composite();

-- Index for triage queries
CREATE INDEX IF NOT EXISTS idx_papers_composite ON research_papers (composite_score DESC NULLS LAST);
CREATE INDEX IF NOT EXISTS idx_papers_status ON research_papers (status);
