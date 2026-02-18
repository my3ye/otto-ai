-- Bidirectional cross-brain communication: Gemini <-> Claude
-- Extends pending_questions to support notes from Gemini to Claude
BEGIN;

ALTER TABLE pending_questions
    ADD COLUMN IF NOT EXISTS direction TEXT NOT NULL DEFAULT 'claude_to_gemini';

ALTER TABLE pending_questions
    ADD COLUMN IF NOT EXISTS source_brain TEXT NOT NULL DEFAULT 'claude';

CREATE INDEX IF NOT EXISTS idx_pending_q_direction
    ON pending_questions (direction, resolved_at) WHERE resolved_at IS NULL;

COMMIT;
