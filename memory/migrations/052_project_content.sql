-- 052_project_content.sql
-- Per-project rich content storage for Universe hub
-- Stores roadmaps, articles, plans, notes, research linked to a project

CREATE TYPE project_content_type AS ENUM (
    'roadmap',
    'article',
    'plan',
    'note',
    'research'
);

CREATE TABLE project_content (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id   TEXT NOT NULL,
    type         project_content_type NOT NULL,
    title        TEXT NOT NULL,
    content      TEXT NOT NULL DEFAULT '',
    metadata     JSONB NOT NULL DEFAULT '{}',
    archived     BOOLEAN NOT NULL DEFAULT FALSE,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_project_content_project_id ON project_content(project_id);
CREATE INDEX idx_project_content_type ON project_content(type);
CREATE INDEX idx_project_content_project_type ON project_content(project_id, type);
CREATE INDEX idx_project_content_archived ON project_content(archived);

-- Auto-update updated_at
CREATE OR REPLACE FUNCTION update_project_content_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_project_content_updated_at
    BEFORE UPDATE ON project_content
    FOR EACH ROW EXECUTE FUNCTION update_project_content_updated_at();
