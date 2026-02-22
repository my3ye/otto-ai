-- Migration 022: A-Mem Associative Memory Linking (Zettelkasten-style)
--
-- Creates a note_links table for bidirectional associative links between
-- semantic memories. When a new memory is stored, it is automatically linked
-- to existing memories with cosine similarity > 0.7.
--
-- Inspired by A-Mem (arXiv:2502.12110): upgrading flat vector retrieval to
-- a linked knowledge graph where retrieving one memory surfaces connected context.

CREATE TABLE IF NOT EXISTS note_links (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id   UUID NOT NULL REFERENCES semantic_memories(id) ON DELETE CASCADE,
    target_id   UUID NOT NULL REFERENCES semantic_memories(id) ON DELETE CASCADE,
    link_strength FLOAT NOT NULL DEFAULT 0.0,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT note_links_no_self_loop CHECK (source_id != target_id),
    CONSTRAINT note_links_unique_pair UNIQUE (source_id, target_id)
);

-- Indexes for fast 1-hop traversal in both directions
CREATE INDEX IF NOT EXISTS idx_note_links_source ON note_links (source_id);
CREATE INDEX IF NOT EXISTS idx_note_links_target ON note_links (target_id);
CREATE INDEX IF NOT EXISTS idx_note_links_strength ON note_links (link_strength DESC);

COMMENT ON TABLE note_links IS
    'Bidirectional associative links between semantic memories. '
    'Implements A-Mem (arXiv:2502.12110) Zettelkasten-style knowledge graph. '
    'Links are created automatically on memory storage when cosine similarity > 0.7. '
    'Bidirectionality: if A→B exists then B→A also exists with the same strength.';

COMMENT ON COLUMN note_links.link_strength IS
    'Cosine similarity between the two memories at time of linking (0.0–1.0). '
    'Higher = stronger associative connection.';
