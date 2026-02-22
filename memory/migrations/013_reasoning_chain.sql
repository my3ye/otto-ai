-- Migration 013: Persistent reasoning chain across heartbeats
-- Stores per-heartbeat reasoning, decisions, expected vs actual outcomes.
-- Creates a feedback loop: decide → act → observe → learn → decide better.

CREATE TABLE IF NOT EXISTS reasoning_chain (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    heartbeat_type  VARCHAR(50) NOT NULL DEFAULT 'orchestrator', -- orchestrator | reflection | alpha
    cycle_ts        TIMESTAMPTZ NOT NULL DEFAULT now(),
    reasoning       TEXT NOT NULL,          -- WHY: key reasoning this cycle
    decisions       TEXT,                   -- WHAT: decisions made
    expected        TEXT,                   -- EXPECTED: what should happen as a result
    actual          TEXT,                   -- ACTUAL: filled by next cycle after observing
    outcome_match   VARCHAR(20) DEFAULT 'pending', -- pending | matched | partial | miss
    metadata        JSONB NOT NULL DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS reasoning_chain_cycle_ts_idx  ON reasoning_chain(cycle_ts DESC);
CREATE INDEX IF NOT EXISTS reasoning_chain_type_ts_idx   ON reasoning_chain(heartbeat_type, cycle_ts DESC);
