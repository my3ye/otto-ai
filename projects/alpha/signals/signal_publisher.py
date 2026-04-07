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


# --- Load strategy config overrides (auto-updated by pipeline_executor.py) ---
def _load_strategy_config() -> dict:
    """Load strategy_config.json from parent alpha dir. Returns {} if missing."""
    config_path = Path(__file__).resolve().parents[1] / "strategy_config.json"
    if config_path.exists():
        try:
            return json.loads(config_path.read_text())
        except Exception:
            pass
    return {}

_STRATEGY = _load_strategy_config()
_SW_CFG   = _STRATEGY.get("single_wallet", {})
_QF_CFG   = _STRATEGY.get("quality_filters", {})
_TPSL_CFG = _STRATEGY.get("tp_sl", {})
_CONV_CFG = _STRATEGY.get("convergence", {})


# --- Signal detection thresholds (kept from original) ---
# Week 1 fix: raised from 3→4 (research shows 3-wallet signals had no discriminating power)
MIN_WALLET_COUNT = _CONV_CFG.get("min_wallet_count", 4)
MIN_TOTAL_USD = _CONV_CFG.get("min_total_usd", 1_000)
CONFIDENCE_LEVELS = set(_CONV_CFG.get("confidence_levels", ["ULTRA", "HIGH"]))
LOOKBACK_HOURS = 2

# --- Single-wallet signal mode thresholds ---
SW_MIN_QUALITY_SCORE = _SW_CFG.get("min_quality_score", 0.6)   # Grade A + score >= threshold
SW_LOOKBACK_HOURS = 2        # Only look at last 2 hours of signals.jsonl
# Timeframe analysis 2026-03-09: min $100 buy required for single-wallet signals.
# 9/12 published signals were dust trades ($0.003-$0.32) with no smart-money conviction.
# $100 floor filters bot dust while keeping real smart-money accumulation.
SW_MIN_BUY_USD = _SW_CFG.get("min_buy_usd", 100)         # Minimum buy size for single-wallet signals

# Noisy wallets excluded from single-wallet mode (same as whale_convergence.py)
# 2026-03-10: SM_10 REMOVED — confirmed 83% WR directional trader. Dust problem
# was fixed by SW_MIN_BUY_USD=$100. SM_10 is now Tier 1 (publish immediately).
SW_NOISY_WALLETS = set(_SW_CFG.get("noisy_wallets", ["SM_1", "SM_2", "SM_4", "SM_7"]))
# Allowlist: if set, only signals from these wallets are published. Empty = no restriction.
# 2026-04-07: Research pipeline confirmed SM_10 (87.5% WR) and SM_5 (100% WR) as the only
# proven performers. Restricting to these two eliminates noise from 100+ unvetted wallets.
SW_ALLOWED_WALLETS = set(_SW_CFG.get("allowed_wallets", []))

# --- Single-wallet DexScreener filters (more permissive than convergence mode) ---
# Convergence hunts for micro-cap pumps. Single-wallet tracks smart money broadly.
SW_FILTER_MIN_MARKET_CAP   = _SW_CFG.get("min_market_cap", 500_000)
# No upper mcap bound — smart money buys mid/large caps too
SW_FILTER_MIN_LIQUIDITY    = _SW_CFG.get("min_liquidity", 50_000)
SW_FILTER_VOLUME_SPIKE_MIN = _SW_CFG.get("volume_spike_min", 1.0)
SW_FILTER_MAX_PUMP_6H      = _SW_CFG.get("max_pump_6h", 40.0)
SW_FILTER_MIN_TOKEN_AGE_DAYS = _SW_CFG.get("min_token_age_days", 1)

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
TP1_PCT = _TPSL_CFG.get("tp1_pct", 0.10)
TP2_PCT = _TPSL_CFG.get("tp2_pct", 0.25)
TP3_PCT = _TPSL_CFG.get("tp3_pct", 0.50)
SL_PCT  = _TPSL_CFG.get("sl_pct",  0.15)

# --- Published signal entry window (Cornix entry timeout) ---
# Research finding 2026-04-04: 22% TP hit rate with 88.9% expiration despite 88.9% directional
# accuracy. Extending published_window_minutes from 30 to 360 gives Cornix 6h entry window.
PUBLISHED_WINDOW_MINUTES = _STRATEGY.get("published_window_minutes", 360)

# --- Quality filter thresholds ---
FILTER_MIN_MARKET_CAP   = _QF_CFG.get("min_market_cap",   100_000)
FILTER_MAX_MARKET_CAP   = _QF_CFG.get("max_market_cap",   3_000_000)
FILTER_MIN_LIQUIDITY    = _QF_CFG.get("min_liquidity",    100_000)
FILTER_VOLUME_SPIKE_MIN = _QF_CFG.get("volume_spike_min", 3.0)
# Week 1 fix v2: tightened from 15% → 10%. Our 0% WR at T+1h shows we're entering after
# a 10-15% move has already happened. 10% h1 filter cuts late entries more aggressively.
# DexScreener has no 2h field; h1 is the correct proxy for recent price action.
FILTER_MAX_PUMP_1H      = _QF_CFG.get("max_pump_1h",      10.0)
# Week 1 fix: raised from 3→7 days. Most rugs happen in the first week; 3-day floor
# still exposed us to peak rug window. 7 days eliminates the majority of rug risk.
FILTER_MIN_TOKEN_AGE_DAYS = _QF_CFG.get("min_token_age_days", 7)
# Week 1 fix: NEW — reject wash-traded tokens. If 24h volume > 20x liquidity the pool
# is being churned artificially. Real organic volume rarely exceeds 10x liquidity/day.
FILTER_MAX_VOL_LIQ_RATIO = 20.0      # 24h_vol / liquidity cap (wash-trade guard)

# --- Quality gate: max signals per day ---
MAX_SIGNALS_PER_DAY = 3

# --- Repeat convergence tracking ---
# Tokens that appear as convergence signals 2+ times within 72h get upgraded to ULTRA tier.
# Backtest: pippin appeared 3x as convergence, returned +19-27% each time.
CONVERGENCE_SEEN_TTL_HOURS = 72  # Prune entries older than 72h

# --- Wallet quality tier system ---
# Research 2026-03-10: Only SM_10 is a proven directional trader (83% WR).
# All other wallets are LP positions, JIT bots, or MEV bundlers with no edge.
#
# Tier 1 — proven directional traders: publish immediately
# Tier 2 — convergence (4+ wallets): publish with convergence tag
# Tier 3 — single unvetted wallet: log but DO NOT publish to @OttoSignals
TIER_1_WALLETS = {"SM_10", "SM_5"}   # SM_10: 87.5% WR; SM_5: 100% WR — both proven performers
MIN_PUBLISHER_QUALITY_SCORE = 50     # Gate: only publish signals scoring >= 50/100


# ---------------------------------------------------------------------------
# State management
# ---------------------------------------------------------------------------

def compute_publisher_quality_score(
    wallet: str,
    signal_type: str,
    wallet_count: int = 1,
    convergence_count: int = 1,
    dex_data: dict | None = None,
) -> int:
    """
    Compute publisher-level quality score (0-100) for a signal.

    Wallet tier (base score):
      Tier 1 — SM_10 (proven 83% WR):           60 points
      Tier 2 — convergence (N wallets):          10 * wallet_count
      Tier 3 — single unvetted wallet:           10 points

    Bonuses (from DexScreener data):
      Token age:    min(age_days, 15) points     (older = more trusted)
      Volume spike: min(spike_ratio * 3, 20) pts (volume spike = conviction)
      Repeat convergence: +10 per repeat detection (pippin x3 → +27%)

    Gate: MIN_PUBLISHER_QUALITY_SCORE = 50
      SM_10: 60 + bonuses → always >= 50 (publish)
      4-wallet convergence + 7-day token + 2x spike: 40+7+6 = 53 (publish)
      5-wallet convergence: 50 + bonuses (publish)
      Single unvetted: 10 + bonuses = max ~35 (blocked)
    """
    # --- Base score from wallet tier ---
    if wallet in TIER_1_WALLETS:
        base = 60                               # Tier 1: proven directional trader
    elif signal_type == "convergence":
        base = 10 * max(wallet_count, 1)       # Tier 2: 4 wallets=40, 5 wallets=50
    else:
        base = 10                               # Tier 3: single unvetted wallet

    # --- Repeat convergence bonus (+10 per additional detection) ---
    if convergence_count > 1:
        base += (convergence_count - 1) * 10

    # --- DexScreener bonuses ---
    if dex_data:
        # Token age bonus (up to 15 points)
        pair_created_ms = dex_data.get("pairCreatedAt", 0) or 0
        if pair_created_ms > 0:
            age_days = (time.time() * 1000 - pair_created_ms) / (1000 * 86400)
            base += min(int(age_days), 15)

        # Volume spike bonus (up to 20 points: spike_ratio * 3, capped at 20)
        vol = dex_data.get("volume", {})
        h1_vol  = vol.get("h1", 0) or 0
        h24_vol = vol.get("h24", 0) or 0
        if h24_vol > 0:
            avg_hourly = h24_vol / 24
            spike_ratio = h1_vol / avg_hourly if avg_hourly > 0 else 0
            base += min(int(spike_ratio * 3), 20)

    return min(base, 100)


def load_state() -> dict:
    if STATE_FILE.exists():
        state = json.loads(STATE_FILE.read_text())
        # Migrate old state without published_tokens_today
        if "published_tokens_today" not in state:
            state["published_tokens_today"] = []
        # Migrate old state without convergence_seen tracker
        if "convergence_seen" not in state:
            state["convergence_seen"] = {}
        return state
    return {
        "last_published_ts": 0,
        "total_published": 0,
        "published_today": 0,
        "today_date": str(date.today()),
        "published_tokens_today": [],
        "convergence_seen": {},
    }


def save_state(state: dict):
    STATE_FILE.write_text(json.dumps(state, indent=2))


def ordinal(n: int) -> str:
    """Return ordinal string: 1→'1st', 2→'2nd', 3→'3rd', 4→'4th', etc."""
    if 11 <= (n % 100) <= 13:
        return f"{n}th"
    return f"{n}{['th', 'st', 'nd', 'rd', 'th', 'th', 'th', 'th', 'th', 'th'][n % 10]}"


def update_convergence_seen(state: dict, token: str, token_symbol: str = "???") -> int:
    """
    Track a token's appearances as a convergence signal.
    Increments the appearance count, updates last_ts, and prunes entries
    older than CONVERGENCE_SEEN_TTL_HOURS (72h).
    Returns the updated appearance count for this token.
    """
    now_ts = int(time.time())
    cutoff_ts = now_ts - CONVERGENCE_SEEN_TTL_HOURS * 3600

    seen: dict = state.setdefault("convergence_seen", {})

    # Prune stale entries (older than 72h)
    stale_keys = [k for k, v in seen.items() if v.get("last_ts", 0) < cutoff_ts]
    for k in stale_keys:
        del seen[k]

    if token in seen:
        seen[token]["count"] += 1
        seen[token]["last_ts"] = now_ts
        # Update symbol if we have a real one now
        if token_symbol != "???":
            seen[token]["token_symbol"] = token_symbol
    else:
        seen[token] = {
            "count": 1,
            "first_ts": now_ts,
            "last_ts": now_ts,
            "token_symbol": token_symbol,
        }

    return seen[token]["count"]


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

    # --- Already-pumped filter: skip if >10% up in last 1h (Week 1 fix v2, was 15%) ---
    # 0% WR at T+1h confirms we're entering after the initial 10-15% move. 10% is the
    # more precise threshold — anything above that and we are already late.
    price_change = dex_data.get("priceChange", {})
    change_1h = price_change.get("h1", 0) or 0
    if change_1h > FILTER_MAX_PUMP_1H:
        return False, f"already pumped: +{change_1h:.1f}% in 1h > {FILTER_MAX_PUMP_1H}%"

    # --- Cascade dump guard: skip if down >20% in 6h (distribution, not accumulation) ---
    # Timeframe analysis 2026-03-09: LABUBU was -11.8% at 1h → -30.4% at 24h (cascading rug).
    # WAR was also -9.6% at 1h but recovered +10.9% at 24h (healthy dip).
    # The key distinguisher: if already down >20% in 6h it's distribution, not accumulation.
    # DexScreener returns h6 (6h) as the closest to 4h for price change data.
    change_6h = price_change.get("h6", 0) or 0
    if change_6h < -20:
        return False, f"cascading dump: {change_6h:.1f}% in 6h (likely distribution, not accumulation)"

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
    window = signal.get("window_minutes", PUBLISHED_WINDOW_MINUTES)
    conv_count = signal.get("convergence_count", 1)
    is_repeat = conv_count >= 2

    # Time formatting
    try:
        dt = datetime.fromisoformat(signal_time.replace("Z", "+00:00"))
        time_str = dt.strftime("%H:%M UTC")
    except Exception:
        time_str = "recent"

    # Confidence tag — repeat ULTRA gets distinct header
    if is_repeat:
        conf_emoji = "🚨"
        conv_ord = ordinal(conv_count)
        conf_tag = f"REPEAT CONVERGENCE — {conv_ord} detection [{wallets} whales]"
    elif confidence == "ULTRA":
        conf_emoji = "🔴"
        conf_tag = f"ULTRA [{wallets} whales]"
    else:
        conf_emoji = "🟡"
        conf_tag = f"HIGH [{wallets} whales]"

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

    # Repeat convergence banner (ULTRA repeat only)
    repeat_banner = ""
    if is_repeat:
        conv_ord = ordinal(conv_count)
        repeat_banner = f"\n⭐ {conv_ord} convergence detected — historically strongest signal tier\n"

    # Dexscreener + Birdeye links
    dex_url = f"https://dexscreener.com/solana/{token}"
    bird_url = f"https://birdeye.so/token/{token}?chain=solana"

    post = f"""{conf_emoji} WHALE ALERT — {conf_tag}{repeat_banner}
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
🏆 Quality: {signal.get("publisher_quality_score", "?")}/100 (Tier 2 — Convergence)
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

    # Publisher quality score + tier badge
    publisher_score = signal.get("publisher_quality_score", 0)
    is_tier1 = wallet in TIER_1_WALLETS
    if is_tier1:
        tier_badge = f"⭐ Tier 1 — Proven Smart Money (83% WR)"
        alert_header = f"⭐ TIER 1 SIGNAL — {wallet}"
    else:
        tier_badge = f"Quality: {publisher_score}/100"
        alert_header = f"🐋 Smart Money Alert — {wallet}"

    # Links
    dex_url  = f"https://dexscreener.com/solana/{token}"
    bird_url = f"https://birdeye.so/token/{token}?chain=solana"

    post = f"""{alert_header}

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
🏆 {tier_badge}
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
        # Allowlist gate: if SW_ALLOWED_WALLETS is set, reject any wallet not in it.
        if SW_ALLOWED_WALLETS and wallet not in SW_ALLOWED_WALLETS:
            continue

        # --- Wallet quality tier gate ---
        # Tier 1 wallets (SM_10) bypass Grade A requirement — proven 83% WR.
        # Other wallets still require Grade A + score >= 0.6 (unvetted = Tier 3, blocked).
        is_tier1 = wallet in TIER_1_WALLETS
        score = r.get("quality_score", 0)
        if not is_tier1:
            if r.get("quality_grade") != "A":
                continue
            if score < SW_MIN_QUALITY_SCORE:
                continue
        # Tier 3 single-wallet signals (non-Tier-1, non-Grade-A) are blocked above.
        # They will be logged by live_watcher but not published to @OttoSignals.

        # Skip zero-amount (parsing failures) and dust trades (no conviction)
        amount_usd = r.get("amount_usd", 0) or 0
        if amount_usd == 0 and r.get("amount_sol", 0) == 0:
            continue
        if amount_usd < SW_MIN_BUY_USD:
            continue

        # Must be within lookback window
        ts_str = r.get("timestamp", "")
        try:
            ts = int(datetime.fromisoformat(ts_str.replace("Z", "+00:00")).timestamp())
        except Exception:
            continue
        if ts < cutoff_ts:
            continue

        # Keep best signal per token (Tier 1 always wins over non-Tier-1)
        existing = best_per_token.get(token)
        prefer_this = (
            existing is None
            or (is_tier1 and existing.get("wallet", "") not in TIER_1_WALLETS)
            or score > existing.get("quality_score", 0)
        )
        if prefer_this:
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

    # Check for duplicate signal_id before appending to prevent re-notification
    if PERF_FILE.exists():
        for line in PERF_FILE.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                existing = json.loads(line)
                if existing.get("signal_id") == sig_id:
                    print(f"[publisher] Skipping duplicate performance entry: {sig_id} ({token_symbol})")
                    return
            except Exception:
                continue

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

        # --- Repeat convergence tracking ---
        # Track this convergence appearance BEFORE quality filters so we count every
        # detection (not just published ones). Symbol updated after dex_data fetch.
        conv_count = update_convergence_seen(state, token, "???")
        # Make a mutable copy of the signal dict to add tracking fields
        signal = dict(signal)
        signal["convergence_count"] = conv_count
        if conv_count >= 2:
            signal["confidence"] = "ULTRA"
            conv_ord = ordinal(conv_count)
            print(f"[publisher] ⭐ REPEAT CONVERGENCE: {token[:16]}... ({conv_ord} detection) → upgraded to ULTRA")
        # --- End repeat convergence tracking ---

        print(f"[publisher] [CONVERGENCE] Processing: {token[:20]}... | {signal['confidence']} | wallets={signal['wallet_count']}")

        dex_data = await fetch_dex_data(token)

        # Update symbol in convergence_seen now that we have dex_data
        if dex_data:
            token_symbol = dex_data.get("baseToken", {}).get("symbol", "???")
            if token_symbol != "???" and token in state["convergence_seen"]:
                state["convergence_seen"][token]["token_symbol"] = token_symbol

        if not no_filters:
            if dex_data is None:
                print(f"[publisher] SKIP: No DexScreener data for {token[:16]}...")
                save_state(state)  # Persist convergence_seen even for skipped signals
                continue
            passes, reason = apply_quality_filters(signal, dex_data)
            if not passes:
                print(f"[publisher] FILTERED OUT: {reason}")
                save_state(state)  # Persist convergence_seen even for filtered signals
                continue
            print(f"[publisher] PASSES filters: {reason}")

        # --- Publisher quality score (wallet tier + convergence count + token age + volume) ---
        pub_score = compute_publisher_quality_score(
            wallet="",
            signal_type="convergence",
            wallet_count=signal["wallet_count"],
            convergence_count=signal.get("convergence_count", 1),
            dex_data=dex_data,
        )
        signal["publisher_quality_score"] = pub_score
        print(f"[publisher] Quality score: {pub_score}/100 (wallets={signal['wallet_count']}, conv_count={signal.get('convergence_count', 1)})")
        if pub_score < MIN_PUBLISHER_QUALITY_SCORE:
            print(f"[publisher] BLOCKED by quality tier: score={pub_score} < {MIN_PUBLISHER_QUALITY_SCORE} (need more wallets or older token)")
            save_state(state)
            continue

        tp_sl = None
        if dex_data:
            price_usd = float(dex_data.get("priceUsd", 0) or 0)
            if price_usd > 0:
                tp_sl = compute_tp_sl(price_usd)
                print(f"[publisher] Entry: {format_price(price_usd)} | TP1: {format_price(tp_sl['tp1'])} | SL: {format_price(tp_sl['sl'])}")

        signal_type = "convergence_ultra" if conv_count >= 2 else "convergence"
        post = format_signal_post(signal, dex_data, tp_sl)

        if dry_run:
            print("--- DRY RUN [CONVERGENCE] ---")
            print(post)
            print("-----------------------------")
            published += 1
            if dex_data:
                record_signal_performance(signal, dex_data, tp_sl, signal_type=signal_type)
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
                    record_signal_performance(signal, dex_data, tp_sl, signal_type=signal_type)
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
            is_tier1_signal = wallet in TIER_1_WALLETS
            tier_label = "TIER 1 ⭐" if is_tier1_signal else "Tier 3"
            print(f"[publisher] [SINGLE-WALLET] Processing: {token[:20]}... | {wallet} ({tier_label}) | watcher_score={score:.3f}")

            dex_data = await fetch_dex_data(token)

            # --- Publisher quality score (wallet tier + token age + volume) ---
            pub_score = compute_publisher_quality_score(
                wallet=wallet,
                signal_type="single_wallet",
                wallet_count=1,
                convergence_count=1,
                dex_data=dex_data,
            )
            signal = dict(signal)
            signal["publisher_quality_score"] = pub_score
            print(f"[publisher] Quality score: {pub_score}/100 ({tier_label})")
            if pub_score < MIN_PUBLISHER_QUALITY_SCORE:
                print(f"[publisher] BLOCKED by quality tier: score={pub_score} < {MIN_PUBLISHER_QUALITY_SCORE} ({tier_label} → not publishing)")
                continue

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

    # Always persist convergence_seen at end of run (may have tracked signals that
    # were filtered out or skipped — these still count as convergence appearances)
    save_state(state)

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
