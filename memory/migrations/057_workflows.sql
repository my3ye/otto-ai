-- Migration 057: Workflow Engine
-- Multi-agent workflow orchestration with auto-eval and evolution.
-- Templates define reusable pipelines. Instances track execution state.
-- Each workflow step becomes a task — reuses existing task_runner.sh.

BEGIN;

-- ═══════════════════════════════════════════════════════════════
-- WORKFLOW TEMPLATES — reusable pipeline definitions
-- ═══════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS workflow_templates (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name                TEXT NOT NULL UNIQUE,
    description         TEXT,

    -- Pipeline definition: ordered list of step specs (JSONB array)
    -- Each step: {position, name, agent_type, prompt_template, review_mode,
    --             on_failure, max_budget_usd, max_turns, timeout_seconds,
    --             working_directory, action, notify_template}
    steps               JSONB NOT NULL DEFAULT '[]',

    -- Defaults
    default_priority    INTEGER NOT NULL DEFAULT 5,
    default_working_dir TEXT DEFAULT '/home/web3relic/otto',

    -- Evolution tracking (autoresearch pattern)
    version             INTEGER NOT NULL DEFAULT 1,
    fitness_score       NUMERIC(6,4),           -- best observed composite score
    parent_version_id   UUID REFERENCES workflow_templates(id) ON DELETE SET NULL,

    -- Organization
    tags                TEXT[] DEFAULT '{}',
    archived            BOOLEAN NOT NULL DEFAULT FALSE,

    -- Audit
    created_by          TEXT DEFAULT 'otto',
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_wf_templates_name ON workflow_templates(name);
CREATE INDEX idx_wf_templates_tags ON workflow_templates USING GIN(tags);
CREATE INDEX idx_wf_templates_archived ON workflow_templates(archived) WHERE archived = FALSE;

-- Auto-update timestamp
CREATE OR REPLACE FUNCTION update_wf_template_ts()
RETURNS TRIGGER AS $$
BEGIN NEW.updated_at = NOW(); RETURN NEW; END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_wf_template_ts
    BEFORE UPDATE ON workflow_templates
    FOR EACH ROW EXECUTE FUNCTION update_wf_template_ts();

-- ═══════════════════════════════════════════════════════════════
-- WORKFLOW INSTANCES — execution state for a single run
-- ═══════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS workflow_instances (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    template_id         UUID REFERENCES workflow_templates(id) ON DELETE SET NULL,

    -- Human-readable name for this run
    name                TEXT NOT NULL,

    -- Input variables interpolated into step prompt_templates
    variables           JSONB NOT NULL DEFAULT '{}',

    -- Execution state
    status              TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'running', 'paused', 'completed', 'failed', 'cancelled')),
    current_step        INTEGER NOT NULL DEFAULT 0,

    -- Per-step data (keyed by step position as string)
    step_outputs        JSONB NOT NULL DEFAULT '{}',   -- {"0": "output...", "1": "output..."}
    step_task_ids       JSONB NOT NULL DEFAULT '{}',   -- {"0": "task-uuid", "1": "task-uuid"}
    step_durations      JSONB NOT NULL DEFAULT '{}',   -- {"0": 45.2, "1": 12.8}

    -- Eval scores (populated by auto-eval after completion)
    eval_scores         JSONB NOT NULL DEFAULT '{}',   -- {"overall": 0.82, "quality": 0.9, "cost": 0.7}
    eval_output         TEXT,                           -- evaluator agent's full output

    -- Cost tracking
    cost_total          NUMERIC(8,4) DEFAULT 0,

    -- Error state
    error               TEXT,
    retry_count         INTEGER NOT NULL DEFAULT 0,

    -- Provenance
    trigger_source      TEXT DEFAULT 'manual',          -- manual | reactive_dispatch | heartbeat | api
    trigger_message     TEXT,                           -- original message that triggered this
    priority            INTEGER NOT NULL DEFAULT 5,
    working_directory   TEXT DEFAULT '/home/web3relic/otto',

    -- Timestamps
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    started_at          TIMESTAMPTZ,
    completed_at        TIMESTAMPTZ,

    -- Owner
    created_by          TEXT DEFAULT 'otto'
);

CREATE INDEX idx_wf_instances_status ON workflow_instances(status);
CREATE INDEX idx_wf_instances_template ON workflow_instances(template_id);
CREATE INDEX idx_wf_instances_created ON workflow_instances(created_at DESC);
CREATE INDEX idx_wf_instances_running ON workflow_instances(status) WHERE status IN ('running', 'paused');

CREATE OR REPLACE FUNCTION update_wf_instance_ts()
RETURNS TRIGGER AS $$
BEGIN NEW.updated_at = NOW(); RETURN NEW; END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_wf_instance_ts
    BEFORE UPDATE ON workflow_instances
    FOR EACH ROW EXECUTE FUNCTION update_wf_instance_ts();

-- ═══════════════════════════════════════════════════════════════
-- WORKFLOW EXPERIMENTS — evolution history (autoresearch pattern)
-- Tracks each mutation attempt: what changed, what the fitness was
-- ═══════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS workflow_experiments (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    template_id         UUID NOT NULL REFERENCES workflow_templates(id) ON DELETE CASCADE,

    -- Which version was tested
    template_version    INTEGER NOT NULL,

    -- What was mutated
    mutation_type       TEXT,        -- prompt_edit | step_reorder | budget_adjust | model_swap | step_add | step_remove
    mutation_detail     TEXT,        -- human-readable description of what changed
    mutation_diff       JSONB,       -- structured diff of what changed

    -- Result
    instance_id         UUID REFERENCES workflow_instances(id) ON DELETE SET NULL,
    fitness_score       NUMERIC(6,4),
    baseline_score      NUMERIC(6,4),   -- score of the version before mutation
    improvement         NUMERIC(6,4),   -- fitness_score - baseline_score
    kept                BOOLEAN,         -- was this mutation kept (fitness improved)?

    -- Cost
    cost_usd            NUMERIC(8,4),

    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_wf_experiments_template ON workflow_experiments(template_id);
CREATE INDEX idx_wf_experiments_kept ON workflow_experiments(kept) WHERE kept = TRUE;
CREATE INDEX idx_wf_experiments_created ON workflow_experiments(created_at DESC);

COMMIT;
