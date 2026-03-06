"""
Signal Publisher — Whale Convergence to Telegram Channel

Formats whale convergence signals for public consumption and posts
them to a Telegram channel via the broadcast system. Includes a
tip wallet address in every post for monetization.

Usage:
    python signal_publisher.py                   # Post any new signals since last run
    python signal_publisher.py --dry-run         # Print without posting
    python signal_publisher.py --test            # Post a single test message

Configuration (environment variables or .env):
    SIGNAL_TIP_WALLET     Solana address to receive tips
    TELEGRAM_BOT_TOKEN    Bot token from @BotFather
    TELEGRAM_CHANNEL      Channel username e.g. @ottosignals

State:
    .publisher_state.json  Tracks last-published signal_ts to avoid duplicates
"""

import argparse
import asyncio
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Add project root to path
ROOT = Path(__file__).resolve().parents[3]  # ~/otto
sys.path.insert(0, str(ROOT))

SIGNALS_DIR = Path(__file__).parent
STATE_FILE = SIGNALS_DIR / ".publisher_state.json"
SIGNALS_JSONL = SIGNALS_DIR.parent / "signals.jsonl"

# Load env from ~/memory/.env or environment
ENV_PATH = Path.home() / "memory" / ".env"


def load_env():
    """Load .env file into os.environ if not already set."""
    if not ENV_PATH.exists():
        return
    for line in ENV_PATH.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k, v = k.strip(), v.strip().strip('"').strip("'")
        if k not in os.environ:
            os.environ[k] = v


load_env()

TIP_WALLET = os.environ.get("SIGNAL_TIP_WALLET", "CONFIGURE_TIP_WALLET_ADDRESS")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHANNEL = os.environ.get("TELEGRAM_CHANNEL", "")

# Signal filter thresholds — only publish high-confidence signals
MIN_WALLET_COUNT = 3        # Minimum unique whales buying same token
MIN_TOTAL_USD = 1_000       # Minimum aggregate buy volume (USD)
CONFIDENCE_LEVELS = {"ULTRA", "HIGH"}  # Only these levels go public

# How many hours back to look for new signals
LOOKBACK_HOURS = 2


def load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {"last_published_ts": 0, "total_published": 0}


def save_state(state: dict):
    STATE_FILE.write_text(json.dumps(state, indent=2))


def shorten_address(addr: str) -> str:
    """5...5 format for readability."""
    if len(addr) < 12:
        return addr
    return f"{addr[:5]}...{addr[-5:]}"


def format_signal_post(signal: dict) -> str:
    """
    Format a convergence signal into a clean, readable Telegram post.
    Includes: token, whale count, confidence, tip wallet.
    """
    token = signal["token"]
    wallets = signal["wallet_count"]
    confidence = signal["confidence"]
    total_usd = signal.get("total_buy_usd", 0)
    signal_time = signal.get("signal_time", "")
    window = signal.get("window_minutes", 30)

    # Confidence indicators
    if confidence == "ULTRA":
        conf_tag = "ULTRA [4+ whales]"
        urgency = "Multiple elite wallets moving in sync."
    else:
        conf_tag = "HIGH [3+ whales]"
        urgency = "Multiple tracked wallets converging."

    # Format USD volume
    if total_usd >= 1_000_000:
        vol_str = f"${total_usd/1_000_000:.1f}M"
    elif total_usd >= 1_000:
        vol_str = f"${total_usd/1_000:.0f}K"
    else:
        vol_str = f"${total_usd:.0f}"

    # Time formatting
    try:
        dt = datetime.fromisoformat(signal_time.replace("Z", "+00:00"))
        time_str = dt.strftime("%H:%M UTC")
    except Exception:
        time_str = "recent"

    post = f"""Whale Convergence Signal — {conf_tag}

Token: <code>{token}</code>
Whales: {wallets} wallets within {window}min
Volume: {vol_str} aggregate
Detected: {time_str}

{urgency}

Dexscreener: https://dexscreener.com/solana/{token}
Birdeye: https://birdeye.so/token/{token}?chain=solana

Not financial advice. Track smart money, manage your own risk.

Tip wallet (SOL/USDC): <code>{TIP_WALLET}</code>
If this signal made you money, a tip keeps Otto running."""

    return post


def get_new_signals(last_ts: int) -> list[dict]:
    """
    Read signals.jsonl, run convergence detection, return signals
    newer than last_ts that pass quality filters.
    """
    # Import signal generator inline to avoid circular issues
    sys.path.insert(0, str(SIGNALS_DIR.parent))
    from signals.whale_convergence import load_buy_signals, detect_convergence

    records = load_buy_signals()
    all_signals = detect_convergence(records)

    new_signals = []
    for s in all_signals:
        if s["signal_ts"] <= last_ts:
            continue
        if s["wallet_count"] < MIN_WALLET_COUNT:
            continue
        if s.get("total_buy_usd", 0) < MIN_TOTAL_USD:
            continue
        if s.get("confidence") not in CONFIDENCE_LEVELS:
            continue
        new_signals.append(s)

    return sorted(new_signals, key=lambda s: s["signal_ts"])


async def post_to_telegram(text: str) -> bool:
    """Post message to Telegram channel. Returns True on success."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHANNEL:
        print("[publisher] ERROR: TELEGRAM_BOT_TOKEN or TELEGRAM_CHANNEL not configured")
        return False

    import httpx
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHANNEL,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.post(url, json=payload)
        data = r.json()
        if r.status_code == 200 and data.get("ok"):
            msg_id = data.get("result", {}).get("message_id")
            chan = TELEGRAM_CHANNEL.lstrip("@")
            print(f"[publisher] Posted: https://t.me/{chan}/{msg_id}")
            return True
        else:
            print(f"[publisher] Telegram error: {data.get('description', r.status_code)}")
            return False
    except Exception as e:
        print(f"[publisher] Exception: {e}")
        return False


async def run(dry_run: bool = False, test_mode: bool = False):
    state = load_state()

    if test_mode:
        test_signal = {
            "token": "ExampleToken1111111111111111111111111111111",
            "wallet_count": 4,
            "confidence": "ULTRA",
            "total_buy_usd": 125_000,
            "signal_time": datetime.now(timezone.utc).isoformat(),
            "window_minutes": 30,
        }
        post = format_signal_post(test_signal)
        print("=== TEST POST ===")
        print(post)
        print("================")
        if not dry_run:
            success = await post_to_telegram(post)
            print(f"[publisher] Test post {'succeeded' if success else 'FAILED'}")
        return

    new_signals = get_new_signals(state["last_published_ts"])
    print(f"[publisher] Found {len(new_signals)} new publishable signals")

    if not new_signals:
        print("[publisher] Nothing to publish")
        return

    published = 0
    for signal in new_signals:
        post = format_signal_post(signal)
        print(f"[publisher] Signal: {signal['token'][:16]}... | {signal['confidence']} | wallets={signal['wallet_count']}")

        if dry_run:
            print("--- DRY RUN ---")
            print(post)
            print("---------------")
            published += 1
        else:
            success = await post_to_telegram(post)
            if success:
                published += 1
                # Update state to track this signal
                state["last_published_ts"] = max(state["last_published_ts"], signal["signal_ts"])
                state["total_published"] = state.get("total_published", 0) + 1
                save_state(state)
            # Small delay between posts to avoid rate limits
            await asyncio.sleep(1)

    print(f"[publisher] Done. Published {published}/{len(new_signals)} signals.")
    if not dry_run and published > 0:
        print(f"[publisher] Total published all-time: {state.get('total_published', 0)}")


def main():
    parser = argparse.ArgumentParser(description="Otto Signal Publisher")
    parser.add_argument("--dry-run", action="store_true", help="Print posts without sending")
    parser.add_argument("--test", action="store_true", help="Post a single test message")
    args = parser.parse_args()

    asyncio.run(run(dry_run=args.dry_run, test_mode=args.test))


if __name__ == "__main__":
    main()
