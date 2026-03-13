-- 040: Decision Proposals — structured collaboration between Otto and Mev
-- Enables Otto to present multi-option decisions with recommendations,
-- and track Mev's responses for context routing.

CREATE TABLE IF NOT EXISTS decision_proposals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    question TEXT NOT NULL,
    context TEXT,
    options JSONB NOT NULL DEFAULT '[]',
    recommendation INT,
    recommendation_reason TEXT,
    source TEXT DEFAULT 'heartbeat',
    source_task_id UUID REFERENCES tasks(id) ON DELETE SET NULL,
    urgency TEXT DEFAULT 'normal',
    status TEXT DEFAULT 'open',
    resolution TEXT,
    resolved_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_proposals_open ON decision_proposals (created_at DESC) WHERE status = 'open';
CREATE INDEX IF NOT EXISTS idx_proposals_source_task ON decision_proposals (source_task_id) WHERE source_task_id IS NOT NULL;
