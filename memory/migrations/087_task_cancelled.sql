-- Migration 087: Add cancelled_at and cancelled_by columns to tasks
-- Enables distinguishing intentional cancellation from genuine failures.

ALTER TABLE tasks ADD COLUMN IF NOT EXISTS cancelled_at TIMESTAMPTZ;
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS cancelled_by TEXT;  -- 'admin', 'system', 'workflow', 'plan'

CREATE INDEX IF NOT EXISTS idx_tasks_cancelled ON tasks (cancelled_at) WHERE cancelled_at IS NOT NULL;
