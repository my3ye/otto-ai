-- AgentOS Migration: Kernel infrastructure tables
-- Reference: arXiv 2602.20934v1 (AgentOS paper)
-- All tables are independent and can be created in any order.

-- 1. Interrupt Queue (replaces cross-brain notes for communication)
CREATE TABLE IF NOT EXISTS interrupt_queue (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    interrupt_type VARCHAR(50) NOT NULL,
    priority INTEGER NOT NULL DEFAULT 5,    -- 0=critical .. 10=background
    source VARCHAR(50) NOT NULL,            -- whatsapp, web, scheduler, task_engine, system
    payload JSONB NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    correlation_id UUID,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    result JSONB,
    error TEXT,
    metadata JSONB DEFAULT '{}'
);
-- Hot path: dequeue next pending interrupt by priority
CREATE INDEX IF NOT EXISTS idx_iq_pending ON interrupt_queue (priority, created_at)
    WHERE status = 'pending';
CREATE INDEX IF NOT EXISTS idx_iq_correlation ON interrupt_queue (correlation_id)
    WHERE correlation_id IS NOT NULL;

-- 2. Semantic Slices (CID-segmented memory groups)
CREATE TABLE IF NOT EXISTS semantic_slices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    label VARCHAR(255) NOT NULL,
    memory_ids UUID[] NOT NULL,
    centroid vector(1536),                  -- mean embedding of member memories
    cid_boundary_score FLOAT,
    token_count INTEGER NOT NULL DEFAULT 0,
    category VARCHAR(100),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_slices_category ON semantic_slices (category);
-- For S-MMU similarity search on slice centroids
CREATE INDEX IF NOT EXISTS idx_slices_centroid ON semantic_slices
    USING ivfflat (centroid vector_cosine_ops) WITH (lists = 20);

-- 3. Semantic Page Table (tracks L1/L2/L3 residency)
CREATE TABLE IF NOT EXISTS semantic_page_table (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slice_id UUID NOT NULL UNIQUE REFERENCES semantic_slices(id) ON DELETE CASCADE,
    level VARCHAR(2) NOT NULL DEFAULT 'L2', -- L1, L2, L3
    importance_score FLOAT NOT NULL DEFAULT 0.5,
    last_accessed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    access_count INTEGER NOT NULL DEFAULT 0,
    loaded_at TIMESTAMPTZ,
    evicted_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_spt_l1 ON semantic_page_table (importance_score DESC)
    WHERE level = 'L1';

-- 4. Cognitive Snapshots (for sync pulse save/restore)
CREATE TABLE IF NOT EXISTS cognitive_snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    l1_slice_ids UUID[] NOT NULL,
    drift_value FLOAT NOT NULL DEFAULT 0.0,
    trigger VARCHAR(50) NOT NULL,
    snapshot_data JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_snapshots_created ON cognitive_snapshots (created_at DESC);

-- 5. Drift Log
CREATE TABLE IF NOT EXISTS kernel_drift_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    delta_psi FLOAT NOT NULL,
    l1_slice_count INTEGER,
    triggered_sync BOOLEAN DEFAULT FALSE,
    measured_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_drift_measured ON kernel_drift_log (measured_at DESC);

-- 6. LLM Provider Registry
CREATE TABLE IF NOT EXISTS llm_providers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL UNIQUE,
    provider_type VARCHAR(50) NOT NULL,     -- openai_compatible, claude_cli
    base_url VARCHAR(500),
    model_name VARCHAR(200) NOT NULL,
    api_key_env VARCHAR(100),
    priority INTEGER NOT NULL DEFAULT 5,    -- lower = preferred
    max_tokens INTEGER DEFAULT 4096,
    temperature FLOAT DEFAULT 0.0,
    enabled BOOLEAN DEFAULT TRUE,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
INSERT INTO llm_providers (name, provider_type, base_url, model_name, api_key_env, priority)
VALUES
    ('kimi', 'openai_compatible', NULL, 'kimi-for-coding', 'KIMI_API_KEY', 1),
    ('claude_haiku', 'claude_cli', NULL, 'haiku', NULL, 5),
    ('claude_sonnet', 'claude_cli', NULL, 'sonnet', NULL, 10)
ON CONFLICT (name) DO NOTHING;

-- 7. Soft-deprecate dual-brain fields (preserve data, stop using)
ALTER TABLE pending_questions ALTER COLUMN direction SET DEFAULT 'inbound';
ALTER TABLE pending_questions ALTER COLUMN source_brain SET DEFAULT 'kernel';
-- Mark cross_brain_graph as deprecated
ALTER TABLE cross_brain_graph ADD COLUMN IF NOT EXISTS deprecated_at TIMESTAMPTZ;
UPDATE cross_brain_graph SET deprecated_at = NOW() WHERE deprecated_at IS NULL;
