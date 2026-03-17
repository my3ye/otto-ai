-- Education Engine: gamified skill learning system
-- Tracks per-user progress through skill trees, XP, and completions

CREATE TABLE IF NOT EXISTS education_progress (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     TEXT NOT NULL DEFAULT 'mev',  -- default to Mev until multi-user
    cluster_id  TEXT NOT NULL,
    node_id     TEXT NOT NULL,
    completed   BOOLEAN NOT NULL DEFAULT FALSE,
    xp_earned   INTEGER NOT NULL DEFAULT 0,
    resources_completed JSONB NOT NULL DEFAULT '[]',  -- list of resource URLs completed
    completed_at TIMESTAMPTZ,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (user_id, node_id)
);

CREATE INDEX IF NOT EXISTS idx_education_progress_user ON education_progress(user_id);
CREATE INDEX IF NOT EXISTS idx_education_progress_cluster ON education_progress(cluster_id);

-- XP log for history/leaderboard
CREATE TABLE IF NOT EXISTS education_xp_log (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     TEXT NOT NULL DEFAULT 'mev',
    cluster_id  TEXT NOT NULL,
    node_id     TEXT NOT NULL,
    resource_url TEXT,
    xp_delta    INTEGER NOT NULL,
    reason      TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_education_xp_log_user ON education_xp_log(user_id);
