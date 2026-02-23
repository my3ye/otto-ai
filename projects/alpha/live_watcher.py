#!/usr/bin/env python3
"""
Alpha Live Watcher — 5-minute wallet polling with signal quality scoring.

Runs every 5 minutes via systemd timer (otto-alpha-watcher.timer).
Detects fresh buy signals from smart money wallets, scores them,
deduplicates, and feeds HIGH-quality signals to the paper trader.

Design:
  - 5-minute scan window (matches timer frequency)
  - Quality score = wallet_win_rate (0.5) + size (0.3) + freshness (0.2)
  - Signals graded A/B/C; only A/B feed paper trader
  - Writes watcher_stats.json for dashboard
  - Deduplicates via existing signals.jsonl + in-memory set
"""

import asyncio
import json
import os
import sys
import time
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import asyncpg
import httpx

# Add bot/ to path for helius_client and wallet_tracker
ALPHA_DIR = Path(__file__).parent
BOT_DIR = ALPHA_DIR / "bot"
sys.path.insert(0, str(BOT_DIR))
sys.path.insert(0, str(ALPHA_DIR / "backtest"))
sys.path.insert(0, str(ALPHA_DIR / "signals"))

from dotenv import load_dotenv
load_dotenv(BOT_DIR / ".env")

from helius_client import get_wallet_transactions
from wallet_tracker import is_swap_event, extract_swap_details, load_wallets

# ── Paths ────────────────────────────────────────────────────────────────────
SIGNALS_PATH = ALPHA_DIR / "signals.jsonl"
WALLETS_PATH = ALPHA_DIR / "wallets.json"
BACKTEST_PATH = ALPHA_DIR / "backtest" / "results" / "per_wallet_backtest.json"
STATS_PATH = ALPHA_DIR / "watcher_stats.json"
WALLET_BALANCES_PATH = ALPHA_DIR / "wallet_balances.json"
PAPER_TRADER_PATH = ALPHA_DIR / "paper_trader.py"
VENV_PYTHON = ALPHA_DIR / ".venv" / "bin" / "python3"
ALERT_COOLDOWNS_PATH = ALPHA_DIR / "alert_cooldowns.json"
WHATSAPP_SEND_SH = Path("/home/web3relic/otto/tools/whatsapp_send.sh")

# ── DB Config ────────────────────────────────────────────────────────────────
DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "user": "otto",
    "password": "LldgQBV1hiPejrKn6UlPQvX76pBqMB",
    "database": "memory",
}

# ── Config ───────────────────────────────────────────────────────────────────
SCAN_WINDOW_SECONDS = 5 * 60       # 5 minutes — matches timer frequency
QUALITY_A_THRESHOLD = 0.35         # Grade A: open paper trade (lowered from 0.45 — size_score was near-zero when API returns no amount data, composite was systematically suppressed)
QUALITY_B_THRESHOLD = 0.25         # Grade B: log as MEDIUM signal, no auto-trade (lowered from 0.40)
MIN_SOL_AMOUNT = 0.1               # Ignore dust buys < 0.1 SOL (raised from 0.01 — require meaningful conviction)
MAX_WALLETS_PER_RUN = 20           # Cap to stay within Helius rate limits
# WhatsApp alert thresholds
ALERT_MIN_WALLETS = 3              # Minimum wallets for HIGH-confidence WhatsApp alert
ALERT_COOLDOWN_SECONDS = 3600      # 1 hour cooldown per token

# BUG FIX 5: Noisy wallets — all SELL/UNKNOWN, zero buys, pollute convergence signals
NOISY_WALLETS = {"SM_1", "SM_2"}

# Base tokens — never treated as copy signals
BASE_TOKENS = {
    "So11111111111111111111111111111111111111112",     # Wrapped SOL
    "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",  # USDC
    "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB",  # USDT
    "Es9vMFrzaCERmKkovDkRs3zqhEYnhEhFdRgEaYNTbEUd",  # USDT alt
    "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263",  # BONK
    "7vfCXTUXx5WJV5JADk17DUJ4ksgau7utNKj4b963voxs",  # ETH (Wormhole)
    "mSoLzYCxHdYgdzU16g5QSh3i5K3z3KZK7ytfqcJm7So",   # mSOL
    "J1toso1uCk3RLmjorhTtrVwY9HJ7X8V9yYac6Y7kGCPn",  # jitoSOL
    "bSo13r4TkiE4KumL71LsHTPpL2euBYLFx6h9HP3piy1",   # bSOL
    "jtojtomepa8beP8AuQc6eXt5FriJwfFMwQx2v2f9mCL",   # JTO
    "orcaEKTdK7LKz57vaAYr624Dp4QuCcrKQhAVmFnvBbQ",   # Orca
    "JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN",   # JUP
    # ── Stablecoins (never alpha signals) ─────────────────────────────────
    "USD1ttGY1N17NEEHLmELoaybftRBUSErhqYiQzvEmuB",   # USD1 (World Liberty) — primary
    "USD1ttGY1N17NEEHLmELZmFE4A7d5nSqeAV3f3BBRDB",  # USD1 (alt address) — BUG FIX
    "USDSwr9ApdHk5bvJKMjzff41FfuX8bSxdKcR81vTwcA",   # USDS (Drift)
    "USDH1SM1ojwWUga67PGrgFWUHibbjqMvuMaDkRJTgkX",   # USDH (Hubble)
    "2b1kV6DkPAnxd5ixfnxCpjxmKwqjjaYmCZfHsFu24GXo",  # PYUSD (PayPal)
    "7kbnvuGBxxj8AG9qp8Scn56muWGaRaFqxg1FsRp3PaFT",  # UXD
    "Fm9rHUTF5v3hwMLbStjZXqNBBoZyGriQaFM6sTFz3K8A",  # USDD
    "AZsHEMXd36Bj1EMNXhowJajpUXzrKcK57wW4ZGXVa7yR",  # BUSD (Wormhole)
    "JuprjznTrTSp2UFa3ZBUFgwdAmtZCq4MQCwysN55USD",   # USD3/JUSD — BUG FIX
    # ── DeFi protocol tokens (too stable, high liquidity) ─────────────────
    "4k3Dyjzvzp8eMZWUXbBCjEvwSkkk59S5iCNLY3QrkX6R",   # RAY (Raydium)
    "METvsvVRapdjFy6HZnpbfFd7WNJiMp1sT1Nz1rSAtFS",   # MET (Meteora)
    "cbbtcf3aa214zXHbiAZQwf4122FBYbraNdFqgw4iMij",    # cbBTC (Coinbase BTC)
    "9n4nbM75f5Ui33ZbPYXn59EwSgE8CGsHtAeTH5YFeJ9E",   # wBTC
    "2FPyTwcZLUgr5Th81bnrK3vGTDYddPTFJGe85tHFdSK3",   # wETH
    "27G8MtK7VtTcCHkpASjSDdkWWYfoqT6ggEuKidVJidD4",   # Unknown DeFi ~$3.7 (not meme)
}


# ── DB Helpers (Bugs 1 + 2) ──────────────────────────────────────────────────

async def get_db_pool() -> Optional[asyncpg.Pool]:
    """Create a short-lived DB connection pool. Returns None on failure."""
    try:
        return await asyncpg.create_pool(**DB_CONFIG, min_size=1, max_size=3, command_timeout=10)
    except Exception as e:
        print(f"[watcher] DB connection failed (non-fatal): {e}")
        return None


async def insert_copy_signal(pool: asyncpg.Pool, signal: dict) -> None:
    """
    BUG FIX 1: Insert a HIGH convergence signal into alpha_copy_signals table.
    BUG FIX (DB dedup): Uses ON CONFLICT DO NOTHING on (signal_type, token_mint, ts_bucket)
    to prevent duplicate convergence signals within the same 5-minute window.
    """
    if pool is None:
        return
    try:
        ts_bucket = signal.get("ts_bucket")
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO alpha_copy_signals
                    (signal_type, token_mint, wallet_count, wallets, avg_entry_price,
                     total_volume_usd, status, ts_bucket)
                VALUES ($1, $2, $3, $4::jsonb, $5, $6, 'pending', $7)
                ON CONFLICT (signal_type, token_mint, ts_bucket)
                    WHERE ts_bucket IS NOT NULL
                DO NOTHING
                """,
                "convergence",
                signal["token"],
                signal.get("wallet_count", 1),
                json.dumps(signal.get("wallets", [])),
                signal.get("token_price_usd") or None,
                signal.get("amount_usd") or None,
                ts_bucket,
            )
    except Exception as e:
        print(f"  [watcher] DB signal insert failed (non-fatal): {e}")


async def cache_prices_to_db(pool: asyncpg.Pool, token_prices: dict[str, float]) -> None:
    """BUG FIX 2: Cache DexScreener prices to alpha_token_prices table."""
    if pool is None or not token_prices:
        return
    try:
        async with pool.acquire() as conn:
            for mint, price_usd in token_prices.items():
                try:
                    await conn.execute(
                        """
                        INSERT INTO alpha_token_prices (mint, price_usd, source)
                        VALUES ($1, $2, 'dexscreener')
                        ON CONFLICT DO NOTHING
                        """,
                        mint, price_usd,
                    )
                except Exception as e:
                    print(f"  [watcher] DB price cache failed for {mint[:12]}: {e}")
    except Exception as e:
        print(f"  [watcher] DB price cache error (non-fatal): {e}")


# ── Wallet SOL balance fetcher ────────────────────────────────────────────────

async def fetch_wallet_balances(wallets: list[dict]) -> dict[str, float]:
    """
    Fetch SOL balance (in SOL) for each wallet via Helius RPC.
    Returns {label: sol_balance}.
    """
    from config import HELIUS_API_KEY, HELIUS_RPC_URL
    if not HELIUS_API_KEY:
        return {}

    balances: dict[str, float] = {}
    async with httpx.AsyncClient(timeout=10.0) as client:
        for wallet in wallets[:20]:  # cap at 20
            address = wallet.get("address", "")
            label = wallet.get("label", address[:8])
            if not address:
                continue
            try:
                resp = await client.post(
                    HELIUS_RPC_URL,
                    json={"jsonrpc": "2.0", "id": 1, "method": "getBalance", "params": [address]},
                )
                resp.raise_for_status()
                data = resp.json()
                lamports = data.get("result", {}).get("value", 0)
                balances[label] = round(lamports / 1_000_000_000, 4)
            except Exception as e:
                print(f"  [watcher] balance fetch failed for {label}: {e}")
    return balances


# ── DexScreener price lookup ──────────────────────────────────────────────────

async def fetch_token_prices(mints: list[str]) -> dict[str, float]:
    """
    Fetch USD prices for a list of Solana token mint addresses via DexScreener.
    Returns {mint: price_usd}.
    """
    prices: dict[str, float] = {}
    if not mints:
        return prices
    # DexScreener allows comma-separated batch (up to 30)
    batch = list(set(mints))[:30]
    addrs = ",".join(batch)
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"https://api.dexscreener.com/tokens/v1/solana/{addrs}",
                headers={"User-Agent": "OttoAlpha/1.0"},
            )
            if resp.status_code != 200:
                return prices
            data = resp.json()
            # Response: list of pair objects, each has baseToken.address and priceUsd
            if isinstance(data, list):
                seen_mints: set[str] = set()
                for pair in data:
                    mint = pair.get("baseToken", {}).get("address", "")
                    price_str = pair.get("priceUsd")
                    if mint and price_str and mint not in seen_mints:
                        try:
                            prices[mint] = float(price_str)
                            seen_mints.add(mint)
                        except (ValueError, TypeError):
                            pass
    except Exception as e:
        print(f"  [watcher] DexScreener price fetch failed: {e}")
    return prices


# ── Wallet win-rate loader ────────────────────────────────────────────────────

def load_wallet_win_rates() -> dict[str, float]:
    """
    Load per-wallet win rates from backtest results.
    Returns {label: win_rate} with default 0.3 for unknown wallets.
    """
    win_rates: dict[str, float] = {}
    try:
        if not BACKTEST_PATH.exists():
            return win_rates
        with open(BACKTEST_PATH) as f:
            data = json.load(f)
        for wallet in data.get("wallets", []):
            label = wallet.get("label", "")
            trades = wallet.get("trades", [])
            if not trades:
                continue
            # Skip dry_run trades (no real price data — return_pct_4h is always 0.0)
            real_trades = [t for t in trades if t.get("note") != "dry_run"]
            if not real_trades:
                continue  # All dry_run → use default 0.3 (not stored, falls through)
            wins = sum(1 for t in real_trades if (t.get("return_pct_4h") or -1) > 0)
            win_rates[label] = wins / len(real_trades)
    except Exception as e:
        print(f"[watcher] Warning: could not load backtest win rates: {e}")
    return win_rates


# ── Signal dedup ─────────────────────────────────────────────────────────────

def load_seen_signals(hours: float = 0.5) -> set[tuple[str, str, int]]:
    """
    BUG FIX 4: Load (wallet_label, token, ts_bucket) tuples already logged in the last N hours.
    ts_bucket rounds tx time to 5-minute intervals to prevent near-duplicate entries
    from repeated scan cycles covering the same transaction window.
    """
    seen: set[tuple[str, str, int]] = set()
    if not SIGNALS_PATH.exists():
        return seen
    cutoff = time.time() - hours * 3600
    try:
        with open(SIGNALS_PATH) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                ts_str = rec.get("timestamp", "")
                if not ts_str:
                    continue
                try:
                    ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00")).timestamp()
                except Exception:
                    continue
                if ts < cutoff:
                    continue
                wallet = rec.get("wallet", "")
                token = rec.get("token", "")
                if wallet and token:
                    # BUG FIX: Use 'or' to treat None ts_bucket same as missing key
                    # rec.get("ts_bucket", default) returns None if field is present as null,
                    # which bypasses dedup. 'or' falls back to computed bucket for None/0/falsy.
                    raw_bucket = rec.get("ts_bucket")
                    ts_bucket = raw_bucket if raw_bucket is not None else int(ts // 300) * 300
                    seen.add((wallet, token, int(ts_bucket)))
    except OSError:
        pass
    return seen


# ── Signal quality scoring ────────────────────────────────────────────────────

def score_signal(
    wallet_label: str,
    token: str,
    amount_sol: float,
    tx_timestamp: int,
    win_rates: dict[str, float],
    all_buyers: list[str],
) -> dict:
    """
    Score a signal on 3 dimensions:

    1. wallet_win_rate (0–1): historical performance from backtest.
       Default 0.30 if no backtest data. Convergence wallets get average of all.

    2. size_score (0–1): normalized SOL amount.
       0.01 SOL → ~0.1, 0.5 SOL → ~0.5, 2+ SOL → 1.0

    3. freshness_score (0–1): how recent the buy was.
       Within last 60s → 1.0, 5 min → 0.0

    composite = 0.50 * win_rate + 0.30 * size + 0.20 * freshness

    Grade: A (>=0.65), B (>=0.40), C (<0.40)
    """
    now = time.time()

    # 1. Wallet win rate
    # FIX: default 0.50 (neutral) instead of 0.30 — backtest has 0 wallets, so all wallets
    # were getting the pessimistic 0.30 default which pulled composite below quality threshold.
    if wallet_label == "CONVERGENCE":
        rates = [win_rates.get(w, 0.50) for w in all_buyers]
        wallet_win_rate = sum(rates) / len(rates) if rates else 0.50
    else:
        wallet_win_rate = win_rates.get(wallet_label, 0.50)

    # 2. Size score — logarithmic scaling
    # FIX: when API returns no amount data (amount_sol==0), use neutral fallback 0.5
    # instead of near-zero (~0.001) which was killing quality scores unfairly.
    import math
    if amount_sol == 0:
        size_score = 0.5
    else:
        size_score = min(1.0, max(0.0, math.log10(max(amount_sol, 0.001) + 1) / math.log10(3)))

    # 3. Freshness score — linear decay over 5 minutes
    age_seconds = max(0, now - tx_timestamp)
    freshness_score = max(0.0, 1.0 - (age_seconds / SCAN_WINDOW_SECONDS))

    composite = 0.50 * wallet_win_rate + 0.30 * size_score + 0.20 * freshness_score

    if composite >= QUALITY_A_THRESHOLD:
        grade = "A"
    elif composite >= QUALITY_B_THRESHOLD:
        grade = "B"
    else:
        grade = "C"

    return {
        "quality_score": round(composite, 3),
        "quality_grade": grade,
        "wallet_win_rate": round(wallet_win_rate, 3),
        "size_score": round(size_score, 3),
        "freshness_score": round(freshness_score, 3),
    }


# ── Paper trader integration ──────────────────────────────────────────────────

def trigger_paper_trade(token: str, signal_name: str, quality: dict) -> bool:
    """
    Invoke paper_trader.py to open a position for a fresh high-quality signal.
    Writes a temp signal file and calls paper trader with --open-signal flag.
    Returns True if successful.
    """
    try:
        python = str(VENV_PYTHON) if VENV_PYTHON.exists() else "python3"
        result = subprocess.run(
            [python, str(PAPER_TRADER_PATH), "--run-once"],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=str(ALPHA_DIR),
        )
        if result.returncode == 0:
            print(f"  [watcher] Paper trader triggered for {token[:16]}: {signal_name}")
            return True
        else:
            print(f"  [watcher] Paper trader failed: {result.stderr[:200]}")
            return False
    except Exception as e:
        print(f"  [watcher] Paper trader error: {e}")
        return False


# ── Signal writer ─────────────────────────────────────────────────────────────

def write_signal(signal: dict) -> None:
    with open(SIGNALS_PATH, "a") as f:
        f.write(json.dumps(signal) + "\n")


# ── WhatsApp alert integration ────────────────────────────────────────────────

def load_alert_cooldowns() -> dict[str, float]:
    """
    Load alert cooldown map: {token_mint: last_alert_unix_ts}.
    Returns empty dict if file missing or malformed.
    """
    try:
        if ALERT_COOLDOWNS_PATH.exists():
            with open(ALERT_COOLDOWNS_PATH) as f:
                return json.load(f)
    except Exception as e:
        print(f"[watcher] Warning: could not load alert cooldowns: {e}")
    return {}


def save_alert_cooldowns(cooldowns: dict[str, float]) -> None:
    """Persist updated cooldown map to disk."""
    try:
        with open(ALERT_COOLDOWNS_PATH, "w") as f:
            json.dump(cooldowns, f, indent=2)
    except Exception as e:
        print(f"[watcher] Warning: could not save alert cooldowns: {e}")


def is_on_cooldown(token: str, cooldowns: dict[str, float]) -> bool:
    """Return True if this token was alerted within ALERT_COOLDOWN_SECONDS."""
    last_ts = cooldowns.get(token, 0)
    return (time.time() - last_ts) < ALERT_COOLDOWN_SECONDS


def send_convergence_alert(signal: dict, cooldowns: dict[str, float]) -> bool:
    """
    Send a WhatsApp alert for a HIGH-confidence convergence signal.
    Only fires when:
      - wallet_count >= ALERT_MIN_WALLETS (3)
      - Token is not on cooldown
    Updates cooldowns in-place if alert is sent.
    Returns True if alert was sent.
    """
    token = signal.get("token", "")
    wallet_count = signal.get("wallet_count", 0)

    if wallet_count < ALERT_MIN_WALLETS:
        return False

    if is_on_cooldown(token, cooldowns):
        print(f"  [watcher] Alert suppressed (cooldown): {token[:16]}...")
        return False

    if not WHATSAPP_SEND_SH.exists():
        print(f"  [watcher] WhatsApp send script not found: {WHATSAPP_SEND_SH}")
        return False

    # Build alert message
    wallets = signal.get("wallets", [])
    amount_sol = signal.get("amount_sol", 0)
    quality_score = signal.get("quality_score", 0)
    quality_grade = signal.get("quality_grade", "?")
    token_short = token[:20] + "..." if len(token) > 20 else token
    now_str = datetime.now(tz=timezone.utc).strftime("%H:%M UTC")

    wallet_list = ", ".join(wallets[:6])
    if len(wallets) > 6:
        wallet_list += f" +{len(wallets) - 6} more"

    message = (
        f"🚨 ALPHA SIGNAL [{now_str}]\n"
        f"Token: {token_short}\n"
        f"Wallets ({wallet_count}): {wallet_list}\n"
        f"Total: {amount_sol:.2f} SOL | Grade: {quality_grade} ({quality_score:.2f})\n"
        f"→ {token}"
    )

    try:
        result = subprocess.run(
            [str(WHATSAPP_SEND_SH), message],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if result.returncode == 0:
            cooldowns[token] = time.time()
            print(f"  [watcher] ✓ WhatsApp alert sent: {wallet_count} wallets → {token[:16]}...")
            return True
        else:
            print(f"  [watcher] WhatsApp alert failed (rc={result.returncode}): {result.stderr[:100]}")
            return False
    except subprocess.TimeoutExpired:
        print(f"  [watcher] WhatsApp alert timed out for {token[:16]}...")
        return False
    except Exception as e:
        print(f"  [watcher] WhatsApp alert error: {e}")
        return False


# ── Core scan ─────────────────────────────────────────────────────────────────

async def scan_for_fresh_signals() -> dict:
    """
    Main watcher loop:
    1. Load wallets + backtest win rates
    2. Poll each wallet for transactions in last 5 minutes
    3. Detect buy signals
    4. Score quality + deduplicate
    5. Write signals and trigger paper trader for grade A signals
    Returns stats dict.
    """
    run_start = time.time()
    now_ts = datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    print(f"\n[watcher] Live scan @ {now_ts}")

    wallets = load_wallets(str(WALLETS_PATH))
    if not wallets:
        print("[watcher] No wallets loaded — aborting")
        return {"error": "no wallets"}

    win_rates = load_wallet_win_rates()
    seen = load_seen_signals(hours=0.5)   # 30min dedup window (ts_bucket keyed)
    alert_cooldowns = load_alert_cooldowns()
    alerts_sent = 0

    # Connect to DB for signal persistence and price caching (non-fatal if fails)
    db_pool = await get_db_pool()

    # Cap wallets per run
    wallets = wallets[:MAX_WALLETS_PER_RUN]
    print(f"[watcher] Scanning {len(wallets)} wallets | win_rates loaded: {len(win_rates)}")

    # Per-token tracking for convergence detection
    token_buyers: dict[str, list[str]] = {}
    token_amounts: dict[str, float] = {}
    token_ts: dict[str, int] = {}
    raw_findings: list[dict] = []

    for wallet in wallets:
        address = wallet.get("address", "")
        label = wallet.get("label", address[:8])
        if not address:
            continue

        # BUG FIX 5: Skip noisy wallets (SM_1/SM_2 — all SELL/UNKNOWN, zero buys)
        if label in NOISY_WALLETS:
            continue

        txns = await get_wallet_transactions(address, limit=10)
        now = int(time.time())
        recent = [tx for tx in txns if (now - tx.get("timestamp", 0)) <= SCAN_WINDOW_SECONDS]
        swaps = [tx for tx in recent if is_swap_event(tx)]

        for tx in swaps:
            details = extract_swap_details(tx)
            if not details:
                continue

            token = details.get("output_mint", "")
            if not token or token == "unknown" or token in BASE_TOKENS:
                continue
            if len(token) < 32:
                continue

            # amount_sol is only meaningful when input was SOL (native SOL→token swaps)
            # Token→token swaps have raw token units as input_amount (not SOL), which
            # creates bogus amounts like 717M "SOL". Use 0 for non-SOL inputs to avoid
            # inflating quality scores; still allow the signal through (size not required).
            input_mint = details.get("input_mint", "")
            raw_amount = details.get("input_amount", 0)
            amount = raw_amount if input_mint == "SOL" else 0.0
            # For SOL inputs, enforce minimum size filter
            if input_mint == "SOL" and amount < MIN_SOL_AMOUNT:
                continue

            tx_ts = tx.get("timestamp", int(time.time()))

            raw_findings.append({
                "wallet_label": label,
                "wallet_address": address,
                "token": token,
                "amount_sol": amount,
                "tx_timestamp": tx_ts,
                **details,
            })

            # Track for convergence
            token_buyers.setdefault(token, []).append(label)
            token_amounts[token] = token_amounts.get(token, 0) + amount
            if token not in token_ts or tx_ts > token_ts[token]:
                token_ts[token] = tx_ts

    print(f"[watcher] Found {len(raw_findings)} raw buy events")

    # ── Fetch prices for detected tokens ─────────────────────────────────────
    detected_tokens = list(token_buyers.keys())
    token_prices = await fetch_token_prices(detected_tokens)
    if token_prices:
        print(f"[watcher] Fetched prices for {len(token_prices)}/{len(detected_tokens)} tokens")
        # BUG FIX 2: Cache DexScreener prices to DB for historical records + API rate limit reduction
        await cache_prices_to_db(db_pool, token_prices)

    # ── Generate signals ──────────────────────────────────────────────────────
    signals_written = 0
    grade_a_count = 0
    grade_b_count = 0

    for token, buyers in token_buyers.items():
        unique_buyers = sorted(set(buyers))
        wallet_count = len(unique_buyers)
        amount = round(token_amounts.get(token, 0), 4)
        tx_ts = token_ts.get(token, int(time.time()))
        # BUG FIX 4: ts_bucket rounds tx time to 5-minute intervals for dedup
        ts_bucket = (tx_ts // 300) * 300

        if wallet_count >= 3:
            # Convergence signal — requires 3+ wallets to match whale_convergence.py MIN_WALLETS
            sig_key = ("CONVERGENCE", token, ts_bucket)
            if sig_key in seen:
                continue

            quality = score_signal("CONVERGENCE", token, amount, tx_ts, win_rates, unique_buyers)
            token_price = token_prices.get(token, 0.0)
            amount_usd = round(amount * token_price, 4) if token_price else 0
            signal = {
                "timestamp": now_ts,
                "wallet": "CONVERGENCE",
                "signal": "HIGH",
                "token": token,
                "wallet_count": wallet_count,
                "wallets": unique_buyers,
                "amount_sol": amount,
                "amount_usd": amount_usd,
                "token_price_usd": round(token_price, 8) if token_price else 0,
                "ts_bucket": ts_bucket,
                "source": "live_watcher",
                "detail": f"LIVE CONVERGENCE: {wallet_count} wallets — {' '.join(unique_buyers)}",
                **quality,
            }
            write_signal(signal)
            # BUG FIX 1: Persist HIGH signal to alpha_copy_signals DB table
            await insert_copy_signal(db_pool, signal)
            seen.add(sig_key)
            signals_written += 1

            if quality["quality_grade"] == "A":
                grade_a_count += 1
                print(f"  [A] HIGH convergence {token[:16]}... | {wallet_count} wallets | "
                      f"score={quality['quality_score']}")
            else:
                grade_b_count += 1
                print(f"  [B] HIGH convergence {token[:16]}... | {wallet_count} wallets | "
                      f"score={quality['quality_score']}")

            # ── WhatsApp alert for high-confidence convergence (3+ wallets) ──
            if wallet_count >= ALERT_MIN_WALLETS:
                if send_convergence_alert(signal, alert_cooldowns):
                    alerts_sent += 1

        else:
            # Single wallet signal
            wallet_label = unique_buyers[0]
            sig_key = (wallet_label, token, ts_bucket)
            if sig_key in seen:
                continue

            quality = score_signal(wallet_label, token, amount, tx_ts, win_rates, unique_buyers)

            # Only log B and A grade singles (skip C to reduce noise)
            if quality["quality_grade"] == "C":
                continue

            token_price = token_prices.get(token, 0.0)
            amount_usd = round(amount * token_price, 4) if token_price else 0
            signal = {
                "timestamp": now_ts,
                "wallet": wallet_label,
                "signal": "MEDIUM",
                "token": token,
                "amount_sol": amount,
                "amount_usd": amount_usd,
                "token_price_usd": round(token_price, 8) if token_price else 0,
                "ts_bucket": ts_bucket,
                "source": "live_watcher",
                "detail": f"LIVE single buy: {amount:.4f} SOL | grade={quality['quality_grade']}",
                **quality,
            }
            write_signal(signal)
            seen.add(sig_key)
            signals_written += 1

            if quality["quality_grade"] == "A":
                grade_a_count += 1
                print(f"  [A] MEDIUM {wallet_label}/{token[:16]}... | "
                      f"score={quality['quality_score']}")
            else:
                grade_b_count += 1

    # ── Persist alert cooldowns ───────────────────────────────────────────────
    if alerts_sent > 0:
        save_alert_cooldowns(alert_cooldowns)
        print(f"[watcher] {alerts_sent} WhatsApp alert(s) sent")

    # ── Trigger paper trader if we have grade A signals ───────────────────────
    if grade_a_count > 0:
        print(f"[watcher] {grade_a_count} grade-A signals → triggering paper trader")
        trigger_paper_trade("", "live_watcher_grade_a", {})

    # ── Fetch wallet SOL balances ─────────────────────────────────────────────
    wallet_balances = await fetch_wallet_balances(wallets)
    if wallet_balances:
        print(f"[watcher] Fetched SOL balances for {len(wallet_balances)} wallets")
        balance_data = {
            "updated_at": now_ts,
            "balances": wallet_balances,
        }
        with open(WALLET_BALANCES_PATH, "w") as f:
            json.dump(balance_data, f, indent=2)

    # ── Write stats for dashboard ─────────────────────────────────────────────
    elapsed = round(time.time() - run_start, 2)
    stats = {
        "last_run": now_ts,
        "elapsed_seconds": elapsed,
        "wallets_scanned": len(wallets),
        "raw_findings": len(raw_findings),
        "signals_written": signals_written,
        "grade_a": grade_a_count,
        "grade_b": grade_b_count,
        "whatsapp_alerts_sent": alerts_sent,
        "win_rates_loaded": len(win_rates),
        "prices_fetched": len(token_prices),
        "balances_fetched": len(wallet_balances),
    }
    with open(STATS_PATH, "w") as f:
        json.dump(stats, f, indent=2)

    # ── Close DB pool ─────────────────────────────────────────────────────────
    if db_pool:
        await db_pool.close()

    print(f"[watcher] Done in {elapsed}s — {signals_written} signals "
          f"({grade_a_count} grade-A, {grade_b_count} grade-B)")
    return stats


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    stats = asyncio.run(scan_for_fresh_signals())
    sys.exit(0)
