"""
Wallet tracker for Project Alpha copy-trading strategy.

Loads smart money wallets from wallets.json, fetches recent transactions,
filters to the last 30 minutes, and detects swap/trade events.
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from typing import Any

from loguru import logger

from config import WALLETS_JSON_PATH, SCAN_WINDOW_SECONDS
from helius_client import get_wallet_transactions


def load_wallets(path: str = WALLETS_JSON_PATH) -> list[dict[str, Any]]:
    """Load wallet definitions from JSON file."""
    try:
        with open(path) as f:
            data = json.load(f)
        wallets = data.get("wallets", [])
        logger.info("Loaded {} wallets from {}", len(wallets), path)
        return wallets
    except FileNotFoundError:
        logger.error("wallets.json not found at {}", path)
        return []
    except json.JSONDecodeError as e:
        logger.error("Invalid JSON in wallets.json: {}", e)
        return []


def is_within_window(tx: dict[str, Any], window_seconds: int = SCAN_WINDOW_SECONDS) -> bool:
    """
    Return True if the transaction timestamp falls within the last N seconds.
    Helius enhanced txns have a top-level 'timestamp' field (Unix epoch, seconds).
    """
    ts = tx.get("timestamp")
    if ts is None:
        return False
    now = int(time.time())
    return (now - ts) <= window_seconds


def is_swap_event(tx: dict[str, Any]) -> bool:
    """
    Detect if a transaction is a DEX swap.
    Helius enhanced transactions include a `type` field.
    """
    tx_type = tx.get("type", "")
    # Helius type values: SWAP, JUPITER_SWAP, RAYDIUM_SWAP, etc.
    return "SWAP" in tx_type.upper()


def extract_swap_details(tx: dict[str, Any]) -> dict[str, Any] | None:
    """
    Extract relevant swap details from a Helius enhanced transaction.
    Returns a simplified swap event dict or None if not parseable.
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

        # Determine input asset
        if native_input:
            input_mint = "SOL"
            input_amount = float(native_input.get("amount", 0)) / 1e9  # lamports → SOL
        elif token_inputs:
            input_mint = token_inputs[0].get("mint", "unknown")
            input_amount = float(token_inputs[0].get("rawTokenAmount", {}).get("tokenAmount", 0))
        else:
            input_mint = "unknown"
            input_amount = 0.0

        # Determine output asset
        if native_output:
            output_mint = "SOL"
            output_amount = float(native_output.get("amount", 0)) / 1e9
        elif token_outputs:
            output_mint = token_outputs[0].get("mint", "unknown")
            output_amount = float(token_outputs[0].get("rawTokenAmount", {}).get("tokenAmount", 0))
        else:
            output_mint = "unknown"
            output_amount = 0.0

        return {
            "signature": tx.get("signature", "")[:20] + "...",
            "timestamp": tx.get("timestamp"),
            "timestamp_human": datetime.fromtimestamp(
                tx.get("timestamp", 0), tz=timezone.utc
            ).strftime("%Y-%m-%d %H:%M:%S UTC"),
            "input_mint": input_mint,
            "input_amount": input_amount,
            "output_mint": output_mint,
            "output_amount": output_amount,
            "fee": tx.get("fee", 0) / 1e9,
        }
    except Exception as e:
        logger.warning("Could not parse swap details: {}", e)
        return None


async def scan_wallets() -> list[dict[str, Any]]:
    """
    Main scan routine:
    1. Load wallets
    2. Fetch recent transactions for each
    3. Filter to last 30 minutes
    4. Detect swap events
    5. Return list of swap findings
    """
    wallets = load_wallets()
    if not wallets:
        logger.warning("No wallets to scan")
        return []

    findings: list[dict[str, Any]] = []

    for wallet in wallets:
        address = wallet.get("address", "")
        label = wallet.get("label", address[:8])

        if not address:
            continue

        logger.info("Scanning wallet: {} ({})", label, address[:8])
        txns = await get_wallet_transactions(address, limit=20)

        # Filter to recent window
        recent = [tx for tx in txns if is_within_window(tx)]
        swaps = [tx for tx in recent if is_swap_event(tx)]

        logger.info(
            "  → {} total txns, {} in last 30min, {} swaps",
            len(txns), len(recent), len(swaps)
        )

        for tx in swaps:
            details = extract_swap_details(tx)
            if details:
                findings.append({
                    "wallet_label": label,
                    "wallet_address": address,
                    **details,
                })

    return findings
