-- Add generations JSONB column for dual-generator (Claude + Gemini) results
-- Each generation stores: {generator: {preview_url, html_path, status, error_text, file_size}}
ALTER TABLE landing_pages
  ADD COLUMN IF NOT EXISTS generations JSONB NOT NULL DEFAULT '{}'::jsonb;
