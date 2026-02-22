-- Migration 027: BMAM Salience-Aware Memory Layer
--
-- Implements salience scoring from the Brain-inspired Multi-Agent Memory Framework
-- (BMAM, arxiv 2601.20465). Adds a salience_score column to semantic_memories.
--
-- Salience formula (computed at write time):
--   salience = 0.3*recency + 0.2*frequency + 0.3*importance + 0.2*goal_relevance
--
-- Search ranking formula (replaces AgeMem-only formula):
--   final_rank = 0.6*cosine_similarity + 0.4*salience_score
--
-- Decay (via POST /memory/salience-decay):
--   salience *= 0.95^days_elapsed for memories not accessed in 3+ days

ALTER TABLE semantic_memories
    ADD COLUMN IF NOT EXISTS salience_score FLOAT NOT NULL DEFAULT 0.5;

COMMENT ON COLUMN semantic_memories.salience_score IS
    'BMAM salience score (0.0–1.0). Computed at write time from recency, retrieval '
    'frequency, importance, and goal-relevance. Decays by 0.95x per day for memories '
    'not accessed in 3+ days. Feeds into search re-ranking: 0.6*cosine + 0.4*salience.';

CREATE INDEX IF NOT EXISTS idx_semantic_salience
    ON semantic_memories (salience_score DESC)
    WHERE deleted_at IS NULL AND archived = FALSE;
