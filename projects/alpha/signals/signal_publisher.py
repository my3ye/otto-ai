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
# Week 1 fix: raised from 3→4 (research shows 3-wallet signals had no discriminating power)
MIN_WALLET_COUNT = 4
MIN_TOTAL_USD = 1_000
CONFIDENCE_LEVELS = {"ULTRA", "HIGH"}
LOOKBACK_HOURS = 2

# --- Single-wallet signal mode thresholds ---
SW_MIN_QUALITY_SCORE = 0.6   # Grade A + score >= 0.6
SW_LOOKBACK_HOURS = 2        # Only look at last 2 hours of signals.jsonl

# Noisy wallets excluded from single-wallet mode (same as whale_convergence.py)
SW_NOISY_WALLETS = {"SM_1", "SM_2", "SM_4", "SM_7"}

# --- Single-wallet DexScreener filters (more permissive than convergence mode) ---
# Convergence hunts for micro-cap pumps. Single-wallet tracks smart money broadly.
SW_FILTER_MIN_MARKET_CAP   = 500_000    # $500K — filter obvious junk/rugs
# No upper mcap bound — smart money buys mid/large caps too
SW_FILTER_MIN_LIQUIDITY    = 50_000     # $50K minimum pool liquidity
SW_FILTER_VOLUME_SPIKE_MIN = 1.0        # h1 vol must be >= 1.0x hourly average (lowered from 1.5 — was filtering 7/8 candidates)
SW_FILTER_MAX_PUMP_6H      = 40.0       # Skip if already up >40% in 6h (already too late)
SW_FILTER_MIN_TOKEN_AGE_DAYS = 1        # Token must be at least 1 day old

# Stablecoins and large-caps to skip (subset of whale_convergence BLOCKED_TOKENS)
SW_BLOCKED_TOKENS = {
    "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",  # USDC
    "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB",  # USDT
    "So11111111111111111111111111111111111111112",     # SOL (wrapped)
    "mSoLzYCxHdYgdzU16g5QSh3i5K3z3KZK7ytfqcJm7So",  # mSOL
    "7dHbWXmci3dT8UFYWYZweBLXgycu7Y3iL6trKn1Y7ARj",  # stSOL
    "J1toso1uCk3RLmjorhTtrVwY9HJ7X8V9yYac6Y7kGCPn",  # jitoSOL
    "JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN",   # JUP
    "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263",  # BONK
    "EKpQGSJtjMFqKZ9KQanSqYXRcF8fBopzLHYxdM65zcjm",  # WIF
}

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
# Week 1 fix: was >25% in 6h → now >15% in 1h. DexScreener has no 2h field; h1 is the
# correct proxy. If a token pumped >15% in the last hour we're already late — skip it.
FILTER_MAX_PUMP_1H      = 15.0       # Skip if price already up >15% in last 1h
# Week 1 fix: raised from 3→7 days. Most rugs happen in the first week; 3-day floor
# still exposed us to peak rug window. 7 days eliminates the majority of rug risk.
FILTER_MIN_TOKEN_AGE_DAYS = 7        # Token must be > 7 days old (was 3)
# Week 1 fix: NEW — reject wash-traded tokens. If 24h volume > 20x liquidity the pool
# is being churned artificially. Real organic volume rarely exceeds 10x liquidity/day.
FILTER_MAX_VOL_LIQ_RATIO = 20.0      # 24h_vol / liquidity cap (wash-trade guard)

# --- Quality gate: max signals per day ---
MAX_SIGNALS_PER_DAY = 3


# ---------------------------------------------------------------------------
# State management
# ---------------------------------------------------------------------------

def load_state() -> dict:
    if STATE_FILE.exists():
        state = json.loads(STATE_FILE.read_text())
        # Migrate old state without published_tokens_today
        if "published_tokens_today" not in state:
            state["published_tokens_today"] = []
        return state
    return {
        "last_published_ts": 0,
        "total_published": 0,
        "published_today": 0,
        "today_date": str(date.today()),
        "published_tokens_today": [],
    }


def save_state(state: dict):
    STATE_FILE.write_text(json.dumps(state, indent=2))


def get_daily_count(state: dict) -> int:
    """Return today's published signal count, resetting if day changed."""
    today_str = str(date.today())
    if state.get("today_date") != today_str:
        state["published_today"] = 0
        state["today_date"] = today_str
        state["published_tokens_today"] = []
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

    # --- Wash-trade guard: reject if 24h volume > 20x liquidity (Week 1 fix) ---
    # Organic volume rarely exceeds 10x liquidity/day. >20x = almost certainly wash-trading.
    if liq > 0 and h24_vol > 0:
        vol_liq_ratio = h24_vol / liq
        if vol_liq_ratio > FILTER_MAX_VOL_LIQ_RATIO:
            return False, f"wash-trade suspect: 24h_vol/liq={vol_liq_ratio:.1f}x > {FILTER_MAX_VOL_LIQ_RATIO}x (vol=${h24_vol:,.0f}, liq=${liq:,.0f})"

    # --- Already-pumped filter: skip if >15% up in last 1h (Week 1 fix, was >25% in 6h) ---
    # DexScreener has no 2h field; h1 is the proxy. >15% in 1h = we are already late.
    price_change = dex_data.get("priceChange", {})
    change_1h = price_change.get("h1", 0) or 0
    if change_1h > FILTER_MAX_PUMP_1H:
        return False, f"already pumped: +{change_1h:.1f}% in 1h > {FILTER_MAX_PUMP_1H}%"

    # --- Token age: > 7 days (Week 1 fix, was 3 days) ---
    pair_created_ms = dex_data.get("pairCreatedAt", 0) or 0
    if pair_created_ms > 0:
        age_days = (time.time() * 1000 - pair_created_ms) / (1000 * 86400)
        if age_days < FILTER_MIN_TOKEN_AGE_DAYS:
            return False, f"token too new: {age_days:.1f} days < {FILTER_MIN_TOKEN_AGE_DAYS} days"

    return True, "all filters passed"


def apply_sw_quality_filters(signal: dict, dex_data: dict) -> tuple[bool, str]:
    """
    Quality filters for single-wallet signals. More permissive than convergence.
    Smart money buys mid-cap tokens too — no upper market cap bound.
    """
    # --- Market cap floor: $500K (filter absolute garbage) ---
    mcap = dex_data.get("marketCap") or dex_data.get("fdv") or 0
    if mcap < SW_FILTER_MIN_MARKET_CAP:
        return False, f"mcap too low: ${mcap:,.0f} < ${SW_FILTER_MIN_MARKET_CAP:,}"

    # --- Liquidity floor: >= $50K ---
    liq = dex_data.get("liquidity", {}).get("usd", 0) or 0
    if liq < SW_FILTER_MIN_LIQUIDITY:
        return False, f"liquidity too low: ${liq:,.0f} < ${SW_FILTER_MIN_LIQUIDITY:,}"

    # --- Volume spike: h1 vol >= 1.5x hourly average ---
    vol = dex_data.get("volume", {})
    h1_vol  = vol.get("h1", 0) or 0
    h24_vol = vol.get("h24", 0) or 0
    if h24_vol > 0:
        avg_hourly = h24_vol / 24
        spike_ratio = h1_vol / avg_hourly if avg_hourly > 0 else 0
        if spike_ratio < SW_FILTER_VOLUME_SPIKE_MIN:
            return False, f"volume spike too low: {spike_ratio:.1f}x < {SW_FILTER_VOLUME_SPIKE_MIN}x"

    # --- Already-pumped filter: skip if >40% up in 6h ---
    price_change = dex_data.get("priceChange", {})
    change_6h = price_change.get("h6", 0) or 0
    if change_6h > SW_FILTER_MAX_PUMP_6H:
        return False, f"already pumped: +{change_6h:.1f}% in 6h > {SW_FILTER_MAX_PUMP_6H}%"

    # --- Token age: > 1 day ---
    pair_created_ms = dex_data.get("pairCreatedAt", 0) or 0
    if pair_created_ms > 0:
        age_days = (time.time() * 1000 - pair_created_ms) / (1000 * 86400)
        if age_days < SW_FILTER_MIN_TOKEN_AGE_DAYS:
            return False, f"token too new: {age_days:.1f} days < {SW_FILTER_MIN_TOKEN_AGE_DAYS} days"

    return True, "all SW filters passed"


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
# Single-wallet signal formatting
# ---------------------------------------------------------------------------

def format_single_wallet_post(signal: dict, dex_data: dict | None, tp_sl: dict | None) -> str:
    """
    Format a single smart-money buy into a Telegram alert.
    Different template from convergence — 🐋 Smart Money Alert.
    """
    token = signal["token"]
    wallet = signal.get("wallet", "Unknown")
    quality_score = signal.get("quality_score", 0)
    amount_sol = signal.get("amount_sol", 0)
    amount_usd = signal.get("amount_usd", 0)

    # Time formatting
    ts_str = signal.get("timestamp", "")
    try:
        dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        time_str = dt.strftime("%H:%M UTC")
    except Exception:
        time_str = "recent"

    # Token name + symbol from DexScreener
    if dex_data:
        base = dex_data.get("baseToken", {})
        token_name   = base.get("name", "Unknown")
        token_symbol = base.get("symbol", "???")
        mcap   = dex_data.get("marketCap") or dex_data.get("fdv") or 0
        liq    = dex_data.get("liquidity", {}).get("usd", 0) or 0
        vol    = dex_data.get("volume", {})
        h1_vol  = vol.get("h1", 0) or 0
        h24_vol = vol.get("h24", 0) or 0
        avg_hourly = h24_vol / 24 if h24_vol > 0 else 0
        spike_ratio = h1_vol / avg_hourly if avg_hourly > 0 else 0
        price_usd = float(dex_data.get("priceUsd", 0) or 0)
        price_change = dex_data.get("priceChange", {})
        change_1h = price_change.get("h1", 0) or 0
        change_24h = price_change.get("h24", 0) or 0
    else:
        token_name   = "Unknown"
        token_symbol = "???"
        mcap, liq, h1_vol, avg_hourly, spike_ratio = 0, 0, 0, 0, 0
        price_usd = 0
        change_1h = change_24h = 0

    # Buy amount display — prefer SOL if non-zero; only show USD if >= $1
    if amount_sol > 0:
        buy_str = f"{amount_sol:.2f} SOL"
        if amount_usd >= 1:
            buy_str += f" (~{format_usd(amount_usd)})"
    elif amount_usd >= 1:
        buy_str = format_usd(amount_usd)
    elif amount_usd > 0:
        buy_str = f"{amount_usd:.4f} USD"
    else:
        buy_str = "amount not available"

    # TP/SL lines
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

    # Volume spike display
    if spike_ratio > 0:
        vol_str = f"{format_usd(h1_vol)}/h  ({spike_ratio:.1f}x avg)"
    else:
        vol_str = "N/A"

    # Price momentum
    momentum = ""
    if change_1h != 0 or change_24h != 0:
        momentum = f"📈 1h: {change_1h:+.1f}%  |  24h: {change_24h:+.1f}%"

    # Score display (1 decimal)
    score_str = f"{quality_score:.2f}"

    # Links
    dex_url  = f"https://dexscreener.com/solana/{token}"
    bird_url = f"https://birdeye.so/token/{token}?chain=solana"

    post = f"""🐋 Smart Money Alert — {wallet}

📍 Token: {token_name} ({token_symbol})
💰 MCap: {format_usd(mcap)}  |  Liquidity: {format_usd(liq)}
📊 Volume: {vol_str}
{momentum}

🎯 Entry Zone: {entry_line}
✅ TP1: {tp1_line}
✅ TP2: {tp2_line}
✅ TP3: {tp3_line}
❌ Stop Loss: {sl_line}
⏱️ Hold: 24-48h  |  {be_note}

💼 Buy: {buy_str}
🏆 Signal Quality: {score_str}/1.0  (Grade A)
🕐 Detected: {time_str}

📈 Chart: {dex_url}
🔍 Birdeye: {bird_url}

⚠️ Not financial advice. DYOR. Risk only what you can afford to lose.

💡 Tip wallet (SOL/USDC): <code>{TIP_WALLET}</code>"""

    return post


# ---------------------------------------------------------------------------
# Single-wallet signal loading
# ---------------------------------------------------------------------------

def get_new_single_wallet_signals(state: dict) -> list[dict]:
    """
    Read signals.jsonl directly and return grade-A smart money buy signals
    that haven't been published yet.

    Filters:
    - quality_grade == 'A' AND quality_score >= SW_MIN_QUALITY_SCORE
    - amount_usd > 0 (skip parsing failures)
    - Not in SW_BLOCKED_TOKENS
    - Not in SW_NOISY_WALLETS
    - Within last SW_LOOKBACK_HOURS
    - Token not already in published_tokens_today

    Deduplication: per unique token, keep only the highest quality_score record.
    Returns sorted by quality_score descending.
    """
    cutoff_ts = time.time() - SW_LOOKBACK_HOURS * 3600
    published_tokens = set(state.get("published_tokens_today", []))

    # token → best signal record for that token
    best_per_token: dict[str, dict] = {}

    if not SIGNALS_JSONL.exists():
        print(f"[publisher] signals.jsonl not found at {SIGNALS_JSONL}")
        return []

    for line in SIGNALS_JSONL.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            r = json.loads(line)
        except Exception:
            continue

        token = r.get("token", "")
        if not token or len(token) < 20:
            continue
        if token in SW_BLOCKED_TOKENS:
            continue
        if token in published_tokens:
            continue

        wallet = r.get("wallet", "")
        if not wallet or wallet in SW_NOISY_WALLETS:
            continue

        # Grade A + score threshold
        if r.get("quality_grade") != "A":
            continue
        score = r.get("quality_score", 0)
        if score < SW_MIN_QUALITY_SCORE:
            continue

        # Skip zero-amount (parsing failures)
        if r.get("amount_usd", 0) == 0 and r.get("amount_sol", 0) == 0:
            continue

        # Must be within lookback window
        ts_str = r.get("timestamp", "")
        try:
            ts = int(datetime.fromisoformat(ts_str.replace("Z", "+00:00")).timestamp())
        except Exception:
            continue
        if ts < cutoff_ts:
            continue

        # Keep best signal per token
        existing = best_per_token.get(token)
        if existing is None or score > existing.get("quality_score", 0):
            best_per_token[token] = r

    signals = list(best_per_token.values())
    signals.sort(key=lambda s: s.get("quality_score", 0), reverse=True)
    print(f"[publisher] Single-wallet: found {len(signals)} unique grade-A tokens in last {SW_LOOKBACK_HOURS}h")
    return signals


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

def record_signal_performance(signal: dict, dex_data: dict | None, tp_sl: dict | None,
                               signal_type: str = "convergence"):
    """
    Write a new entry to signal_performance.jsonl when a signal is published.
    This feeds the performance tracker that checks for TP/SL hits.
    signal_type: "convergence" or "single_wallet"
    """
    import hashlib
    token = signal["token"]
    # convergence signals use signal_ts (int), single-wallet use timestamp (ISO str)
    sig_ts = signal.get("signal_ts") or int(
        datetime.fromisoformat(
            signal.get("timestamp", "").replace("Z", "+00:00")
        ).timestamp()
    )

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
        "signal_type":     signal_type,
        "token":           token,
        "token_name":      token_name,
        "token_symbol":    token_symbol,
        "signal_ts":       sig_ts,
        "signal_time":     signal.get("signal_time") or signal.get("timestamp", ""),
        "published_ts":    int(time.time()),
        "entry_price":     tp_sl["entry"] if tp_sl else None,
        "tp1_price":       tp_sl["tp1"]   if tp_sl else None,
        "tp2_price":       tp_sl["tp2"]   if tp_sl else None,
        "tp3_price":       tp_sl["tp3"]   if tp_sl else None,
        "sl_price":        tp_sl["sl"]    if tp_sl else None,
        "be_price":        tp_sl["be"]    if tp_sl else None,
        "wallet_count":    signal.get("wallet_count", 0),
        "wallet":          signal.get("wallet", ""),
        "quality_score":   signal.get("quality_score", None),
        "total_buy_usd":   signal.get("total_buy_usd") or signal.get("amount_usd", 0),
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

    print(f"[publisher] Recorded performance entry: {sig_id} ({token_name}/{token_symbol}) [{signal_type}]")


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
    published = 0

    # -----------------------------------------------------------------------
    # TIER 1: Convergence signals (premium — 3+ wallets, HIGH/ULTRA)
    # -----------------------------------------------------------------------
    convergence_signals = get_new_signals(state["last_published_ts"])
    print(f"[publisher] Convergence signals: {len(convergence_signals)} new | Daily: {daily_count}/{MAX_SIGNALS_PER_DAY}")

    for signal in convergence_signals:
        if published >= remaining_today:
            print(f"[publisher] Daily limit reached. Stopping at {published} published.")
            break

        token = signal["token"]
        print(f"[publisher] [CONVERGENCE] Processing: {token[:20]}... | {signal['confidence']} | wallets={signal['wallet_count']}")

        dex_data = await fetch_dex_data(token)

        if not no_filters:
            if dex_data is None:
                print(f"[publisher] SKIP: No DexScreener data for {token[:16]}...")
                continue
            passes, reason = apply_quality_filters(signal, dex_data)
            if not passes:
                print(f"[publisher] FILTERED OUT: {reason}")
                continue
            print(f"[publisher] PASSES filters: {reason}")

        tp_sl = None
        if dex_data:
            price_usd = float(dex_data.get("priceUsd", 0) or 0)
            if price_usd > 0:
                tp_sl = compute_tp_sl(price_usd)
                print(f"[publisher] Entry: {format_price(price_usd)} | TP1: {format_price(tp_sl['tp1'])} | SL: {format_price(tp_sl['sl'])}")

        post = format_signal_post(signal, dex_data, tp_sl)

        if dry_run:
            print("--- DRY RUN [CONVERGENCE] ---")
            print(post)
            print("-----------------------------")
            published += 1
            if dex_data:
                record_signal_performance(signal, dex_data, tp_sl, signal_type="convergence")
        else:
            success = await post_to_telegram(post)
            if success:
                published += 1
                state["last_published_ts"] = max(state["last_published_ts"], signal["signal_ts"])
                state["total_published"]   = state.get("total_published", 0) + 1
                state["published_today"]   = state.get("published_today", 0) + 1
                state["today_date"]        = str(date.today())
                # Track token to avoid duplicate from single-wallet mode
                if token not in state["published_tokens_today"]:
                    state["published_tokens_today"].append(token)
                save_state(state)
                if dex_data:
                    record_signal_performance(signal, dex_data, tp_sl, signal_type="convergence")
            await asyncio.sleep(1)

    # -----------------------------------------------------------------------
    # TIER 2: Single-wallet signals (grade-A smart money buys)
    # -----------------------------------------------------------------------
    remaining_today = MAX_SIGNALS_PER_DAY - daily_count - published
    if remaining_today <= 0:
        print(f"[publisher] No slots remaining for single-wallet signals ({published} convergence published).")
    else:
        sw_signals = get_new_single_wallet_signals(state)
        print(f"[publisher] Single-wallet signals: {len(sw_signals)} candidates | {remaining_today} slot(s) remaining")

        sw_published = 0
        for signal in sw_signals:
            if sw_published >= remaining_today:
                print(f"[publisher] Single-wallet slot limit reached.")
                break

            token = signal["token"]
            wallet = signal.get("wallet", "?")
            score  = signal.get("quality_score", 0)
            print(f"[publisher] [SINGLE-WALLET] Processing: {token[:20]}... | {wallet} | score={score:.3f}")

            dex_data = await fetch_dex_data(token)

            if not no_filters:
                if dex_data is None:
                    print(f"[publisher] SKIP: No DexScreener data for {token[:16]}...")
                    continue
                passes, reason = apply_sw_quality_filters(signal, dex_data)
                if not passes:
                    print(f"[publisher] FILTERED OUT: {reason}")
                    continue
                print(f"[publisher] PASSES SW filters: {reason}")

            tp_sl = None
            if dex_data:
                price_usd = float(dex_data.get("priceUsd", 0) or 0)
                if price_usd > 0:
                    tp_sl = compute_tp_sl(price_usd)
                    print(f"[publisher] Entry: {format_price(price_usd)} | TP1: {format_price(tp_sl['tp1'])} | SL: {format_price(tp_sl['sl'])}")

            post = format_single_wallet_post(signal, dex_data, tp_sl)

            if dry_run:
                print("--- DRY RUN [SINGLE-WALLET] ---")
                print(post)
                print("-------------------------------")
                sw_published += 1
                published += 1
                if dex_data:
                    record_signal_performance(signal, dex_data, tp_sl, signal_type="single_wallet")
            else:
                success = await post_to_telegram(post)
                if success:
                    sw_published += 1
                    published += 1
                    state["total_published"]   = state.get("total_published", 0) + 1
                    state["published_today"]   = state.get("published_today", 0) + 1
                    state["today_date"]        = str(date.today())
                    if token not in state["published_tokens_today"]:
                        state["published_tokens_today"].append(token)
                    save_state(state)
                    if dex_data:
                        record_signal_performance(signal, dex_data, tp_sl, signal_type="single_wallet")
                await asyncio.sleep(1)

        print(f"[publisher] Single-wallet: published {sw_published}/{len(sw_signals)} candidates")

    total_this_run = published
    print(f"[publisher] Done. Published {total_this_run} signals this run.")
    if not dry_run and total_this_run > 0:
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
