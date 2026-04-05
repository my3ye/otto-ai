-- Migration 082: A2A Standard Tasks (Google A2A v1.0)
-- Stores external A2A task lifecycle, separate from internal task queue.

CREATE TABLE IF NOT EXISTS a2a_tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    external_task_id TEXT,           -- caller-provided task ID
    state TEXT NOT NULL DEFAULT 'submitted'
        CHECK (state IN ('submitted','working','input-required','completed','failed','canceled')),
    status_message TEXT,
    input_messages JSONB NOT NULL DEFAULT '[]',   -- conversation history (A2A Message parts)
    artifacts JSONB NOT NULL DEFAULT '[]',         -- output artifacts (A2A Parts)
    metadata JSONB NOT NULL DEFAULT '{}',
    linked_task_id UUID REFERENCES tasks(id),      -- bridge to Otto internal task queue
    created_by TEXT,                               -- sender agent identity
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS a2a_task_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id UUID NOT NULL REFERENCES a2a_tasks(id) ON DELETE CASCADE,
    state TEXT NOT NULL,
    message TEXT,
    timestamp TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_a2a_tasks_state ON a2a_tasks(state);
CREATE INDEX IF NOT EXISTS idx_a2a_tasks_external ON a2a_tasks(external_task_id) WHERE external_task_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_a2a_tasks_linked ON a2a_tasks(linked_task_id) WHERE linked_task_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_a2a_task_history_task ON a2a_task_history(task_id, timestamp);
