-- Migration 018: Agent tuning proposals
-- Stores Gemini-generated proposals for improving agent prompts
-- Proposals are NEVER auto-applied — they are reviewed by the heartbeat

CREATE TABLE IF NOT EXISTS agent_tuning (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_name  TEXT NOT NULL,           -- e.g. "heartbeat", "reflection"
    proposed_change TEXT NOT NULL,       -- the actual text diff / instruction
    rationale   TEXT NOT NULL,           -- why this change is proposed
    applied     BOOLEAN NOT NULL DEFAULT FALSE,
    applied_at  TIMESTAMPTZ,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS agent_tuning_agent_name_idx ON agent_tuning (agent_name);
CREATE INDEX IF NOT EXISTS agent_tuning_applied_idx ON agent_tuning (applied);
