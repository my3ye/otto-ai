-- Migration 055: Context injection history
-- Persists every /context/inject call for OMS browsing and drift analysis

CREATE TABLE IF NOT EXISTS context_injections (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trigger     TEXT NOT NULL,          -- 'startup' | 'compact' | 'resume' | 'heartbeat' | 'reflection' | 'task' | 'whatsapp'
    source      TEXT NOT NULL,          -- raw source param passed to /context/inject
    max_tokens  INT NOT NULL,
    token_estimate INT NOT NULL,
    context_text TEXT NOT NULL,         -- full injected context
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_context_injections_created_at
    ON context_injections (created_at DESC);

CREATE INDEX IF NOT EXISTS idx_context_injections_trigger
    ON context_injections (trigger);
