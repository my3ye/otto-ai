-- Otto AI — Database Schema
-- Initializes the 5 core tables for the Memory API.
-- This runs automatically when postgres starts via docker-entrypoint-initdb.d/

-- Required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- ── Sessions ─────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS sessions (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_id    TEXT NOT NULL DEFAULT 'default',
    context     JSONB,
    started_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ended_at    TIMESTAMPTZ,
    summary     TEXT
);

CREATE INDEX IF NOT EXISTS idx_sessions_agent_id ON sessions(agent_id);
CREATE INDEX IF NOT EXISTS idx_sessions_started_at ON sessions(started_at DESC);

-- ── Semantic Memory ───────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS semantic_memories (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    content     TEXT NOT NULL,
    category    TEXT NOT NULL DEFAULT 'general',
    confidence  FLOAT NOT NULL DEFAULT 0.8,
    source      TEXT,
    embedding   VECTOR(1536),            -- OpenAI text-embedding-3-small
    metadata    JSONB,
    archived    BOOLEAN NOT NULL DEFAULT FALSE,
    deleted_at  TIMESTAMPTZ,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_semantic_embedding
    ON semantic_memories USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

CREATE INDEX IF NOT EXISTS idx_semantic_category ON semantic_memories(category);
CREATE INDEX IF NOT EXISTS idx_semantic_archived ON semantic_memories(archived, deleted_at);

-- ── Episodic Events ───────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS episodic_events (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id          UUID REFERENCES sessions(id) ON DELETE SET NULL,
    content             TEXT NOT NULL,
    event_type          TEXT NOT NULL DEFAULT 'general',
    importance          FLOAT NOT NULL DEFAULT 0.5,
    metadata            JSONB DEFAULT '{}',
    consolidation_id    UUID,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_episodic_session ON episodic_events(session_id);
CREATE INDEX IF NOT EXISTS idx_episodic_created ON episodic_events(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_episodic_event_type ON episodic_events(event_type);
CREATE INDEX IF NOT EXISTS idx_episodic_importance ON episodic_events(importance DESC);

-- ── Procedural Memory ─────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS procedural_memories (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name            TEXT NOT NULL UNIQUE,
    description     TEXT NOT NULL,
    steps           JSONB NOT NULL,
    category        TEXT NOT NULL DEFAULT 'general',
    trust_score     FLOAT NOT NULL DEFAULT 0.5,
    use_count       INTEGER NOT NULL DEFAULT 0,
    success_count   INTEGER NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_procedural_category ON procedural_memories(category);
CREATE INDEX IF NOT EXISTS idx_procedural_trust ON procedural_memories(trust_score DESC);

-- ── Tasks ─────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS tasks (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title               TEXT NOT NULL,
    prompt              TEXT NOT NULL,
    priority            INTEGER NOT NULL DEFAULT 5,
    status              TEXT NOT NULL DEFAULT 'pending',   -- pending, running, completed, failed
    budget_usd          FLOAT NOT NULL DEFAULT 1.0,
    timeout_seconds     INTEGER NOT NULL DEFAULT 300,
    agent_type          TEXT NOT NULL DEFAULT 'general-purpose',
    model               TEXT NOT NULL DEFAULT 'sonnet',
    created_by          TEXT NOT NULL DEFAULT 'user',
    output              TEXT,
    exit_code           INTEGER,
    metadata            JSONB,
    pid                 INTEGER,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    started_at          TIMESTAMPTZ,
    completed_at        TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_priority ON tasks(priority DESC);
CREATE INDEX IF NOT EXISTS idx_tasks_created ON tasks(created_at DESC);
