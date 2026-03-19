-- Migration 059: Native Crypto Engine tables
-- Replaces Bankr-mediated execution with native Otto stack
-- (bankr_* tables from migration 058 remain untouched — clean break)

-- Executed trades (native, not Bankr-mediated)
CREATE TABLE IF NOT EXISTS crypto_trades (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chain           TEXT NOT NULL,                    -- base | eth | polygon | solana | hyperliquid
    action          TEXT NOT NULL,                    -- swap | buy | sell | bridge | launch
    token_in        TEXT,
    token_out       TEXT,
    amount_in       NUMERIC,
    amount_out      NUMERIC,
    amount_usd      NUMERIC,
    tx_hash         TEXT,                             -- on-chain transaction hash
    status          TEXT NOT NULL DEFAULT 'pending',  -- pending | completed | failed | cancelled
    nl_input        TEXT,                             -- original NL command (if from NL parser)
    trade_intent    JSONB,                            -- parsed TradeIntent struct
    quote_data      JSONB,                            -- 0x quote response
    error           TEXT,
    source          TEXT NOT NULL DEFAULT 'manual',   -- manual | nl_parser | monitor | dca
    monitor_id      UUID,                             -- links to price_monitors if triggered by monitor
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at    TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_crypto_trades_chain ON crypto_trades(chain);
CREATE INDEX IF NOT EXISTS idx_crypto_trades_status ON crypto_trades(status);
CREATE INDEX IF NOT EXISTS idx_crypto_trades_created ON crypto_trades(created_at DESC);

-- Conditional orders: limit, stop-loss, DCA
CREATE TABLE IF NOT EXISTS price_monitors (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    monitor_type    TEXT NOT NULL,                    -- limit_buy | limit_sell | stop_loss | dca | take_profit
    status          TEXT NOT NULL DEFAULT 'active',   -- active | triggered | cancelled | expired
    chain           TEXT NOT NULL,
    token_in        TEXT NOT NULL,
    token_out       TEXT,
    amount_usd      NUMERIC,                          -- USDC amount per trigger (or per DCA interval)
    trigger_price   NUMERIC,                          -- price in USD at which to trigger
    trigger_type    TEXT,                             -- above | below | percent_change
    trigger_pct     NUMERIC,                          -- for percent_change triggers
    -- DCA-specific
    dca_interval_hours INTEGER,                       -- hours between DCA buys
    dca_max_runs    INTEGER,                          -- max executions (NULL = infinite)
    dca_runs_done   INTEGER NOT NULL DEFAULT 0,
    next_run_at     TIMESTAMPTZ,                      -- when to next check/execute
    -- State
    last_price      NUMERIC,                          -- last seen price
    last_checked_at TIMESTAMPTZ,
    nl_description  TEXT,                             -- human-readable description
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    triggered_at    TIMESTAMPTZ,
    expires_at      TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_price_monitors_status ON price_monitors(status);
CREATE INDEX IF NOT EXISTS idx_price_monitors_next_run ON price_monitors(next_run_at) WHERE status = 'active';

-- Native signal board
CREATE TABLE IF NOT EXISTS crypto_signals (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    token           TEXT NOT NULL,
    chain           TEXT NOT NULL,
    direction       TEXT NOT NULL,                    -- long | short | neutral | exit
    confidence      NUMERIC,                          -- 0.0-1.0
    rationale       TEXT,
    entry_price     NUMERIC,
    target_price    NUMERIC,
    stop_price      NUMERIC,
    tx_hash         TEXT,                             -- on-chain proof (from executed trade)
    trade_id        UUID REFERENCES crypto_trades(id),
    status          TEXT NOT NULL DEFAULT 'open',     -- open | closed | cancelled
    win             BOOLEAN,                          -- NULL = open, TRUE = win, FALSE = loss
    exit_price      NUMERIC,
    pnl_pct         NUMERIC,
    metadata        JSONB,                            -- extra data (whale wallets, indicators)
    published_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    closed_at       TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_crypto_signals_status ON crypto_signals(status);
CREATE INDEX IF NOT EXISTS idx_crypto_signals_token ON crypto_signals(token);
CREATE INDEX IF NOT EXISTS idx_crypto_signals_published ON crypto_signals(published_at DESC);

-- Token launches
CREATE TABLE IF NOT EXISTS token_launches (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            TEXT NOT NULL,
    symbol          TEXT NOT NULL,
    chain           TEXT NOT NULL,                    -- base | solana
    contract_address TEXT,                            -- set after launch
    launch_mechanism TEXT NOT NULL,                   -- doppler | raydium_launchlab | manual
    total_supply    NUMERIC,
    creator_fee_pct NUMERIC,
    description     TEXT,
    status          TEXT NOT NULL DEFAULT 'pending',  -- pending | launched | failed
    tx_hash         TEXT,
    launch_data     JSONB,                            -- full launch response
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    launched_at     TIMESTAMPTZ
);
