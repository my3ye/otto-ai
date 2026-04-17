-- Local embedding fallback columns (384-dim from all-MiniLM-L6-v2)
-- Separate from OpenAI's 1536-dim embedding_hv to handle dimension mismatch cleanly.

ALTER TABLE semantic_memories
    ADD COLUMN IF NOT EXISTS embedding_local halfvec(384),
    ADD COLUMN IF NOT EXISTS summary_embedding_local halfvec(384);

-- HNSW index for fast cosine search on local embeddings
CREATE INDEX IF NOT EXISTS idx_semantic_embedding_local_hnsw
    ON semantic_memories USING hnsw (embedding_local halfvec_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- Track which provider was used for each memory
ALTER TABLE semantic_memories
    ADD COLUMN IF NOT EXISTS embedding_provider TEXT DEFAULT NULL;

-- Backfill existing records: they all came from OpenAI
UPDATE semantic_memories
    SET embedding_provider = 'openai'
    WHERE embedding_hv IS NOT NULL AND embedding_provider IS NULL;
