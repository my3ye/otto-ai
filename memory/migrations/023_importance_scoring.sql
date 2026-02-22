-- Migration 023: AgeMem Importance Scoring
--
-- Adds importance_score and ttl_days to semantic_memories.
-- importance_score (0.0–1.0) is computed at write time based on category,
-- recency, and duplicate detection. It feeds into weighted search ranking:
--   final_score = 0.7 * cosine_similarity + 0.2 * importance_score + 0.1 * recency_factor
--
-- ttl_days: optional expiration. Memories with ttl_days set are deleted
-- by the reflection heartbeat when created_at + ttl_days < NOW().

ALTER TABLE semantic_memories
    ADD COLUMN IF NOT EXISTS importance_score FLOAT NOT NULL DEFAULT 0.5;

ALTER TABLE semantic_memories
    ADD COLUMN IF NOT EXISTS ttl_days INTEGER DEFAULT NULL;

COMMENT ON COLUMN semantic_memories.importance_score IS
    'AgeMem importance weight (0.0–1.0). Computed at write time from category, '
    'recency context, and duplicate detection. Feeds into weighted search ranking. '
    'identity=1.0, directive=0.95, infrastructure=0.9, project_alpha=0.85, research=0.8, default=0.5.';

COMMENT ON COLUMN semantic_memories.ttl_days IS
    'Optional TTL in days. If set, memory is hard-deleted by reflection heartbeat '
    'when NOW() > created_at + ttl_days. NULL means permanent.';

CREATE INDEX IF NOT EXISTS idx_semantic_importance
    ON semantic_memories (importance_score DESC)
    WHERE deleted_at IS NULL AND archived = FALSE;

CREATE INDEX IF NOT EXISTS idx_semantic_ttl
    ON semantic_memories (created_at)
    WHERE ttl_days IS NOT NULL AND deleted_at IS NULL;
