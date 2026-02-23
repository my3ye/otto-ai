-- SuRe: Surprise-based Replay for Memory Consolidation
-- Adds surprise_score and surprise_replayed to episodic_events.
-- surprise_score: 0.0 (expected) to 1.0 (maximally surprising)
-- surprise_replayed: TRUE once the event has been surfaced for lesson extraction

BEGIN;

ALTER TABLE episodic_events
    ADD COLUMN IF NOT EXISTS surprise_score REAL DEFAULT 0.5
        CHECK (surprise_score BETWEEN 0.0 AND 1.0),
    ADD COLUMN IF NOT EXISTS surprise_replayed BOOLEAN DEFAULT FALSE;

-- Partial index: fast retrieval of pending high-surprise events
CREATE INDEX IF NOT EXISTS idx_episodic_surprise_queue
    ON episodic_events (surprise_score DESC)
    WHERE surprise_replayed = FALSE;

-- Back-fill: error-type events are inherently surprising
UPDATE episodic_events
SET surprise_score = 0.85
WHERE event_type = 'error' AND surprise_score = 0.5;

COMMIT;
