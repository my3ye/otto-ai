-- Multi-Agent Kernel Upgrade
-- Reference: arXiv 2602.20934v1 (AgentOS multi-agent coordination)
-- Adds agent registry, agent-scoped interrupt processing, and activity logging.

-- 1. Agent Registry
CREATE TABLE IF NOT EXISTS kernel_agents (
    id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    role VARCHAR(200) NOT NULL,
    status VARCHAR(20) DEFAULT 'idle',     -- idle, active, suspended, error
    config JSONB DEFAULT '{}',             -- l1_capacity, drift_threshold, interrupt_types, cli_agent, etc.
    last_active_at TIMESTAMPTZ,
    last_interrupt_id UUID,
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Pre-register 4 core agents
INSERT INTO kernel_agents (id, name, role, config) VALUES
    ('otto', 'Otto', 'Primary conversational agent — gateway messages from Mev',
     '{"l1_capacity": 12000, "drift_threshold": 0.3, "interrupt_types": ["sig_msg_admin","sig_directive","sig_context_full","sig_perception_err"]}'),
    ('orchestrator', 'Orchestrator', 'Hourly heartbeat — reviews tasks, creates work, messages Mev',
     '{"l1_capacity": 8000, "drift_threshold": 0.4, "interrupt_types": ["sig_heartbeat"], "cli_agent": "heartbeat", "cli_model": "opus", "timeout_seconds": 600}'),
    ('reflection', 'Reflection', 'Half-hourly self-improvement — MARS, memory consolidation',
     '{"l1_capacity": 8000, "drift_threshold": 0.4, "interrupt_types": ["sig_heartbeat"], "cli_agent": "reflection", "cli_model": "opus", "timeout_seconds": 600}'),
    ('task_worker', 'Task Worker', 'Executes queued tasks as detached CLI sessions',
     '{"l1_capacity": 6000, "drift_threshold": 0.5, "interrupt_types": ["sig_task_complete","sig_task_failed"], "max_concurrent": 5}')
ON CONFLICT (id) DO NOTHING;

-- 2. Agent-scope columns (backward-compatible: default 'otto')
ALTER TABLE interrupt_queue ADD COLUMN IF NOT EXISTS agent_id VARCHAR(50) DEFAULT 'otto';
ALTER TABLE cognitive_snapshots ADD COLUMN IF NOT EXISTS agent_id VARCHAR(50) DEFAULT 'otto';
ALTER TABLE kernel_drift_log ADD COLUMN IF NOT EXISTS agent_id VARCHAR(50) DEFAULT 'otto';

-- 3. Indexes for agent-scoped queries
CREATE INDEX IF NOT EXISTS idx_iq_agent_pending ON interrupt_queue (agent_id, priority, created_at) WHERE status = 'pending';
CREATE INDEX IF NOT EXISTS idx_snapshots_agent ON cognitive_snapshots (agent_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_drift_agent ON kernel_drift_log (agent_id, measured_at DESC);

-- 4. Agent activity log
CREATE TABLE IF NOT EXISTS agent_activity_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id VARCHAR(50) REFERENCES kernel_agents(id),
    event_type VARCHAR(50) NOT NULL,  -- started, completed, failed, rate_limited
    interrupt_id UUID,
    details JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_agent_activity ON agent_activity_log (agent_id, created_at DESC);
