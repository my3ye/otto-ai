-- 046: AutoEvolve — autoresearch-inspired self-improvement experiment tracking
-- Tracks proposed changes to Otto system files (heartbeat.md, reflection.md, etc.)
-- with before/after metrics and keep/discard decisions.
--
-- Pattern adapted from karpathy/autoresearch:
--   program.md → target_file (heartbeat.md, reflection.md)
--   val_bpb metric → metric_before/metric_after (RL2F accuracy, task success rate)
--   results.tsv → this table
--   keep/discard loop → outcome field

CREATE TABLE IF NOT EXISTS autoevolve_experiments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- What we changed and why
    target_file TEXT NOT NULL,           -- e.g. '.claude/agents/heartbeat.md'
    hypothesis TEXT NOT NULL,            -- WHY we expect this to help
    change_description TEXT NOT NULL,    -- WHAT was changed (human-readable diff summary)

    -- Metric tracking (RL2F accuracy by default, 0.0-1.0)
    metric_name TEXT NOT NULL DEFAULT 'rl2f_accuracy',
    metric_before FLOAT,                 -- metric value before change
    metric_after FLOAT,                  -- metric value after N evaluation cycles
    evaluation_cycles INT DEFAULT 0,     -- how many cycles evaluated under new change

    -- Experiment lifecycle
    status TEXT NOT NULL DEFAULT 'proposed',  -- proposed | active | keep | discard | crashed
    outcome TEXT,                        -- narrative summary of what happened
    git_checkpoint TEXT,                 -- git commit hash before experiment (for rollback)

    -- Generation tracking (like autoresearch's iteration count)
    generation INT NOT NULL DEFAULT 1,   -- which improvement generation this belongs to
    source TEXT DEFAULT 'reflection',    -- which agent proposed this

    created_at TIMESTAMPTZ DEFAULT NOW(),
    evaluated_at TIMESTAMPTZ,
    resolved_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_autoevolve_status ON autoevolve_experiments (status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_autoevolve_target ON autoevolve_experiments (target_file, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_autoevolve_generation ON autoevolve_experiments (generation DESC);

-- Track Otto's current software generation (total kept experiments)
CREATE TABLE IF NOT EXISTS autoevolve_generation (
    id INT PRIMARY KEY DEFAULT 1,
    current_generation INT NOT NULL DEFAULT 0,
    last_updated TIMESTAMPTZ DEFAULT NOW()
);

INSERT INTO autoevolve_generation (id, current_generation) VALUES (1, 0)
ON CONFLICT (id) DO NOTHING;
