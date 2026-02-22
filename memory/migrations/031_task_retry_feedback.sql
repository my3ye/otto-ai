-- RL2F Phase 2: Task-level retry feedback chain
-- Stores structured feedback turns for each QA rejection + retry cycle.
-- Each row = one rejection event: original task rejected, feedback generated, outcome tracked.
-- Enables: feedback chain retrieval per task, retry success rate metrics.

BEGIN;

CREATE TABLE IF NOT EXISTS task_retry_feedback (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    original_task_id UUID NOT NULL,      -- the rejected task ID
    retry_task_id UUID,                  -- the new retry task ID (set when heartbeat creates it)
    attempt_number INT NOT NULL DEFAULT 1, -- 1 = first rejection, 2 = second, etc.
    feedback JSONB NOT NULL,             -- structured rl2f_feedback JSON from qa_runner.sh
    qa_rejection_reason TEXT,            -- plain text rejection summary
    feedback_injected BOOLEAN DEFAULT FALSE, -- whether feedback was injected into retry prompt
    outcome VARCHAR(20) DEFAULT 'pending', -- pending | succeeded | failed | abandoned
    outcome_details TEXT,                -- what happened in the retry
    created_at TIMESTAMPTZ DEFAULT now(),
    resolved_at TIMESTAMPTZ             -- when outcome was updated (retry completed)
);

-- Query feedback chain for a specific original task
CREATE INDEX IF NOT EXISTS idx_trf_original_task
    ON task_retry_feedback (original_task_id, attempt_number);

-- Query by retry task (to update outcome when retry completes)
CREATE INDEX IF NOT EXISTS idx_trf_retry_task
    ON task_retry_feedback (retry_task_id)
    WHERE retry_task_id IS NOT NULL;

-- Metrics: filter by outcome
CREATE INDEX IF NOT EXISTS idx_trf_outcome
    ON task_retry_feedback (outcome, created_at DESC);

COMMIT;
