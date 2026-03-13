-- Migration 039: Connect reasoning chain to learning principles (RL2F Layer 2)
-- When a reasoning entry gets outcome_match = 'miss' or 'partial', we extract
-- WHY the prediction failed and store it as a reusable learning principle.
-- This closes the autonomous self-improvement loop.

-- Track which reasoning entries have already had lessons extracted
ALTER TABLE reasoning_chain
    ADD COLUMN IF NOT EXISTS lesson_extracted BOOLEAN DEFAULT FALSE;

-- Link principles back to the reasoning entries that generated them
ALTER TABLE principles
    ADD COLUMN IF NOT EXISTS source_reasoning_ids UUID[] DEFAULT '{}';

-- Index for finding unprocessed misses efficiently
CREATE INDEX IF NOT EXISTS idx_reasoning_unextracted_misses
    ON reasoning_chain (cycle_ts DESC)
    WHERE outcome_match IN ('miss', 'partial') AND lesson_extracted = FALSE;
