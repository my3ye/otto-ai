-- Migration 034: CAT context workspace
-- Implements inter-heartbeat scratch pad from CAT (Context as a Tool, arXiv 2512.22087)
-- Agents read/write named artifacts to maintain continuity across cycles

CREATE TABLE IF NOT EXISTS context_workspace (
    key         TEXT PRIMARY KEY,
    value       TEXT NOT NULL,
    metadata    JSONB NOT NULL DEFAULT '{}',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Index on updated_at for listing most-recent artifacts first
CREATE INDEX IF NOT EXISTS idx_workspace_updated ON context_workspace (updated_at DESC);
