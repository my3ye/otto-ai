-- Migration 008: Migrate semantic_memories to halfvec(1536) + HNSW index
-- Benefits: ~50% storage reduction, 23% faster index builds, equivalent recall
-- Source: research note pgvector-0.8 (importance: 9)

-- Add halfvec column alongside existing vector column
ALTER TABLE semantic_memories ADD COLUMN IF NOT EXISTS embedding_hv halfvec(1536);

-- Populate halfvec column from existing vector data
UPDATE semantic_memories
SET embedding_hv = embedding::halfvec(1536)
WHERE embedding IS NOT NULL AND embedding_hv IS NULL;

-- Drop old IVFFlat index on vector column
DROP INDEX IF EXISTS idx_semantic_embedding;

-- Create HNSW index on halfvec column (cosine distance)
CREATE INDEX IF NOT EXISTS idx_semantic_embedding_hv
    ON semantic_memories USING hnsw (embedding_hv halfvec_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- Note: after confirming the halfvec column works correctly in production,
-- the old vector column can be dropped with:
--   ALTER TABLE semantic_memories DROP COLUMN embedding;
-- and embedding_hv renamed to embedding. Done as a separate step for safety.
