-- Migration 061: Secrets Vault
-- Encrypted key-value store for API keys, credentials, and secrets.
-- Values are Fernet-encrypted before storage — DB never holds plaintext.

CREATE TABLE IF NOT EXISTS secrets_vault (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    key_name         TEXT NOT NULL UNIQUE,                      -- e.g. "openai_api_key"
    display_name     TEXT NOT NULL,                             -- e.g. "OpenAI API Key"
    description      TEXT,
    service_group    TEXT NOT NULL DEFAULT 'general',           -- bankr, crypto, email, llm, webassist, general
    allowed_services JSONB NOT NULL DEFAULT '["*"]',            -- ["*"] = all, or ["bankr","crypto"]
    encrypted_value  TEXT NOT NULL,                             -- Fernet-encrypted, base64url
    encryption_version INT NOT NULL DEFAULT 1,
    last_rotated_at  TIMESTAMPTZ DEFAULT NOW(),
    revoked_at       TIMESTAMPTZ,                               -- soft delete
    created_at       TIMESTAMPTZ DEFAULT NOW(),
    updated_at       TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS secrets_audit_log (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    secret_id     UUID REFERENCES secrets_vault(id) ON DELETE SET NULL,
    key_name      TEXT NOT NULL,
    action        TEXT NOT NULL CHECK (action IN ('read','created','updated','rotated','revoked')),
    service       TEXT,          -- which service performed the action
    agent_task_id TEXT,          -- task_id if called from task runner
    created_at    TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_secrets_key_name
    ON secrets_vault(key_name) WHERE revoked_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_secrets_audit_created
    ON secrets_audit_log(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_secrets_audit_secret_id
    ON secrets_audit_log(secret_id);
