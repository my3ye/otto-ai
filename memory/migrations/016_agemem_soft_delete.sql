-- Migration 016: AgeMem-style soft-delete for semantic memories
-- Adds deleted_at column so reflection agent can make explicit forget decisions
-- instead of relying solely on heuristic decay/archive.

ALTER TABLE semantic_memories
    ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ DEFAULT NULL;

-- Partial index: most queries filter WHERE deleted_at IS NULL, so index nulls only
CREATE INDEX IF NOT EXISTS idx_semantic_deleted_null
    ON semantic_memories (id)
    WHERE deleted_at IS NULL;

COMMENT ON COLUMN semantic_memories.deleted_at IS
    'AgeMem soft-delete. NULL = active. Non-NULL = forgotten by agent decision.';
