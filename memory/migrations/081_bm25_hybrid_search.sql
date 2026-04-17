-- BM25 hybrid search: add tsvector column + GIN indexes for full-text and trigram search
-- OmniMem paper (arXiv 2604.01007v1) finding: BM25 + pgvector set-union improves recall 30-50%

-- Add generated tsvector column from content
ALTER TABLE semantic_memories
ADD COLUMN IF NOT EXISTS content_tsv tsvector
GENERATED ALWAYS AS (to_tsvector('english', coalesce(content, ''))) STORED;

-- GIN index on tsvector for fast full-text search (ts_rank)
CREATE INDEX IF NOT EXISTS idx_semantic_content_tsv
ON semantic_memories USING GIN (content_tsv);

-- GIN index on content for pg_trgm fuzzy matching (already have pg_trgm extension)
CREATE INDEX IF NOT EXISTS idx_semantic_content_trgm
ON semantic_memories USING GIN (content gin_trgm_ops);
