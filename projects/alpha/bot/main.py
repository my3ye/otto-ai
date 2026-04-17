"""
Project Alpha — Solana Smart Money Scanner
Entry point: runs one scan cycle, prints findings, and writes signals to signals.jsonl.

Usage:
    python main.py

Env vars (via .env or environment):
    HELIUS_API_KEY      — Helius API key (required for live data)
    WALLET_PRIVATE_KEY  — Trading wallet private key (for execution phase)
"""

import asyncio
import json
import os
import sys
import time
from datetime import datetime, timezone

from loguru import logger

from config import HELIUS_API_KEY, WALLETS_JSON_PATH, SCAN_WINDOW_SECONDS
from wallet_tracker import scan_wallets


# Configure loguru for clean output
logger.remove()
logger.add(
    sys.stderr,
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | {message}",
    colorize=True,
    level="DEBUG",
)

SIGNALS_PATH = "/home/web3relic/otto/projects/alpha/signals.jsonl"

# Minimum valid Solana base58 address length (BUG FIX 2)
MIN_TOKEN_ADDR_LEN = 32

# Base tokens that appear as routing intermediaries — never treated as copy signals
# Synced with backtest/data_fetcher.py BASE_TOKENS
BASE_TOKENS = {
    # ── Native / Wrapped ─────────────────────────────────────────────────────
    "So11111111111111111111111111111111111111112",    # Wrapped SOL
    "7vfCXTUXx5WJV5JADk17DUJ4ksgau7utNKj4b963voxs",  # ETH (Wormhole)
    "cbbtcf3aa214zXHbiAZQwf4122FBYbraNdFqgw4iMij",   # cbBTC (Coinbase BTC on Solana)
    # ── Liquid Staking Tokens ────────────────────────────────────────────────
    "mSoLzYCxHdYgdzU16g5QSh3i5K3z3KZK7ytfqcJm7So",   # mSOL
    "J1toso1uCk3RLmjorhTtrVwY9HJ7X8V9yYac6Y7kGCPn",  # jitoSOL
    "bSo13r4TkiE4KumL71LsHTPpL2euBYLFx6h9HP3piy1",   # bSOL
    "jtojtomepa8beP8AuQc6eXt5FriJwfFMwQx2v2f9mCL",   # JTO (Jito governance)
    # ── Stablecoins ──────────────────────────────────────────────────────────
    "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",  # USDC
    "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB",  # USDT
    "Es9vMFrzaCERmKkovDkRs3zqhEYnhEhFdRgEaYNTbEUd",  # USDT (alt)
    "USD1ttGY1N17NEEHLmELoaybftRBUSErhqYiQzvEmuB",   # USD1 (World Liberty) — correct address
    "USD1ttGY1N17NEEHLmELZmFE4A7d5nSqeAV3f3BBRDB",  # USD1 (alt address)
    "USDSwr9ApdHk5bvJKMjzff41FfuX8bSxdKcR81vTwcA",  # USDS (Drift)
    "USDH1SM1ojwWUga67PGrgFWUHibbjqMvuMaDkRJTgkX",  # USDH (Hubble)
    "2b1kV6DkPAnxd5ixfnxCpjxmKwqjjaYmCZfHsFu24GXo", # PYUSD (PayPal)
    "7kbnvuGBxxj8AG9qp8Scn56muWGaRaFqxg1FsRp3PaFT", # UXD
    "Fm9rHUTF5v3hwMLbStjZXqNBBoZyGriQaFM6sTFz3K8A", # USDD
    "AZsHEMXd36Bj1EMNXhowJajpUXzrKcK57wW4ZGXVa7yR", # BUSD (Wormhole)
    "JuprjznTrTSp2UFa3ZBUFgwdAmtZCq4MQCwysN55USD",  # USD3/JUSD stablecoin
    # ── Major Protocol / Large-Cap Tokens ────────────────────────────────────
    "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263",  # BONK (major meme)
    "4k3Dyjzvzp8eMZWUXbBCjEvwSkkk59S5iCNLY3QrkX6R",  # RAY (Raydium governance)
    "JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN",  # JUP (Jupiter governance/routing)
    "orcaEKTdK7LKz57vaAYr624Dp4QuCcrKQhAVmFnvBbQ",  # ORCA (Orca DEX router)
    "orcaEKTdK7LKz57vaAYr9QeNsVEPfiu6QeMU1kektZE",  # ORCA (alt address)
    "METvsvVRapdj9cFLzq4Tr43xK4tAjQfwX76z3n6mWQL",  # MET (Meteora, large-cap DeFi)
    "27G8MtK7VtTcCHkpASjSDdkWWYfoqT6ggEuKidVJidD4", # large-cap DeFi token (identified in audit)
}


def print_banner() -> None:
    print("\n" + "=" * 60)
    print("  PROJECT ALPHA — Solana Smart Money Scanner v0.1")
    print(f"  Scan time: {datetime.now(tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print(f"  Window: last {SCAN_WINDOW_SECONDS // 60} minutes")
    print(f"  Helius API: {'CONFIGURED' if HELIUS_API_KEY else 'NOT SET (mock mode)'}")
    print("=" * 60 + "\n")


def print_findings(findings: list[dict]) -> None:
    if not findings:
        print("\n[+] No swap events detected in the last 30 minutes.")
        print("    (No API key = mock/empty mode. Set HELIUS_API_KEY in .env for live data.)\n")
        return

    print(f"\n[+] Found {len(findings)} swap event(s):\n")
    for i, f in enumerate(findings, 1):
        print(f"  [{i}] Wallet: {f['wallet_label']} ({f['wallet_address'][:8]}...)")
        print(f"      Time:   {f['timestamp_human']}")
        print(f"      Trade:  {f['input_amount']:.4f} {f['input_mint'][:8]} → "
              f"{f['output_amount']:.4f} {f['output_mint'][:8]}")
        print(f"      Sig:    {f['signature']}")
        print()


# ---------------------------------------------------------------------------
# Signal generation helpers
# ---------------------------------------------------------------------------

def validate_token_address(token: str) -> bool:
    """BUG FIX 2: Reject truncated token addresses (< 32 chars)."""
    if len(token) < MIN_TOKEN_ADDR_LEN:
        logger.warning(
            "Skipping signal — truncated token address ({} chars): {}", len(token), token
        )
        return False
    return True


def load_recent_signal_pairs(hours: int = 1) -> set[tuple[str, str]]:
    """
    BUG FIX 1: Load (wallet_label, token) pairs already logged in the last N hours.
    Used to skip duplicate MEDIUM signals within one scan session.
    """
    seen: set[tuple[str, str]] = set()
    if not os.path.exists(SIGNALS_PATH):
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
                    seen.add((wallet, token))
    except OSError:
        pass
    return seen


def append_signal(signal: dict) -> None:
    """Append one signal record to signals.jsonl."""
    with open(SIGNALS_PATH, "a") as f:
        f.write(json.dumps(signal) + "\n")


def generate_signals(findings: list[dict]) -> tuple[int, int]:
    """
    Convert raw scan findings into HIGH/MEDIUM signals and write to signals.jsonl.

    Bug fixes applied:
      BUG FIX 1 — SIGNAL DEDUP: Skip MEDIUM (wallet, token) pairs already logged
                  in the last 1 hour. Checked against signals.jsonl on disk plus
                  an in-memory set updated during this run.
      BUG FIX 2 — ADDRESS VALIDATION: Skip any signal whose token address is
                  shorter than 32 characters (truncated Solana base58).
      BUG FIX 3 — CONVERGENCE DEDUP: Deduplicate wallet labels via set() before
                  computing wallet_count so a single wallet appearing in multiple
                  transactions counts as one unique buyer, not many.
      BUG FIX 4 — HIGH SIGNAL DEDUP: Skip HIGH/CONVERGENCE signals for (token)
                  already logged in the last 2 hours. Uses ("CONVERGENCE", token)
                  pair in the same recent_pairs set. Prevents the same convergence
                  from firing on every 30-min cycle.

    Returns:
        (high_count, medium_count) — number of signals written this cycle.
    """
    now_ts = datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # BUG FIX 1 + 4: Load pairs already logged in the last 2 hours (covers HIGH too)
    recent_pairs = load_recent_signal_pairs(hours=2)

    # Group valid findings by token
    token_buyers: dict[str, list[str]] = {}   # token → [wallet_label, ...]
    token_amounts: dict[str, float] = {}      # token → total input_amount (SOL equiv)

    for f in findings:
        token = f.get("output_mint", "")
        if not token or token == "unknown":
            continue
        if token in BASE_TOKENS:
            continue
        # BUG FIX 2: validate address length
        if not validate_token_address(token):
            continue

        wallet_label = f.get("wallet_label", "unknown")
        token_buyers.setdefault(token, []).append(wallet_label)
        token_amounts[token] = token_amounts.get(token, 0) + f.get("input_amount", 0)

    high_count = 0
    medium_count = 0

    for token, wallets in token_buyers.items():
        # BUG FIX 3: deduplicate wallet list before counting
        unique_wallets = sorted(set(wallets))
        wallet_count = len(unique_wallets)
        amount = round(token_amounts.get(token, 0), 4)

        if wallet_count >= 2:
            # BUG FIX 4: skip HIGH if same convergence already logged in last 2 hours
            if ("CONVERGENCE", token) in recent_pairs:
                logger.debug(
                    "Skipping duplicate HIGH convergence: {}...", token[:16]
                )
                continue
            # HIGH convergence signal — multiple distinct wallets buying same token
            signal = {
                "timestamp": now_ts,
                "wallet": "CONVERGENCE",
                "signal": "HIGH",
                "token": token,
                "wallet_count": wallet_count,
                "wallets": unique_wallets,
                "amount_sol": amount,
                "amount_usd": 0,
                "detail": f"CONVERGENCE: {wallet_count} wallets — {' '.join(unique_wallets)}",
            }
            append_signal(signal)
            high_count += 1
            recent_pairs.add(("CONVERGENCE", token))  # Track in-memory for this run
            logger.info(
                "HIGH signal: {}... — {} unique wallets ({})",
                token[:16],
                wallet_count,
                ", ".join(unique_wallets),
            )
        else:
            # MEDIUM signal — single wallet buy
            wallet_label = unique_wallets[0]
            # BUG FIX 1: skip if already logged in last 1 hour
            if (wallet_label, token) in recent_pairs:
                logger.debug(
                    "Skipping duplicate MEDIUM: {} / {}...", wallet_label, token[:16]
                )
                continue
            signal = {
                "timestamp": now_ts,
                "wallet": wallet_label,
                "signal": "MEDIUM",
                "token": token,
                "amount_sol": amount,
                "amount_usd": 0,
                "detail": f"single wallet buy: {amount:.4f} SOL equiv",
            }
            append_signal(signal)
            medium_count += 1
            # Track in-memory so subsequent findings in this run are also deduped
            recent_pairs.add((wallet_label, token))

    return high_count, medium_count


# ---------------------------------------------------------------------------
# Main scan loop
# ---------------------------------------------------------------------------

async def run_scan() -> list[dict]:
    """Execute one full scan cycle, write signals, and return findings."""
    print_banner()

    logger.info("Starting scan cycle...")
    findings = await scan_wallets()

    print_findings(findings)

    # Generate and persist signals
    if findings:
        high, medium = generate_signals(findings)
        logger.info("Signals written: {} HIGH, {} MEDIUM", high, medium)
        print(f"\nSignals logged: {high} HIGH, {medium} MEDIUM → {SIGNALS_PATH}")
    else:
        high, medium = 0, 0

    # Summary
    print(f"\nScan complete. {len(findings)} swap event(s) found.")
    if findings:
        print("\nNext steps (Phase 2):")
        print("  - Cross-reference output mints against known token list")
        print("  - Run rug safety filter (getAsset authority checks)")
        print("  - Queue copy-trade execution via Jupiter V6")

    return findings


if __name__ == "__main__":
    results = asyncio.run(run_scan())
    # Exit 0 even if no findings — empty scan is valid
    sys.exit(0)
