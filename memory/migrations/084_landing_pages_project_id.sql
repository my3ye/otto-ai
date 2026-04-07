-- Migration 084: Add project_id to landing_pages
-- Links landing pages to WebAssist projects (Supabase UUID)

ALTER TABLE landing_pages ADD COLUMN IF NOT EXISTS project_id TEXT;
CREATE INDEX IF NOT EXISTS idx_landing_pages_project_id ON landing_pages(project_id) WHERE project_id IS NOT NULL;
