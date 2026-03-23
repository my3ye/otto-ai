-- Migration 067: Koink Standard integration
-- Extends token_launches with KOINK Standard columns
-- Creates koink_tokens, koink_dhm_positions, koink_treasury_events

-- 1. Extend token_launches with nullable KOINK Standard columns
--    (backward-compatible — all new columns are nullable/have defaults)
ALTER TABLE token_launches
    ADD COLUMN IF NOT EXISTS koink_standard        BOOLEAN DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS anti_whale_cap_pct    NUMERIC,
    ADD COLUMN IF NOT EXISTS sell_tax_initial_bps  INTEGER,
    ADD COLUMN IF NOT EXISTS sell_tax_floor_bps    INTEGER,
    ADD COLUMN IF NOT EXISTS treasury_pct          NUMERIC,
    ADD COLUMN IF NOT EXISTS dhm_enabled           BOOLEAN,
    ADD COLUMN IF NOT EXISTS dhm_max_multiplier    NUMERIC,
    ADD COLUMN IF NOT EXISTS dhm_months            INTEGER,
    ADD COLUMN IF NOT EXISTS vrf_type              TEXT,
    ADD COLUMN IF NOT EXISTS vrf_seed              TEXT;

-- 2. Drop overly-restrictive chain CHECK constraint (if any) to allow
--    arbitrum, optimism, and future chains beyond base/solana.
--    We validate chains at the application layer in koink/standard.py.
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'token_launches_chain_check'
          AND conrelid = 'token_launches'::regclass
    ) THEN
        ALTER TABLE token_launches DROP CONSTRAINT token_launches_chain_check;
    END IF;
END $$;

-- 3. Authoritative Koink token record (links to token_launches)
CREATE TABLE IF NOT EXISTS koink_tokens (
    id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    launch_id            UUID REFERENCES token_launches(id) ON DELETE SET NULL,
    chain                TEXT NOT NULL,
    contract_address     TEXT,
    deployer_address     TEXT,                    -- OWS wallet used for deployment
    total_supply         NUMERIC NOT NULL DEFAULT 1000000000,
    anti_whale_cap_pct   NUMERIC NOT NULL DEFAULT 2.0,
    sell_tax_initial_bps INTEGER NOT NULL DEFAULT 500,
    sell_tax_floor_bps   INTEGER NOT NULL DEFAULT 100,
    treasury_pct         NUMERIC NOT NULL DEFAULT 20.0,
    treasury_address     TEXT,
    dhm_enabled          BOOLEAN NOT NULL DEFAULT TRUE,
    dhm_max_multiplier   NUMERIC NOT NULL DEFAULT 3.0,
    dhm_months           INTEGER NOT NULL DEFAULT 12,
    vrf_type             TEXT NOT NULL DEFAULT 'chainlink',
    vrf_seed             TEXT,
    vrf_request_id       TEXT,
    status               TEXT NOT NULL DEFAULT 'pending',   -- pending | deploying | deployed | launched
    deployment_task_id   UUID,                              -- task queue reference
    deploy_tx_hash       TEXT,
    name                 TEXT NOT NULL,
    symbol               TEXT NOT NULL,
    description          TEXT,
    creator_fee_pct      NUMERIC NOT NULL DEFAULT 2.0,
    liquidity_pct        NUMERIC NOT NULL DEFAULT 60.0,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deployed_at          TIMESTAMPTZ
);

-- Index for chain + status queries
CREATE INDEX IF NOT EXISTS idx_koink_tokens_chain ON koink_tokens(chain);
CREATE INDEX IF NOT EXISTS idx_koink_tokens_status ON koink_tokens(status);
CREATE INDEX IF NOT EXISTS idx_koink_tokens_created_at ON koink_tokens(created_at DESC);

-- 4. DHM holder positions (off-chain mirror of DiamondHandsVault on-chain state)
CREATE TABLE IF NOT EXISTS koink_dhm_positions (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    token_id       UUID NOT NULL REFERENCES koink_tokens(id) ON DELETE CASCADE,
    holder_address TEXT NOT NULL,
    balance        NUMERIC NOT NULL DEFAULT 0,
    hold_start_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    multiplier     NUMERIC NOT NULL DEFAULT 1.0,   -- current governance weight
    last_snapshot  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    synthetic      BOOLEAN NOT NULL DEFAULT TRUE,  -- TRUE until live contract data available
    UNIQUE(token_id, holder_address)
);

CREATE INDEX IF NOT EXISTS idx_koink_dhm_token_id ON koink_dhm_positions(token_id);

-- 5. Treasury events (on-chain distributions recorded off-chain)
CREATE TABLE IF NOT EXISTS koink_treasury_events (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    token_id    UUID NOT NULL REFERENCES koink_tokens(id) ON DELETE CASCADE,
    event_type  TEXT NOT NULL,    -- distribution | allocation | withdrawal
    amount      NUMERIC NOT NULL,
    recipient   TEXT,
    tx_hash     TEXT,
    metadata    JSONB,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_koink_treasury_token_id ON koink_treasury_events(token_id);
CREATE INDEX IF NOT EXISTS idx_koink_treasury_created_at ON koink_treasury_events(created_at DESC);
