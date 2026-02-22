-- Migration 013: Metrics Snapshots
-- Daily snapshot table for Otto's self-awareness dashboard.
-- Stores point-in-time metrics so the reflection heartbeat can detect degradation trends.
BEGIN;

CREATE TABLE IF NOT EXISTS metrics_snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- One row per UTC calendar day (UNIQUE enforced via upsert)
    snapshot_date DATE NOT NULL,

    -- Task metrics (all-time counts at snapshot time)
    tasks_total          INTEGER NOT NULL DEFAULT 0,
    tasks_completed      INTEGER NOT NULL DEFAULT 0,
    tasks_failed         INTEGER NOT NULL DEFAULT 0,
    tasks_pending        INTEGER NOT NULL DEFAULT 0,
    tasks_running        INTEGER NOT NULL DEFAULT 0,
    task_success_rate    NUMERIC(5,4),          -- completed / (completed + failed), 0–1
    task_avg_completion_s NUMERIC(10,2),        -- avg seconds from started_at → completed_at

    -- Heartbeat metrics (rolling 7-day window at snapshot time)
    heartbeats_7d        INTEGER NOT NULL DEFAULT 0,
    heartbeat_avg_duration_s  NUMERIC(8,2),
    heartbeat_avg_budget_usd  NUMERIC(8,4),
    heartbeat_failure_rate    NUMERIC(5,4),     -- % runs with errors > 0

    -- Communication (rolling 7-day window)
    messages_sent_7d          INTEGER NOT NULL DEFAULT 0,
    pending_questions_open    INTEGER NOT NULL DEFAULT 0,
    pending_questions_resolved INTEGER NOT NULL DEFAULT 0,

    -- Memory (point-in-time counts)
    semantic_memories_total   INTEGER NOT NULL DEFAULT 0,
    episodic_events_total     INTEGER NOT NULL DEFAULT 0,
    graph_entities_total      INTEGER,          -- nullable; from Neo4j if reachable

    -- Raw full-dashboard JSON for ad-hoc queries
    raw_data JSONB NOT NULL DEFAULT '{}'::jsonb,

    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT metrics_snapshots_date_unique UNIQUE (snapshot_date)
);

CREATE INDEX IF NOT EXISTS idx_metrics_snapshots_date
    ON metrics_snapshots (snapshot_date DESC);

COMMIT;
