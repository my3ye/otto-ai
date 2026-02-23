-- RL2F: Reinforcement Learning from Teacher Feedback
-- Stores Opus teacher critiques of Otto's decisions using Abhidharma evaluation framework.
-- Root condition analysis (lobha/dosa/moha vs alobha/adosa/amoha)
-- Mental factor scores (sati, panna, viriya, upekkha, ekaggata)

BEGIN;

CREATE TABLE IF NOT EXISTS rl2f_feedback (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cycle_ts TIMESTAMPTZ NOT NULL,
    heartbeat_type TEXT NOT NULL,
    system_state TEXT,
    decision TEXT NOT NULL,
    teacher_feedback TEXT,
    root_condition_analysis JSONB,
    mental_factor_scores JSONB,
    outcome TEXT,
    outcome_match VARCHAR(20),
    used_in_training BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Query by cycle timestamp (most recent first)
CREATE INDEX IF NOT EXISTS idx_rl2f_cycle_ts
    ON rl2f_feedback (cycle_ts DESC);

-- Query by heartbeat type + time
CREATE INDEX IF NOT EXISTS idx_rl2f_type_ts
    ON rl2f_feedback (heartbeat_type, cycle_ts DESC);

-- Find untrained examples for next training batch
CREATE INDEX IF NOT EXISTS idx_rl2f_untrained
    ON rl2f_feedback (created_at)
    WHERE used_in_training = FALSE;

COMMIT;
