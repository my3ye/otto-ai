-- Task Plans: DAG-based multi-task orchestration from a single instruction.
-- A plan decomposes one instruction into N tasks with dependency edges.
-- The plan executor auto-runs tasks as their dependencies complete.

CREATE TABLE IF NOT EXISTS task_plans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT NOT NULL,
    instruction TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'executing', 'completed', 'failed', 'cancelled')),
    topology TEXT CHECK (topology IN ('parallel', 'sequential', 'hybrid')),
    total_items INT NOT NULL DEFAULT 0,
    completed_items INT NOT NULL DEFAULT 0,
    failed_items INT NOT NULL DEFAULT 0,
    agents_employed TEXT[] DEFAULT '{}',
    created_by TEXT NOT NULL DEFAULT 'reactive_dispatch',
    trigger_message TEXT,
    metadata JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

-- Add plan_id and depends_on to tasks
ALTER TABLE tasks
    ADD COLUMN IF NOT EXISTS plan_id UUID REFERENCES task_plans(id),
    ADD COLUMN IF NOT EXISTS depends_on UUID[] DEFAULT '{}';

-- Index for plan executor: find tasks belonging to a plan
CREATE INDEX IF NOT EXISTS idx_tasks_plan_id ON tasks(plan_id) WHERE plan_id IS NOT NULL;

-- Index for pending plans
CREATE INDEX IF NOT EXISTS idx_task_plans_status ON task_plans(status) WHERE status IN ('pending', 'executing');

COMMENT ON TABLE task_plans IS 'DAG-based multi-task plans. One instruction → N tasks with dependency edges.';
COMMENT ON COLUMN tasks.plan_id IS 'FK to task_plans — groups tasks from the same instruction';
COMMENT ON COLUMN tasks.depends_on IS 'UUID array of task IDs that must complete before this task can run';
