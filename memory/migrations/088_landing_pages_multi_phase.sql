-- Migration 088: Multi-phase landing page pipeline
-- Adds website scraping, copy synthesis, template selection columns
-- Updates status lifecycle for the new multi-phase flow

ALTER TABLE landing_pages
  ADD COLUMN IF NOT EXISTS scraped_content JSONB NOT NULL DEFAULT '{}'::jsonb,
  ADD COLUMN IF NOT EXISTS synthesized_copy JSONB NOT NULL DEFAULT '{}'::jsonb,
  ADD COLUMN IF NOT EXISTS selected_template TEXT;

-- Drop the old status constraint and add new one covering both legacy + new statuses
ALTER TABLE landing_pages DROP CONSTRAINT IF EXISTS landing_pages_status_check;
ALTER TABLE landing_pages ADD CONSTRAINT landing_pages_status_check
  CHECK (status IN (
    -- Legacy (kept for existing rows)
    'pending', 'researching', 'designing', 'generating', 'review',
    -- New multi-phase pipeline
    'phase1',           -- Tracks A+B+C running in parallel
    'synthesizing',     -- Copy synthesis from scraped + competitor data
    'template_review',  -- Admin selects design template
    'enriching',        -- Merging selected template + copy
    'qa',               -- QA pass on enriched page
    'client_preview',   -- Final page ready for client
    -- Terminal
    'published', 'archived', 'failed'
  ));
