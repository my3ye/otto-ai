-- Migration 062: Onchain Task System Phase 1
-- Adds upvote, dependency scoring, and chain anchoring to tasks
-- Implements priority formula: final_priority = 0.5*base + 0.3*dependency + 0.2*upvote_factor
-- Date: 2026-03-20

ALTER TABLE tasks
  ADD COLUMN IF NOT EXISTS upvotes INT NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS dependency_score FLOAT NOT NULL DEFAULT 0.0,
  ADD COLUMN IF NOT EXISTS chain_id TEXT,
  ADD COLUMN IF NOT EXISTS chain_hash TEXT,
  ADD COLUMN IF NOT EXISTS chain_anchored_at TIMESTAMP WITH TIME ZONE;

-- Index for sorting by upvotes (for community-prioritized view)
CREATE INDEX IF NOT EXISTS idx_tasks_upvotes ON tasks (upvotes DESC) WHERE status = 'pending';

-- Computed priority view for onchain task ordering
CREATE OR REPLACE VIEW tasks_priority_scored AS
SELECT
  id,
  title,
  status,
  priority,
  upvotes,
  dependency_score,
  chain_id,
  chain_hash,
  -- Wilson score approximation for upvotes (stable for small counts)
  ROUND(
    (0.5 * (priority::float / 10.0))
    + (0.3 * LEAST(dependency_score, 1.0))
    + (0.2 * (upvotes::float / NULLIF(upvotes + 10, 0)))
  , 3) AS computed_priority_score,
  created_at,
  agent_type,
  created_by
FROM tasks
WHERE deleted_at IS NULL OR deleted_at IS NOT NULL  -- include all, filter in query
ORDER BY computed_priority_score DESC, created_at DESC;

COMMENT ON COLUMN tasks.upvotes IS 'Community upvote count — drives priority weighting';
COMMENT ON COLUMN tasks.dependency_score IS 'System dependency score 0.0-1.0 — how many critical systems depend on this task';
COMMENT ON COLUMN tasks.chain_id IS 'Onchain task ID once anchored to blockchain';
COMMENT ON COLUMN tasks.chain_hash IS 'Transaction hash of onchain anchoring';
COMMENT ON COLUMN tasks.chain_anchored_at IS 'When this task was anchored to the chain';
