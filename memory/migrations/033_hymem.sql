-- HyMem: Dual-granularity memory retrieval (arXiv 2602.13933)
-- Adds summary tier for fast, lightweight retrieval with detailed tier fallback

BEGIN;

-- Add summary_content column for the fast summary tier
ALTER TABLE semantic_memories
ADD COLUMN IF NOT EXISTS summary_content TEXT;

-- Add embedding for summary tier (separate from full content embedding)
ALTER TABLE semantic_memories
ADD COLUMN IF NOT EXISTS summary_embedding vector(1536);

ALTER TABLE semantic_memories
ADD COLUMN IF NOT EXISTS summary_embedding_hv halfvec(1536);

-- Index for fast summary tier searches
CREATE INDEX IF NOT EXISTS idx_semantic_summary_embedding 
ON semantic_memories USING hnsw (summary_embedding_hv halfvec_cosine_ops)
WHERE summary_embedding_hv IS NOT NULL;

-- Track which tier was used for retrieval analytics
ALTER TABLE semantic_memories
ADD COLUMN IF NOT EXISTS summary_retrieval_count INTEGER NOT NULL DEFAULT 0;

COMMIT;
