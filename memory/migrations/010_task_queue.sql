-- Migration 010: Task Queue
-- Decouples heavy work from the heartbeat into independent Claude sessions.
BEGIN;

CREATE TABLE IF NOT EXISTS tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- What to do
    title TEXT NOT NULL,
    prompt TEXT NOT NULL,
    context TEXT,

    -- Scheduling
    priority INTEGER NOT NULL DEFAULT 5
        CHECK (priority BETWEEN 1 AND 10),
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'running', 'completed', 'failed', 'cancelled')),

    -- Execution config
    model TEXT NOT NULL DEFAULT 'sonnet',
    max_budget_usd NUMERIC(5,2) NOT NULL DEFAULT 1.00,
    max_turns INTEGER NOT NULL DEFAULT 10,
    timeout_seconds INTEGER NOT NULL DEFAULT 300,
    working_directory TEXT DEFAULT '/home/web3relic/otto',

    -- Execution state
    pid INTEGER,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    output TEXT,
    error TEXT,
    exit_code INTEGER,

    -- Review
    reviewed BOOLEAN NOT NULL DEFAULT FALSE,
    reviewed_at TIMESTAMPTZ,

    -- Provenance
    created_by TEXT NOT NULL DEFAULT 'heartbeat',
    session_id UUID REFERENCES sessions(id) ON DELETE SET NULL,

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Performance indexes
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks (status);
CREATE INDEX IF NOT EXISTS idx_tasks_priority ON tasks (priority DESC) WHERE status = 'pending';
CREATE INDEX IF NOT EXISTS idx_tasks_reviewed ON tasks (reviewed) WHERE status IN ('completed', 'failed') AND reviewed = FALSE;
CREATE INDEX IF NOT EXISTS idx_tasks_created ON tasks (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_tasks_running ON tasks (status) WHERE status = 'running';

COMMIT;
