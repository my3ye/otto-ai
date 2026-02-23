-- 035_drift_history.sql
-- Agent Drift detection history (arXiv 2601.04170)
-- Stores per-cycle drift check results for trend analysis.

CREATE TABLE IF NOT EXISTS drift_history (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    checked_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    overall_drift   FLOAT NOT NULL CHECK (overall_drift BETWEEN 0 AND 1),
    per_directive   JSONB NOT NULL DEFAULT '[]'::jsonb,
    flags           JSONB NOT NULL DEFAULT '[]'::jsonb,
    task_ids        UUID[] DEFAULT '{}',
    metadata        JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_drift_history_checked_at ON drift_history (checked_at DESC);
