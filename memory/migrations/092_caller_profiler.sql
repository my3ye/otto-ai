-- Migration 092: Caller Profiler (STEM Agent 2603.22359)
-- Track tool usage patterns per agent_type for behavioral profiling

CREATE TABLE IF NOT EXISTS agent_tool_usage (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_type VARCHAR(100) NOT NULL,
    tool_name VARCHAR(200) NOT NULL,
    invocation_count INTEGER NOT NULL DEFAULT 1,
    success_count INTEGER NOT NULL DEFAULT 0,
    failure_count INTEGER NOT NULL DEFAULT 0,
    avg_latency_ms DOUBLE PRECISION,
    last_used TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    session_id UUID,
    task_id UUID,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Aggregation index: unique per agent_type + tool_name for upserts
CREATE UNIQUE INDEX IF NOT EXISTS idx_agent_tool_usage_agent_tool
  ON agent_tool_usage (agent_type, tool_name);

-- Query patterns
CREATE INDEX IF NOT EXISTS idx_agent_tool_usage_agent
  ON agent_tool_usage (agent_type);
CREATE INDEX IF NOT EXISTS idx_agent_tool_usage_last_used
  ON agent_tool_usage (last_used DESC);
