-- Migration 017: Evaluation Results
-- Stores benchmark-gated self-modification eval runs for trend tracking

CREATE TABLE IF NOT EXISTS eval_results (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    aggregate_score FLOAT NOT NULL,         -- 0.0–1.0
    per_task_json   JSONB NOT NULL,         -- [{task_id, score, input, output, criteria, notes}]
    context         TEXT,                   -- what changed before this run (e.g. patch applied)
    triggered_by    TEXT NOT NULL DEFAULT 'manual',  -- manual | self_patch | scheduled
    duration_s      FLOAT,                  -- how long the eval took
    model_used      TEXT DEFAULT 'claude-haiku-4-5-20251001'  -- model used for task responses
);

CREATE INDEX IF NOT EXISTS idx_eval_results_run_at ON eval_results (run_at DESC);
CREATE INDEX IF NOT EXISTS idx_eval_results_triggered_by ON eval_results (triggered_by);
