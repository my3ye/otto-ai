-- Migration 025: Cross-brain structured graph nodes (G2CP implementation)
-- Replaces lossy text cross-brain notes with typed, structured graph nodes.
-- Both Claude and Gemini brains read/write to this table for zero-drift communication.
-- Based on: G2CP paper (arXiv 2602.13370)

CREATE TABLE IF NOT EXISTS cross_brain_graph (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    node_type VARCHAR(50) NOT NULL,          -- directive, decision, task_state, context
    name VARCHAR(255) NOT NULL,               -- short label/identifier
    content JSONB NOT NULL,                   -- typed structured fields
    source_brain VARCHAR(50) DEFAULT 'gemini', -- which brain wrote this node
    priority INTEGER DEFAULT 5,               -- 1-10, higher = more important
    active BOOLEAN DEFAULT TRUE,              -- soft delete / supersede
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS cross_brain_graph_type_active_idx
    ON cross_brain_graph (node_type, active);

CREATE INDEX IF NOT EXISTS cross_brain_graph_created_idx
    ON cross_brain_graph (created_at DESC);

CREATE INDEX IF NOT EXISTS cross_brain_graph_priority_idx
    ON cross_brain_graph (priority DESC, created_at DESC)
    WHERE active = TRUE;
