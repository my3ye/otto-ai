-- Live Systems registry + weekly auto-improvement cycle tracking
-- Distinction: Tasks have a done state; Live Systems have ongoing weekly improvement loops.

CREATE TABLE IF NOT EXISTS live_systems (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            TEXT NOT NULL UNIQUE,
    description     TEXT,
    service_name    TEXT,              -- systemd service name (e.g. otto-memory)
    repo_path       TEXT,              -- absolute path to git repo
    health_endpoint TEXT,              -- URL to GET for health check
    eval_criteria   JSONB DEFAULT '[]'::jsonb,  -- list of {name, check, threshold} objects
    improvement_prompt TEXT,           -- LLM prompt template for identifying improvements
    status          TEXT NOT NULL DEFAULT 'active'  CHECK (status IN ('active', 'paused', 'failed')),
    last_improved_at TIMESTAMPTZ,
    next_improvement_at TIMESTAMPTZ,   -- scheduled next run (null = not scheduled)
    cycle_count     INTEGER NOT NULL DEFAULT 0,
    consecutive_failures INTEGER NOT NULL DEFAULT 0,
    metadata        JSONB DEFAULT '{}'::jsonb,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS live_system_improvements (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    system_id       UUID NOT NULL REFERENCES live_systems(id) ON DELETE CASCADE,
    cycle_number    INTEGER NOT NULL,
    started_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at    TIMESTAMPTZ,
    -- Checkpoint
    checkpoint_tag  TEXT,              -- git tag or snapshot identifier
    pre_state       JSONB DEFAULT '{}'::jsonb,  -- captured state before improvement
    -- Improvement
    improvement_identified TEXT,       -- what improvement was identified
    improvement_task_id UUID,          -- task queue ID if delegated to task runner
    improvement_applied BOOLEAN DEFAULT FALSE,
    -- Evals
    eval_results    JSONB DEFAULT '{}'::jsonb,  -- {passed: bool, checks: [...]}
    eval_passed     BOOLEAN,
    -- Rollback
    rollback_performed BOOLEAN DEFAULT FALSE,
    rollback_reason TEXT,
    -- Status
    status          TEXT NOT NULL DEFAULT 'running'
                    CHECK (status IN ('running', 'completed', 'failed', 'rolled_back')),
    notes           TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_live_system_improvements_system_id
    ON live_system_improvements(system_id);
CREATE INDEX IF NOT EXISTS idx_live_system_improvements_started_at
    ON live_system_improvements(started_at DESC);
CREATE INDEX IF NOT EXISTS idx_live_systems_status
    ON live_systems(status);
CREATE INDEX IF NOT EXISTS idx_live_systems_next_improvement
    ON live_systems(next_improvement_at)
    WHERE next_improvement_at IS NOT NULL;
