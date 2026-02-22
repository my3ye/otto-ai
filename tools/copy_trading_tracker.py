#!/usr/bin/env python3
"""
copy_trading_tracker.py — Project Alpha: Solana Copy Trading Data Ingestion

Fetches, normalizes, and stores swap events from tracked smart money wallets
into PostgreSQL for analysis and copy signal generation.

Usage:
    # Full ingest: all wallets, last 30 minutes
    python3 tools/copy_trading_tracker.py

    # Custom window
    python3 tools/copy_trading_tracker.py --window 3600

    # Specific wallets only
    python3 tools/copy_trading_tracker.py --wallets SM_1,SM_3

    # Show PnL summary
    python3 tools/copy_trading_tracker.py --pnl-summary

    # Sync wallet registry to DB
    python3 tools/copy_trading_tracker.py --sync-wallets

Author: Otto (Project Alpha)
Date: 2026-02-21
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import asyncpg
import httpx
from dotenv import load_dotenv

# ─── Config ──────────────────────────────────────────────────────────────────

_alpha_env = Path(__file__).parent.parent / "projects" / "alpha" / "bot" / ".env"
if _alpha_env.exists():
    load_dotenv(_alpha_env)

HELIUS_API_KEY = os.environ.get("HELIUS_API_KEY", "")
HELIUS_API_BASE = "https://api.helius.xyz/v0"
HELIUS_RPC_URL = (
    f"https://mainnet.helius-rpc.com/?api-key={HELIUS_API_KEY}"
    if HELIUS_API_KEY
    else "https://api.mainnet-beta.solana.com"
)

WALLETS_JSON = Path(__file__).parent.parent / "projects" / "alpha" / "wallets.json"

# DexScreener API (free, no key needed)
DEXSCREENER_API_BASE = "https://api.dexscreener.com/latest/dex"

# Core wallet set (SM_1 and SM_2 dropped as noisy; core trio + SM_8 only positive Sharpe)
CORE_WALLETS = {"SM_5", "SM_8", "SM_18", "SM_19"}
NOISY_WALLETS = {"SM_1", "SM_2"}

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "user": "otto",
    "password": "LldgQBV1hiPejrKn6UlPQvX76pBqMB",
    "database": "memory",
}

# Known stablecoin/base token mints (exclude from "what did they buy" analysis)
STABLECOINS = {
    "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",  # USDC
    "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB",   # USDT
    "So11111111111111111111111111111111111111112",       # Wrapped SOL
    "mSoLzYCxHdYgdzU16g5QSh3i5K3z3KZK7ytfqcJm7So",   # mSOL
    "7dHbWXmci3dT8UFYWYZweBLXgycu7Y3iL6trKn1Y7ARj",   # stSOL
    "J1toso1uCk3RLmjorhTtrVwY9HJ7X8V9yYac6Y7kGCPn",   # jitoSOL
}

KNOWN_SYMBOLS = {
    "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v": "USDC",
    "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB": "USDT",
    "So11111111111111111111111111111111111111112": "SOL",
    "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263": "BONK",
    "JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN": "JUP",
    "mSoLzYCxHdYgdzU16g5QSh3i5K3z3KZK7ytfqcJm7So": "mSOL",
}


# ─── Helius API ───────────────────────────────────────────────────────────────

async def fetch_wallet_swaps(
    address: str,
    limit: int = 50,
    before_sig: str | None = None,
) -> list[dict[str, Any]]:
    """Fetch recent SWAP transactions for a wallet via Helius Enhanced TX API."""
    if not HELIUS_API_KEY:
        print(f"  [WARN] No HELIUS_API_KEY — skipping {address[:12]}...")
        return []

    url = f"{HELIUS_API_BASE}/addresses/{address}/transactions"
    params: dict[str, Any] = {
        "api-key": HELIUS_API_KEY,
        "limit": limit,
        "type": "SWAP",
    }
    if before_sig:
        params["before"] = before_sig

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()
            return data if isinstance(data, list) else []
    except httpx.HTTPStatusError as e:
        print(f"  [ERROR] Helius API {e.response.status_code} for {address[:12]}: {e.response.text[:100]}")
        return []
    except Exception as e:
        print(f"  [ERROR] fetch_wallet_swaps({address[:12]}): {e}")
        return []


async def fetch_token_price_jup(mint: str) -> float | None:
    """Fetch token USD price from Jupiter price API (free, no key needed)."""
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(
                "https://api.jup.ag/price/v2",
                params={"ids": mint},
            )
            if resp.status_code == 200:
                data = resp.json()
                price_data = data.get("data", {}).get(mint, {})
                p = price_data.get("price")
                return float(p) if p else None
    except Exception:
        pass
    return None


async def fetch_token_price_dexscreener(
    token_address: str,
) -> dict[str, Any] | None:
    """
    Fetch token price and market data from DexScreener.

    Returns a dict with keys: price_usd, price_sol, pair_address,
    volume_24h, liquidity_usd, symbol — or None on failure.

    Rate limit: 60 req/min. Caller must enforce delay between calls.
    DexScreener docs: https://docs.dexscreener.com/api/reference
    """
    url = f"{DEXSCREENER_API_BASE}/tokens/{token_address}"
    try:
        async with httpx.AsyncClient(timeout=12.0) as client:
            resp = await client.get(url)
            if resp.status_code != 200:
                return None
            data = resp.json()

        pairs = data.get("pairs") or []
        if not pairs:
            return None

        # Prefer Solana pairs; fall back to first available
        solana_pairs = [p for p in pairs if p.get("chainId") == "solana"]
        best = solana_pairs[0] if solana_pairs else pairs[0]

        price_usd = best.get("priceUsd")
        price_native = best.get("priceNative")  # price in SOL
        pair_address = best.get("pairAddress")
        volume = best.get("volume", {})
        liquidity = best.get("liquidity", {})
        base_token = best.get("baseToken", {})
        symbol = base_token.get("symbol")

        return {
            "price_usd": float(price_usd) if price_usd else None,
            "price_sol": float(price_native) if price_native else None,
            "pair_address": pair_address,
            "volume_24h": float(volume.get("h24", 0) or 0),
            "liquidity_usd": float(liquidity.get("usd", 0) or 0),
            "symbol": symbol,
        }
    except Exception as e:
        print(f"  [WARN] DexScreener price fetch failed for {token_address[:12]}: {e}")
        return None


async def cache_token_price(
    pool: asyncpg.Pool,
    mint: str,
    price_info: dict[str, Any],
    source: str = "dexscreener",
) -> None:
    """Store a price record in alpha_token_prices."""
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO alpha_token_prices
                (mint, price_usd, price_sol, pair_address, volume_24h, liquidity_usd, source, fetched_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, NOW())
            ON CONFLICT DO NOTHING
            """,
            mint,
            price_info.get("price_usd"),
            price_info.get("price_sol"),
            price_info.get("pair_address"),
            price_info.get("volume_24h"),
            price_info.get("liquidity_usd"),
            source,
        )


async def get_cached_price(pool: asyncpg.Pool, mint: str, max_age_seconds: int = 300) -> dict | None:
    """Return the most recent cached price for a token if fresh enough."""
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT price_usd, price_sol, pair_address, volume_24h, liquidity_usd, fetched_at
            FROM alpha_token_prices
            WHERE mint = $1
              AND fetched_at > NOW() - ($2 * INTERVAL '1 second')
            ORDER BY fetched_at DESC
            LIMIT 1
            """,
            mint,
            max_age_seconds,
        )
        return dict(row) if row else None


async def enrich_trades_with_prices(pool: asyncpg.Pool, wallet_filter: set[str] | None = None) -> dict:
    """
    Backfill price data for all BUY trades that lack price information.

    Queries alpha_trades for unique output_mints (tokens bought) that have no
    entry in alpha_token_prices, then fetches current price from DexScreener
    and caches it. Returns summary stats.
    """
    print("\n[Price Enrichment] Fetching missing token prices from DexScreener...")

    # Build wallet filter clause
    wallet_clause = ""
    if wallet_filter:
        labels = ", ".join(f"'{w}'" for w in wallet_filter)
        wallet_clause = f"AND wallet_label IN ({labels})"

    async with pool.acquire() as conn:
        # Find tokens bought by tracked wallets that have no recent price
        rows = await conn.fetch(
            f"""
            SELECT DISTINCT t.output_mint, t.output_symbol
            FROM alpha_trades t
            WHERE t.direction = 'BUY'
              AND t.output_mint NOT IN (SELECT UNNEST($1::text[]))
              {wallet_clause}
              AND NOT EXISTS (
                  SELECT 1 FROM alpha_token_prices p
                  WHERE p.mint = t.output_mint
              )
            ORDER BY t.output_mint
            """,
            list(STABLECOINS),
        )

    tokens_to_fetch = [(r["output_mint"], r["output_symbol"]) for r in rows]
    print(f"[Price Enrichment] {len(tokens_to_fetch)} tokens need price data")

    fetched = 0
    failed = 0

    for i, (mint, symbol) in enumerate(tokens_to_fetch):
        display = symbol or mint[:12]
        price_info = await fetch_token_price_dexscreener(mint)

        if price_info and price_info.get("price_usd"):
            await cache_token_price(pool, mint, price_info)
            # Backfill symbol into trades if we now know it
            if price_info.get("symbol") and not symbol:
                async with pool.acquire() as conn:
                    await conn.execute(
                        "UPDATE alpha_trades SET output_symbol = $1 WHERE output_mint = $2 AND output_symbol IS NULL",
                        price_info["symbol"],
                        mint,
                    )
            fetched += 1
            print(f"  [{i+1}/{len(tokens_to_fetch)}] {display}: ${price_info['price_usd']:.8f} "
                  f"(vol24h=${price_info['volume_24h']:,.0f}, liq=${price_info['liquidity_usd']:,.0f})")
        else:
            failed += 1
            print(f"  [{i+1}/{len(tokens_to_fetch)}] {display}: no price data")

        # DexScreener rate limit: 60 req/min → 1s delay between calls
        if i < len(tokens_to_fetch) - 1:
            await asyncio.sleep(1.1)

    print(f"[Price Enrichment] Done: {fetched} fetched, {failed} failed")
    return {"tokens_fetched": fetched, "tokens_failed": failed}


async def compute_backtest_pnl(pool: asyncpg.Pool, wallet_filter: set[str] | None = None) -> list[dict]:
    """
    Calculate P&L for each wallet by matching BUY trades to current prices.

    For each BUY trade with a known entry price equivalent (SOL spent × SOL/USD)
    and a current token price, compute holding period return.

    Note: This is an approximation — real P&L needs matched entry/exit pairs.
    Here we use current price as exit proxy (paper P&L).
    """
    # Build optional wallet filter
    wallet_clause = ""
    params: list[Any] = []
    if wallet_filter:
        wallet_clause = "AND t.wallet_label = ANY($1)"
        params.append(list(wallet_filter))

    sol_price_info = await fetch_token_price_dexscreener("So11111111111111111111111111111111111111112")
    sol_usd = sol_price_info["price_usd"] if sol_price_info and sol_price_info.get("price_usd") else 150.0
    print(f"[Backtest] SOL/USD reference: ${sol_usd:.2f}")

    query = f"""
        SELECT
            t.wallet_label,
            t.output_mint,
            t.output_symbol,
            t.output_amount,
            t.input_amount  AS sol_spent,
            t.input_mint,
            t.block_time,
            p.price_usd     AS current_price_usd
        FROM alpha_trades t
        LEFT JOIN LATERAL (
            SELECT price_usd
            FROM alpha_token_prices
            WHERE mint = t.output_mint
            ORDER BY fetched_at DESC
            LIMIT 1
        ) p ON TRUE
        WHERE t.direction = 'BUY'
          AND t.output_mint NOT IN (SELECT UNNEST(${'$2' if wallet_filter else '$1'}::text[]))
          AND p.price_usd IS NOT NULL
          {wallet_clause}
        ORDER BY t.wallet_label, t.block_time
    """
    # Rebuild with correct param indices
    stablecoins_list = list(STABLECOINS)
    if wallet_filter:
        async with pool.acquire() as conn:
            rows = await conn.fetch(query, list(wallet_filter), stablecoins_list)
    else:
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT
                    t.wallet_label,
                    t.output_mint,
                    t.output_symbol,
                    t.output_amount,
                    t.input_amount  AS sol_spent,
                    t.input_mint,
                    t.block_time,
                    p.price_usd     AS current_price_usd
                FROM alpha_trades t
                LEFT JOIN LATERAL (
                    SELECT price_usd
                    FROM alpha_token_prices
                    WHERE mint = t.output_mint
                    ORDER BY fetched_at DESC
                    LIMIT 1
                ) p ON TRUE
                WHERE t.direction = 'BUY'
                  AND t.output_mint NOT IN (SELECT UNNEST($1::text[]))
                  AND p.price_usd IS NOT NULL
                ORDER BY t.wallet_label, t.block_time
                """,
                stablecoins_list,
            )

    # Aggregate per wallet
    from collections import defaultdict
    wallet_stats: dict[str, dict] = defaultdict(lambda: {
        "trades": 0, "wins": 0, "losses": 0,
        "total_pnl_usd": 0.0, "total_invested_usd": 0.0,
        "returns": [],
    })

    for row in rows:
        lbl = row["wallet_label"]
        sol_spent = float(row["sol_spent"] or 0)
        tokens_received = float(row["output_amount"] or 0)
        current_price = float(row["current_price_usd"] or 0)

        # Entry cost in USD: SOL spent × SOL/USD
        # (uses SOL as base; trades denominated in other bases are skipped)
        if row["input_mint"] != SOL_MINT or sol_spent <= 0 or current_price <= 0:
            continue

        entry_cost_usd = sol_spent * sol_usd
        current_value_usd = tokens_received * current_price
        pnl_usd = current_value_usd - entry_cost_usd
        pct_return = (pnl_usd / entry_cost_usd) * 100 if entry_cost_usd > 0 else 0

        wallet_stats[lbl]["trades"] += 1
        wallet_stats[lbl]["total_pnl_usd"] += pnl_usd
        wallet_stats[lbl]["total_invested_usd"] += entry_cost_usd
        wallet_stats[lbl]["returns"].append(pct_return)
        if pnl_usd > 0:
            wallet_stats[lbl]["wins"] += 1
        else:
            wallet_stats[lbl]["losses"] += 1

    results = []
    for lbl, stats in sorted(wallet_stats.items()):
        returns = stats["returns"]
        n = len(returns)
        if n == 0:
            continue
        avg_return = sum(returns) / n
        # Sharpe approximation: mean / std (annualized not applied — raw signal quality)
        import statistics
        std_return = statistics.stdev(returns) if n > 1 else 0.0
        sharpe = avg_return / std_return if std_return > 0 else 0.0
        win_rate = stats["wins"] / stats["trades"] if stats["trades"] > 0 else 0.0

        results.append({
            "wallet_label": lbl,
            "trades_with_price": stats["trades"],
            "win_rate": round(win_rate, 3),
            "avg_return_pct": round(avg_return, 2),
            "total_pnl_usd": round(stats["total_pnl_usd"], 2),
            "total_invested_usd": round(stats["total_invested_usd"], 2),
            "sharpe_approx": round(sharpe, 3),
        })

    # Sort by Sharpe descending
    results.sort(key=lambda x: x["sharpe_approx"], reverse=True)
    return results


# ─── Normalization ────────────────────────────────────────────────────────────

SOL_MINT = "So11111111111111111111111111111111111111112"


def classify_direction(input_mint: str, output_mint: str) -> str:
    """
    Determine trade direction from the perspective of the tracked wallet.
    BUY  = acquiring a non-stable token (e.g. SOL/USDC → TOKEN)
    SELL = disposing of a non-stable token (e.g. TOKEN → SOL/USDC)
    """
    input_is_base = input_mint in STABLECOINS
    output_is_base = output_mint in STABLECOINS

    if input_is_base and not output_is_base:
        return "BUY"
    elif not input_is_base and output_is_base:
        return "SELL"
    else:
        return "UNKNOWN"


def normalize_swap(tx: dict[str, Any], wallet_address: str, wallet_label: str) -> dict[str, Any] | None:
    """
    Convert a Helius enhanced transaction into a normalized trade record.
    Returns None if the swap can't be parsed.
    """
    try:
        events = tx.get("events", {})
        swap = events.get("swap")
        if not swap:
            return None

        token_inputs = swap.get("tokenInputs", [])
        token_outputs = swap.get("tokenOutputs", [])
        native_input = swap.get("nativeInput")
        native_output = swap.get("nativeOutput")

        # ─── Input (what wallet spent) ────────────────────────────────────
        if native_input:
            input_mint = SOL_MINT
            raw_in = native_input.get("amount", "0")
            input_amount = int(raw_in) / 1e9
        elif token_inputs:
            ti = token_inputs[0]
            input_mint = ti.get("mint", "unknown")
            raw_amount = ti.get("rawTokenAmount", {})
            decimals = int(raw_amount.get("decimals", 6))
            input_amount = int(raw_amount.get("tokenAmount", "0")) / (10 ** decimals)
        else:
            input_mint = "unknown"
            input_amount = 0.0

        # ─── Output (what wallet received) ────────────────────────────────
        if native_output:
            output_mint = SOL_MINT
            raw_out = native_output.get("amount", "0")
            output_amount = int(raw_out) / 1e9
        elif token_outputs:
            to = token_outputs[0]
            output_mint = to.get("mint", "unknown")
            raw_amount = to.get("rawTokenAmount", {})
            decimals = int(raw_amount.get("decimals", 6))
            output_amount = int(raw_amount.get("tokenAmount", "0")) / (10 ** decimals)
        else:
            output_mint = "unknown"
            output_amount = 0.0

        direction = classify_direction(input_mint, output_mint)
        ts = tx.get("timestamp", 0)

        return {
            "wallet_address": wallet_address,
            "wallet_label": wallet_label,
            "signature": tx.get("signature", ""),
            "slot": tx.get("slot"),
            "block_time": datetime.fromtimestamp(ts, tz=timezone.utc) if ts else None,
            "source_dex": tx.get("source", "UNKNOWN"),
            "direction": direction,
            "input_mint": input_mint,
            "input_symbol": KNOWN_SYMBOLS.get(input_mint),
            "input_amount": input_amount,
            "output_mint": output_mint,
            "output_symbol": KNOWN_SYMBOLS.get(output_mint),
            "output_amount": output_amount,
            "fee_sol": tx.get("fee", 0) / 1e9,
            "raw_tx": json.dumps({
                "description": tx.get("description", ""),
                "type": tx.get("type", ""),
                "source": tx.get("source", ""),
                "slot": tx.get("slot"),
            }),
        }
    except Exception as e:
        print(f"  [WARN] normalize_swap error: {e}")
        return None


# ─── Database Operations ──────────────────────────────────────────────────────

async def get_db_pool() -> asyncpg.Pool:
    return await asyncpg.create_pool(**DB_CONFIG, min_size=1, max_size=5)


async def sync_wallets_to_db(pool: asyncpg.Pool) -> int:
    """Upsert wallet registry from wallets.json into alpha_wallets table."""
    with open(WALLETS_JSON) as f:
        data = json.load(f)

    wallets = data.get("wallets", [])
    upserted = 0

    async with pool.acquire() as conn:
        for w in wallets:
            await conn.execute(
                """
                INSERT INTO alpha_wallets (address, label, strategy, notes, active)
                VALUES ($1, $2, $3, $4, TRUE)
                ON CONFLICT (address) DO UPDATE SET
                    label = EXCLUDED.label,
                    strategy = EXCLUDED.strategy,
                    notes = EXCLUDED.notes,
                    active = TRUE
                """,
                w["address"],
                w.get("label", ""),
                w.get("strategy"),
                w.get("notes"),
            )
            upserted += 1

    return upserted


async def store_trades(pool: asyncpg.Pool, trades: list[dict[str, Any]]) -> int:
    """Batch insert trades, ignoring duplicates (by signature)."""
    if not trades:
        return 0

    inserted = 0
    async with pool.acquire() as conn:
        for t in trades:
            if not t.get("signature") or not t.get("block_time"):
                continue
            try:
                await conn.execute(
                    """
                    INSERT INTO alpha_trades (
                        wallet_address, wallet_label, signature, slot, block_time,
                        source_dex, direction, input_mint, input_symbol, input_amount,
                        output_mint, output_symbol, output_amount, fee_sol, raw_tx
                    ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15::jsonb)
                    ON CONFLICT (signature) DO NOTHING
                    """,
                    t["wallet_address"], t["wallet_label"], t["signature"],
                    t["slot"], t["block_time"], t["source_dex"], t["direction"],
                    t["input_mint"], t["input_symbol"], t["input_amount"],
                    t["output_mint"], t["output_symbol"], t["output_amount"],
                    t["fee_sol"], t["raw_tx"],
                )
                inserted += 1
            except Exception as e:
                print(f"  [WARN] DB insert error for {t.get('signature','?')[:20]}: {e}")

    return inserted


async def update_wallet_scan_time(pool: asyncpg.Pool, address: str) -> None:
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE alpha_wallets SET last_scanned_at = NOW() WHERE address = $1",
            address,
        )


async def get_latest_signature(pool: asyncpg.Pool, wallet_address: str) -> str | None:
    """Get the most recent stored signature for a wallet (for pagination)."""
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT signature FROM alpha_trades WHERE wallet_address = $1 ORDER BY block_time DESC LIMIT 1",
            wallet_address,
        )
        return row["signature"] if row else None


# ─── PnL Analysis ─────────────────────────────────────────────────────────────

async def compute_pnl_summary(pool: asyncpg.Pool, hours: int = 24) -> list[dict]:
    """
    Compute simple PnL metrics per wallet for the last N hours.
    Uses token flow as proxy (true PnL needs entry/exit price matching).
    """
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT
                wallet_label,
                COUNT(*) FILTER (WHERE direction = 'BUY')  AS buy_count,
                COUNT(*) FILTER (WHERE direction = 'SELL') AS sell_count,
                COUNT(*) AS total_trades,
                COUNT(DISTINCT output_mint) FILTER (WHERE direction = 'BUY') AS unique_tokens_bought,
                SUM(input_amount) FILTER (WHERE direction = 'BUY' AND input_mint IN (
                    'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v',
                    'So11111111111111111111111111111111111111112'
                )) AS total_spent_base,
                MIN(block_time) AS first_trade,
                MAX(block_time) AS last_trade
            FROM alpha_trades
            WHERE block_time > NOW() - ($1 * INTERVAL '1 hour')
            GROUP BY wallet_label
            ORDER BY total_trades DESC
            """,
            hours,
        )
        return [dict(r) for r in rows]


# ─── Main Ingestion Loop ──────────────────────────────────────────────────────

async def run_ingestion(window_seconds: int = 1800, label_filter: list[str] | None = None) -> dict:
    """Main data ingestion: scan all wallets, store swaps to DB."""
    print(f"\n{'='*60}")
    print(f"  Copy Trading Tracker — {datetime.now(tz=timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"  Window: {window_seconds}s | Wallets: {label_filter or 'all'}")
    print(f"{'='*60}\n")

    if not HELIUS_API_KEY:
        print("[FATAL] HELIUS_API_KEY not set — cannot proceed")
        return {"error": "No API key"}

    # Load wallets
    with open(WALLETS_JSON) as f:
        wallet_data = json.load(f)

    wallets = wallet_data.get("wallets", [])
    if label_filter:
        wallets = [w for w in wallets if w.get("label") in label_filter]

    print(f"Tracking {len(wallets)} wallets\n")

    pool = await get_db_pool()

    # Ensure wallets are in DB
    await sync_wallets_to_db(pool)

    now_ts = int(time.time())
    cutoff_ts = now_ts - window_seconds

    total_fetched = 0
    total_stored = 0
    all_trades: list[dict] = []

    for wallet in wallets:
        address = wallet["address"]
        label = wallet.get("label", address[:8])

        print(f"  → {label} ({address[:12]}...)")

        # Fetch recent swaps
        txns = await fetch_wallet_swaps(address, limit=50)

        # Filter to window
        recent = [tx for tx in txns if tx.get("timestamp", 0) >= cutoff_ts]
        total_fetched += len(recent)

        print(f"     {len(txns)} txns fetched, {len(recent)} in window")

        # Normalize
        trades = []
        for tx in recent:
            normalized = normalize_swap(tx, address, label)
            if normalized:
                trades.append(normalized)

        # Store to DB
        stored = await store_trades(pool, trades)
        total_stored += stored
        all_trades.extend(trades)

        await update_wallet_scan_time(pool, address)

        if trades:
            for t in trades[:3]:
                direction_icon = "↑" if t["direction"] == "BUY" else "↓" if t["direction"] == "SELL" else "↔"
                in_sym = t["input_symbol"] or t["input_mint"][:8]
                out_sym = t["output_symbol"] or t["output_mint"][:8]
                print(f"     {direction_icon} {t['direction']}: {t['input_amount']:.4f} {in_sym} → {t['output_amount']:.4f} {out_sym} ({t['source_dex']})")

        # Rate limit: be kind to Helius free tier
        await asyncio.sleep(0.3)

    print(f"\n{'─'*60}")
    print(f"  Fetched: {total_fetched} swaps | New stored: {total_stored}")

    # Detect copy signals (convergence)
    signals = detect_convergence(all_trades)
    if signals:
        print(f"\n  ⚡ {len(signals)} CONVERGENCE SIGNALS:")
        for sig in signals:
            print(f"     [{sig['wallet_count']} wallets] {sig['token_symbol'] or sig['token_mint'][:12]}")

    await pool.close()

    return {
        "wallets_scanned": len(wallets),
        "swaps_fetched": total_fetched,
        "new_trades_stored": total_stored,
        "convergence_signals": len(signals),
    }


# ─── Convergence Detection ────────────────────────────────────────────────────

def detect_convergence(trades: list[dict], min_wallets: int = 3) -> list[dict]:
    """
    Find tokens bought by 2+ wallets in this scan window.
    This is the core copy-trading signal: multiple smart wallets buying same token.
    """
    from collections import defaultdict

    token_buyers: dict[str, list[dict]] = defaultdict(list)

    for t in trades:
        if t["direction"] == "BUY" and t["output_mint"] not in STABLECOINS:
            token_buyers[t["output_mint"]].append({
                "wallet_label": t["wallet_label"],
                "wallet_address": t["wallet_address"],
                "amount": t["output_amount"],
                "source_dex": t["source_dex"],
            })

    signals = []
    for mint, buyers in token_buyers.items():
        # Deduplicate by wallet_label — same wallet buying multiple times counts as ONE
        seen_labels: set[str] = set()
        unique_buyers: list[dict] = []
        for b in buyers:
            if b["wallet_label"] not in seen_labels:
                seen_labels.add(b["wallet_label"])
                unique_buyers.append(b)
        if len(unique_buyers) >= min_wallets:
            signals.append({
                "token_mint": mint,
                "token_symbol": KNOWN_SYMBOLS.get(mint),
                "wallet_count": len(unique_buyers),
                "wallets": unique_buyers,
            })

    return signals


# ─── CLI ──────────────────────────────────────────────────────────────────────

async def main():
    parser = argparse.ArgumentParser(description="Solana copy trading data ingestion")
    parser.add_argument("--window", type=int, default=1800, help="Look-back window in seconds (default: 1800)")
    parser.add_argument("--wallets", type=str, default=None, help="Comma-separated wallet labels to scan (default: all active)")
    parser.add_argument("--pnl-summary", action="store_true", help="Show PnL summary from stored data")
    parser.add_argument("--sync-wallets", action="store_true", help="Sync wallet registry to DB and exit")
    parser.add_argument("--enrich-prices", action="store_true",
                        help="Fetch missing token prices from DexScreener and cache in DB")
    parser.add_argument("--backtest", action="store_true",
                        help="Run backtesting P&L calculation using cached prices")
    parser.add_argument("--core-only", action="store_true",
                        help="Restrict enrichment/backtest to core wallets (SM_5, SM_8, SM_18, SM_19)")
    args = parser.parse_args()

    label_filter = [x.strip() for x in args.wallets.split(",")] if args.wallets else None
    wallet_set = set(label_filter) if label_filter else (CORE_WALLETS if args.core_only else None)

    pool = await get_db_pool()

    if args.sync_wallets:
        n = await sync_wallets_to_db(pool)
        print(f"Synced {n} wallets to alpha_wallets table")
        await pool.close()
        return

    if args.pnl_summary:
        rows = await compute_pnl_summary(pool, hours=24)
        print("\n=== PnL Summary (last 24h) ===")
        if not rows:
            print("No trade data yet — run ingestion first")
        for r in rows:
            print(f"  {r['wallet_label']}: {r['total_trades']} trades, "
                  f"{r['buy_count']} buys / {r['sell_count']} sells, "
                  f"{r['unique_tokens_bought']} tokens bought")
        await pool.close()
        return

    if args.enrich_prices:
        result = await enrich_trades_with_prices(pool, wallet_filter=wallet_set)
        print(f"\nEnrichment result: {json.dumps(result, indent=2)}")
        await pool.close()
        return

    if args.backtest:
        print("\n[Backtest] Computing wallet P&L with current prices...")
        results = await compute_backtest_pnl(pool, wallet_filter=wallet_set)
        print("\n=== Backtest P&L by Wallet (Sharpe ranked) ===")
        if not results:
            print("No priced trades found. Run --enrich-prices first.")
        for r in results:
            flag = " ★ CORE" if r["wallet_label"] in CORE_WALLETS else ""
            flag += " ✗ NOISY" if r["wallet_label"] in NOISY_WALLETS else ""
            print(
                f"  {r['wallet_label']}{flag}: "
                f"trades={r['trades_with_price']} "
                f"win_rate={r['win_rate']:.1%} "
                f"avg_ret={r['avg_return_pct']:+.1f}% "
                f"pnl=${r['total_pnl_usd']:+,.2f} "
                f"sharpe={r['sharpe_approx']:.3f}"
            )
        await pool.close()
        return

    await pool.close()

    # Default: run ingestion (skip noisy wallets unless explicitly requested)
    if label_filter is None:
        # Exclude noisy wallets from default scans
        with open(WALLETS_JSON) as f:
            wallet_data = json.load(f)
        active_labels = [
            w.get("label") for w in wallet_data.get("wallets", [])
            if w.get("active", True) and w.get("label") not in NOISY_WALLETS
        ]
        label_filter = active_labels or None

    result = await run_ingestion(window_seconds=args.window, label_filter=label_filter)
    print(f"\nResult: {json.dumps(result, indent=2)}")


if __name__ == "__main__":
    asyncio.run(main())
