-- IMPL-03: VISTA Structured Failure Labels
-- Adds failure classification columns to task_retry_feedback
-- for hypothesis-driven retry optimization (VISTA paper, 2603.18388)

ALTER TABLE task_retry_feedback
    ADD COLUMN IF NOT EXISTS failure_type VARCHAR(50),
    ADD COLUMN IF NOT EXISTS failure_hypothesis TEXT;

-- Index for per-type retry success analysis
CREATE INDEX IF NOT EXISTS idx_trf_failure_type
    ON task_retry_feedback (failure_type)
    WHERE failure_type IS NOT NULL;

COMMENT ON COLUMN task_retry_feedback.failure_type IS 'VISTA taxonomy: scope_creep | quality_insufficient | incomplete | wrong_approach | format_violation | timeout_related | dependency_missing';
COMMENT ON COLUMN task_retry_feedback.failure_hypothesis IS 'LLM-generated root cause hypothesis for this specific failure';
