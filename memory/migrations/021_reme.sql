-- Migration 021: ReMe (Retrieval-enhanced Memory Evolution)
--
-- Adds a retrieval_count column to semantic_memories so that retrieval
-- frequency can be used as a bidirectional signal:
--   - Frequently retrieved → confidence boost
--   - Never retrieved (old) → accelerated relevance decay

ALTER TABLE semantic_memories
    ADD COLUMN IF NOT EXISTS retrieval_count INTEGER NOT NULL DEFAULT 0;

COMMENT ON COLUMN semantic_memories.retrieval_count IS
    'Total number of times this memory has been returned in semantic search results. '
    'Used by ReMe to strengthen frequently-retrieved memories and accelerate decay '
    'on memories that are never recalled.';

CREATE INDEX IF NOT EXISTS idx_semantic_retrieval_count
    ON semantic_memories (retrieval_count DESC);
