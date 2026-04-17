-- Migration 091: Pyramid retrieval summaries + A-MEM relationship types
-- Phase 2 of research-superior patterns implementation
-- Reference: OmniMem (2604.01007) pyramid retrieval, A-MEM (2502.12110) relationship types

-- Add summary column to semantic_slices for L1 Handle (pyramid retrieval)
ALTER TABLE semantic_slices
  ADD COLUMN IF NOT EXISTS summary VARCHAR(200);

-- Add relationship_type to note_links for A-MEM typed links
ALTER TABLE note_links
  ADD COLUMN IF NOT EXISTS relationship_type VARCHAR(20) DEFAULT 'related';

-- Backfill summaries from existing slice labels (first-sentence proxy)
-- Labels are already short descriptors; they serve as initial summaries
UPDATE semantic_slices
  SET summary = LEFT(label, 200)
  WHERE summary IS NULL;

-- Index for relationship type queries
CREATE INDEX IF NOT EXISTS idx_note_links_relationship_type
  ON note_links (relationship_type);
