-- Migration 068: Koink table hardening
-- Adds CHECK constraints for status/event_type, plus archived/deleted_at
-- for consistency with the rest of the codebase (MEMORY.md: always use BOTH columns).

-- 1. Status CHECK constraint on koink_tokens
ALTER TABLE koink_tokens
    ADD CONSTRAINT koink_tokens_status_check
    CHECK (status IN ('pending', 'deploying', 'deployed', 'launched'));

-- 2. Event type CHECK constraint on koink_treasury_events
ALTER TABLE koink_treasury_events
    ADD CONSTRAINT koink_treasury_events_event_type_check
    CHECK (event_type IN ('distribution', 'allocation', 'withdrawal'));

-- 3. Soft-delete columns on koink_tokens (consistent with all other tables)
ALTER TABLE koink_tokens
    ADD COLUMN IF NOT EXISTS archived    BOOLEAN      NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS deleted_at  TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_koink_tokens_archived ON koink_tokens(archived) WHERE archived = FALSE;

-- 4. Soft-delete columns on koink_dhm_positions
ALTER TABLE koink_dhm_positions
    ADD COLUMN IF NOT EXISTS archived    BOOLEAN      NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS deleted_at  TIMESTAMPTZ;

-- 5. Soft-delete columns on koink_treasury_events
ALTER TABLE koink_treasury_events
    ADD COLUMN IF NOT EXISTS archived    BOOLEAN      NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS deleted_at  TIMESTAMPTZ;
