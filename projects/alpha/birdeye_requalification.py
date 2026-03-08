#!/usr/bin/env python3
"""
birdeye_requalification.py — Week 2 Wallet Re-Qualification Pipeline

Uses Birdeye API to score existing wallets by actual win rate and trade quality,
then discovers + validates new high-performing wallets.

Research basis: SIGNAL_QUALITY_RESEARCH.md Section 4 + Section 7
Target: replace low-quality swap-frequency wallets with 65%+ win rate verified wallets

Steps:
  1. Score all active wallets in wallets.json using Birdeye PnL data
  2. Mark wallets below threshold (win_rate < 55%) for replacement
  3. Discover new wallet candidates via DexScreener early-buyer analysis
  4. Validate candidates via Birdeye — keep only 65%+ win rate wallets
  5. Update wallets.json with the qualified pool

Usage:
  python3 birdeye_requalification.py              # Full run
  python3 birdeye_requalification.py --dry-run    # Preview without writing
  python3 birdeye_requalification.py --score-only # Score existing wallets, no discovery
  python3 birdeye_requalification.py --wallet <address>  # Score a single wallet
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

# Add bot/ to path for birdeye_client and helius_client
ALPHA_DIR = Path(__file__).parent
BOT_DIR = ALPHA_DIR / "bot"
sys.path.insert(0, str(BOT_DIR))

from birdeye_client import (
    get_token_security,
    get_price_at_timestamp,
    compute_wallet_win_rate,
    compute_wallet_win_rate_from_pairs,
    score_wallet,
    RATE_LIMIT_SLEEP,
)
# Helius is the wallet tx source (Birdeye wallet endpoints require paid plan)
import asyncio
from helius_client import get_wallet_transactions as _helius_get_txs


def get_wallet_tx_list_sync(address: str, limit: int = 50) -> list[dict]:
    """Sync wrapper for async Helius wallet transaction fetcher."""
    try:
        return asyncio.run(_helius_get_txs(address, limit=limit))
    except Exception as e:
        print(f"    [!] Helius tx fetch error for {address[:12]}: {e}")
        return []


def get_wallet_transactions_extended(
    address: str,
    limit_per_page: int = 100,
    max_pages: int = 3,
) -> list[dict]:
    """
    Fetch up to limit_per_page * max_pages SWAP transactions using cursor pagination.

    Uses Helius Enhanced TX API with 'before' cursor for pagination.
    Handles key rotation on monthly quota exhaustion.
    Returns combined list of transactions across all pages.
    """
    from helius_rotator import get_helius_key, mark_key_exhausted, is_quota_exhaustion, HELIUS_API_BASE

    all_txs: list[dict] = []
    before_cursor: str | None = None

    for page in range(max_pages):
        key = get_helius_key()
        if not key:
            print(f"    [!] All Helius keys exhausted on page {page}")
            break

        url = f"{HELIUS_API_BASE}/addresses/{address}/transactions"
        params: dict = {
            "api-key": key,
            "limit": limit_per_page,
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
                        continue  # retry with next key
                    else:
                        print(f"    [!] Helius rate limited (transient) on page {page}")
                        break

                resp.raise_for_status()
                data = resp.json()

        except Exception as e:
            print(f"    [!] Helius fetch error (page {page}): {e}")
            break

        if not data or not isinstance(data, list):
            break

        all_txs.extend(data)
        print(f"    [helius] Page {page + 1}: {len(data)} txs (total {len(all_txs)})")

        if len(data) < limit_per_page:
            break  # No more pages

        # Set cursor to last signature for next page
        before_cursor = data[-1].get("signature")
        if not before_cursor:
            break

        time.sleep(0.5)  # Be nice to the rate limiter between pages

    return all_txs

# ── Config ────────────────────────────────────────────────────────────────────

WALLETS_FILE = ALPHA_DIR / "wallets.json"

# Qualification thresholds (from research)
MIN_WIN_RATE_KEEP = 0.55       # Keep existing wallet if win_rate >= 55%
MIN_WIN_RATE_ADD = 0.65        # Only add new wallets at >= 65%
MIN_TRADE_COUNT = 30           # Must have 30+ completed trades
MIN_AVG_HOLD_MINUTES = 5.0     # Not a bot (<5min hold = sniper/MEV)
MAX_NEW_WALLETS_PER_RUN = 5    # Max new wallets to add per run

# Early buyer discovery (via DexScreener)
PUMP_THRESHOLD_PCT = 100.0     # 2x+ pumped tokens qualify
PUMP_VOLUME_MIN = 100_000      # Min 24h volume USD
MAX_TOKENS_TO_CHECK = 8        # DexScreener budget
EARLY_BUYER_TOP_N = 30         # Check top N first buyers per token
MAX_EARLY_BUYER_SIGS = 500     # First N signatures = early buyers

# Base/stable tokens — never candidates
BASE_TOKENS = {
    "So11111111111111111111111111111111111111112",   # wSOL
    "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",  # USDC
    "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB",  # USDT
    "Es9vMFrzaCERmKkovDkRs3zqhEYnhEhFdRgEaYNTbEUd",  # USDT alt
    "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263",  # BONK
    "mSoLzYCxHdYgdzU16g5QSh3i5K3z3KZK7ytfqcJm7So",  # mSOL
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def load_wallets() -> dict:
    if not WALLETS_FILE.exists():
        return {"wallets": [], "wallet_count": 0, "last_updated": ""}
    return json.loads(WALLETS_FILE.read_text())


def save_wallets(data: dict, dry_run: bool = False) -> None:
    data["last_updated"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    data["wallet_count"] = len(data.get("wallets", []))
    if dry_run:
        print(f"[DRY RUN] Would save {data['wallet_count']} wallets")
        return
    WALLETS_FILE.write_text(json.dumps(data, indent=2))
    print(f"[wallets] Saved {data['wallet_count']} wallets to {WALLETS_FILE}")


def load_env() -> dict[str, str]:
    env: dict[str, str] = {}
    env_files = [
        Path("/home/web3relic/memory/.env"),
        ALPHA_DIR / ".env",
    ]
    for env_file in env_files:
        if env_file.exists():
            for line in env_file.read_text().splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    env[k.strip()] = v.strip()
    return env


# ── Step 1: Score Existing Wallets ────────────────────────────────────────────

def score_existing_wallet(wallet: dict) -> dict:
    """
    Score a single wallet using Helius tx history + Birdeye OHLCV pricing.
    Returns updated wallet dict with birdeye_score, win_rate, trade_count fields.
    """
    address = wallet.get("address", "")
    label = wallet.get("label", address[:8])
    print(f"\n  [score] {label} ({address[:12]}...)")

    txs = get_wallet_tx_list_sync(address, limit=50)
    time.sleep(RATE_LIMIT_SLEEP)

    if not txs:
        print(f"    → No Birdeye tx data (API may not index this wallet)")
        wallet["birdeye_score"] = None
        wallet["birdeye_win_rate"] = None
        wallet["birdeye_trade_count"] = 0
        wallet["birdeye_checked_at"] = datetime.now(timezone.utc).isoformat()
        return wallet

    stats = compute_wallet_win_rate(txs, lookback_days=90)
    composite = score_wallet(stats)

    wallet["birdeye_score"] = composite
    wallet["birdeye_win_rate"] = stats["win_rate"]
    wallet["birdeye_trade_count"] = stats["trade_count"]
    wallet["birdeye_avg_hold_min"] = stats["avg_hold_minutes"]
    wallet["birdeye_pnl_usd"] = stats.get("total_realized_pnl_usd", 0.0)
    wallet["birdeye_checked_at"] = datetime.now(timezone.utc).isoformat()

    wr_pct = stats["win_rate"] * 100
    verdict = "✓ KEEP" if stats["win_rate"] >= MIN_WIN_RATE_KEEP and not stats["disqualified"] else "✗ REPLACE"
    print(f"    WR={wr_pct:.0f}% | trades={stats['trade_count']} | "
          f"hold={stats['avg_hold_minutes']:.0f}min | score={composite:.2f} | {verdict}")

    return wallet


def score_all_wallets(wallets_data: dict, dry_run: bool = False) -> dict:
    """Score all active wallets. Mark weak ones for replacement."""
    active_wallets = [w for w in wallets_data.get("wallets", []) if w.get("active", True) is not False]
    print(f"\n[Step 1] Scoring {len(active_wallets)} active wallets via Birdeye...")

    scored = []
    for wallet in wallets_data.get("wallets", []):
        if wallet.get("active", True) is False:
            scored.append(wallet)
            continue
        updated = score_existing_wallet(wallet)
        scored.append(updated)

    wallets_data["wallets"] = scored
    return wallets_data


# ── Step 2: Find Wallets to Replace ───────────────────────────────────────────

def identify_replacement_candidates(wallets_data: dict) -> list[str]:
    """
    Return addresses of wallets that should be replaced.
    Criteria: birdeye_win_rate < MIN_WIN_RATE_KEEP, trade_count < MIN_TRADE_COUNT,
    or avg_hold < MIN_AVG_HOLD_MINUTES (bot behavior).
    """
    to_replace = []
    for wallet in wallets_data.get("wallets", []):
        if wallet.get("active", True) is False:
            continue
        wr = wallet.get("birdeye_win_rate")
        tc = wallet.get("birdeye_trade_count", 0)
        hold = wallet.get("birdeye_avg_hold_min", 0)

        if wr is None:
            # No Birdeye data — could be unlisted. Don't replace blindly.
            continue
        if wr < MIN_WIN_RATE_KEEP:
            to_replace.append(wallet["address"])
            print(f"  → Replace {wallet.get('label', '?')}: win_rate={wr*100:.0f}% < {MIN_WIN_RATE_KEEP*100:.0f}%")
        elif tc < MIN_TRADE_COUNT:
            to_replace.append(wallet["address"])
            print(f"  → Replace {wallet.get('label', '?')}: trades={tc} < {MIN_TRADE_COUNT}")
        elif hold < MIN_AVG_HOLD_MINUTES and hold > 0:
            to_replace.append(wallet["address"])
            print(f"  → Replace {wallet.get('label', '?')}: avg_hold={hold:.1f}min < {MIN_AVG_HOLD_MINUTES}min (bot)")

    print(f"\n[Step 2] {len(to_replace)} wallets queued for replacement")
    return to_replace


# ── Step 3: Discover New Wallet Candidates ────────────────────────────────────

def fetch_pumped_tokens_dexscreener() -> list[dict]:
    """Find 2x+ pumped Solana tokens from DexScreener trending."""
    print("\n[Step 3a] Fetching pumped tokens from DexScreener...")
    pumped = []

    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.get("https://api.dexscreener.com/token-boosts/top/v1")
            resp.raise_for_status()
            boosts = resp.json()

            sol_tokens = [
                t["tokenAddress"] for t in boosts
                if isinstance(t, dict)
                and t.get("chainId") == "solana"
                and t.get("tokenAddress") not in BASE_TOKENS
            ]
            print(f"  {len(sol_tokens)} trending Solana tokens to check")

            for addr in sol_tokens[:MAX_TOKENS_TO_CHECK + 5]:
                try:
                    r = client.get(f"https://api.dexscreener.com/latest/dex/tokens/{addr}")
                    r.raise_for_status()
                    pairs = r.json().get("pairs", []) or []
                    pairs = [p for p in pairs if p.get("chainId") == "solana"]
                    if not pairs:
                        continue
                    pairs.sort(
                        key=lambda p: float(p.get("liquidity", {}).get("usd", 0) or 0),
                        reverse=True,
                    )
                    best = pairs[0]
                    price_change = float(best.get("priceChange", {}).get("h24") or 0)
                    volume_24h = float(best.get("volume", {}).get("h24") or 0)

                    if price_change >= PUMP_THRESHOLD_PCT and volume_24h >= PUMP_VOLUME_MIN:
                        pair_created = best.get("pairCreatedAt")
                        age_days = None
                        if pair_created:
                            age_days = (time.time() - pair_created / 1000) / 86400

                        pumped.append({
                            "token_address": addr,
                            "symbol": best.get("baseToken", {}).get("symbol", "?"),
                            "price_change_24h": price_change,
                            "volume_24h": volume_24h,
                            "liquidity_usd": float(best.get("liquidity", {}).get("usd", 0) or 0),
                            "pair_address": best.get("pairAddress", ""),
                            "age_days": age_days,
                        })
                        print(f"  [+] {best.get('baseToken', {}).get('symbol')} "
                              f"+{price_change:.0f}% / ${volume_24h:,.0f} vol")

                    time.sleep(0.3)
                    if len(pumped) >= MAX_TOKENS_TO_CHECK:
                        break

                except Exception as e:
                    print(f"  [!] DexScreener error for {addr[:8]}: {e}")
                    continue

    except Exception as e:
        print(f"  [!] DexScreener error: {e}")

    print(f"  {len(pumped)} pumped tokens selected")
    return pumped


def get_early_buyers_helius(
    token_address: str,
    helius_key: str,
    top_n: int = EARLY_BUYER_TOP_N,
) -> list[str]:
    """
    Get wallet addresses that bought a token early (first N signatures).
    Uses Helius RPC getSignaturesForAddress.
    Returns list of unique wallet addresses.
    """
    rpc_url = f"https://mainnet.helius-rpc.com/?api-key={helius_key}"
    all_sigs = []
    batch_size = 200
    calls = 0

    # Walk backwards to find earliest transactions
    while calls < 3 and len(all_sigs) < MAX_EARLY_BUYER_SIGS:
        before = all_sigs[-1]["signature"] if all_sigs else None
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getSignaturesForAddress",
            "params": [
                token_address,
                {"limit": batch_size, **({"before": before} if before else {})}
            ]
        }
        try:
            with httpx.Client(timeout=15.0) as client:
                resp = client.post(rpc_url, json=payload)
                resp.raise_for_status()
                result = resp.json().get("result", [])
        except Exception as e:
            print(f"    [!] getSignaturesForAddress error: {e}")
            break

        if not result:
            break
        all_sigs.extend(result)
        calls += 1
        if len(result) < batch_size:
            break
        time.sleep(0.3)

    # Earliest first
    all_sigs.reverse()
    early_sigs = all_sigs[:top_n]

    # Extract accounts from signatures (signers are the first account)
    buyers = []
    for sig_info in early_sigs:
        # We'd need to parse the tx to get the buyer wallet — use a simplified approach:
        # The signer of the first N txs on a new token is the early buyer
        memo = sig_info.get("memo", "")
        # Can't extract wallet from sig alone — use transaction parser
        # Return sig list and parse separately
        _ = sig_info.get("signature", "")

    # Use Helius enhanced transactions to parse signers
    sigs = [s["signature"] for s in early_sigs]
    wallets: set[str] = set()

    # Parse in batches of 10
    for i in range(0, len(sigs), 10):
        batch = sigs[i:i+10]
        url = f"https://api.helius.xyz/v0/transactions?api-key={helius_key}"
        try:
            with httpx.Client(timeout=15.0) as client:
                resp = client.post(url, json={"transactions": batch})
                resp.raise_for_status()
                txs = resp.json()
                for tx in txs:
                    fee_payer = tx.get("feePayer", "")
                    if fee_payer and fee_payer not in BASE_TOKENS:
                        wallets.add(fee_payer)
            time.sleep(0.3)
        except Exception as e:
            print(f"    [!] Helius tx parse error: {e}")
            break

    return list(wallets)


def discover_new_candidates(
    pumped_tokens: list[dict],
    existing_addresses: set[str],
    env: dict[str, str],
) -> list[str]:
    """
    Find wallet candidates from early buyers of pumped tokens.
    Filters out known wallets and BASE_TOKENS.
    """
    helius_key = env.get("HELIUS_API_KEY", "")
    if not helius_key:
        print("  [!] No HELIUS_API_KEY — cannot discover new wallets from early buyers")
        return []

    candidates: dict[str, int] = {}  # address → count of pumped tokens they bought early

    for token in pumped_tokens:
        addr = token["token_address"]
        symbol = token["symbol"]
        print(f"  [early buyers] {symbol} ({addr[:8]}...)...")

        buyers = get_early_buyers_helius(addr, helius_key)
        print(f"    → {len(buyers)} early buyers found")

        for buyer in buyers:
            if buyer in existing_addresses or buyer in BASE_TOKENS:
                continue
            candidates[buyer] = candidates.get(buyer, 0) + 1

    # Sort by frequency (wallets appearing as early buyer of multiple pumps = better signal)
    sorted_candidates = sorted(candidates.items(), key=lambda x: x[1], reverse=True)
    top_candidates = [addr for addr, _ in sorted_candidates[:20]]  # Top 20 for validation

    print(f"\n  {len(top_candidates)} new wallet candidates found (filtered from {len(candidates)} total)")
    return top_candidates


# ── Step 4: Validate Candidates via Birdeye ───────────────────────────────────

def validate_candidate(address: str, multi_token_count: int = 1) -> dict | None:
    """
    Validate a wallet candidate via Helius tx history + Birdeye OHLCV pricing.
    Returns wallet dict if qualified (sufficient trade activity), None otherwise.
    """
    txs = get_wallet_tx_list_sync(address, limit=50)
    time.sleep(RATE_LIMIT_SLEEP)

    if not txs:
        return None

    stats = compute_wallet_win_rate(txs, lookback_days=90)
    composite = score_wallet(stats)

    wr = stats["win_rate"]
    tc = stats["trade_count"]
    hold = stats["avg_hold_minutes"]

    print(f"    {address[:12]}... WR={wr*100:.0f}% trades={tc} hold={hold:.0f}min score={composite:.2f}", end="")

    # Gate checks
    if stats["disqualified"]:
        print(f" → SKIP (insufficient data: {stats['reason']})")
        return None
    if wr < MIN_WIN_RATE_ADD:
        print(f" → SKIP (win_rate {wr*100:.0f}% < {MIN_WIN_RATE_ADD*100:.0f}%)")
        return None
    if tc < MIN_TRADE_COUNT:
        print(f" → SKIP (trades {tc} < {MIN_TRADE_COUNT})")
        return None
    if hold < MIN_AVG_HOLD_MINUTES:
        print(f" → SKIP (bot: avg_hold {hold:.1f}min < {MIN_AVG_HOLD_MINUTES}min)")
        return None

    print(f" → ✓ QUALIFIED")
    return {
        "address": address,
        "source": f"birdeye_requalification {datetime.now(timezone.utc).strftime('%Y-%m-%d')}",
        "strategy": "birdeye_validated",
        "birdeye_score": composite,
        "birdeye_win_rate": wr,
        "birdeye_trade_count": tc,
        "birdeye_avg_hold_min": hold,
        "birdeye_pnl_usd": stats["total_realized_pnl_usd"],
        "birdeye_checked_at": datetime.now(timezone.utc).isoformat(),
        "early_token_count": multi_token_count,
        "notes": (
            f"Birdeye-validated: {wr*100:.0f}% WR, {tc} trades, "
            f"{hold:.0f}min avg hold. Early buyer across {multi_token_count} pumped token(s)."
        ),
    }


# ── Step 5: Update wallets.json ───────────────────────────────────────────────

def apply_updates(
    wallets_data: dict,
    to_replace: list[str],
    new_wallets: list[dict],
    dry_run: bool = False,
) -> dict:
    """Deactivate weak wallets, add qualified new ones, assign labels."""
    wallets = wallets_data.get("wallets", [])

    # Deactivate wallets queued for replacement
    replaced_count = 0
    for wallet in wallets:
        if wallet.get("address") in to_replace:
            wallet["active"] = False
            wallet["deactivated_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            wallet["deactivation_reason"] = "birdeye_requalification: win_rate below threshold"
            replaced_count += 1

    # Determine next label number
    existing_labels = [w.get("label", "") for w in wallets]
    existing_nums = []
    for lbl in existing_labels:
        if lbl and lbl.startswith("SM_"):
            try:
                existing_nums.append(int(lbl[3:]))
            except ValueError:
                pass
    next_num = max(existing_nums, default=0) + 1

    # Add new qualified wallets
    added_count = 0
    for new_w in new_wallets[:MAX_NEW_WALLETS_PER_RUN]:
        # Skip if address already in pool
        if any(w.get("address") == new_w["address"] for w in wallets):
            print(f"  [skip] {new_w['address'][:12]}... already in pool")
            continue
        new_w["label"] = f"SM_{next_num}"
        next_num += 1
        wallets.append(new_w)
        added_count += 1
        print(f"  [+] Added {new_w['label']} — {new_w['address'][:16]}... "
              f"(WR={new_w.get('birdeye_win_rate', 0)*100:.0f}%)")

    wallets_data["wallets"] = wallets
    wallets_data["last_requalification"] = datetime.now(timezone.utc).isoformat()
    wallets_data["requalification_summary"] = {
        "deactivated": replaced_count,
        "added": added_count,
        "run_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
    }
    # Update birdeye_note
    wallets_data["birdeye_note"] = (
        f"BIRDEYE_API_KEY configured. Last re-qualification: "
        f"{datetime.now(timezone.utc).strftime('%Y-%m-%d')}. "
        f"Deactivated {replaced_count} wallets, added {added_count} validated."
    )

    print(f"\n[wallets] Updated: deactivated={replaced_count}, added={added_count}")
    return wallets_data


# ── Pair Tracking Analysis ────────────────────────────────────────────────────

PAIR_TRACKING_RESULTS_FILE = ALPHA_DIR / "winrate_pair_tracking_results.json"


def score_wallet_pair_tracking(wallet: dict) -> dict:
    """
    Score a wallet using buy/sell pair tracking from extended Helius tx history.

    Fetches up to 300 SWAP transactions (3 pages × 100), then uses
    compute_wallet_win_rate_from_pairs() to compute realized PnL per completed
    trade cycle (buy → sell of same token), with FIFO cost basis and
    token→token rollover support.

    Returns updated wallet dict with 'pair_tracking' sub-dict.
    """
    address = wallet.get("address", "")
    label = wallet.get("label", address[:8])
    print(f"\n  [pair-track] {label} ({address[:12]}...)")

    txs = get_wallet_transactions_extended(address, limit_per_page=100, max_pages=3)
    time.sleep(0.3)  # Brief pause between wallets

    if not txs:
        print(f"    → No transaction data (Helius unavailable or wallet inactive)")
        return {
            **wallet,
            "pair_tracking": {
                "status": "no_data",
                "win_rate": None,
                "completed_trades": 0,
                "wins": 0,
                "losses": 0,
                "open_positions": 0,
                "realized_pnl_sol": 0.0,
                "txs_fetched": 0,
            },
        }

    print(f"    → {len(txs)} total SWAP txs fetched")
    stats = compute_wallet_win_rate_from_pairs(address, txs, lookback_days=90)

    wr_pct = stats["win_rate"] * 100
    status = "SUFFICIENT" if not stats["disqualified"] else "INSUFFICIENT"
    hold_h = stats["avg_hold_minutes"] / 60

    print(
        f"    WR={wr_pct:.0f}%  completed={stats['completed_trades']} "
        f"(W={stats['wins']}/L={stats['losses']})  "
        f"open={stats['open_positions']}  "
        f"PnL={stats['realized_pnl_sol']:+.3f} SOL  "
        f"hold={hold_h:.1f}h  [{status}]"
    )

    return {
        **wallet,
        "pair_tracking": {
            **stats,
            "txs_fetched": len(txs),
            "checked_at": datetime.now(timezone.utc).isoformat(),
        },
    }


def run_pair_tracking_analysis(wallets_data: dict, target_label: str | None = None) -> None:
    """
    Run pair tracking win rate computation on all active wallets (or one specific wallet).

    Saves results to winrate_pair_tracking_results.json.
    Does NOT modify wallets.json — analysis only.
    """
    active_wallets = [
        w for w in wallets_data.get("wallets", [])
        if w.get("active", True) is not False
    ]

    if target_label:
        active_wallets = [w for w in active_wallets if w.get("label") == target_label]
        if not active_wallets:
            print(f"  [!] No active wallet found with label {target_label}")
            return

    print(f"\n[Pair Tracking] Running on {len(active_wallets)} active wallets...")
    print("  Method: buy/sell pair tracking from Helius tx history (up to 300 txs each)")
    print("  Computes: FIFO cost basis + token→token rollovers + realized PnL in SOL\n")

    results = []
    for wallet in active_wallets:
        scored = score_wallet_pair_tracking(wallet)
        pt = scored.get("pair_tracking", {})
        results.append({
            "label": wallet.get("label", "?"),
            "address": wallet.get("address", ""),
            "txs_fetched": pt.get("txs_fetched", 0),
            "completed_trades": pt.get("completed_trades", 0),
            "wins": pt.get("wins", 0),
            "losses": pt.get("losses", 0),
            "open_positions": pt.get("open_positions", 0),
            "win_rate": pt.get("win_rate"),
            "realized_pnl_sol": pt.get("realized_pnl_sol", 0.0),
            "avg_hold_minutes": pt.get("avg_hold_minutes", 0.0),
            "disqualified": pt.get("disqualified", True),
            "reason": pt.get("reason", ""),
            "method": pt.get("method", "helius_pair_tracking"),
        })

    # ── Summary ───────────────────────────────────────────────────────────────
    sufficient = [r for r in results if not r["disqualified"]]
    total_with_data = [r for r in results if r["completed_trades"] > 0]

    print("\n" + "=" * 60)
    print("  Pair Tracking Results Summary")
    print("=" * 60)
    print(f"  Wallets analyzed:   {len(results)}")
    print(f"  With completed trades: {len(total_with_data)}")
    print(f"  Sufficient data (5+):  {len(sufficient)}")

    if sufficient:
        avg_wr = sum(r["win_rate"] for r in sufficient) / len(sufficient)
        print(f"  Avg win rate (sufficient): {avg_wr * 100:.1f}%")
        print(f"\n  {'Label':<8}  {'WR%':>5}  {'Done':>5}  {'W/L':>7}  {'Open':>5}  {'PnL(SOL)':>10}")
        print(f"  {'-'*8}  {'-'*5}  {'-'*5}  {'-'*7}  {'-'*5}  {'-'*10}")
        for r in sorted(sufficient, key=lambda x: -(x["win_rate"] or 0)):
            print(
                f"  {r['label']:<8}  {r['win_rate']*100:>5.0f}%  "
                f"{r['completed_trades']:>5}  "
                f"{r['wins']}/{r['losses']:>3}  "
                f"{r['open_positions']:>5}  "
                f"{r['realized_pnl_sol']:>+10.3f}"
            )

    if total_with_data:
        print(f"\n  All wallets with >0 completed trades:")
        print(f"  {'Label':<8}  {'WR%':>5}  {'Done':>5}  {'Txs':>5}  {'Status'}")
        print(f"  {'-'*8}  {'-'*5}  {'-'*5}  {'-'*5}  {'-'*15}")
        for r in sorted(total_with_data, key=lambda x: -(x["completed_trades"])):
            status = "OK" if not r["disqualified"] else f"LOW ({r['completed_trades']}<5)"
            wr_str = f"{r['win_rate']*100:.0f}%" if r["win_rate"] is not None else "N/A"
            print(
                f"  {r['label']:<8}  {wr_str:>5}  {r['completed_trades']:>5}  "
                f"{r['txs_fetched']:>5}  {status}"
            )

    # ── Save results ──────────────────────────────────────────────────────────
    output = {
        "run_date": datetime.now(timezone.utc).isoformat(),
        "method": "helius_pair_tracking",
        "description": (
            "Buy/sell pair tracking from Helius tx history. "
            "FIFO cost basis matching, token→token rollover, realized PnL in SOL."
        ),
        "summary": {
            "total_analyzed": len(results),
            "with_completed_trades": len(total_with_data),
            "sufficient_data": len(sufficient),
            "avg_win_rate_sufficient": round(
                sum(r["win_rate"] for r in sufficient) / len(sufficient), 3
            ) if sufficient else None,
        },
        "wallets": results,
    }

    PAIR_TRACKING_RESULTS_FILE.write_text(json.dumps(output, indent=2))
    print(f"\n  Results saved to: {PAIR_TRACKING_RESULTS_FILE}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Birdeye wallet re-qualification pipeline")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without writing")
    parser.add_argument("--score-only", action="store_true", help="Score existing wallets only")
    parser.add_argument("--wallet", help="Score a single wallet address and exit")
    parser.add_argument(
        "--pair-tracking",
        action="store_true",
        help=(
            "Run buy/sell pair tracking win rate computation on all wallets. "
            "Fetches up to 300 txs each. Saves to winrate_pair_tracking_results.json. "
            "Does NOT modify wallets.json."
        ),
    )
    args = parser.parse_args()

    print("=" * 60)
    print("  Birdeye Wallet Re-Qualification Pipeline")
    print(f"  Date: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    if args.dry_run:
        print("  Mode: DRY RUN")
    print("=" * 60)

    env = load_env()

    # ── Pair tracking analysis mode ────────────────────────────────────────────
    if args.pair_tracking:
        print("  Mode: PAIR TRACKING (buy/sell pairs via Helius, no wallet changes)")
        print("=" * 60)
        wallets_data = load_wallets()
        active_wallets = [w for w in wallets_data.get("wallets", []) if w.get("active", True) is not False]
        print(f"\nLoaded {len(wallets_data['wallets'])} wallets ({len(active_wallets)} active)")
        run_pair_tracking_analysis(wallets_data, target_label=args.wallet)
        sys.exit(0)

    # ── Single wallet score mode ───────────────────────────────────────────────
    if args.wallet:
        print(f"\nScoring single wallet: {args.wallet}")
        txs = get_wallet_tx_list_sync(args.wallet, limit=50)
        if not txs:
            print("  No transaction data from Helius. Wallet may be inactive or not indexed.")
            sys.exit(0)
        stats = compute_wallet_win_rate(txs)
        score = score_wallet(stats)
        print(f"\nResults:")
        print(f"  Win rate:    {stats['win_rate']*100:.1f}%")
        print(f"  Trade count: {stats['trade_count']}")
        print(f"  Hold time:   {stats['avg_hold_minutes']:.1f} min avg")
        print(f"  PnL (USD):   ${stats['total_realized_pnl_usd']:,.2f}")
        print(f"  Composite:   {score:.3f}/1.000")
        print(f"  Status:      {'QUALIFIED (65%+)' if stats['win_rate'] >= MIN_WIN_RATE_ADD and not stats['disqualified'] else 'NOT QUALIFIED'}")
        if stats["disqualified"]:
            print(f"  Reason:      {stats['reason']}")
        sys.exit(0)

    # ── Full pipeline ──────────────────────────────────────────────────────────
    wallets_data = load_wallets()
    active_wallets = [w for w in wallets_data.get("wallets", []) if w.get("active", True) is not False]
    print(f"\nLoaded {len(wallets_data['wallets'])} wallets ({len(active_wallets)} active)")

    # Step 1: Score existing wallets
    wallets_data = score_all_wallets(wallets_data, dry_run=args.dry_run)

    # Step 2: Identify replacements
    print(f"\n[Step 2] Identifying wallets below threshold...")
    to_replace = identify_replacement_candidates(wallets_data)

    if args.score_only:
        print("\n[score-only mode] Writing scores, skipping discovery.")
        save_wallets(wallets_data, dry_run=args.dry_run)
        # Print summary
        active = [w for w in wallets_data["wallets"] if w.get("active", True) is not False]
        scored = [w for w in active if w.get("birdeye_win_rate") is not None]
        print(f"\nSummary:")
        print(f"  Active wallets:    {len(active)}")
        print(f"  Birdeye-scored:    {len(scored)}")
        if scored:
            avg_wr = sum(w["birdeye_win_rate"] for w in scored) / len(scored)
            print(f"  Avg win rate:      {avg_wr*100:.1f}%")
            print(f"  Below threshold:   {len(to_replace)}")
        sys.exit(0)

    # Step 3: Discover new candidates
    pumped_tokens = fetch_pumped_tokens_dexscreener()
    existing_addresses = {w["address"] for w in wallets_data.get("wallets", [])}

    new_candidates: list[str] = []
    if pumped_tokens:
        print("\n[Step 3b] Finding early buyers of pumped tokens...")
        new_candidates = discover_new_candidates(pumped_tokens, existing_addresses, env)
    else:
        print("\n[Step 3] No pumped tokens found — skipping discovery")

    # Step 4: Validate candidates
    new_qualified: list[dict] = []
    if new_candidates:
        print(f"\n[Step 4] Validating {len(new_candidates)} candidates via Birdeye...")
        for addr in new_candidates:
            if len(new_qualified) >= MAX_NEW_WALLETS_PER_RUN:
                break
            result = validate_candidate(addr)
            if result:
                new_qualified.append(result)

    print(f"\n  {len(new_qualified)} new wallets qualified")

    # Step 5: Apply updates
    print("\n[Step 5] Applying updates to wallets.json...")
    wallets_data = apply_updates(wallets_data, to_replace, new_qualified, dry_run=args.dry_run)
    save_wallets(wallets_data, dry_run=args.dry_run)

    # ── Final summary ──────────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("  Re-qualification Complete")
    print("=" * 60)
    active = [w for w in wallets_data["wallets"] if w.get("active", True) is not False]
    scored = [w for w in active if w.get("birdeye_win_rate") is not None]
    qualified = [w for w in scored if (w.get("birdeye_win_rate") or 0) >= MIN_WIN_RATE_KEEP]

    print(f"  Active wallets:  {len(active)}")
    print(f"  Birdeye scored:  {len(scored)}")
    print(f"  Win rate ≥55%:   {len(qualified)}")
    if scored:
        avg_wr = sum((w.get("birdeye_win_rate") or 0) for w in scored) / len(scored)
        print(f"  Avg win rate:    {avg_wr*100:.1f}%")
    print(f"  Deactivated:     {len(to_replace)}")
    print(f"  Added:           {len(new_qualified)}")
    if not args.dry_run:
        print(f"\n  wallets.json updated. Week 2 pipeline ready.")
    else:
        print(f"\n  [DRY RUN] No changes written.")


if __name__ == "__main__":
    main()
