-- Migration 020: Copy Trading Data Storage
-- Stores normalized swap/trade events from tracked smart money wallets
-- for Project Alpha copy trading strategy.
-- Created: 2026-02-21

-- Wallet registry: canonical list of smart money wallets being tracked
CREATE TABLE IF NOT EXISTS alpha_wallets (
    id              SERIAL PRIMARY KEY,
    address         TEXT UNIQUE NOT NULL,
    label           TEXT NOT NULL,               -- e.g. "SM_1"
    strategy        TEXT,                        -- e.g. "mev_routing", "active_trader"
    notes           TEXT,
    win_rate        FLOAT DEFAULT 0,             -- 0-1, updated by analysis job
    total_pnl_usd   FLOAT DEFAULT 0,             -- cumulative PnL tracked
    trade_count     INT DEFAULT 0,
    last_scanned_at TIMESTAMPTZ,
    added_at        TIMESTAMPTZ DEFAULT NOW(),
    active          BOOLEAN DEFAULT TRUE
);

-- Trade events: one row per normalized swap event
CREATE TABLE IF NOT EXISTS alpha_trades (
    id              BIGSERIAL PRIMARY KEY,
    wallet_address  TEXT NOT NULL REFERENCES alpha_wallets(address) ON DELETE CASCADE,
    wallet_label    TEXT NOT NULL,
    signature       TEXT UNIQUE NOT NULL,        -- Solana transaction signature
    slot            BIGINT,
    block_time      TIMESTAMPTZ NOT NULL,
    source_dex      TEXT,                        -- JUPITER, RAYDIUM, ORCA, etc.
    direction       TEXT NOT NULL CHECK (direction IN ('BUY', 'SELL', 'UNKNOWN')),
    input_mint      TEXT NOT NULL,               -- token being sold/spent
    input_symbol    TEXT,                        -- resolved symbol (cached)
    input_amount    FLOAT NOT NULL,
    output_mint     TEXT NOT NULL,               -- token being bought/received
    output_symbol   TEXT,                        -- resolved symbol (cached)
    output_amount   FLOAT NOT NULL,
    fee_sol         FLOAT DEFAULT 0,
    raw_tx          JSONB,                       -- full Helius transaction (for replay)
    ingested_at     TIMESTAMPTZ DEFAULT NOW()
);

-- Token price cache: to avoid redundant price lookups
CREATE TABLE IF NOT EXISTS alpha_token_prices (
    mint            TEXT NOT NULL,
    price_usd       FLOAT NOT NULL,
    fetched_at      TIMESTAMPTZ DEFAULT NOW(),
    source          TEXT DEFAULT 'helius',
    PRIMARY KEY (mint, fetched_at)
);

-- Wallet PnL snapshots: periodic aggregations for dashboard
CREATE TABLE IF NOT EXISTS alpha_wallet_pnl (
    id              SERIAL PRIMARY KEY,
    wallet_address  TEXT NOT NULL,
    wallet_label    TEXT NOT NULL,
    snapshot_at     TIMESTAMPTZ DEFAULT NOW(),
    period          TEXT NOT NULL,               -- '24h', '7d', '30d', 'all'
    trade_count     INT DEFAULT 0,
    buy_count       INT DEFAULT 0,
    sell_count       INT DEFAULT 0,
    win_count       INT DEFAULT 0,
    loss_count      INT DEFAULT 0,
    total_volume_usd FLOAT DEFAULT 0,
    realized_pnl_usd FLOAT DEFAULT 0,
    win_rate        FLOAT DEFAULT 0
);

-- Copy signals: convergence events that warrant following
CREATE TABLE IF NOT EXISTS alpha_copy_signals (
    id              BIGSERIAL PRIMARY KEY,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    signal_type     TEXT NOT NULL,               -- 'convergence', 'whale_buy', 'early_entry'
    token_mint      TEXT NOT NULL,
    token_symbol    TEXT,
    wallet_count    INT DEFAULT 1,               -- how many smart wallets triggered
    wallets         JSONB,                       -- array of {label, address, amount}
    avg_entry_price FLOAT,
    total_volume_usd FLOAT,
    status          TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'followed', 'ignored', 'expired')),
    notes           TEXT
);

-- Indexes for query performance
CREATE INDEX IF NOT EXISTS idx_alpha_trades_wallet ON alpha_trades(wallet_address);
CREATE INDEX IF NOT EXISTS idx_alpha_trades_block_time ON alpha_trades(block_time DESC);
CREATE INDEX IF NOT EXISTS idx_alpha_trades_output_mint ON alpha_trades(output_mint);
CREATE INDEX IF NOT EXISTS idx_alpha_trades_direction ON alpha_trades(direction);
CREATE INDEX IF NOT EXISTS idx_alpha_copy_signals_token ON alpha_copy_signals(token_mint);
CREATE INDEX IF NOT EXISTS idx_alpha_copy_signals_created ON alpha_copy_signals(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_alpha_token_prices_mint ON alpha_token_prices(mint, fetched_at DESC);
