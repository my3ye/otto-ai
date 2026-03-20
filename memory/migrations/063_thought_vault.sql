-- Migration 063: Thought Vault
-- Dedicated storage for Mev's voice notes and long-form thought dumps.
-- Separate from episodic events — these are raw private inputs with their own
-- synthesis lifecycle.

CREATE TABLE IF NOT EXISTS thought_vault (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source              TEXT NOT NULL DEFAULT 'whatsapp',       -- whatsapp, web, manual
    source_message_id   TEXT UNIQUE,                            -- prevents duplicate inserts on retry
    raw_content         TEXT NOT NULL,                          -- original transcript or text
    cleaned_content     TEXT,                                   -- optional: human/LLM-cleaned version
    importance          INT NOT NULL DEFAULT 5 CHECK (importance BETWEEN 1 AND 10),
    tags                TEXT[] NOT NULL DEFAULT '{}',
    themes              TEXT[] NOT NULL DEFAULT '{}',           -- LLM-extracted during synthesis
    synthesis_id        UUID,                                   -- FK set after synthesis
    processed           BOOLEAN NOT NULL DEFAULT FALSE,         -- has been included in a synthesis run
    deleted_at          TIMESTAMPTZ,
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS thought_synthesis (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title           TEXT NOT NULL,
    summary         TEXT NOT NULL,                              -- LLM-written synthesis
    themes          TEXT[] NOT NULL DEFAULT '{}',
    entry_ids       UUID[] NOT NULL DEFAULT '{}',               -- which thought_vault entries this covers
    entry_count     INT NOT NULL DEFAULT 0,
    model           TEXT NOT NULL DEFAULT 'claude-3-5-sonnet-20241022',
    deleted_at      TIMESTAMPTZ,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- FK: thought_vault.synthesis_id → thought_synthesis.id (deferred, set after synthesis)
ALTER TABLE thought_vault
    ADD CONSTRAINT fk_thought_synthesis
    FOREIGN KEY (synthesis_id) REFERENCES thought_synthesis(id) ON DELETE SET NULL
    DEFERRABLE INITIALLY DEFERRED;

-- GIN indexes for fast tag/theme array filtering
CREATE INDEX IF NOT EXISTS idx_thought_vault_tags
    ON thought_vault USING GIN (tags);
CREATE INDEX IF NOT EXISTS idx_thought_vault_themes
    ON thought_vault USING GIN (themes);

CREATE INDEX IF NOT EXISTS idx_thought_vault_created
    ON thought_vault (created_at DESC)
    WHERE deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_thought_vault_unprocessed
    ON thought_vault (created_at DESC)
    WHERE processed = FALSE AND deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_thought_synthesis_created
    ON thought_synthesis (created_at DESC)
    WHERE deleted_at IS NULL;
