-- 049: Conclusion capture — audit trail for decisions propagated across docs
CREATE TABLE IF NOT EXISTS conclusions (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    decision        TEXT NOT NULL,
    context         TEXT,
    rationale       TEXT,
    project_slug    TEXT,                   -- universe project this relates to
    article_ids     UUID[] DEFAULT '{}',    -- articles marked for update
    tags            TEXT[] DEFAULT '{}',
    targets_hit     TEXT[] DEFAULT '{}',    -- which subsystems were updated
    memory_id       UUID,                   -- semantic memory fact ID
    episode_id      UUID,                   -- episodic event ID
    created_at      TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_conclusions_project ON conclusions(project_slug) WHERE project_slug IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_conclusions_created  ON conclusions(created_at DESC);
