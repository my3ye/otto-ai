-- Migration 009: Hierarchical memory upgrades (MIRIX + MemRL + Continual Learning)
-- Adds utility tracking, recency, consolidation flag, and relevance decay to memory tables.

-- semantic_memories: utility tracking + relevance decay (MemRL + Continual Learning)
ALTER TABLE semantic_memories
    ADD COLUMN IF NOT EXISTS utility_score     FLOAT   NOT NULL DEFAULT 1.0,
    ADD COLUMN IF NOT EXISTS last_retrieved_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS relevance_score   FLOAT   NOT NULL DEFAULT 1.0,
    ADD COLUMN IF NOT EXISTS archived          BOOLEAN NOT NULL DEFAULT FALSE;

-- Index for fast utility/relevance queries
CREATE INDEX IF NOT EXISTS idx_semantic_utility   ON semantic_memories (utility_score DESC);
CREATE INDEX IF NOT EXISTS idx_semantic_relevance ON semantic_memories (relevance_score DESC);
CREATE INDEX IF NOT EXISTS idx_semantic_archived  ON semantic_memories (archived) WHERE archived = FALSE;

-- episodic_events: consolidation flag for episodic→semantic consolidation loop (MIRIX)
ALTER TABLE episodic_events
    ADD COLUMN IF NOT EXISTS consolidated    BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS summary         TEXT;

CREATE INDEX IF NOT EXISTS idx_episodic_consolidated ON episodic_events (consolidated) WHERE consolidated = FALSE;
