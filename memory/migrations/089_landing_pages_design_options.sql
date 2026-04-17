-- Migration 089: Design review phase for landing page pipeline
-- Adds design_options + selected_design columns so the pipeline generates
-- 3 design.md candidates for review before proceeding to template generation.
-- Inserts 'design_review' status between 'synthesizing' and 'template_review'.

ALTER TABLE landing_pages
  ADD COLUMN IF NOT EXISTS design_options JSONB NOT NULL DEFAULT '{}'::jsonb,
  ADD COLUMN IF NOT EXISTS selected_design TEXT;

-- Rebuild status constraint with design_review added
ALTER TABLE landing_pages DROP CONSTRAINT IF EXISTS landing_pages_status_check;
ALTER TABLE landing_pages ADD CONSTRAINT landing_pages_status_check
  CHECK (status IN (
    -- Legacy (kept for existing rows)
    'pending', 'researching', 'designing', 'generating', 'review',
    -- Multi-phase pipeline
    'phase1',           -- Tracks A+B+C running in parallel
    'synthesizing',     -- Copy synthesis from scraped + competitor data
    'design_review',    -- Admin selects one of 3 generated design options
    'template_review',  -- Admin selects design template
    'enriching',        -- Merging selected template + copy
    'qa',               -- QA pass on enriched page
    'client_preview',   -- Final page ready for client
    -- Terminal
    'published', 'archived', 'failed'
  ));
