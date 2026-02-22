-- Migration 016: MARS principle extraction table
-- Stores normative principles derived from episodic failures/successes
-- Based on MARS (Metacognitive Agent Reflective Self-improvement) framework

CREATE TABLE IF NOT EXISTS principles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    principle TEXT NOT NULL,
    category TEXT DEFAULT 'general',  -- memory_ops, task_execution, alpha_trading, outreach, general
    source_events UUID[] DEFAULT '{}',  -- episodic event IDs that led to this principle
    confidence FLOAT DEFAULT 0.5 CHECK (confidence >= 0.0 AND confidence <= 1.0),
    times_applied INT DEFAULT 0,
    times_violated INT DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_principles_category ON principles (category);
CREATE INDEX IF NOT EXISTS idx_principles_confidence ON principles (confidence DESC);

-- Auto-update updated_at on row changes
CREATE OR REPLACE FUNCTION update_principles_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS principles_updated_at ON principles;
CREATE TRIGGER principles_updated_at
    BEFORE UPDATE ON principles
    FOR EACH ROW EXECUTE FUNCTION update_principles_updated_at();
