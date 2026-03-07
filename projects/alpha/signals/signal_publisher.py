"""
Signal Publisher — Whale Convergence to Telegram Channel

Phase 1 upgrades (2026-03-07):
- TP/SL exit system: TP1=+10%, TP2=+25%, TP3=+50%, SL=-15%
- Quality filters: market cap, liquidity, volume spike, price action, token age
- Cornix-compatible signal format with token name, prices, explicit TP/SL
- Daily signal limit: max 3 per day (quality over quantity)
- Performance tracking: feeds signal_performance.py

Usage:
    python signal_publisher.py                   # Post any new signals since last run
    python signal_publisher.py --dry-run         # Print without posting
    python signal_publisher.py --test            # Post a single test message
    python signal_publisher.py --no-filters      # Skip quality filters (debug only)
    python signal_publisher.py --check-perf      # Check open signal performance

Configuration (environment variables or ~/memory/.env):
    SIGNAL_TIP_WALLET     Solana address to receive tips
    TELEGRAM_BOT_TOKEN    Bot token from @BotFather
    TELEGRAM_CHANNEL      Channel username e.g. @OttoSignals

State:
    .publisher_state.json  Tracks last-published signal_ts, daily count, etc.
"""

import argparse
import asyncio
import json
import os
import sys
import time
from datetime import datetime, timezone, date
from pathlib import Path

# Add project root to path
ROOT = Path(__file__).resolve().parents[3]  # ~/otto
sys.path.insert(0, str(ROOT))

SIGNALS_DIR = Path(__file__).parent
STATE_FILE = SIGNALS_DIR / ".publisher_state.json"
SIGNALS_JSONL = SIGNALS_DIR.parent / "signals.jsonl"
PERF_FILE = SIGNALS_DIR / "signal_performance.jsonl"

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

# --- Signal detection thresholds (kept from original) ---
MIN_WALLET_COUNT = 3
MIN_TOTAL_USD = 1_000
CONFIDENCE_LEVELS = {"ULTRA", "HIGH"}
LOOKBACK_HOURS = 2

# --- TP/SL levels (Phase 1 fix: replace 4h time exits) ---
TP1_PCT = 0.10   # +10%
TP2_PCT = 0.25   # +25%
TP3_PCT = 0.50   # +50%
SL_PCT  = 0.15   # -15% (stored as positive, applied as negative)

# --- Quality filter thresholds ---
FILTER_MIN_MARKET_CAP   = 100_000    # $100K minimum market cap
FILTER_MAX_MARKET_CAP   = 3_000_000  # $3M maximum market cap
FILTER_MIN_LIQUIDITY    = 100_000    # $100K minimum pool liquidity
FILTER_VOLUME_SPIKE_MIN = 3.0        # h1 vol must be >= 3x (h24/24) average
FILTER_MAX_PUMP_6H      = 25.0       # Skip if price already up >25% in 6h
FILTER_MIN_TOKEN_AGE_DAYS = 3        # Token must be > 3 days old

# --- Quality gate: max signals per day ---
MAX_SIGNALS_PER_DAY = 3


# ---------------------------------------------------------------------------
# State management
# ---------------------------------------------------------------------------

def load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {
        "last_published_ts": 0,
        "total_published": 0,
        "published_today": 0,
        "today_date": str(date.today()),
    }


def save_state(state: dict):
    STATE_FILE.write_text(json.dumps(state, indent=2))


def get_daily_count(state: dict) -> int:
    """Return today's published signal count, resetting if day changed."""
    today_str = str(date.today())
    if state.get("today_date") != today_str:
        state["published_today"] = 0
        state["today_date"] = today_str
    return state.get("published_today", 0)


# ---------------------------------------------------------------------------
# DexScreener API
# ---------------------------------------------------------------------------

async def fetch_dex_data(token_address: str) -> dict | None:
    """
    Fetch token data from DexScreener free API.
    Returns the highest-liquidity Solana pair, or None on failure.
    """
    import httpx
    url = f"https://api.dexscreener.com/latest/dex/tokens/{token_address}"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(url)
        if r.status_code != 200:
            print(f"[publisher] DexScreener {r.status_code} for {token_address[:16]}...")
            return None
        data = r.json()
        pairs = data.get("pairs") or []
        # Filter to Solana pairs only, pick highest liquidity
        solana_pairs = [p for p in pairs if p.get("chainId") == "solana"]
        if not solana_pairs:
            return None
        best = max(solana_pairs, key=lambda p: p.get("liquidity", {}).get("usd", 0))
        return best
    except Exception as e:
        print(f"[publisher] DexScreener error for {token_address[:16]}...: {e}")
        return None


# ---------------------------------------------------------------------------
# Quality filters
# ---------------------------------------------------------------------------

def apply_quality_filters(signal: dict, dex_data: dict) -> tuple[bool, str]:
    """
    Run all quality filters against a signal + DexScreener data.
    Returns (passes: bool, reason: str).
    'reason' explains why it passed or failed.
    """
    token_short = signal["token"][:16]

    # --- Market cap filter: $100K - $3M ---
    mcap = dex_data.get("marketCap") or dex_data.get("fdv") or 0
    if mcap < FILTER_MIN_MARKET_CAP:
        return False, f"mcap too low: ${mcap:,.0f} < ${FILTER_MIN_MARKET_CAP:,}"
    if mcap > FILTER_MAX_MARKET_CAP:
        return False, f"mcap too high: ${mcap:,.0f} > ${FILTER_MAX_MARKET_CAP:,}"

    # --- Liquidity floor: >= $100K ---
    liq = dex_data.get("liquidity", {}).get("usd", 0) or 0
    if liq < FILTER_MIN_LIQUIDITY:
        return False, f"liquidity too low: ${liq:,.0f} < ${FILTER_MIN_LIQUIDITY:,}"

    # --- Volume spike: h1 vol >= 3x hourly average (h24/24) ---
    vol = dex_data.get("volume", {})
    h1_vol  = vol.get("h1", 0) or 0
    h24_vol = vol.get("h24", 0) or 0
    if h24_vol > 0:
        avg_hourly = h24_vol / 24
        spike_ratio = h1_vol / avg_hourly if avg_hourly > 0 else 0
        if spike_ratio < FILTER_VOLUME_SPIKE_MIN:
            return False, f"volume spike too low: {spike_ratio:.1f}x < {FILTER_VOLUME_SPIKE_MIN}x (h1=${h1_vol:,.0f}, avg=${avg_hourly:,.0f})"

    # --- Already-pumped filter: skip if >25% up in 6h ---
    price_change = dex_data.get("priceChange", {})
    change_6h = price_change.get("h6", 0) or 0
    if change_6h > FILTER_MAX_PUMP_6H:
        return False, f"already pumped: +{change_6h:.1f}% in 6h > {FILTER_MAX_PUMP_6H}%"

    # --- Token age: > 3 days ---
    pair_created_ms = dex_data.get("pairCreatedAt", 0) or 0
    if pair_created_ms > 0:
        age_days = (time.time() * 1000 - pair_created_ms) / (1000 * 86400)
        if age_days < FILTER_MIN_TOKEN_AGE_DAYS:
            return False, f"token too new: {age_days:.1f} days < {FILTER_MIN_TOKEN_AGE_DAYS} days"

    return True, "all filters passed"


# ---------------------------------------------------------------------------
# TP/SL calculation
# ---------------------------------------------------------------------------

def compute_tp_sl(entry_price: float) -> dict:
    """
    Given entry price, compute TP1/TP2/TP3 and SL prices.
    After TP1 hit: move stop to breakeven (entry price).
    """
    return {
        "entry": entry_price,
        "tp1": entry_price * (1 + TP1_PCT),
        "tp2": entry_price * (1 + TP2_PCT),
        "tp3": entry_price * (1 + TP3_PCT),
        "sl":  entry_price * (1 - SL_PCT),
        "be":  entry_price,  # Breakeven after TP1 hit
    }


# ---------------------------------------------------------------------------
# Signal post formatting (Cornix-compatible)
# ---------------------------------------------------------------------------

def shorten_address(addr: str) -> str:
    """5...5 format for readability."""
    if len(addr) < 12:
        return addr
    return f"{addr[:5]}...{addr[-5:]}"


def format_usd(value: float) -> str:
    """Format USD value compactly."""
    if value >= 1_000_000:
        return f"${value/1_000_000:.2f}M"
    elif value >= 1_000:
        return f"${value/1_000:.1f}K"
    else:
        return f"${value:.0f}"


def format_price(price: float) -> str:
    """Format token price with appropriate decimal places."""
    if price >= 1:
        return f"${price:.4f}"
    elif price >= 0.001:
        return f"${price:.6f}"
    else:
        return f"${price:.8f}"


def format_signal_post(signal: dict, dex_data: dict | None, tp_sl: dict | None) -> str:
    """
    Format a convergence signal into a Cornix-compatible Telegram post.
    Includes token name, market cap, liquidity, volume spike, TP/SL prices.
    """
    token = signal["token"]
    wallets = signal["wallet_count"]
    confidence = signal["confidence"]
    total_usd = signal.get("total_buy_usd", 0)
    signal_time = signal.get("signal_time", "")
    window = signal.get("window_minutes", 30)

    # Time formatting
    try:
        dt = datetime.fromisoformat(signal_time.replace("Z", "+00:00"))
        time_str = dt.strftime("%H:%M UTC")
    except Exception:
        time_str = "recent"

    # Confidence tag
    conf_emoji = "🔴" if confidence == "ULTRA" else "🟡"
    conf_tag = f"ULTRA [{wallets} whales]" if confidence == "ULTRA" else f"HIGH [{wallets} whales]"

    # Token name + symbol from DexScreener
    if dex_data:
        base = dex_data.get("baseToken", {})
        token_name   = base.get("name", "Unknown")
        token_symbol = base.get("symbol", "???")
        mcap   = dex_data.get("marketCap") or dex_data.get("fdv") or 0
        liq    = dex_data.get("liquidity", {}).get("usd", 0) or 0
        vol    = dex_data.get("volume", {})
        h1_vol = vol.get("h1", 0) or 0
        h24_vol = vol.get("h24", 0) or 0
        avg_hourly = h24_vol / 24 if h24_vol > 0 else 0
        spike_ratio = h1_vol / avg_hourly if avg_hourly > 0 else 0
        # Approximate 2h volume
        h2_vol_est = h1_vol * 2
        price_usd = float(dex_data.get("priceUsd", 0) or 0)
    else:
        token_name   = "Unknown"
        token_symbol = "???"
        mcap, liq, h2_vol_est, avg_hourly, spike_ratio = 0, 0, 0, 0, 0
        price_usd = 0

    # Build TP/SL lines
    if tp_sl and price_usd > 0:
        entry_line = format_price(tp_sl["entry"])
        tp1_line   = f"{format_price(tp_sl['tp1'])} (+10%)"
        tp2_line   = f"{format_price(tp_sl['tp2'])} (+25%)"
        tp3_line   = f"{format_price(tp_sl['tp3'])} (+50%)"
        sl_line    = f"{format_price(tp_sl['sl'])} (-15%)"
        be_note    = f"Move stop to breakeven ({entry_line}) after TP1 hits"
    else:
        entry_line = "see chart"
        tp1_line   = "+10%"
        tp2_line   = "+25%"
        tp3_line   = "+50%"
        sl_line    = "-15%"
        be_note    = "Move stop to breakeven after TP1 hits"

    # Build volume spike string
    if spike_ratio > 0:
        spike_str = f"{format_usd(h2_vol_est)} (~{spike_ratio:.1f}x spike vs avg)"
    else:
        spike_str = format_usd(total_usd) + " whale aggregate"

    # Dexscreener + Birdeye links
    dex_url = f"https://dexscreener.com/solana/{token}"
    bird_url = f"https://birdeye.so/token/{token}?chain=solana"

    post = f"""{conf_emoji} WHALE ALERT — {conf_tag}

📍 Token: {token_name} ({token_symbol})
💰 Market Cap: {format_usd(mcap)} | Liquidity: {format_usd(liq)}
📊 DEX Volume 2h: {spike_str}

🎯 Entry Zone: {entry_line}
✅ TP1: {tp1_line}
✅ TP2: {tp2_line}
✅ TP3: {tp3_line}
❌ Stop Loss: {sl_line}
⏱️ Hold: 24-48h | {be_note}

📡 Source: {wallets} smart money wallets converged in {window}min window
💵 Whale buys: {format_usd(total_usd)} aggregate
🕐 Detected: {time_str}

📈 Chart: {dex_url}
🔍 Birdeye: {bird_url}

⚠️ Not financial advice. DYOR. Risk only what you can afford to lose.

💡 Tip wallet (SOL/USDC): <code>{TIP_WALLET}</code>"""

    return post


# ---------------------------------------------------------------------------
# Signal loading (unchanged logic from original)
# ---------------------------------------------------------------------------

def get_new_signals(last_ts: int) -> list[dict]:
    """
    Read signals.jsonl, run convergence detection, return signals
    newer than last_ts that pass basic quality filters.
    """
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


# ---------------------------------------------------------------------------
# Performance tracking
# ---------------------------------------------------------------------------

def record_signal_performance(signal: dict, dex_data: dict | None, tp_sl: dict | None):
    """
    Write a new entry to signal_performance.jsonl when a signal is published.
    This feeds the performance tracker that checks for TP/SL hits.
    """
    import hashlib
    token = signal["token"]
    sig_ts = signal["signal_ts"]

    # Stable unique ID: hash of token + signal_ts
    sig_id = hashlib.sha256(f"{token}:{sig_ts}".encode()).hexdigest()[:12]

    token_name = "Unknown"
    token_symbol = "???"
    if dex_data:
        base = dex_data.get("baseToken", {})
        token_name   = base.get("name", "Unknown")
        token_symbol = base.get("symbol", "???")

    entry = {
        "signal_id":       sig_id,
        "token":           token,
        "token_name":      token_name,
        "token_symbol":    token_symbol,
        "signal_ts":       sig_ts,
        "signal_time":     signal.get("signal_time", ""),
        "published_ts":    int(time.time()),
        "entry_price":     tp_sl["entry"] if tp_sl else None,
        "tp1_price":       tp_sl["tp1"]   if tp_sl else None,
        "tp2_price":       tp_sl["tp2"]   if tp_sl else None,
        "tp3_price":       tp_sl["tp3"]   if tp_sl else None,
        "sl_price":        tp_sl["sl"]    if tp_sl else None,
        "be_price":        tp_sl["be"]    if tp_sl else None,
        "wallet_count":    signal.get("wallet_count", 0),
        "total_buy_usd":   signal.get("total_buy_usd", 0),
        "confidence":      signal.get("confidence", ""),
        "status":          "open",
        "stop_moved_to_be": False,
        "tp1_hit":         False,
        "tp2_hit":         False,
        "tp3_hit":         False,
        "sl_hit":          False,
        "checked_1h":      False,
        "checked_4h":      False,
        "checked_24h":     False,
        "checked_48h":     False,
        "final_pnl":       None,
        "closed_at":       None,
    }

    with open(PERF_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")

    print(f"[publisher] Recorded performance entry: {sig_id} ({token_name}/{token_symbol})")


# ---------------------------------------------------------------------------
# Telegram posting
# ---------------------------------------------------------------------------

async def post_to_telegram(text: str) -> bool:
    """Post message to Telegram channel. Returns True on success."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHANNEL:
        print("[publisher] ERROR: TELEGRAM_BOT_TOKEN or TELEGRAM_CHANNEL not configured")
        return False

    import httpx
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id":                 TELEGRAM_CHANNEL,
        "text":                    text,
        "parse_mode":              "HTML",
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


# ---------------------------------------------------------------------------
# Main runner
# ---------------------------------------------------------------------------

async def run(dry_run: bool = False, test_mode: bool = False,
              no_filters: bool = False, check_perf: bool = False):
    state = load_state()

    # Check performance on open signals if requested
    if check_perf:
        from signals.signal_performance import check_open_signals
        await check_open_signals(dry_run=dry_run)
        return

    if test_mode:
        test_signal = {
            "token":        "ExampleToken1111111111111111111111111111111",
            "wallet_count": 4,
            "confidence":   "ULTRA",
            "total_buy_usd": 125_000,
            "signal_time":  datetime.now(timezone.utc).isoformat(),
            "window_minutes": 30,
            "signal_ts":    int(time.time()),
        }
        # Build dummy TP/SL at $0.001234 for demo
        tp_sl = compute_tp_sl(0.001234)
        post = format_signal_post(test_signal, None, tp_sl)
        print("=== TEST POST ===")
        print(post)
        print("================")
        if not dry_run:
            success = await post_to_telegram(post)
            print(f"[publisher] Test post {'succeeded' if success else 'FAILED'}")
        return

    # Check daily limit
    daily_count = get_daily_count(state)
    if daily_count >= MAX_SIGNALS_PER_DAY:
        print(f"[publisher] Daily limit reached: {daily_count}/{MAX_SIGNALS_PER_DAY} signals today. Skipping.")
        return

    remaining_today = MAX_SIGNALS_PER_DAY - daily_count
    new_signals = get_new_signals(state["last_published_ts"])
    print(f"[publisher] Found {len(new_signals)} new signals | Daily count: {daily_count}/{MAX_SIGNALS_PER_DAY}")

    if not new_signals:
        print("[publisher] Nothing to publish")
        return

    published = 0
    for signal in new_signals:
        if published >= remaining_today:
            print(f"[publisher] Daily limit reached mid-run. Stopping at {published} published.")
            break

        token = signal["token"]
        print(f"[publisher] Processing: {token[:20]}... | {signal['confidence']} | wallets={signal['wallet_count']}")

        # Fetch DexScreener data
        dex_data = await fetch_dex_data(token)

        # Apply quality filters (unless --no-filters)
        if not no_filters:
            if dex_data is None:
                print(f"[publisher] SKIP: No DexScreener data available for {token[:16]}...")
                continue
            passes, reason = apply_quality_filters(signal, dex_data)
            if not passes:
                print(f"[publisher] FILTERED OUT: {reason}")
                continue
            print(f"[publisher] PASSES filters: {reason}")

        # Compute TP/SL from current price
        tp_sl = None
        if dex_data:
            price_usd = float(dex_data.get("priceUsd", 0) or 0)
            if price_usd > 0:
                tp_sl = compute_tp_sl(price_usd)
                print(f"[publisher] Entry: {format_price(price_usd)} | TP1: {format_price(tp_sl['tp1'])} | SL: {format_price(tp_sl['sl'])}")

        # Format post
        post = format_signal_post(signal, dex_data, tp_sl)

        if dry_run:
            print("--- DRY RUN ---")
            print(post)
            print("---------------")
            published += 1
            # Still record to perf tracker in dry-run (with dry-run note)
            if dex_data:
                record_signal_performance(signal, dex_data, tp_sl)
        else:
            success = await post_to_telegram(post)
            if success:
                published += 1
                state["last_published_ts"]  = max(state["last_published_ts"], signal["signal_ts"])
                state["total_published"]    = state.get("total_published", 0) + 1
                state["published_today"]    = state.get("published_today", 0) + 1
                state["today_date"]         = str(date.today())
                save_state(state)
                # Record to performance tracker
                if dex_data:
                    record_signal_performance(signal, dex_data, tp_sl)
            # Rate limit delay between posts
            await asyncio.sleep(1)

    print(f"[publisher] Done. Published {published}/{len(new_signals)} signals.")
    if not dry_run and published > 0:
        print(f"[publisher] Total published all-time: {state.get('total_published', 0)}")


def main():
    parser = argparse.ArgumentParser(description="Otto Signal Publisher")
    parser.add_argument("--dry-run",     action="store_true", help="Print posts without sending")
    parser.add_argument("--test",        action="store_true", help="Post a single test message")
    parser.add_argument("--no-filters",  action="store_true", help="Skip quality filters (debug)")
    parser.add_argument("--check-perf",  action="store_true", help="Check open signal performance")
    args = parser.parse_args()

    asyncio.run(run(
        dry_run=args.dry_run,
        test_mode=args.test,
        no_filters=args.no_filters,
        check_perf=args.check_perf,
    ))


if __name__ == "__main__":
    main()
