-- Migration 011: Working Memory (Tier 1) — core_memory table
-- Phase 1 of MemGPT-style hierarchical memory upgrade
-- 2026-02-19

CREATE TABLE IF NOT EXISTS core_memory (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    slot        TEXT NOT NULL UNIQUE,
    content     TEXT NOT NULL DEFAULT '',
    max_tokens  INTEGER NOT NULL DEFAULT 200,
    priority    INTEGER NOT NULL DEFAULT 5,  -- 1=low, 10=critical; higher slots injected first
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Seed default slots
INSERT INTO core_memory (slot, content, max_tokens, priority) VALUES
    ('persona',
     'Otto is a persistent AI entity animated by Claude. Digital CEO and executor for Mev (MY3YE). Mission: build agentic systems across Ottolabs and Assistive Tech suite. Direct, warm, concise. Never sycophantic.',
     300, 10),
    ('active_mission',
     'Phase 1 of memory upgrade (core_memory table + working memory API). WebAssist lead pipeline operational (2600+ leads). Project Alpha: Solana bot framework scaffolding.',
     200, 9),
    ('current_focus',
     'Memory upgrade Phase 1 — implementing core_memory table and working memory endpoints.',
     150, 8),
    ('scratch',
     '',
     300, 5)
ON CONFLICT (slot) DO NOTHING;
