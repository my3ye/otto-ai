-- Migration 053: Add owner field to tasks
-- Tracks whether a task was created by Otto (heartbeat/orchestrator) or Mev (OMS UI)

ALTER TABLE tasks
    ADD COLUMN IF NOT EXISTS owner TEXT NOT NULL DEFAULT 'otto'
    CHECK (owner IN ('otto', 'mev'));

-- Existing tasks all default to 'otto'
-- Index for fast owner-filtered queries
CREATE INDEX IF NOT EXISTS idx_tasks_owner ON tasks(owner);
