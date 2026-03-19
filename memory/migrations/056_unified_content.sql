-- 056_unified_content.sql
-- Unified Content System — replaces articles, social_calendar_posts, project_content
-- Single content model with granular versioning and content relationships

-- ═══════════════════════════════════════════════════════════════
-- UNIFIED CONTENT TABLE
-- ═══════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS content (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Classification
    content_type    TEXT NOT NULL,              -- article | social_post | landing_copy | roadmap | plan | note | research
    project_id      TEXT,                       -- universe project slug (nullable)
    character       TEXT,                       -- my3ye | pipi | otto (nullable, mainly social_post)

    -- Core
    title           TEXT NOT NULL DEFAULT 'Untitled',
    body            TEXT NOT NULL DEFAULT '',
    metadata        JSONB NOT NULL DEFAULT '{}', -- type-specific fields

    -- Workflow
    status          TEXT NOT NULL DEFAULT 'draft',
    scheduled_at    TIMESTAMPTZ,
    published_at    TIMESTAMPTZ,

    -- Organization
    tags            TEXT[] DEFAULT '{}',
    version         INTEGER NOT NULL DEFAULT 1,

    -- Hierarchy (threads, page sections, series)
    parent_id       UUID REFERENCES content(id) ON DELETE SET NULL,
    sort_order      INTEGER DEFAULT 0,

    -- Audit
    created_by      TEXT DEFAULT 'mev',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Soft delete
    archived        BOOLEAN NOT NULL DEFAULT FALSE
);

-- ═══════════════════════════════════════════════════════════════
-- GRANULAR VERSION HISTORY
-- Every content-changing edit snapshots the previous state
-- ═══════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS content_versions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    content_id      UUID NOT NULL REFERENCES content(id) ON DELETE CASCADE,
    version         INTEGER NOT NULL,

    -- Full snapshot of state at this version
    title           TEXT,
    body            TEXT,
    metadata        JSONB,
    status          TEXT,
    tags            TEXT[],

    -- Change tracking
    changed_fields  TEXT[],              -- which fields changed in the NEXT version
    change_note     TEXT,                -- human description of what changed
    changed_by      TEXT DEFAULT 'mev',

    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE(content_id, version)
);

-- ═══════════════════════════════════════════════════════════════
-- CONTENT RELATIONSHIPS
-- Links between content items (promotes, extends, etc.)
-- ═══════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS content_links (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id       UUID NOT NULL REFERENCES content(id) ON DELETE CASCADE,
    target_id       UUID NOT NULL REFERENCES content(id) ON DELETE CASCADE,
    link_type       TEXT NOT NULL,        -- promotes | extends | references | derived_from | section_of | variant_of
    metadata        JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE(source_id, target_id, link_type)
);

-- ═══════════════════════════════════════════════════════════════
-- INDEXES
-- ═══════════════════════════════════════════════════════════════

-- Primary filters
CREATE INDEX idx_content_type ON content(content_type);
CREATE INDEX idx_content_project ON content(project_id) WHERE project_id IS NOT NULL;
CREATE INDEX idx_content_character ON content(character) WHERE character IS NOT NULL;
CREATE INDEX idx_content_status ON content(status);

-- Composite filters
CREATE INDEX idx_content_type_project ON content(content_type, project_id);
CREATE INDEX idx_content_type_character ON content(content_type, character);
CREATE INDEX idx_content_type_status ON content(content_type, status);

-- Scheduling / sorting
CREATE INDEX idx_content_scheduled ON content(scheduled_at DESC) WHERE scheduled_at IS NOT NULL;
CREATE INDEX idx_content_updated ON content(updated_at DESC);

-- Hierarchy
CREATE INDEX idx_content_parent ON content(parent_id) WHERE parent_id IS NOT NULL;

-- Tags & metadata (GIN for containment queries)
CREATE INDEX idx_content_tags ON content USING GIN(tags);
CREATE INDEX idx_content_metadata ON content USING GIN(metadata);

-- Archived filter
CREATE INDEX idx_content_archived ON content(archived) WHERE archived = TRUE;

-- Versioning
CREATE INDEX idx_content_versions_lookup ON content_versions(content_id, version DESC);

-- Links
CREATE INDEX idx_content_links_source ON content_links(source_id);
CREATE INDEX idx_content_links_target ON content_links(target_id);

-- ═══════════════════════════════════════════════════════════════
-- AUTO-UPDATE TRIGGER
-- ═══════════════════════════════════════════════════════════════
CREATE OR REPLACE FUNCTION update_content_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_content_updated_at
    BEFORE UPDATE ON content
    FOR EACH ROW EXECUTE FUNCTION update_content_updated_at();
