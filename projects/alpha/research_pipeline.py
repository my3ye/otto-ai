#!/usr/bin/env python3
"""
Progressive Research Pipeline — v2 (Measurement-First)

Major changes from v1:
  - Phase 0: UPDATE signal performance with real Birdeye price data.
             OHLCV between signal_ts and now tells us TP1/SL hit status.
             This replaces the "hypothesize forever" loop.
  - Phase 1: Compute actual win rate statistics from updated data.
  - Phase 2: Only call Claude if new measurements exist (saves budget on idle cycles).
  - Phase 3: Prune hypothesis/action-item lists (cap at 8/3, remove duplicates).

Root cause of v1 failure: Claude kept saying "implement retroactive PnL backtest" for
9 consecutive iterations but the pipeline never did it. v2 does the measurement first,
then passes real data to Claude for analysis.

State file: ~/otto/projects/alpha/research_state.json
"""

import json
import os
import subprocess
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path

# ── Paths ────────────────────────────────────────────────────────────────────
ALPHA_DIR   = Path(__file__).parent
STATE_FILE  = ALPHA_DIR / "research_state.json"
SIGNALS_FILE = ALPHA_DIR / "signals.jsonl"
PERF_FILE   = ALPHA_DIR / "signals" / "signal_performance.jsonl"
WA_SEND     = Path.home() / "otto" / "tools" / "whatsapp_send.sh"
LOG_FILE    = Path.home() / "otto" / "logs" / "research_pipeline.log"

# Birdeye client lives in bot/
BOT_DIR = ALPHA_DIR / "bot"
sys.path.insert(0, str(BOT_DIR))
sys.path.insert(0, str(ALPHA_DIR))

CLAUDE_CLI  = Path.home() / ".local" / "bin" / "claude"

# Import implementation executor (DexScreener-based, no API key required)
try:
    from pipeline_executor import run_implementation_cycle, compute_backtest_metrics, apply_strategy_updates
    HAS_EXECUTOR = True
except ImportError:
    HAS_EXECUTOR = False
MAX_BUDGET  = "0.15"       # USD per Claude call — only used when new data exists
MAX_HYPOTHESES  = 8        # Prune to this after each cycle
MAX_ACTION_ITEMS = 3       # Keep only 3 most recent/relevant action items
MAX_FINDINGS    = 15       # Cap stored findings

# TP/SL thresholds (match signal publisher)
TP1_PCT = 0.10   # +10%
TP2_PCT = 0.25   # +25%
TP3_PCT = 0.50   # +50%
SL_PCT  = -0.15  # -15%


# ── Logging ──────────────────────────────────────────────────────────────────
def log(msg: str):
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")


# ── State ────────────────────────────────────────────────────────────────────
def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except Exception as e:
            log(f"State load error: {e} — starting fresh")
    return {
        "iteration": 0,
        "first_run_done": False,
        "last_run": None,
        "last_claude_call": None,
        "total_signals_measured": 0,
        "hypotheses": [
            "SM_10 is the only directional trader (83% WR) — signals from SM_10 solo are highest quality",
            "Convergence signals (2+ wallets on same token within 1h) achieve >60% win rate vs single-wallet",
            "Wallet pool contains LP/bot positions — fee-payer cluster re-qualification needed",
            "TP1 (+10%) hit rate correlates with quality_score > 0.72 threshold",
            "Tokens with >$100k DEX liquidity have higher TP hit rates than low-liquidity tokens",
        ],
        "findings": [],
        "confirmed_actions": [],
        "action_items": [
            "Re-qualify wallet pool using Birdeye API to remove LP/bot positions",
            "Implement TP1/SL exits: TP1=+10%, SL=-15% (track actual hit rates)",
        ],
    }


def save_state(state: dict):
    # Prune to avoid bloat
    state["findings"] = state["findings"][-MAX_FINDINGS:]
    state["hypotheses"] = state["hypotheses"][-MAX_HYPOTHESES:]
    state["action_items"] = list(dict.fromkeys(state["action_items"]))[-MAX_ACTION_ITEMS:]  # dedupe + cap
    state["last_run"] = datetime.now(timezone.utc).isoformat()
    STATE_FILE.write_text(json.dumps(state, indent=2))


# ── Birdeye: Get current price for a token ───────────────────────────────────
def _get_birdeye_key() -> str:
    """Load BIRDEYE_API_KEY from env files or OS environment."""
    key = os.environ.get("BIRDEYE_API_KEY", "")
    if key:
        return key
    for env_file in [ALPHA_DIR / ".env", Path.home() / "memory" / ".env"]:
        if env_file.exists():
            for line in env_file.read_text().splitlines():
                line = line.strip()
                if line.startswith("BIRDEYE_API_KEY="):
                    val = line.split("=", 1)[1].strip()
                    if val:
                        return val
    return ""


def get_token_price_now(token_address: str, api_key: str) -> float | None:
    """Get current token price via Birdeye token_overview (free tier)."""
    import httpx
    try:
        url = "https://public-api.birdeye.so/defi/token_overview"
        headers = {
            "X-API-KEY": api_key,
            "x-chain": "solana",
            "accept": "application/json",
        }
        with httpx.Client(timeout=15.0) as client:
            resp = client.get(url, headers=headers, params={"address": token_address})
            if resp.status_code == 429:
                log(f"  Birdeye rate limit on {token_address[:8]}")
                return None
            if resp.status_code != 200:
                return None
            data = resp.json().get("data", {}) or {}
            price = data.get("price") or data.get("priceUsd")
            return float(price) if price else None
    except Exception as e:
        log(f"  Birdeye error for {token_address[:8]}: {e}")
        return None


def get_token_ohlcv_range(
    token_address: str, time_from: int, time_to: int, api_key: str
) -> list[dict]:
    """Get 1H OHLCV candles for a token between two unix timestamps."""
    import httpx
    try:
        url = "https://public-api.birdeye.so/defi/ohlcv"
        headers = {
            "X-API-KEY": api_key,
            "x-chain": "solana",
            "accept": "application/json",
        }
        params = {
            "address": token_address,
            "type": "1H",
            "time_from": time_from,
            "time_to": time_to,
        }
        with httpx.Client(timeout=20.0) as client:
            resp = client.get(url, headers=headers, params=params)
            if resp.status_code != 200:
                return []
            data = resp.json().get("data", {})
            return data.get("items", []) or []
    except Exception:
        return []


# ── Phase 0: Update signal performance with real Birdeye data ────────────────
def update_signal_performance() -> dict:
    """
    For each unique open signal in signal_performance.jsonl:
      1. Fetch OHLCV from signal_ts to now
      2. Determine if TP1/SL was hit (using candle high/low)
      3. Compute current PnL for still-open signals
      4. Update the file with status changes

    Returns a summary dict with measurement stats.
    """
    if not PERF_FILE.exists():
        log("signal_performance.jsonl not found — skipping measurement phase")
        return {"signals_measured": 0, "newly_closed": 0, "error": "file not found"}

    api_key = _get_birdeye_key()
    if not api_key:
        log("No Birdeye API key — skipping measurement phase")
        return {"signals_measured": 0, "newly_closed": 0, "error": "no api key"}

    # Load all signals (last-write-wins per signal_id for dedup)
    signals_by_id: dict[str, dict] = {}
    with open(PERF_FILE) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                s = json.loads(line)
                signals_by_id[s["signal_id"]] = s
            except Exception:
                continue

    now_ts = int(time.time())
    newly_closed = 0
    updated = 0

    # Process open signals
    open_signals = [s for s in signals_by_id.values() if s.get("status") == "open"]
    log(f"Updating {len(open_signals)} open signals via Birdeye ({len(signals_by_id)} total unique)...")

    for sig in open_signals:
        token = sig.get("token", "")
        entry_price = float(sig.get("entry_price", 0) or 0)
        if not token or entry_price <= 0:
            continue

        signal_ts = int(sig.get("signal_ts", now_ts - 3600))
        age_hours = (now_ts - signal_ts) / 3600

        # Fetch OHLCV from signal time to now
        candles = get_token_ohlcv_range(token, signal_ts, now_ts, api_key)
        time.sleep(0.7)  # Rate limit: 100 req/min

        if not candles:
            # Fall back to current price only
            current_price = get_token_price_now(token, api_key)
            time.sleep(0.7)
            if current_price and current_price > 0:
                pnl_pct = (current_price - entry_price) / entry_price * 100
                sig["current_price"] = round(current_price, 8)
                sig["current_pnl_pct"] = round(pnl_pct, 2)
                updated += 1
            continue

        # Find max high and min low since signal time
        max_high = max(
            float(c.get("h", c.get("high", entry_price)) or entry_price)
            for c in candles
        )
        min_low = min(
            float(c.get("l", c.get("low", entry_price)) or entry_price)
            for c in candles
        )
        current_close = float(candles[-1].get("c", candles[-1].get("close", entry_price)) or entry_price)

        # TP/SL calculations
        tp1_price = entry_price * (1 + TP1_PCT)
        tp2_price = entry_price * (1 + TP2_PCT)
        tp3_price = entry_price * (1 + TP3_PCT)
        sl_price  = entry_price * (1 + SL_PCT)   # negative offset = lower price

        tp1_hit = max_high >= tp1_price
        tp2_hit = max_high >= tp2_price
        tp3_hit = max_high >= tp3_price
        sl_hit  = min_low  <= sl_price

        sig["tp1_hit"] = tp1_hit
        sig["tp2_hit"] = tp2_hit
        sig["tp3_hit"] = tp3_hit
        sig["sl_hit"]  = sl_hit
        sig["max_price_since_entry"] = round(max_high, 8)
        sig["min_price_since_entry"] = round(min_low, 8)
        sig["current_price"] = round(current_close, 8)

        # Determine final outcome (if signal is old enough: >48h)
        if age_hours >= 48:
            if sl_hit and not tp1_hit:
                sig["status"] = "closed_sl"
                sig["final_pnl"] = round(SL_PCT * 100, 1)  # -15%
                sig["closed_at"] = datetime.now(timezone.utc).isoformat()
                newly_closed += 1
            elif tp3_hit:
                sig["status"] = "closed_tp3"
                sig["final_pnl"] = round(TP3_PCT * 100, 1)  # +50%
                sig["closed_at"] = datetime.now(timezone.utc).isoformat()
                newly_closed += 1
            elif tp2_hit:
                sig["status"] = "closed_tp2"
                sig["final_pnl"] = round(TP2_PCT * 100, 1)  # +25%
                sig["closed_at"] = datetime.now(timezone.utc).isoformat()
                newly_closed += 1
            elif tp1_hit:
                sig["status"] = "closed_tp1"
                sig["final_pnl"] = round(TP1_PCT * 100, 1)  # +10%
                sig["closed_at"] = datetime.now(timezone.utc).isoformat()
                newly_closed += 1
            else:
                # Neither TP1 nor SL — expired at current price
                pnl_pct = (current_close - entry_price) / entry_price * 100
                sig["status"] = "closed_expired"
                sig["final_pnl"] = round(pnl_pct, 2)
                sig["closed_at"] = datetime.now(timezone.utc).isoformat()
                newly_closed += 1
        else:
            # Still open — compute current PnL
            pnl_pct = (current_close - entry_price) / entry_price * 100
            sig["current_pnl_pct"] = round(pnl_pct, 2)

        updated += 1

    # Write updated signals back (all unique, one line per signal_id)
    if updated > 0:
        with open(PERF_FILE, "w") as f:
            for sig in signals_by_id.values():
                f.write(json.dumps(sig) + "\n")
        log(f"Updated {updated} signals | {newly_closed} newly closed")

    return {
        "signals_measured": len(open_signals),
        "newly_closed": newly_closed,
        "updated": updated,
    }


# ── Phase 1: Compute signal performance statistics ───────────────────────────
def analyze_performance() -> dict:
    """Parse signal_performance.jsonl and compute TP/SL stats with real data."""
    if not PERF_FILE.exists():
        return {"error": "signal_performance.jsonl not found"}

    signals_by_id: dict[str, dict] = {}
    with open(PERF_FILE) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                s = json.loads(line)
                signals_by_id[s["signal_id"]] = s
            except Exception:
                continue

    open_signals   = [s for s in signals_by_id.values() if s.get("status") == "open"]
    closed_signals = [s for s in signals_by_id.values() if s.get("status", "").startswith("closed_")]

    # TP/SL breakdown
    tp1_hits = sum(1 for s in closed_signals if s.get("tp1_hit"))
    tp2_hits = sum(1 for s in closed_signals if s.get("tp2_hit"))
    tp3_hits = sum(1 for s in closed_signals if s.get("tp3_hit"))
    sl_hits  = sum(1 for s in signals_by_id.values() if s.get("sl_hit"))
    expired  = sum(1 for s in closed_signals if s.get("status") == "closed_expired")

    # Win rate (tp1+ hit = win, sl = loss)
    pnls = [s.get("final_pnl") for s in closed_signals if s.get("final_pnl") is not None]
    wins = [p for p in pnls if p > 0]
    win_rate = round(len(wins) / len(pnls) * 100, 1) if pnls else None
    avg_pnl  = round(sum(pnls) / len(pnls), 2) if pnls else None

    # Win rate by wallet
    wallet_stats: dict[str, dict] = defaultdict(lambda: {"wins": 0, "total": 0, "pnl_sum": 0.0})
    for s in closed_signals:
        w = s.get("wallet", "?")
        pnl = s.get("final_pnl")
        if pnl is not None:
            wallet_stats[w]["total"] += 1
            wallet_stats[w]["pnl_sum"] += pnl
            if pnl > 0:
                wallet_stats[w]["wins"] += 1

    wallet_summary = {}
    for w, stats in wallet_stats.items():
        n = stats["total"]
        if n > 0:
            wallet_summary[w] = {
                "win_rate": round(stats["wins"] / n * 100, 1),
                "trades": n,
                "avg_pnl": round(stats["pnl_sum"] / n, 2),
            }

    # Current PnL for open signals
    open_pnls = [s.get("current_pnl_pct") for s in open_signals if s.get("current_pnl_pct") is not None]
    avg_open_pnl = round(sum(open_pnls) / len(open_pnls), 2) if open_pnls else None

    return {
        "open_signals":    len(open_signals),
        "closed_signals":  len(closed_signals),
        "tp1_hits": tp1_hits,
        "tp2_hits": tp2_hits,
        "tp3_hits": tp3_hits,
        "sl_hits":  sl_hits,
        "expired":  expired,
        "win_rate_pct":  win_rate,
        "avg_pnl_pct":   avg_pnl,
        "avg_open_pnl":  avg_open_pnl,
        "wallet_stats":  wallet_summary,
        "total_unique_signals": len(signals_by_id),
    }


# ── Phase 2: Signal volume analysis ─────────────────────────────────────────
def analyze_signals() -> dict:
    """Parse signals.jsonl and compute stats for last 24h and last 3h."""
    if not SIGNALS_FILE.exists():
        return {"error": "signals.jsonl not found"}

    now_ts = datetime.now(timezone.utc).timestamp()
    cutoff_3h  = now_ts - 3 * 3600
    cutoff_24h = now_ts - 24 * 3600

    signals_3h  = []
    signals_24h = []
    wallet_counts: dict = defaultdict(int)

    seen_ids_3h  = set()
    seen_ids_24h = set()

    try:
        with open(SIGNALS_FILE) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    s = json.loads(line)
                except Exception:
                    continue
                ts_str = s.get("timestamp", "")
                if not ts_str:
                    continue
                try:
                    ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00")).timestamp()
                except Exception:
                    continue

                token = s.get("token", "")
                wallets_raw = s.get("wallets", "")
                sid = f"{token}:{wallets_raw}"

                if ts >= cutoff_24h and sid not in seen_ids_24h:
                    seen_ids_24h.add(sid)
                    signals_24h.append(s)
                    wallet_list = wallets_raw.split() if isinstance(wallets_raw, str) else (wallets_raw or [])
                    for w in wallet_list:
                        wallet_counts[w.strip()] += 1
                    if ts >= cutoff_3h and sid not in seen_ids_3h:
                        seen_ids_3h.add(sid)
                        signals_3h.append(s)

        top_wallets = sorted(wallet_counts.items(), key=lambda x: x[1], reverse=True)[:5]

        return {
            "last_3h":  {"count": len(signals_3h)},
            "last_24h": {"count": len(signals_24h)},
            "top_wallets_24h": top_wallets,
        }
    except Exception as e:
        return {"error": str(e)}


# ── Phase 3: Claude research (only when new data) ─────────────────────────────
def build_research_prompt(state: dict, signal_stats: dict, perf_stats: dict) -> str:
    prev_findings = state["findings"][-3:] if state["findings"] else []
    findings_text = "\n".join(
        f"  - [iter {f.get('iteration','?')}] {f.get('finding','')}"
        for f in prev_findings
    ) or "  (none yet)"
    hypotheses_text = "\n".join(
        f"  {i+1}. {h}" for i, h in enumerate(state["hypotheses"])
    )
    actions_text = "\n".join(f"  - {a}" for a in state["action_items"][:3])

    perf_json = json.dumps(perf_stats, indent=2)
    signals_json = json.dumps({
        "last_3h": signal_stats.get("last_3h", {}),
        "last_24h": signal_stats.get("last_24h", {}),
        "top_wallets_24h": signal_stats.get("top_wallets_24h", []),
    }, indent=2)

    # Load current strategy config for Claude context
    config_path = ALPHA_DIR / "strategy_config.json"
    current_config_summary = {}
    if config_path.exists():
        try:
            cfg = json.loads(config_path.read_text())
            current_config_summary = {
                "min_quality_score": cfg.get("single_wallet", {}).get("min_quality_score", 0.6),
                "max_pump_1h": cfg.get("quality_filters", {}).get("max_pump_1h", 10.0),
                "min_token_age_days": cfg.get("quality_filters", {}).get("min_token_age_days", 7),
                "last_auto_change": cfg.get("changes_log", [{}])[-1].get("change", "none") if cfg.get("changes_log") else "none",
            }
        except Exception:
            pass

    return f"""You are Otto's Progressive Research Agent for crypto signal quality improvement.
This is iteration {state['iteration'] + 1}.

IMPORTANT CONTEXT:
- Otto publishes signals to Telegram @OttoSignals. No auto-trading. No execution layer.
- Signals are informational only. Focus on signal QUALITY, not execution.
- TP/SL outcomes are now tracked via DexScreener (real price data, no API key required).
- Strategy config is auto-updated by pipeline_executor.py each cycle based on win rate.
- Do NOT suggest "implement retroactive PnL backtest" — it is already running each cycle.
- Do NOT suggest "implement auto-update" — it is already implemented.

## Current Strategy Config (auto-managed)
{json.dumps(current_config_summary, indent=2)}

## Real Signal Performance (updated this cycle via DexScreener + Birdeye)
{perf_json}

## Signal Volume Stats
{signals_json}

## Active Hypotheses
{hypotheses_text}

## Recent Findings
{findings_text}

## Outstanding Action Items
{actions_text}

## Your Task
1. Analyze the REAL performance data above — which hypotheses are confirmed/refuted?
2. What patterns appear in the wallet stats (win rate, avg PnL by wallet)?
3. What single configuration change would improve signal quality most?
   (Examples: raise quality_score threshold, filter by wallet, add convergence requirement)
4. Propose max 2 NEW hypotheses (testable, specific, not already in the list)

Focus ONLY on what the data shows. No speculation without data.
Reference specific numbers from the performance stats.

## Output Format (strict JSON)
```json
{{
  "primary_finding": "One sentence — most important insight from real data",
  "significance": "LOW|MEDIUM|HIGH",
  "significance_reason": "Why — HIGH only for actionable breakthrough with data evidence",
  "hypothesis_updates": [
    {{"hypothesis": "exact text from list", "verdict": "CONFIRMED|REFUTED|NEEDS_MORE_DATA", "evidence": "specific data point"}}
  ],
  "new_hypotheses": ["hypothesis 1 (max 2)"],
  "top_action": "Single best config change to make right now — specific and executable",
  "additional_observations": ["obs 1 (max 2)"]
}}
```
Output ONLY the JSON block, no prose before or after.
"""


def run_claude_research(prompt: str) -> dict | None:
    """Call Claude CLI with research prompt, return parsed JSON findings."""
    try:
        result = subprocess.run(
            [
                str(CLAUDE_CLI),
                "--print",
                "--dangerously-skip-permissions",
                "--model", "haiku",
                f"--max-budget-usd={MAX_BUDGET}",
                "-p", prompt,
            ],
            capture_output=True, text=True, timeout=180
        )
        output = result.stdout.strip()
        if result.returncode != 0:
            log(f"Claude exit {result.returncode}: {result.stderr[:200]}")

        start = output.find("{")
        end   = output.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(output[start:end])
        else:
            log(f"No JSON in Claude output: {output[:300]}")
            return None
    except subprocess.TimeoutExpired:
        log("Claude research timed out (180s)")
        return None
    except Exception as e:
        log(f"Claude research error: {e}")
        return None


# ── Notification ─────────────────────────────────────────────────────────────
def send_whatsapp(msg: str):
    if not WA_SEND.exists():
        log(f"WhatsApp send script not found: {WA_SEND}")
        return
    try:
        subprocess.run([str(WA_SEND), msg], timeout=30, check=False)
        log("WhatsApp notification sent")
    except Exception as e:
        log(f"WhatsApp send failed: {e}")


# ── Main ─────────────────────────────────────────────────────────────────────
def main():
    log("=== Research Pipeline v2 Starting ===")

    state = load_state()
    iteration = state["iteration"] + 1
    log(f"Iteration {iteration} | Prev findings: {len(state['findings'])} | Hypotheses: {len(state['hypotheses'])}")

    # Phase 0a: Run DexScreener-based performance check (no API key, always available)
    executor_result = {}
    if HAS_EXECUTOR:
        log("Phase 0a: Implementation cycle — closing signals via DexScreener...")
        executor_result = run_implementation_cycle()
        log(f"Executor: {executor_result.get('changes_count', 0)} strategy changes applied")
    else:
        log("Phase 0a: pipeline_executor not available — skipping DexScreener check")

    # Phase 0b: Update signal performance with real Birdeye data (if key available)
    log("Phase 0b: Updating signal performance via Birdeye (if key available)...")
    measurement_result = update_signal_performance()
    newly_closed   = measurement_result.get("newly_closed", 0)
    signals_measured = measurement_result.get("signals_measured", 0)

    # If Birdeye failed, check if DexScreener closed anything
    if newly_closed == 0 and executor_result:
        exec_metrics = executor_result.get("metrics", {})
        newly_closed = max(newly_closed, exec_metrics.get("closed_count", 0))

    state["total_signals_measured"] = state.get("total_signals_measured", 0) + signals_measured

    # Phase 1: Compute real stats
    log("Phase 1: Computing performance statistics...")
    perf_stats   = analyze_performance()
    signal_stats = analyze_signals()

    log(
        f"Perf: {perf_stats.get('closed_signals', 0)} closed | "
        f"WR: {perf_stats.get('win_rate_pct', 'N/A')}% | "
        f"Avg PnL: {perf_stats.get('avg_pnl_pct', 'N/A')}% | "
        f"Signals 24h: {signal_stats.get('last_24h', {}).get('count', 0)}"
    )

    # Phase 2: Decide whether to call Claude
    # Call Claude if: (a) newly closed signals, (b) first run, (c) haven't called in 12+ hours
    last_claude = state.get("last_claude_call")
    hours_since_claude = 999
    if last_claude:
        try:
            last_dt = datetime.fromisoformat(last_claude.replace("Z", "+00:00"))
            hours_since_claude = (datetime.now(timezone.utc) - last_dt).total_seconds() / 3600
        except Exception:
            pass

    # DEDUP GUARD: Skip Claude call if the last 3+ findings share the same top_action.
    # This prevents burning budget on identical analyses when data hasn't changed.
    # Use 50-char prefix — LLM rephrases diverge after char ~50-60, but intent is stable.
    recent_findings = state.get("findings", [])[-3:]
    recent_actions = [f.get("top_action", "").strip()[:50] for f in recent_findings]
    # If all 3 most recent top_actions are non-empty and identical (by 50-char prefix), skip
    all_same_action = (
        len(recent_actions) >= 3
        and len(set(a for a in recent_actions if a)) == 1
        and not newly_closed  # Only skip if no new data this cycle
    )
    if all_same_action:
        log(f"Phase 2: Skipping Claude call — last {len(recent_actions)} findings have identical top_action prefix (data unchanged)")

    should_research = (
        not all_same_action  # Don't call if data is clearly stale (same finding repeated)
        and (
            newly_closed > 0                        # New closures = new data to analyze
            or not state.get("first_run_done")      # First run ever
            or hours_since_claude >= 12             # Been 12+ hours since last analysis
            or perf_stats.get("closed_signals", 0) > 0 and iteration <= 2  # First 2 iters with data
        )
    )

    findings = None
    if should_research:
        log(f"Phase 2: Running Claude research (newly_closed={newly_closed}, hours_since={hours_since_claude:.1f}h)...")
        prompt = build_research_prompt(state, signal_stats, perf_stats)
        findings = run_claude_research(prompt)
        state["last_claude_call"] = datetime.now(timezone.utc).isoformat()

        if findings is None:
            log("Research agent produced no output — skipping hypothesis updates")
        else:
            log(f"Finding: [{findings.get('significance', '?')}] {findings.get('primary_finding', '')[:100]}")

            # Store finding
            state["findings"].append({
                "iteration": iteration,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "finding":   findings.get("primary_finding", ""),
                "significance": findings.get("significance", "LOW"),
                "top_action": findings.get("top_action", ""),
            })

            # Update hypotheses
            for update in findings.get("hypothesis_updates", []):
                verdict = update.get("verdict", "")
                hyp     = update.get("hypothesis", "")
                if verdict == "REFUTED":
                    state["hypotheses"] = [h for h in state["hypotheses"] if h != hyp]
                    log(f"Hypothesis REFUTED → removed: {hyp[:60]}")
                elif verdict == "CONFIRMED":
                    log(f"Hypothesis CONFIRMED: {hyp[:60]}")

            # Add new hypotheses (max 2)
            for new_hyp in findings.get("new_hypotheses", [])[:2]:
                if new_hyp and new_hyp not in state["hypotheses"]:
                    state["hypotheses"].append(new_hyp)
                    log(f"New hypothesis: {new_hyp[:80]}")

            # Update action items (add new top_action, replace if similar)
            top_action = findings.get("top_action", "")
            if top_action and top_action not in state["action_items"]:
                state["action_items"].append(top_action)
    else:
        log(f"Phase 2: Skipping Claude research (no new closures, {hours_since_claude:.1f}h since last call)")

    # Phase 2b: Auto-update strategy config based on backtest metrics
    if HAS_EXECUTOR:
        log("Phase 2b: Applying strategy auto-updates based on backtest metrics...")
        backtest_metrics = compute_backtest_metrics()
        auto_changes = apply_strategy_updates(backtest_metrics)
        if auto_changes:
            log(f"Auto-updated strategy config: {len(auto_changes)} change(s)")
            for c in auto_changes:
                change_summary = c.get("change", "")
                log(f"  → {change_summary}")
            # Add to findings if significant
            if any(c.get("field", "").startswith("single_wallet") for c in auto_changes):
                state["findings"].append({
                    "iteration": iteration,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "finding": f"Auto-updated strategy config: {', '.join(c.get('change', '') for c in auto_changes[:2])}",
                    "significance": "MEDIUM",
                    "top_action": "Strategy config updated automatically — monitor next cycle for win rate change",
                })
        else:
            log("Phase 2b: No strategy updates needed this cycle")

    # Phase 3: Update iteration and save
    state["iteration"] = iteration
    save_state(state)
    log(f"State saved — iter {iteration} | hypotheses: {len(state['hypotheses'])}")

    # Phase 4: Notification logic
    significance = findings.get("significance", "LOW") if findings else "LOW"
    is_first_run = not state.get("first_run_done", False)

    if is_first_run and findings:
        closed = perf_stats.get("closed_signals", 0)
        wr = perf_stats.get("win_rate_pct", "N/A")
        msg = (
            f"[Research Pipeline v2] Cycle 1 complete\n"
            f"Signals measured: {signals_measured} | Closed: {closed} | WR: {wr}%\n"
            f"Finding [{significance}]: {findings.get('primary_finding', '')[:200]}\n"
            f"Top action: {findings.get('top_action', '')[:150]}\n"
            f"v2 now measures actual TP/SL hit rates via Birdeye. Will notify on HIGH findings only."
        )
        send_whatsapp(msg)
        state["first_run_done"] = True
        save_state(state)

    elif significance == "HIGH" and findings:
        # DEDUP GUARD: Only notify if this top_action hasn't been notified recently.
        # Key: normalized first 50 chars of top_action — stable across LLM rephrasing.
        top_action_key = findings.get("top_action", "").strip()[:50]
        notified_actions = state.get("notified_actions", {})
        last_notified_ts = notified_actions.get(top_action_key, 0)
        hours_since_notified = (time.time() - float(last_notified_ts)) / 3600 if last_notified_ts else 999

        if hours_since_notified < 48:
            log(
                f"Phase 4: Skipping HIGH notification — same action already notified "
                f"{hours_since_notified:.1f}h ago (dedup key: '{top_action_key[:50]}...')"
            )
        else:
            msg = (
                f"[Research - HIGH] Iter {iteration}\n"
                f"Finding: {findings.get('primary_finding', '')[:200]}\n"
                f"WR: {perf_stats.get('win_rate_pct', 'N/A')}% ({perf_stats.get('closed_signals', 0)} signals)\n"
                f"Action: {findings.get('top_action', '')[:150]}"
            )
            send_whatsapp(msg)
            # Record notification — persist via state
            notified_actions[top_action_key] = time.time()
            # Prune old entries (keep only last 20)
            if len(notified_actions) > 20:
                oldest_key = min(notified_actions, key=lambda k: notified_actions[k])
                del notified_actions[oldest_key]
            state["notified_actions"] = notified_actions
            save_state(state)

    elif newly_closed > 0 and not is_first_run:
        log(f"Phase 4: {newly_closed} signals closed — no WhatsApp (not HIGH significance)")

    log(f"=== Research Pipeline v2 Complete (iter {iteration}) ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
