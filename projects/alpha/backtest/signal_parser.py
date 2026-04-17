"""
Signal parser for signals.jsonl
Extracts structured convergence signals for backtesting.
"""

import json
from datetime import datetime, timezone
from typing import Optional
from data_fetcher import BASE_TOKENS

SIGNALS_PATH = "/home/web3relic/otto/projects/alpha/signals.jsonl"


def _parse_ts(ts_str: str) -> Optional[int]:
    """Parse ISO timestamp string to Unix int."""
    try:
        # Handle both UTC (Z) and offset formats
        ts_str = ts_str.replace("Z", "+00:00")
        dt = datetime.fromisoformat(ts_str)
        return int(dt.timestamp())
    except Exception:
        return None


def load_raw_signals() -> list[dict]:
    """Load all lines from signals.jsonl."""
    records = []
    with open(SIGNALS_PATH) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return records


def extract_convergence_signals(min_wallets: int = 2) -> list[dict]:
    """
    Extract HIGH convergence signals where min_wallets tracked wallets
    bought the same token within 30 minutes.

    Returns list of:
    {
        "signal_ts": int (unix),
        "token": str,
        "wallet_count": int,
        "wallets": list[str],
        "raw": dict,
    }
    """
    records = load_raw_signals()
    signals = []
    seen = set()  # deduplicate (token, approx_ts)

    for r in records:
        token = r.get("token")
        sig = r.get("signal", "")

        # Skip if no token or not a convergence signal
        if not token or sig != "HIGH":
            continue

        # Skip base tokens (USDC, USDT, SOL, etc.)
        if token in BASE_TOKENS:
            continue

        ts_str = r.get("timestamp")
        if not ts_str:
            continue
        ts = _parse_ts(ts_str)
        if not ts:
            continue

        # Determine wallet count
        wallet_count = 0
        wallets = []

        if "buyer_count" in r:
            wallet_count = int(r["buyer_count"])
        elif "wallet_count" in r:
            wallet_count = int(r["wallet_count"])
        elif r.get("wallet") in ("MULTI", "CONVERGENCE"):
            # Parse from detail string e.g. "CONVERGENCE: 2 wallets — SM_1 SM_3"
            detail = r.get("detail", "")
            for word in detail.split():
                if word.isdigit():
                    wallet_count = int(word)
                    break
            # Extract wallet labels
            if "—" in detail:
                wallet_part = detail.split("—", 1)[1].strip()
                wallets = list(set(wallet_part.split()))
            elif "wallets buying:" in detail:
                wallet_part = detail.split("wallets buying:", 1)[1].strip()
                wallets = wallet_part.split()
        elif "wallets" in r and isinstance(r["wallets"], str):
            wallets = [w.strip() for w in r["wallets"].replace(",", " ").split() if w.strip()]
            wallet_count = len(set(wallets))

        if wallet_count < min_wallets:
            continue

        # Deduplicate: same token within 2-hour window
        dedup_key = (token, ts // 7200)
        if dedup_key in seen:
            continue
        seen.add(dedup_key)

        signals.append({
            "signal_ts": ts,
            "signal_time": datetime.fromtimestamp(ts, tz=timezone.utc).isoformat(),
            "token": token,
            "wallet_count": wallet_count,
            "wallets": wallets,
            "raw": r,
        })

    signals.sort(key=lambda s: s["signal_ts"])
    return signals


def extract_medium_signals(min_wallets: int = 1) -> list[dict]:
    """
    Extract MEDIUM individual wallet signals for single-wallet copy strategy analysis.
    """
    records = load_raw_signals()
    signals = []

    for r in records:
        token = r.get("token")
        sig = r.get("signal", "")

        if not token or sig != "MEDIUM":
            continue
        if token in BASE_TOKENS or len(token) < 10:
            continue

        ts_str = r.get("timestamp")
        if not ts_str:
            continue
        ts = _parse_ts(ts_str)
        if not ts:
            continue

        wallet = r.get("wallet") or r.get("label", "unknown")
        amount_usd = r.get("amount_usd") or r.get("amount_usd_est") or 0
        try:
            amount_usd = float(str(amount_usd).replace("$", "").strip() or 0)
        except Exception:
            amount_usd = 0

        signals.append({
            "signal_ts": ts,
            "signal_time": datetime.fromtimestamp(ts, tz=timezone.utc).isoformat(),
            "token": token,
            "wallet": wallet,
            "amount_usd": amount_usd,
            "raw": r,
        })

    return signals


if __name__ == "__main__":
    conv = extract_convergence_signals()
    print(f"Convergence signals (HIGH, 2+ wallets): {len(conv)}")
    for s in conv:
        print(f"  {s['signal_time']} | token={s['token'][:16]}... | wallets={s['wallet_count']}")

    med = extract_medium_signals()
    print(f"\nMedium signals (individual wallets): {len(med)}")
    # Group by wallet
    by_wallet = {}
    for s in med:
        w = s["wallet"]
        by_wallet.setdefault(w, []).append(s)
    for w, sigs in sorted(by_wallet.items()):
        print(f"  {w}: {len(sigs)} signals")
