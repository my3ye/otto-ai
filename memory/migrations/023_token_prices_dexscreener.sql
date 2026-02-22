-- Migration 023: Enrich alpha_token_prices with DexScreener fields
-- Adds pair_address, price_sol, volume_24h, liquidity_usd columns
-- and a current_price view for latest price per token.
-- Created: 2026-02-22

-- Add DexScreener-specific columns (safe IF NOT EXISTS pattern via DO block)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'alpha_token_prices' AND column_name = 'pair_address'
    ) THEN
        ALTER TABLE alpha_token_prices ADD COLUMN pair_address TEXT;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'alpha_token_prices' AND column_name = 'price_sol'
    ) THEN
        ALTER TABLE alpha_token_prices ADD COLUMN price_sol NUMERIC(20, 10);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'alpha_token_prices' AND column_name = 'volume_24h'
    ) THEN
        ALTER TABLE alpha_token_prices ADD COLUMN volume_24h NUMERIC(20, 2);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'alpha_token_prices' AND column_name = 'liquidity_usd'
    ) THEN
        ALTER TABLE alpha_token_prices ADD COLUMN liquidity_usd NUMERIC(20, 2);
    END IF;

    -- Update source default to distinguish Jupiter vs DexScreener entries
    -- (existing rows remain as 'helius'; new DexScreener rows set source='dexscreener')
END$$;

-- View: latest price per token (most recent fetch wins)
CREATE OR REPLACE VIEW alpha_token_prices_latest AS
SELECT DISTINCT ON (mint)
    mint,
    pair_address,
    price_usd,
    price_sol,
    volume_24h,
    liquidity_usd,
    fetched_at,
    source
FROM alpha_token_prices
ORDER BY mint, fetched_at DESC;

-- Index for faster "get latest price for token" lookups (already created in 020, but
-- re-declare in case the previous migration was partially applied)
CREATE INDEX IF NOT EXISTS idx_alpha_token_prices_mint_fetched
    ON alpha_token_prices(mint, fetched_at DESC);
