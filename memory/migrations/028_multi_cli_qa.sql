-- Migration 028: Multi-CLI task execution + QA layer
-- Adds cli backend field to tasks, QA review tracking

-- Add cli field: which CLI tool runs this task (claude, gemini, kimi)
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS cli TEXT NOT NULL DEFAULT 'claude';

-- Add QA tracking fields
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS qa_status TEXT DEFAULT NULL;  -- pending_qa, approved, rejected, committed
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS qa_output TEXT DEFAULT NULL;  -- QA agent's review
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS qa_reviewer TEXT DEFAULT NULL; -- which CLI did the QA
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS commit_hash TEXT DEFAULT NULL; -- git commit SHA if committed

-- Index for queue management by cli type
CREATE INDEX IF NOT EXISTS idx_tasks_cli ON tasks (cli, status);
