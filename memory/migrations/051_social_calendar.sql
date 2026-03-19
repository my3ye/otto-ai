-- Social Calendar: scheduled posts, launches, countdowns, meme drops per character/brand
-- Used by the Social Calendar section in the OMS

CREATE TABLE IF NOT EXISTS social_calendar_posts (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    character       TEXT NOT NULL DEFAULT 'pipi',   -- pipi, koink, otto, etc.
    title           TEXT NOT NULL DEFAULT 'Untitled',
    content         TEXT NOT NULL DEFAULT '',
    platforms       TEXT[] DEFAULT '{}',            -- x, telegram, instagram, discord, etc.
    post_type       TEXT NOT NULL DEFAULT 'post',   -- post, launch, countdown, meme_drop, announcement, thread
    scheduled_at    TIMESTAMPTZ,
    status          TEXT NOT NULL DEFAULT 'draft',  -- draft, scheduled, posted, cancelled
    notes           TEXT,
    tags            TEXT[] DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS social_calendar_character_idx
    ON social_calendar_posts(character, scheduled_at DESC);

CREATE INDEX IF NOT EXISTS social_calendar_status_idx
    ON social_calendar_posts(status, scheduled_at);

CREATE INDEX IF NOT EXISTS social_calendar_scheduled_idx
    ON social_calendar_posts(scheduled_at)
    WHERE scheduled_at IS NOT NULL;
