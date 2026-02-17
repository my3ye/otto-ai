-- Pending Questions: tracks questions Otto asks Mev so replies get proper context
BEGIN;

CREATE TABLE IF NOT EXISTS pending_questions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    question TEXT NOT NULL,
    intent TEXT NOT NULL DEFAULT 'general',  -- mission, goal, decision, clarification, general
    context TEXT,  -- additional context about why Otto asked
    channel TEXT NOT NULL DEFAULT 'whatsapp',
    asked_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    resolved_at TIMESTAMPTZ,
    answer TEXT,
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX idx_pending_q_resolved ON pending_questions (resolved_at) WHERE resolved_at IS NULL;
CREATE INDEX idx_pending_q_asked ON pending_questions (asked_at DESC);

COMMIT;
