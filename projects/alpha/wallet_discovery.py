#!/usr/bin/env python3
"""
wallet_discovery.py — FeePayer-Filtered Directional Trader Discovery

Rebuilds the wallet pool by finding REAL directional traders on Solana.

The old "early buyer" approach found LP positions, JIT LPs, and bots.
This pipeline finds wallets that:
  - Initiated their own SWAP transactions (feePayer = wallet)
  - Have directional trades (buy token X, later sell token X)
  - Show positive realized PnL from completed trade cycles

Strategy:
  1. Get trending tokens from DexScreener (high volume, recent activity)
  2. For each token, fetch recent SWAP transactions via Helius Enhanced TX API
  3. Extract unique feePayer wallets from those transactions
  4. Pre-filter: wallet must directly appear in tokenTransfers (not MEV relay target)
  5. Score each candidate using buy/sell pair tracking (compute_wallet_win_rate_from_pairs)
  6. Rank by win_rate × realized_pnl, filter by quality thresholds
  7. Output: discovered_traders.json with scored candidates

Usage:
  python3 wallet_discovery.py              # Full discovery run
  python3 wallet_discovery.py --dry-run    # Analyze only (no file write)
  python3 wallet_discovery.py --max-candidates N  # Limit candidate evaluation
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

# ── Path setup ────────────────────────────────────────────────────────────────

ALPHA_DIR = Path(__file__).parent
BOT_DIR = ALPHA_DIR / "bot"
sys.path.insert(0, str(BOT_DIR))

from helius_rotator import (
    get_helius_key,
    mark_key_exhausted,
    is_quota_exhaustion,
    HELIUS_API_BASE,
)
from birdeye_client import (
    compute_wallet_win_rate_from_pairs,
    score_wallet,
)

# ── Config ────────────────────────────────────────────────────────────────────

OUTPUT_FILE = ALPHA_DIR / "discovered_traders.json"
WALLETS_FILE = ALPHA_DIR / "wallets.json"

# DexScreener: token selection
DEXSCREENER_MAX_TOKENS = 10          # Trending tokens to fetch
DEXSCREENER_MIN_VOLUME_24H = 50_000  # Min $50k 24h volume to qualify
DEXSCREENER_MIN_PRICE_CHANGE = 10.0  # Min +10% 24h price change (recently active)

# Helius: how many recent swaps to fetch per trending token
SWAPS_PER_TOKEN = 100       # Recent SWAP txs to pull per trending token
WALLET_TX_PAGES = 2         # Pages of wallet tx history for scoring (2 × 100 = 200 txs)
WALLET_TX_PAGE_SIZE = 100   # Txs per page

# Candidate pre-filtering
MAX_CANDIDATES_TO_SCORE = 80    # Max wallets to run full pair-tracking on
MIN_TOKENS_SEEN = 1              # Min trending tokens a wallet must appear on
MIN_FEEPAYER_TXS = 2             # Min SWAP txs as feePayer across all tokens

# Scoring thresholds (for inclusion in discovered_traders.json top list)
MIN_COMPLETED_TRADES = 5         # At least 5 completed buy→sell cycles
MIN_WIN_RATE = 0.55              # 55%+ win rate
MIN_REALIZED_PNL = 0.0           # Positive PnL (> 0 SOL realized)
MAX_INACTIVE_DAYS = 14           # Must have traded within last 14 days

# Base/stable tokens — never wallet candidates
BASE_TOKENS: set[str] = {
    "So11111111111111111111111111111111111111112",   # wSOL
    "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",  # USDC
    "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB",  # USDT
    "Es9vMFrzaCERmKkovDkRs3zqhEYnhEhFdRgEaYNTbEUd",  # USDT alt
    "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263",  # BONK
    "mSoLzYCxHdYgdzU16g5QSh3i5K3z3KZK7ytfqcJm7So",  # mSOL
    "jtojtomepa8beP8AuQc6eXt5FriJwfFMwQx2v2f9mCL",  # jitoSOL
    "bSo13r4TkiE4KumL71LsHTPpL2euBYLFx6h9HP3piy1",  # bSOL
    "7vfCXTUXx5WJV5JADk17DUJ4ksgau7utNKj4b963voxs",  # ETH (Wormhole)
    "3NZ9JMVBmGAqocybic2c7LQCJScmgsAZ6vQqTDzcqmJh",  # BTC (Wormhole)
}

# ── Helpers ───────────────────────────────────────────────────────────────────


def load_wallets() -> dict:
    """Load existing wallets.json to exclude known wallets from discovery."""
    if not WALLETS_FILE.exists():
        return {"wallets": []}
    try:
        return json.loads(WALLETS_FILE.read_text())
    except Exception:
        return {"wallets": []}


def get_known_addresses(wallets_data: dict) -> set[str]:
    """Return set of already-tracked wallet addresses."""
    return {w.get("address", "") for w in wallets_data.get("wallets", [])}


def days_since(unix_ts: int) -> float:
    """Return how many days ago a unix timestamp was."""
    return (time.time() - unix_ts) / 86400 if unix_ts else 999.0


# ── Phase 1: DexScreener Token Discovery ──────────────────────────────────────


def fetch_trending_tokens() -> list[dict]:
    """
    Fetch trending Solana tokens from DexScreener.

    Uses:
      1. /token-boosts/top/v1 → get boosted token addresses
      2. /latest/dex/tokens/{addr} → get volume and price change
      3. Filter by MIN_VOLUME_24H and MIN_PRICE_CHANGE

    Returns list of {token_address, symbol, volume_24h, price_change_24h, ...}
    sorted by volume × price_change (recently active and hot).
    """
    print("[dexscreener] Fetching trending Solana tokens...")
    selected = []

    try:
        with httpx.Client(timeout=15.0) as client:
            # Step 1: Get boosted tokens
            resp = client.get("https://api.dexscreener.com/token-boosts/top/v1")
            resp.raise_for_status()
            boosts = resp.json()

            sol_addrs = [
                t["tokenAddress"]
                for t in boosts
                if isinstance(t, dict)
                and t.get("chainId") == "solana"
                and t.get("tokenAddress") not in BASE_TOKENS
            ]
            print(f"  {len(sol_addrs)} boosted Solana tokens to evaluate")

            # Step 2: Check each for volume and price change
            for addr in sol_addrs[:25]:   # evaluate up to 25, take best
                try:
                    r = client.get(f"https://api.dexscreener.com/latest/dex/tokens/{addr}")
                    r.raise_for_status()
                    pairs = r.json().get("pairs") or []
                    pairs = [p for p in pairs if p.get("chainId") == "solana"]
                    if not pairs:
                        continue

                    # Use highest-liquidity pair
                    pairs.sort(
                        key=lambda p: float((p.get("liquidity") or {}).get("usd") or 0),
                        reverse=True,
                    )
                    best = pairs[0]
                    price_change = float((best.get("priceChange") or {}).get("h24") or 0)
                    volume_24h = float((best.get("volume") or {}).get("h24") or 0)
                    liquidity_usd = float((best.get("liquidity") or {}).get("usd") or 0)
                    symbol = (best.get("baseToken") or {}).get("symbol", "?")
                    pair_created = best.get("pairCreatedAt")
                    age_days = (time.time() - pair_created / 1000) / 86400 if pair_created else None

                    if volume_24h >= DEXSCREENER_MIN_VOLUME_24H and price_change >= DEXSCREENER_MIN_PRICE_CHANGE:
                        selected.append({
                            "token_address": addr,
                            "symbol": symbol,
                            "price_change_24h": price_change,
                            "volume_24h": volume_24h,
                            "liquidity_usd": liquidity_usd,
                            "age_days": age_days,
                        })
                        print(f"  [+] {symbol} ({addr[:8]}...) +{price_change:.0f}% / ${volume_24h:,.0f} vol")

                    if len(selected) >= DEXSCREENER_MAX_TOKENS * 2:
                        break

                    time.sleep(0.3)

                except Exception as e:
                    print(f"  [!] DexScreener pair error for {addr[:8]}: {e}")
                    continue

    except Exception as e:
        print(f"[dexscreener] Error: {e}")

    # Sort by volume × price_change (most active hot tokens)
    selected.sort(key=lambda t: t["volume_24h"] * max(t["price_change_24h"], 1), reverse=True)
    result = selected[:DEXSCREENER_MAX_TOKENS]
    print(f"[dexscreener] {len(result)} trending tokens selected for trader extraction\n")
    return result


# ── Phase 2: FeePayer Wallet Extraction (Helius) ───────────────────────────────


def fetch_token_swap_txs(
    token_address: str,
    limit: int = SWAPS_PER_TOKEN,
) -> list[dict]:
    """
    Fetch recent SWAP transactions for a token mint address via Helius Enhanced TX API.

    Returns Helius-format transaction list (includes feePayer, tokenTransfers, etc.).
    This is different from the old approach — we query the TOKEN, not a specific wallet,
    to find wallets that recently traded it.
    """
    key = get_helius_key()
    if not key:
        print("  [!] No Helius key available")
        return []

    url = f"{HELIUS_API_BASE}/addresses/{token_address}/transactions"
    params = {"api-key": key, "limit": min(limit, 100), "type": "SWAP"}

    try:
        with httpx.Client(timeout=20.0) as client:
            resp = client.get(url, params=params)
            if resp.status_code == 429:
                body = resp.text
                if is_quota_exhaustion(body):
                    mark_key_exhausted(key)
                    # Retry with next key
                    key2 = get_helius_key()
                    if key2:
                        params["api-key"] = key2
                        resp = client.get(url, params=params)
                    else:
                        return []
                else:
                    print(f"  [!] Helius rate limit (transient) on token {token_address[:8]}")
                    time.sleep(2.0)
                    return []
            resp.raise_for_status()
            data = resp.json()
            return data if isinstance(data, list) else []

    except Exception as e:
        print(f"  [!] Helius token TX fetch error for {token_address[:8]}: {e}")
        return []


def extract_feepayer_traders(
    token_address: str,
    token_txs: list[dict],
) -> list[dict]:
    """
    Extract feePayer wallets from token swap transactions.

    Filters:
    - feePayer must not be in BASE_TOKENS
    - feePayer must directly appear in tokenTransfers for this token
      (rules out MEV bundlers where feePayer pays but tokens flow elsewhere)
    - Not a JIT LP transaction (same token sent ≈ received by same wallet)

    Returns list of {address, last_seen_ts, token, is_buyer, is_seller}
    """
    traders = []

    for tx in token_txs:
        fee_payer = tx.get("feePayer", "")
        if not fee_payer or fee_payer in BASE_TOKENS:
            continue

        ts = tx.get("timestamp", 0)
        token_transfers = tx.get("tokenTransfers") or []

        # Find transfers involving this token and the feePayer
        fp_recv = 0.0   # feePayer received this token
        fp_sent = 0.0   # feePayer sent this token
        for xfer in token_transfers:
            if xfer.get("mint") != token_address:
                continue
            amount = float(xfer.get("tokenAmount") or 0)
            if xfer.get("toUserAccount") == fee_payer:
                fp_recv += amount
            if xfer.get("fromUserAccount") == fee_payer:
                fp_sent += amount

        # feePayer must directly participate in this token's transfer
        if fp_recv <= 0 and fp_sent <= 0:
            continue  # feePayer didn't touch this token — likely MEV/relayer

        # JIT LP detection: sent ≈ received (within 0.5% tolerance)
        if fp_sent > 0 and fp_recv > 0:
            ratio_diff = abs(fp_recv - fp_sent) / fp_sent
            if ratio_diff < 0.005:
                continue  # JIT LP atomic add/remove — not a directional trade

        traders.append({
            "address": fee_payer,
            "last_seen_ts": ts,
            "token": token_address,
            "is_buyer": fp_recv > 0 and fp_sent == 0,
            "is_seller": fp_sent > 0 and fp_recv == 0,
        })

    return traders


def collect_candidate_wallets(
    trending_tokens: list[dict],
    known_addresses: set[str],
) -> dict[str, dict]:
    """
    Phase 2 main: for each trending token, extract feePayer traders.

    Returns dict: {wallet_address: {
        "tokens_seen": [list of token addresses],
        "token_symbols": [list of symbols],
        "feepayer_tx_count": int,
        "last_seen_ts": int,
        "buy_count": int,
        "sell_count": int,
    }}
    """
    candidates: dict[str, dict] = {}

    for token in trending_tokens:
        addr = token["token_address"]
        symbol = token["symbol"]
        print(f"[helius] Fetching recent swaps for {symbol} ({addr[:8]}...)...")

        txs = fetch_token_swap_txs(addr, limit=SWAPS_PER_TOKEN)
        print(f"  {len(txs)} SWAP txs fetched")

        if not txs:
            time.sleep(1.0)
            continue

        traders = extract_feepayer_traders(addr, txs)
        new_count = 0
        for t in traders:
            wallet = t["address"]

            # Skip known/existing pool wallets
            if wallet in known_addresses:
                continue

            if wallet not in candidates:
                candidates[wallet] = {
                    "tokens_seen": [],
                    "token_symbols": [],
                    "feepayer_tx_count": 0,
                    "last_seen_ts": 0,
                    "buy_count": 0,
                    "sell_count": 0,
                }
                new_count += 1

            c = candidates[wallet]
            if addr not in c["tokens_seen"]:
                c["tokens_seen"].append(addr)
                c["token_symbols"].append(symbol)
            c["feepayer_tx_count"] += 1
            c["last_seen_ts"] = max(c["last_seen_ts"], t["last_seen_ts"])
            if t["is_buyer"]:
                c["buy_count"] += 1
            if t["is_seller"]:
                c["sell_count"] += 1

        print(f"  {len(traders)} directional traders extracted, {new_count} new candidates")
        time.sleep(0.5)

    return candidates


# ── Phase 3: Pre-filtering ────────────────────────────────────────────────────


def prefilter_candidates(candidates: dict[str, dict]) -> list[tuple[str, dict]]:
    """
    Pre-filter candidates before expensive pair tracking scoring.

    Filters out:
    - Wallets with < MIN_FEEPAYER_TXS SWAP transactions (too little data)
    - Wallets inactive > MAX_INACTIVE_DAYS

    Ranks by:
    - Multi-token presence (traded on multiple trending tokens = broader awareness)
    - Recent activity (last_seen_ts)
    - Higher feepayer_tx_count

    Returns sorted list of (address, metadata) tuples.
    """
    print(f"\n[prefilter] {len(candidates)} raw candidates → filtering...")

    filtered = []
    now = time.time()
    too_few_txs = 0
    too_inactive = 0

    for addr, meta in candidates.items():
        # Filter: minimum SWAP activity
        if meta["feepayer_tx_count"] < MIN_FEEPAYER_TXS:
            too_few_txs += 1
            continue

        # Filter: recency
        days_inactive = days_since(meta["last_seen_ts"])
        if days_inactive > MAX_INACTIVE_DAYS:
            too_inactive += 1
            continue

        # Score for ranking: prioritize multi-token traders with recent activity
        tokens_count = len(meta["tokens_seen"])
        recency_score = max(0, 1 - days_inactive / MAX_INACTIVE_DAYS)
        rank_score = (
            tokens_count * 3.0          # multi-token = strong signal
            + meta["feepayer_tx_count"] * 0.5  # more active
            + recency_score * 2.0       # recent traders
        )
        filtered.append((addr, meta, rank_score))

    # Sort by rank score descending
    filtered.sort(key=lambda x: x[2], reverse=True)

    print(f"  Removed {too_few_txs} (too few txs), {too_inactive} (inactive)")
    print(f"  {len(filtered)} candidates pass pre-filter")

    # Return top N as (addr, meta) pairs
    top = [(addr, meta) for addr, meta, _ in filtered[:MAX_CANDIDATES_TO_SCORE]]
    return top


# ── Phase 4: Scoring via Pair Tracking ────────────────────────────────────────


def fetch_wallet_txs_paginated(
    wallet_address: str,
    pages: int = WALLET_TX_PAGES,
    page_size: int = WALLET_TX_PAGE_SIZE,
) -> list[dict]:
    """
    Fetch wallet's recent SWAP transactions using Helius Enhanced TX API with pagination.
    Returns up to pages * page_size transactions in chronological order (oldest last).
    """
    all_txs: list[dict] = []
    before_cursor: str | None = None

    for page in range(pages):
        key = get_helius_key()
        if not key:
            print(f"    [!] All Helius keys exhausted on page {page + 1}")
            break

        url = f"{HELIUS_API_BASE}/addresses/{wallet_address}/transactions"
        params: dict = {
            "api-key": key,
            "limit": page_size,
            "type": "SWAP",
        }
        if before_cursor:
            params["before"] = before_cursor

        try:
            with httpx.Client(timeout=20.0) as client:
                resp = client.get(url, params=params)

                if resp.status_code == 429:
                    body = resp.text
                    if is_quota_exhaustion(body):
                        mark_key_exhausted(key)
                        continue  # try next key
                    else:
                        print(f"    [!] Helius rate limit (transient) page {page + 1}")
                        time.sleep(3.0)
                        break

                resp.raise_for_status()
                data = resp.json()

        except Exception as e:
            print(f"    [!] Helius fetch error page {page + 1}: {e}")
            break

        if not data or not isinstance(data, list):
            break

        all_txs.extend(data)

        if len(data) < page_size:
            break  # No more pages

        before_cursor = data[-1].get("signature")
        if not before_cursor:
            break

        time.sleep(0.5)

    return all_txs


def score_candidate(
    wallet_address: str,
    meta: dict,
    idx: int,
    total: int,
) -> dict | None:
    """
    Score a single candidate wallet using pair tracking.

    Fetches wallet's tx history and runs compute_wallet_win_rate_from_pairs().
    Returns result dict or None if scoring fails.
    """
    tokens_str = ", ".join(meta["token_symbols"][:3])
    print(
        f"  [{idx+1}/{total}] {wallet_address[:16]}... "
        f"(tokens={tokens_str}, feepayer_txs={meta['feepayer_tx_count']})"
    )

    txs = fetch_wallet_txs_paginated(wallet_address)
    if not txs:
        print(f"    → No tx history (wallet inactive or API error)")
        return None

    print(f"    → {len(txs)} SWAP txs fetched")

    stats = compute_wallet_win_rate_from_pairs(
        wallet_address,
        txs,
        lookback_days=90,
        min_sol_per_trade=0.01,
    )

    composite = score_wallet(stats)

    wr = stats["win_rate"]
    n = stats["completed_trades"]
    pnl = stats["realized_pnl_sol"]
    hold_h = stats["avg_hold_minutes"] / 60
    status = "INSUFFICIENT" if stats["disqualified"] else "OK"

    print(
        f"    WR={wr*100:.0f}%  trades={n}  "
        f"pnl={pnl:+.3f}SOL  hold={hold_h:.1f}h  "
        f"score={composite:.3f}  [{status}]"
    )

    days_inactive = days_since(meta["last_seen_ts"])

    return {
        "address": wallet_address,
        "win_rate": stats["win_rate"],
        "completed_trades": stats["completed_trades"],
        "wins": stats["wins"],
        "losses": stats["losses"],
        "open_positions": stats["open_positions"],
        "realized_pnl_sol": stats["realized_pnl_sol"],
        "avg_hold_minutes": stats["avg_hold_minutes"],
        "composite_score": composite,
        "disqualified": stats["disqualified"],
        "disqualification_reason": stats.get("reason", ""),
        "method": "helius_pair_tracking",
        # Discovery metadata
        "tokens_found_on": meta["tokens_seen"],
        "token_symbols": meta["token_symbols"],
        "feepayer_tx_count": meta["feepayer_tx_count"],
        "last_seen_ts": meta["last_seen_ts"],
        "days_since_active": round(days_inactive, 1),
        "discovery_buy_count": meta["buy_count"],
        "discovery_sell_count": meta["sell_count"],
        "scored_at": datetime.now(timezone.utc).isoformat(),
    }


# ── Phase 5: Final filtering + output ─────────────────────────────────────────


def classify_wallet(result: dict) -> str:
    """
    Classify wallet type based on pair tracking results.
    Returns: "QUALIFIED", "LOW_WIN_RATE", "LOW_PNL", "INSUFFICIENT", "BOT_SUSPECTED"
    """
    if result["disqualified"]:
        return "INSUFFICIENT"
    if result["avg_hold_minutes"] < 5:
        return "BOT_SUSPECTED"
    if result["win_rate"] < MIN_WIN_RATE:
        return "LOW_WIN_RATE"
    if result["realized_pnl_sol"] <= MIN_REALIZED_PNL:
        return "LOW_PNL"
    if result["days_since_active"] > MAX_INACTIVE_DAYS:
        return "INACTIVE"
    return "QUALIFIED"


def print_summary(all_results: list[dict], qualified: list[dict]) -> None:
    """Print ranked discovery summary table."""
    print(f"\n{'='*70}")
    print("  WALLET DISCOVERY RESULTS — FeePayer-Filtered Directional Traders")
    print(f"{'='*70}")
    print(f"  Candidates scored:   {len(all_results)}")
    print(f"  Qualified traders:   {len(qualified)}")

    if qualified:
        avg_wr = sum(r["win_rate"] for r in qualified) / len(qualified)
        avg_pnl = sum(r["realized_pnl_sol"] for r in qualified) / len(qualified)
        print(f"  Avg win rate:        {avg_wr*100:.1f}%")
        print(f"  Avg realized PnL:    {avg_pnl:+.3f} SOL")

    print(f"\n  {'Address':<16}  {'WR%':>5}  {'Trades':>6}  {'W/L':>7}  {'PnL(SOL)':>10}  {'Hold':>6}  {'Classification'}")
    print(f"  {'─'*16}  {'─'*5}  {'─'*6}  {'─'*7}  {'─'*10}  {'─'*6}  {'─'*20}")

    # Sort all results for display: qualified first (by score), then others
    qualified_set = {r["address"] for r in qualified}
    display_order = (
        sorted([r for r in all_results if r["address"] in qualified_set],
               key=lambda r: -r["composite_score"])
        + sorted([r for r in all_results if r["address"] not in qualified_set and r["completed_trades"] > 0],
                 key=lambda r: -r["completed_trades"])
    )

    for r in display_order[:30]:  # Show top 30 in table
        classification = classify_wallet(r)
        wr_str = f"{r['win_rate']*100:.0f}%" if r["completed_trades"] > 0 else "N/A"
        hold_str = f"{r['avg_hold_minutes']/60:.1f}h"
        symbol = "★" if classification == "QUALIFIED" else " "
        print(
            f"{symbol} {r['address'][:16]}  "
            f"{wr_str:>5}  "
            f"{r['completed_trades']:>6}  "
            f"{r['wins']}/{r['losses']:<3}  "
            f"{r['realized_pnl_sol']:>+10.3f}  "
            f"{hold_str:>6}  "
            f"{classification}"
        )

    if qualified:
        print(f"\n  Top Qualified Traders (★):")
        for i, r in enumerate(qualified[:20]):
            tokens_str = ", ".join(r["token_symbols"][:3])
            print(f"  {i+1:2d}. {r['address']}")
            print(f"      WR={r['win_rate']*100:.0f}%  trades={r['completed_trades']}  "
                  f"PnL={r['realized_pnl_sol']:+.4f}SOL  score={r['composite_score']:.3f}")
            print(f"      Discovered on: {tokens_str}  active {r['days_since_active']:.1f}d ago")


# ── Main ──────────────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(
        description="FeePayer-Filtered Directional Trader Discovery for Solana"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Score candidates but don't write discovered_traders.json"
    )
    parser.add_argument(
        "--max-candidates", type=int, default=MAX_CANDIDATES_TO_SCORE,
        help=f"Max candidates to score (default: {MAX_CANDIDATES_TO_SCORE})"
    )
    args = parser.parse_args()

    print(f"\n{'='*70}")
    print("  Wallet Discovery — FeePayer-Filtered Directional Traders")
    print(f"  Date: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    if args.dry_run:
        print("  Mode: DRY RUN (no file writes)")
    print(f"{'='*70}\n")

    # ── Phase 0: Load known wallets ───────────────────────────────────────────
    wallets_data = load_wallets()
    known_addresses = get_known_addresses(wallets_data)
    print(f"[state] {len(known_addresses)} wallets already in pool (will skip these)")

    # ── Phase 1: DexScreener token discovery ──────────────────────────────────
    trending_tokens = fetch_trending_tokens()
    if not trending_tokens:
        print("[ERROR] No trending tokens found. Check DexScreener API or thresholds.")
        print("  Lowering thresholds for retry...")
        # Retry with looser criteria
        global DEXSCREENER_MIN_PRICE_CHANGE, DEXSCREENER_MIN_VOLUME_24H
        DEXSCREENER_MIN_PRICE_CHANGE = 0.0
        DEXSCREENER_MIN_VOLUME_24H = 10_000
        trending_tokens = fetch_trending_tokens()

    if not trending_tokens:
        print("[FATAL] Still no tokens. Cannot proceed.")
        sys.exit(1)

    # ── Phase 2: Extract feePayer wallets from token swap txs ─────────────────
    print("\n[Phase 2] Extracting feePayer traders from token swap transactions...")
    raw_candidates = collect_candidate_wallets(trending_tokens, known_addresses)
    print(f"\n[Phase 2] {len(raw_candidates)} unique candidate wallets collected")

    if not raw_candidates:
        print("[ERROR] No candidates found. Trending tokens may have low activity.")
        sys.exit(1)

    # ── Phase 3: Pre-filter candidates ────────────────────────────────────────
    print("\n[Phase 3] Pre-filtering candidates...")
    filtered_candidates = prefilter_candidates(raw_candidates)

    # Apply max-candidates limit
    if args.max_candidates < len(filtered_candidates):
        print(f"  Limiting to top {args.max_candidates} candidates (--max-candidates)")
        filtered_candidates = filtered_candidates[:args.max_candidates]

    if not filtered_candidates:
        print("[ERROR] No candidates pass pre-filter. Try lower thresholds.")
        sys.exit(1)

    # ── Phase 4: Score candidates via pair tracking ────────────────────────────
    total = len(filtered_candidates)
    print(f"\n[Phase 4] Scoring {total} candidates via pair tracking...")
    print("  Fetching wallet tx history + running buy/sell pair matching...\n")

    all_results: list[dict] = []
    for idx, (wallet_addr, meta) in enumerate(filtered_candidates):
        result = score_candidate(wallet_addr, meta, idx, total)
        if result:
            all_results.append(result)
        time.sleep(0.3)  # Be polite between wallet fetches

    print(f"\n[Phase 4] {len(all_results)} wallets successfully scored")

    # ── Phase 5: Filter qualified traders ─────────────────────────────────────
    qualified: list[dict] = []
    for r in all_results:
        classification = classify_wallet(r)
        if classification == "QUALIFIED":
            qualified.append(r)

    # Sort qualified by composite score descending
    qualified.sort(key=lambda r: -r["composite_score"])

    # ── Print summary ──────────────────────────────────────────────────────────
    print_summary(all_results, qualified)

    # ── Save results ───────────────────────────────────────────────────────────
    output = {
        "discovery_date": datetime.now(timezone.utc).isoformat(),
        "method": "feepayer_filtered_pair_tracking",
        "description": (
            "FeePayer-filtered directional trader discovery. "
            "Sourced from DexScreener trending tokens. "
            "Filtered by feePayer participation in token transfers (not LP/MEV targets). "
            "Scored via buy/sell pair tracking with FIFO cost basis."
        ),
        "config": {
            "trending_tokens_analyzed": len(trending_tokens),
            "candidates_collected": len(raw_candidates),
            "candidates_scored": len(all_results),
            "min_completed_trades": MIN_COMPLETED_TRADES,
            "min_win_rate": MIN_WIN_RATE,
            "min_realized_pnl": MIN_REALIZED_PNL,
            "max_inactive_days": MAX_INACTIVE_DAYS,
        },
        "summary": {
            "total_scored": len(all_results),
            "qualified_traders": len(qualified),
            "avg_win_rate_qualified": (
                round(sum(r["win_rate"] for r in qualified) / len(qualified), 3)
                if qualified else None
            ),
            "avg_pnl_qualified_sol": (
                round(sum(r["realized_pnl_sol"] for r in qualified) / len(qualified), 4)
                if qualified else None
            ),
        },
        "trending_tokens": [
            {
                "address": t["token_address"],
                "symbol": t["symbol"],
                "price_change_24h": t["price_change_24h"],
                "volume_24h": t["volume_24h"],
            }
            for t in trending_tokens
        ],
        "qualified_traders": qualified,
        "all_scored": sorted(all_results, key=lambda r: -r["composite_score"]),
    }

    if args.dry_run:
        print(f"\n[DRY RUN] Would save {len(qualified)} qualified traders to {OUTPUT_FILE}")
        print(f"  Total scored: {len(all_results)} candidates")
    else:
        OUTPUT_FILE.write_text(json.dumps(output, indent=2))
        print(f"\n[saved] Results written to {OUTPUT_FILE}")
        print(f"  Qualified traders: {len(qualified)}")
        print(f"  Total scored: {len(all_results)}")

    # ── Final summary for heartbeat review ────────────────────────────────────
    print(f"\n{'='*70}")
    print("DISCOVERY SUMMARY")
    print(f"  Trending tokens analyzed: {len(trending_tokens)}")
    print(f"  Unique feePayer candidates: {len(raw_candidates)}")
    print(f"  After pre-filtering: {len(filtered_candidates)}")
    print(f"  Successfully scored: {len(all_results)}")
    print(f"  QUALIFIED (WR≥{MIN_WIN_RATE*100:.0f}%, PnL>0, {MIN_COMPLETED_TRADES}+ trades): {len(qualified)}")
    if qualified:
        print(f"\n  TOP QUALIFIED WALLET CANDIDATES:")
        for i, r in enumerate(qualified[:10]):
            print(
                f"  {i+1:2d}. {r['address']}  "
                f"WR={r['win_rate']*100:.0f}%  "
                f"trades={r['completed_trades']}  "
                f"PnL={r['realized_pnl_sol']:+.4f}SOL  "
                f"score={r['composite_score']:.3f}"
            )
    else:
        print(f"\n  No qualified traders found in this discovery run.")
        print(f"  Consider: lowering thresholds, analyzing more tokens, or expanding time window.")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    main()
