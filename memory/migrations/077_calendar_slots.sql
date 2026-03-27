-- Migration 077: Unified content calendar slots
-- A thin scheduling layer over the content table.
-- Each slot = one publishing action on one platform on one date.
-- One content item can have multiple slots (article on Paragraph + tweet about it).

CREATE TABLE IF NOT EXISTS calendar_slots (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    content_id      UUID NOT NULL REFERENCES content(id) ON DELETE CASCADE,
    slot_date       DATE NOT NULL,
    slot_position   INTEGER NOT NULL DEFAULT 0,
    platform        TEXT NOT NULL DEFAULT 'paragraph',
    action          TEXT NOT NULL DEFAULT 'publish',
    status          TEXT NOT NULL DEFAULT 'queued',
    posted_at       TIMESTAMPTZ,
    posted_by       TEXT,
    notes           TEXT,
    pinned          BOOLEAN NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),

    UNIQUE(content_id, slot_date, platform)
);

-- Primary access patterns
CREATE INDEX idx_calendar_slots_date ON calendar_slots(slot_date, slot_position);
CREATE INDEX idx_calendar_slots_status ON calendar_slots(status, slot_date);
CREATE INDEX idx_calendar_slots_content ON calendar_slots(content_id);
CREATE INDEX idx_calendar_slots_pinned ON calendar_slots(pinned) WHERE pinned = TRUE;
CREATE INDEX idx_calendar_slots_platform ON calendar_slots(platform, slot_date);

-- Reuse the content updated_at trigger function
CREATE TRIGGER trg_calendar_slots_updated
    BEFORE UPDATE ON calendar_slots
    FOR EACH ROW EXECUTE FUNCTION update_content_updated_at();

-- Constrain valid values
ALTER TABLE calendar_slots ADD CONSTRAINT chk_slot_platform
    CHECK (platform IN ('paragraph', 'x', 'telegram', 'farcaster', 'linkedin', 'discord', 'polkadot_forum', 'gitcoin'));

ALTER TABLE calendar_slots ADD CONSTRAINT chk_slot_action
    CHECK (action IN ('publish', 'announce', 'share', 'thread', 'deploy'));

ALTER TABLE calendar_slots ADD CONSTRAINT chk_slot_status
    CHECK (status IN ('queued', 'ready', 'posted', 'skipped'));
