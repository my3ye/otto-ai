-- Migration 091: Pyramid Retrieval + A-MEM Relationship Types
--
-- IMPL-04: Add summary column to semantic_slices for pyramid retrieval.
--   S-MMU loads summaries (L1 handles) for all candidates, then expands top-K.
--   This replaces the current 300-char truncation approach.
--
-- IMPL-07: Add relationship_type to note_links for A-MEM relationship classification.
--   Heuristic classification: extends, refines, contradicts, related (default).

-- Pyramid retrieval: summary handles for slices
ALTER TABLE semantic_slices ADD COLUMN IF NOT EXISTS summary VARCHAR(200);

-- A-MEM relationship types on note_links
ALTER TABLE note_links ADD COLUMN IF NOT EXISTS relationship_type VARCHAR(20) NOT NULL DEFAULT 'related';

-- Backfill summaries from existing slice labels (label is already a short descriptor)
UPDATE semantic_slices SET summary = label WHERE summary IS NULL;
