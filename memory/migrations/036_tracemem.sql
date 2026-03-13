-- 036_tracemem.sql
-- TraceMem: narrative consolidation layer (arXiv 2602.09712, Feb 2026)
-- Three-stage memory consolidation: trace buffering → synaptic (episodic) → systems (narrative).
-- This migration adds the consolidation_id column so narrative-consolidated events
-- are not re-processed on subsequent /episodic/consolidate calls.

ALTER TABLE episodic_events ADD COLUMN IF NOT EXISTS consolidation_id UUID;

CREATE INDEX IF NOT EXISTS idx_episodic_consolidation_id
    ON episodic_events (consolidation_id)
    WHERE consolidation_id IS NOT NULL;
