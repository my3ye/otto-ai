-- Migration 080: ONEON Invisible Web3 Infrastructure Layer
-- Phase 1A: session keys, actions log, credentials, auth tokens + identity extensions
-- Architecture: ~/otto/docs/oneon-invisible-web3-layer-architecture-2026-03-28.md

-- 1. Session keys for invisible signing (Tier 1 custodial)
CREATE TABLE IF NOT EXISTS oneon_session_keys (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    identity_id           UUID NOT NULL REFERENCES oneon_identities(id) ON DELETE CASCADE,
    public_key            TEXT NOT NULL,
    encrypted_private_key TEXT NOT NULL,  -- AES-256-GCM encrypted with ONEON_VAULT_MASTER_KEY
    permissions           TEXT[] NOT NULL DEFAULT '{}',  -- VOTE, POST, MESSAGE, CLAIM_CREDENTIAL
    expires_at            TIMESTAMPTZ NOT NULL,
    revoked_at            TIMESTAMPTZ,
    created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_oneon_session_keys_identity ON oneon_session_keys(identity_id);
CREATE INDEX IF NOT EXISTS idx_oneon_session_keys_pubkey   ON oneon_session_keys(public_key);

-- 2. Actions log (invisible signed operations)
CREATE TABLE IF NOT EXISTS oneon_actions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    identity_id     UUID NOT NULL REFERENCES oneon_identities(id) ON DELETE CASCADE,
    action_type     TEXT NOT NULL,  -- vote, post, message, credential_claim
    payload         JSONB NOT NULL DEFAULT '{}',
    tx_hash         TEXT,           -- NULL until submitted to chain
    status          TEXT NOT NULL DEFAULT 'pending',  -- pending, submitted, confirmed, failed
    gas_sponsored   BOOLEAN NOT NULL DEFAULT TRUE,
    error_message   TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    confirmed_at    TIMESTAMPTZ,
    CONSTRAINT oneon_actions_status_check
        CHECK (status IN ('pending', 'submitted', 'confirmed', 'failed'))
);
CREATE INDEX IF NOT EXISTS idx_oneon_actions_identity ON oneon_actions(identity_id);
CREATE INDEX IF NOT EXISTS idx_oneon_actions_status   ON oneon_actions(status);

-- 3. Credentials (W3C VCs surfaced as achievements)
CREATE TABLE IF NOT EXISTS oneon_credentials (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    subject_id        UUID NOT NULL REFERENCES oneon_identities(id) ON DELETE CASCADE,
    issuer_id         UUID REFERENCES oneon_identities(id) ON DELETE SET NULL,
    credential_type   TEXT NOT NULL,   -- community_builder, first_vote, mentor, etc.
    claims            JSONB NOT NULL DEFAULT '{}',
    vc_jwt            TEXT,            -- full W3C VC JWT (off-chain)
    credential_hash   TEXT,            -- on-chain anchor hash (Phase 1B)
    badge_name        TEXT NOT NULL,   -- user-friendly name
    badge_description TEXT,
    badge_image_url   TEXT,
    issued_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    revoked_at        TIMESTAMPTZ,
    anchored_at       TIMESTAMPTZ      -- when hash was written to chain (Phase 1B)
);
CREATE INDEX IF NOT EXISTS idx_oneon_credentials_subject ON oneon_credentials(subject_id);
CREATE INDEX IF NOT EXISTS idx_oneon_credentials_type    ON oneon_credentials(credential_type);

-- 4. Magic link tokens (auth)
CREATE TABLE IF NOT EXISTS oneon_auth_tokens (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    identity_id   UUID NOT NULL REFERENCES oneon_identities(id) ON DELETE CASCADE,
    token_hash    TEXT NOT NULL UNIQUE,  -- SHA-256 of token (never store raw)
    token_type    TEXT NOT NULL DEFAULT 'magic_link',  -- magic_link, passkey_challenge
    expires_at    TIMESTAMPTZ NOT NULL,
    used_at       TIMESTAMPTZ,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT oneon_auth_tokens_type_check
        CHECK (token_type IN ('magic_link', 'passkey_challenge', 'session'))
);
CREATE INDEX IF NOT EXISTS idx_oneon_auth_tokens_hash     ON oneon_auth_tokens(token_hash);
CREATE INDEX IF NOT EXISTS idx_oneon_auth_tokens_identity ON oneon_auth_tokens(identity_id);

-- 5. Extend oneon_identities with smart account + auth fields
ALTER TABLE oneon_identities
    ADD COLUMN IF NOT EXISTS smart_account_address TEXT,
    ADD COLUMN IF NOT EXISTS smart_account_deployed BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS smart_account_salt TEXT,
    ADD COLUMN IF NOT EXISTS passkey_credential_id TEXT,
    ADD COLUMN IF NOT EXISTS email_hash TEXT,
    ADD COLUMN IF NOT EXISTS email_encrypted TEXT,
    ADD COLUMN IF NOT EXISTS email_verified BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS gas_budget_daily_usd NUMERIC(10,4) NOT NULL DEFAULT 0.10,
    ADD COLUMN IF NOT EXISTS gas_used_today_usd NUMERIC(10,4) NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS gas_day_reset_at TIMESTAMPTZ NOT NULL DEFAULT NOW();

CREATE INDEX IF NOT EXISTS idx_oneon_identities_email_hash
    ON oneon_identities(email_hash) WHERE email_hash IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_oneon_identities_smart_account
    ON oneon_identities(smart_account_address) WHERE smart_account_address IS NOT NULL;
