"""
Helius API key rotation manager.

Manages a pool of Helius API keys, rotating when one hits its monthly quota
limit. State is persisted to helius_key_state.json so rotation survives
process restarts.

Monthly quota auto-resets on the 1st of each month (Helius billing cycle).

Usage:
    from helius_rotator import get_helius_key, get_helius_rpc_url, mark_key_exhausted, rotation_status

    key = get_helius_key()       # Returns first available key, or None if all exhausted
    rpc = get_helius_rpc_url()   # Returns full RPC URL with active key
    mark_key_exhausted(key)      # Called when a key returns quota-exceeded 429
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

# Load .env from the bot directory (same dir as this file)
load_dotenv(Path(__file__).parent / ".env")

# State file lives in the alpha project root (outside bot/) for cross-script access
STATE_PATH = Path(__file__).parent.parent / "helius_key_state.json"

HELIUS_API_BASE = "https://api.helius.xyz/v0"
HELIUS_RPC_BASE = "https://mainnet.helius-rpc.com"
HELIUS_PUBLIC_RPC = "https://api.mainnet-beta.solana.com"

# Phrases in 429 response body that indicate monthly quota exhaustion
# (vs transient rate limiting which should just be retried later)
QUOTA_EXHAUSTION_PHRASES = [
    "max usage reached",
    "monthly quota",
    "quota exceeded",
    "plan limit",
    "upgrade your plan",
]


def _load_all_keys() -> list[str]:
    """Load all configured Helius keys from environment in priority order."""
    keys: list[str] = []
    # Primary key (backward compat)
    primary = os.environ.get("HELIUS_API_KEY", "").strip()
    if primary:
        keys.append(primary)
    # Numbered keys 1–10
    for i in range(1, 11):
        k = os.environ.get(f"HELIUS_API_KEY_{i}", "").strip()
        if k and k not in keys:
            keys.append(k)
    return keys


def _current_month() -> str:
    """Return current year-month string e.g. '2026-03'."""
    return datetime.now(timezone.utc).strftime("%Y-%m")


def _load_state() -> dict:
    """Load rotation state from disk."""
    if STATE_PATH.exists():
        try:
            with open(STATE_PATH) as f:
                return json.load(f)
        except Exception:
            pass
    return {"exhausted_keys": [], "month": _current_month()}


def _save_state(state: dict) -> None:
    """Persist rotation state to disk."""
    try:
        with open(STATE_PATH, "w") as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        print(f"[helius_rotator] Failed to save state: {e}")


def _get_fresh_state() -> dict:
    """Return state, auto-resetting if month has changed."""
    state = _load_state()
    if state.get("month") != _current_month():
        state = {"exhausted_keys": [], "month": _current_month()}
        _save_state(state)
    return state


def get_helius_key() -> str | None:
    """
    Return the first available (non-exhausted) Helius API key.
    Auto-resets exhausted list if the month has changed (quota reset).
    Returns None if all keys are exhausted.
    """
    state = _get_fresh_state()
    exhausted = set(state.get("exhausted_keys", []))
    for key in _load_all_keys():
        if key not in exhausted:
            return key
    return None


def get_helius_rpc_url() -> str:
    """Return Helius RPC URL using the current active key, or public fallback."""
    key = get_helius_key()
    if key:
        return f"{HELIUS_RPC_BASE}/?api-key={key}"
    return HELIUS_PUBLIC_RPC


def mark_key_exhausted(key: str) -> None:
    """
    Mark a key as quota-exhausted for this month.
    The key will be skipped until the billing month rolls over.
    """
    state = _get_fresh_state()
    exhausted: list[str] = state.get("exhausted_keys", [])
    if key not in exhausted:
        exhausted.append(key)
        state["exhausted_keys"] = exhausted
        _save_state(state)
        all_keys = _load_all_keys()
        remaining = len(all_keys) - len(exhausted)
        print(
            f"[helius_rotator] Key {key[:8]}... quota exhausted."
            f" {remaining}/{len(all_keys)} key(s) available."
        )


def is_quota_exhaustion(response_text: str) -> bool:
    """Check if a 429 response body indicates monthly quota exhaustion."""
    lower = response_text.lower()
    return any(phrase in lower for phrase in QUOTA_EXHAUSTION_PHRASES)


def rotation_status() -> dict:
    """Return current rotation status dict for logging/monitoring."""
    state = _get_fresh_state()
    all_keys = _load_all_keys()
    exhausted = set(state.get("exhausted_keys", []))
    available = [k for k in all_keys if k not in exhausted]
    return {
        "total_keys": len(all_keys),
        "exhausted": len(exhausted),
        "available": len(available),
        "month": state.get("month"),
        "active_key_prefix": available[0][:8] + "..." if available else None,
        "pipeline_status": "ACTIVE" if available else "ALL_KEYS_EXHAUSTED",
    }
