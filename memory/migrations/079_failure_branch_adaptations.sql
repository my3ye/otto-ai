-- Failure-branch adaptation tracking for RL2F
-- Records in-task failure detection, root-cause analysis, correction attempts, and retest results
CREATE TABLE IF NOT EXISTS failure_branch_adaptations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id UUID NOT NULL,
    -- Detection
    failure_type VARCHAR(50) NOT NULL,          -- timeout, error, quality, approach, dependency
    failure_signal TEXT NOT NULL,                -- what triggered detection
    confidence FLOAT NOT NULL DEFAULT 0.0,      -- 0.0-1.0 detection confidence
    -- Root-cause analysis
    root_cause TEXT,                             -- LLM-generated root cause
    root_cause_category VARCHAR(50),            -- prompt, scope, dependency, environment, logic
    -- Correction
    correction_strategy TEXT,                    -- what correction was applied
    corrected_prompt TEXT,                       -- the adjusted prompt/approach
    -- Retest
    retest_passed BOOLEAN,                       -- did the correction work?
    retest_details TEXT,                          -- retest output/evidence
    -- Outcome
    status VARCHAR(20) NOT NULL DEFAULT 'detected',  -- detected, analyzing, correcting, retesting, resolved, failed
    attempt_number INT NOT NULL DEFAULT 1,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    resolved_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_fba_task_id ON failure_branch_adaptations(task_id);
CREATE INDEX IF NOT EXISTS idx_fba_status ON failure_branch_adaptations(status);
CREATE INDEX IF NOT EXISTS idx_fba_failure_type ON failure_branch_adaptations(failure_type);
CREATE INDEX IF NOT EXISTS idx_fba_created ON failure_branch_adaptations(created_at DESC);
