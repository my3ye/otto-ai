-- Migration 076: Add label column to content_versions
-- Allows named checkpoints like "Post-review draft", "Final approved"
ALTER TABLE content_versions ADD COLUMN IF NOT EXISTS label TEXT;

CREATE INDEX IF NOT EXISTS idx_content_versions_label
  ON content_versions(content_id, label)
  WHERE label IS NOT NULL;
