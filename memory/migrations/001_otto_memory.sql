-- Otto Memory Schema Migration
-- Run against the existing 'memory' database

BEGIN;

-- ── Sessions (episodic session tracking) ──────────────────────────
CREATE TABLE IF NOT EXISTS sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_type TEXT NOT NULL DEFAULT 'claude_code',  -- claude_code, whatsapp, api
    started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    ended_at TIMESTAMPTZ,
    summary TEXT,
    key_decisions JSONB DEFAULT '[]'::jsonb,
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX idx_sessions_started ON sessions (started_at DESC);
CREATE INDEX idx_sessions_type ON sessions (session_type);

-- ── Episodic Events ───────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS episodic_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID REFERENCES sessions(id) ON DELETE SET NULL,
    content TEXT NOT NULL,
    event_type TEXT NOT NULL DEFAULT 'observation',  -- observation, decision, action, learning, error
    importance INTEGER NOT NULL DEFAULT 5 CHECK (importance BETWEEN 1 AND 10),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX idx_episodic_session ON episodic_events (session_id);
CREATE INDEX idx_episodic_created ON episodic_events (created_at DESC);
CREATE INDEX idx_episodic_importance ON episodic_events (importance DESC);
CREATE INDEX idx_episodic_type ON episodic_events (event_type);

-- ── Semantic Memories ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS semantic_memories (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    content TEXT NOT NULL,
    category TEXT NOT NULL DEFAULT 'general',  -- identity, infrastructure, person, project, skill, belief, general
    confidence REAL NOT NULL DEFAULT 0.8 CHECK (confidence BETWEEN 0.0 AND 1.0),
    source TEXT,  -- where this fact came from
    embedding vector(1536),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX idx_semantic_category ON semantic_memories (category);
CREATE INDEX idx_semantic_confidence ON semantic_memories (confidence DESC);
CREATE INDEX idx_semantic_embedding ON semantic_memories USING ivfflat (embedding vector_cosine_ops) WITH (lists = 10);

-- ── Procedures (skills with outcome tracking) ─────────────────────
CREATE TABLE IF NOT EXISTS procedures (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL UNIQUE,
    description TEXT,
    steps JSONB NOT NULL DEFAULT '[]'::jsonb,
    success_count INTEGER NOT NULL DEFAULT 0,
    failure_count INTEGER NOT NULL DEFAULT 0,
    last_used TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX idx_procedures_name ON procedures (name);

-- ── Migrate system_facts into semantic_memories ───────────────────
INSERT INTO semantic_memories (content, category, confidence, source)
SELECT
    key || ': ' || value::text,
    CASE
        WHEN key LIKE 'identity.%' THEN 'identity'
        WHEN key LIKE 'infra.%' THEN 'infrastructure'
        WHEN key LIKE 'comms.%' THEN 'infrastructure'
        ELSE 'general'
    END,
    1.0,
    'migrated from system_facts'
FROM system_facts;

COMMIT;
