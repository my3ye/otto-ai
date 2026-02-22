-- Migration 019: APC (Adaptive Plan Caching)
-- Stores successful task execution plans for reuse on semantically similar future tasks.
-- Implements arXiv 2506.14852: "Agentic Plan Caching" — test-time memory for agent planning.
--
-- When a new task arrives, POST /plans/match checks this table for a cached plan
-- with cosine similarity > 0.85. If found, the cached plan is injected as the top
-- candidate in LATS planning, reducing cost and improving success rate.

CREATE TABLE IF NOT EXISTS plan_cache (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id         UUID,                          -- source task (reference only, no FK)
    task_title      TEXT NOT NULL,                 -- short name of the original task
    task_prompt     TEXT NOT NULL,                 -- full task description
    task_embedding  vector(1536) NOT NULL,         -- embedding of task_prompt (text-embedding-3-small)
    selected_plan   TEXT NOT NULL,                 -- the winning approach prompt that was executed
    plan_metadata   JSONB NOT NULL DEFAULT '{}',   -- full ApproachCandidate fields (scores, reasoning)
    success         BOOLEAN NOT NULL DEFAULT TRUE, -- did the task complete successfully?
    execution_time_s INTEGER,                      -- wall-clock execution time in seconds
    model_used      TEXT NOT NULL DEFAULT 'gemini-2.0-flash',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    used_count      INTEGER NOT NULL DEFAULT 0,    -- times this cache entry was reused
    last_used_at    TIMESTAMPTZ
);

-- Cosine similarity index for fast approximate nearest-neighbor search
CREATE INDEX IF NOT EXISTS plan_cache_embedding_idx
    ON plan_cache USING ivfflat (task_embedding vector_cosine_ops)
    WITH (lists = 50);

-- Filter by success rate (only reuse successful plans)
CREATE INDEX IF NOT EXISTS plan_cache_success_idx ON plan_cache (success);

-- Fast lookup by task_id
CREATE INDEX IF NOT EXISTS plan_cache_task_id_idx ON plan_cache (task_id);
