-- Migration 083: Landing Pages
-- Product entity for generated landing pages — orchestrated by workflow engine, served by nginx

CREATE TABLE IF NOT EXISTS landing_pages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slug TEXT NOT NULL UNIQUE,
    business_name TEXT NOT NULL,
    business_url TEXT,
    description TEXT,
    target_audience TEXT,

    -- Aggregated research (populated by workflow step callbacks)
    research_data JSONB NOT NULL DEFAULT '{}',
    competitor_data JSONB NOT NULL DEFAULT '{}',
    design_decisions JSONB NOT NULL DEFAULT '{}',

    -- Generated output
    html_path TEXT,                  -- /var/www/html/landing-pages/{slug}/index.html
    preview_url TEXT,                -- https://otto.505.systems/landing-pages/{slug}/

    -- Lifecycle
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending','researching','designing','generating','review','published','archived')),
    error_text TEXT,

    -- Workflow link
    workflow_instance_id UUID,       -- FK to workflow_instances (nullable, set after workflow starts)

    -- Metadata
    created_by TEXT DEFAULT 'otto',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_landing_pages_status ON landing_pages(status);
CREATE INDEX IF NOT EXISTS idx_landing_pages_slug ON landing_pages(slug);
CREATE INDEX IF NOT EXISTS idx_landing_pages_workflow ON landing_pages(workflow_instance_id)
    WHERE workflow_instance_id IS NOT NULL;

-- Auto-update updated_at on row changes
CREATE OR REPLACE FUNCTION update_landing_pages_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_landing_pages_updated_at
    BEFORE UPDATE ON landing_pages
    FOR EACH ROW
    EXECUTE FUNCTION update_landing_pages_updated_at();
