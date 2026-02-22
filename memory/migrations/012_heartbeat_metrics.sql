-- Migration 012: Heartbeat Metrics
-- Tracks performance of each heartbeat run so Otto can evaluate self-improvement over time.
BEGIN;

CREATE TABLE IF NOT EXISTS heartbeat_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- When and what type of heartbeat
    timestamp TIMESTAMPTZ NOT NULL DEFAULT now(),
    heartbeat_type TEXT NOT NULL DEFAULT 'orchestrator'
        CHECK (heartbeat_type IN ('orchestrator', 'reflection', 'alpha')),

    -- Performance metrics
    duration_s NUMERIC(8,2),           -- Total run time in seconds
    budget_used NUMERIC(8,4),          -- USD spent on this heartbeat run

    -- Task metrics
    tasks_created INTEGER NOT NULL DEFAULT 0,
    tasks_launched INTEGER NOT NULL DEFAULT 0,
    tasks_reviewed INTEGER NOT NULL DEFAULT 0,

    -- Communication metrics
    messages_sent INTEGER NOT NULL DEFAULT 0,

    -- Error tracking
    errors JSONB NOT NULL DEFAULT '[]'::jsonb,

    -- Free-form extra data (blockers resolved, notes, etc.)
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb
);

-- Query patterns: recent metrics, trends by type, time-series
CREATE INDEX IF NOT EXISTS idx_heartbeat_metrics_timestamp
    ON heartbeat_metrics (timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_heartbeat_metrics_type_ts
    ON heartbeat_metrics (heartbeat_type, timestamp DESC);

COMMIT;
