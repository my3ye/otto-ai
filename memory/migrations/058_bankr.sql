-- Migration 058: BANKR Bot integration tables
-- Three tables: bankr_trades, bankr_signals, bankr_jobs

CREATE TABLE IF NOT EXISTS bankr_trades (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id      TEXT,                          -- BANKR async job ID
    thread_id   TEXT,                          -- BANKR conversation thread
    prompt      TEXT NOT NULL,                 -- NL prompt sent to BANKR
    chain       TEXT,                          -- e.g. "base", "solana", "eth"
    token_in    TEXT,
    token_out   TEXT,
    amount_in   NUMERIC,
    amount_out  NUMERIC,
    tx_hash     TEXT,                          -- on-chain TX hash on success
    status      TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'completed', 'failed', 'cancelled')),
    raw_result  JSONB,                         -- full BANKR job response
    error       TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_bankr_trades_status ON bankr_trades(status);
CREATE INDEX IF NOT EXISTS idx_bankr_trades_created ON bankr_trades(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_bankr_trades_chain ON bankr_trades(chain);

-- Auto-update updated_at on any UPDATE
CREATE OR REPLACE FUNCTION update_bankr_updated_at()
RETURNS TRIGGER AS $$
BEGIN NEW.updated_at = NOW(); RETURN NEW; END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_bankr_trades_ts
    BEFORE UPDATE ON bankr_trades
    FOR EACH ROW EXECUTE FUNCTION update_bankr_updated_at();

CREATE TABLE IF NOT EXISTS bankr_signals (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    signal_type     TEXT NOT NULL,             -- "whale_convergence"|"limit_trigger"|"manual"
    token           TEXT NOT NULL,
    chain           TEXT,
    direction       TEXT NOT NULL,             -- "long"|"short"|"neutral"
    confidence      NUMERIC,                   -- 0-1
    entry_price     NUMERIC,
    target_price    NUMERIC,
    stop_price      NUMERIC,
    tx_hash         TEXT,                      -- proof TX on bankrsignals.com
    bankr_signal_id TEXT,                      -- ID returned by bankrsignals.com
    published       BOOLEAN NOT NULL DEFAULT FALSE,
    win             BOOLEAN,                   -- NULL = open, TRUE = win, FALSE = loss
    pnl_pct         NUMERIC,                   -- realized % PnL on close
    metadata        JSONB,                     -- convergence wallets, scores, etc.
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    closed_at       TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_bankr_signals_published ON bankr_signals(published);
CREATE INDEX IF NOT EXISTS idx_bankr_signals_token ON bankr_signals(token);
CREATE INDEX IF NOT EXISTS idx_bankr_signals_created ON bankr_signals(created_at DESC);

CREATE TABLE IF NOT EXISTS bankr_jobs (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id      TEXT NOT NULL UNIQUE,          -- BANKR job ID for polling
    job_type    TEXT NOT NULL
        CHECK (job_type IN ('trade', 'limit', 'dca', 'stop_loss', 'launch', 'portfolio')),
    prompt      TEXT NOT NULL,
    status      TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'completed', 'failed', 'cancelled')),
    result      JSONB,
    error       TEXT,
    poll_count  INTEGER NOT NULL DEFAULT 0,
    trade_id    UUID REFERENCES bankr_trades(id),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_bankr_jobs_job_id ON bankr_jobs(job_id);
CREATE INDEX IF NOT EXISTS idx_bankr_jobs_status ON bankr_jobs(status);

CREATE TRIGGER trg_bankr_jobs_ts
    BEFORE UPDATE ON bankr_jobs
    FOR EACH ROW EXECUTE FUNCTION update_bankr_updated_at();
