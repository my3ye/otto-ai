#!/usr/bin/env python3
"""
Pipeline Executor — Implementation Loop for Research Pipeline

Runs as part of research_pipeline.py each cycle. Does three things:
1. run_performance_check() — calls signal_performance.py --check to close open signals
2. compute_backtest_metrics() — analyzes closed signals, returns stats
3. apply_strategy_updates(metrics) — if enough data, tightens/relaxes filters and logs changes

This is the feedback loop that turns research findings into actual config changes.
All changes are written to strategy_config.json + logged with rationale.
"""

import asyncio
import json
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ALPHA_DIR    = Path(__file__).parent
SIGNALS_DIR  = ALPHA_DIR / "signals"
PERF_FILE    = SIGNALS_DIR / "signal_performance.jsonl"
CONFIG_FILE  = ALPHA_DIR / "strategy_config.json"
CHANGES_LOG  = ALPHA_DIR / "pipeline_changes.jsonl"

PYTHON = sys.executable


# ── Logging ──────────────────────────────────────────────────────────────────

def log(msg: str):
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    print(f"[executor {ts}] {msg}", flush=True)


# ── Config I/O ────────────────────────────────────────────────────────────────

def load_config() -> dict:
    if CONFIG_FILE.exists():
        try:
            return json.loads(CONFIG_FILE.read_text())
        except Exception as e:
            log(f"Config load error: {e}")
    # Return minimal defaults if missing
    return {
        "version": 1,
        "single_wallet": {"min_quality_score": 0.6},
        "quality_filters": {"max_pump_1h": 10.0},
        "auto_update": {
            "enabled": True,
            "min_closed_signals": 5,
            "win_rate_tighten_threshold": 0.40,
            "win_rate_relax_threshold": 0.65,
            "quality_score_step": 0.05,
            "quality_score_min": 0.55,
            "quality_score_max": 0.80,
            "max_changes_per_cycle": 2,
        },
        "changes_log": [],
    }


def save_config(config: dict):
    config["updated_at"] = datetime.now(timezone.utc).isoformat()
    CONFIG_FILE.write_text(json.dumps(config, indent=2))


# ── Step 1: Performance Check ─────────────────────────────────────────────────

def run_performance_check() -> dict:
    """
    Run signal_performance.py --check to close open signals.
    Returns summary of what was updated.
    """
    perf_script = SIGNALS_DIR / "signal_performance.py"
    if not perf_script.exists():
        log("signal_performance.py not found — skipping perf check")
        return {"error": "script not found"}

    log("Running signal performance check (DexScreener price lookup)...")
    try:
        result = subprocess.run(
            [PYTHON, str(perf_script), "--check"],
            capture_output=True, text=True, timeout=120,
            cwd=str(ALPHA_DIR),
        )
        output = result.stdout + result.stderr
        log(f"Perf check done (exit={result.returncode}). Output lines: {len(output.splitlines())}")
        if result.returncode != 0:
            log(f"Perf check stderr: {result.stderr[:300]}")
        # Parse summary line
        summary = {"exit_code": result.returncode, "output_snippet": output[-500:] if output else ""}
        for line in output.splitlines():
            if "Updated" in line and "entries" in line:
                summary["update_line"] = line.strip()
            if "No changes" in line:
                summary["update_line"] = "No changes"
        return summary
    except subprocess.TimeoutExpired:
        log("Perf check timed out (120s)")
        return {"error": "timeout"}
    except Exception as e:
        log(f"Perf check error: {e}")
        return {"error": str(e)}


# ── Step 2: Backtest Metrics ──────────────────────────────────────────────────

def compute_backtest_metrics() -> dict:
    """
    Analyze signal_performance.jsonl. Returns:
    - overall win_rate, avg_pnl
    - by_wallet: {wallet: {win_rate, n, avg_pnl}}
    - by_signal_type: {single_wallet|convergence: {win_rate, n}}
    - by_quality_tier: {<0.65, 0.65-0.75, >0.75}: {win_rate, n}
    - open_count, closed_count
    """
    if not PERF_FILE.exists():
        return {"error": "no perf file"}

    entries = []
    seen = set()
    for line in PERF_FILE.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            e = json.loads(line)
        except Exception:
            continue
        sid = e.get("signal_id", "")
        if sid in seen:
            continue
        seen.add(sid)
        entries.append(e)

    open_signals   = [e for e in entries if e.get("status") == "open"]
    closed_signals = [e for e in entries if e.get("status") != "open"]

    if not closed_signals:
        return {
            "open_count": len(open_signals),
            "closed_count": 0,
            "win_rate": None,
            "avg_pnl": None,
            "insufficient_data": True,
        }

    # Overall metrics
    pnls = [e["final_pnl"] for e in closed_signals if e.get("final_pnl") is not None]
    wins = [p for p in pnls if p > 0]
    overall_wr  = round(len(wins) / len(pnls), 3) if pnls else None
    avg_pnl     = round(sum(pnls) / len(pnls), 2) if pnls else None
    tp1_rate    = round(sum(1 for e in closed_signals if e.get("tp1_hit")) / len(closed_signals), 3)
    sl_rate     = round(sum(1 for e in closed_signals if e.get("sl_hit")) / len(closed_signals), 3)
    timeout_rate = round(sum(1 for e in closed_signals if e.get("status") == "timeout") / len(closed_signals), 3)

    # By wallet
    by_wallet: dict = defaultdict(lambda: {"wins": 0, "total": 0, "pnls": []})
    for e in closed_signals:
        w = e.get("wallet", "unknown")
        pnl = e.get("final_pnl")
        by_wallet[w]["total"] += 1
        if pnl is not None:
            by_wallet[w]["pnls"].append(pnl)
            if pnl > 0:
                by_wallet[w]["wins"] += 1

    wallet_stats = {}
    for w, d in by_wallet.items():
        n = d["total"]
        wr = round(d["wins"] / n, 3) if n > 0 else None
        ap = round(sum(d["pnls"]) / len(d["pnls"]), 2) if d["pnls"] else None
        wallet_stats[w] = {"n": n, "win_rate": wr, "avg_pnl": ap}

    # By signal type
    by_type: dict = defaultdict(lambda: {"wins": 0, "total": 0})
    for e in closed_signals:
        t = e.get("signal_type", "unknown")
        pnl = e.get("final_pnl")
        by_type[t]["total"] += 1
        if pnl is not None and pnl > 0:
            by_type[t]["wins"] += 1

    type_stats = {}
    for t, d in by_type.items():
        n = d["total"]
        wr = round(d["wins"] / n, 3) if n > 0 else None
        type_stats[t] = {"n": n, "win_rate": wr}

    # By quality tier
    tier_stats: dict = {
        "low (<0.65)":  {"wins": 0, "total": 0},
        "mid (0.65-0.75)": {"wins": 0, "total": 0},
        "high (>0.75)": {"wins": 0, "total": 0},
    }
    for e in closed_signals:
        qs  = e.get("quality_score", 0) or 0
        pnl = e.get("final_pnl")
        if qs < 0.65:
            tier = "low (<0.65)"
        elif qs <= 0.75:
            tier = "mid (0.65-0.75)"
        else:
            tier = "high (>0.75)"
        tier_stats[tier]["total"] += 1
        if pnl is not None and pnl > 0:
            tier_stats[tier]["wins"] += 1

    for tier, d in tier_stats.items():
        n = d["total"]
        d["win_rate"] = round(d["wins"] / n, 3) if n > 0 else None

    return {
        "open_count":    len(open_signals),
        "closed_count":  len(closed_signals),
        "win_rate":      overall_wr,
        "avg_pnl":       avg_pnl,
        "tp1_rate":      tp1_rate,
        "sl_rate":       sl_rate,
        "timeout_rate":  timeout_rate,
        "by_wallet":     wallet_stats,
        "by_signal_type": type_stats,
        "by_quality_tier": tier_stats,
    }


# ── Step 3: Auto-Update Strategy ─────────────────────────────────────────────

def apply_strategy_updates(metrics: dict) -> list[dict]:
    """
    Given backtest metrics, propose and apply strategy config changes.
    Returns list of changes made (empty if nothing changed).

    Rules:
    - Need min_closed_signals before making any changes
    - If overall win_rate < tighten_threshold → raise min_quality_score by step
    - If overall win_rate > relax_threshold AND was previously tightened → lower step
    - Quality score bounded by [quality_score_min, quality_score_max]
    - Log every change with rationale
    - Max 2 changes per cycle (don't make too many at once)
    """
    config = load_config()
    auto = config.get("auto_update", {})

    if not auto.get("enabled", True):
        log("Auto-update disabled in config — skipping")
        return []

    if metrics.get("insufficient_data") or metrics.get("error"):
        log(f"Insufficient data for auto-update: {metrics.get('error') or 'no closed signals'}")
        return []

    min_n   = auto.get("min_closed_signals", 5)
    closed  = metrics.get("closed_count", 0)
    if closed < min_n:
        log(f"Only {closed} closed signals (need {min_n}) — no auto-update yet")
        return []

    wr           = metrics.get("win_rate")
    tighten_thr  = auto.get("win_rate_tighten_threshold", 0.40)
    relax_thr    = auto.get("win_rate_relax_threshold", 0.65)
    step         = auto.get("quality_score_step", 0.05)
    qs_min       = auto.get("quality_score_min", 0.55)
    qs_max       = auto.get("quality_score_max", 0.80)
    max_changes  = auto.get("max_changes_per_cycle", 2)

    changes = []
    now_iso = datetime.now(timezone.utc).isoformat()

    sw_config = config.get("single_wallet", {})
    current_qs = sw_config.get("min_quality_score", 0.6)

    if wr is not None and wr < tighten_thr:
        new_qs = min(qs_max, round(current_qs + step, 3))
        if new_qs > current_qs:
            change = {
                "ts": now_iso,
                "field": "single_wallet.min_quality_score",
                "old": current_qs,
                "new": new_qs,
                "change": f"Raised quality threshold {current_qs} → {new_qs}",
                "rationale": (
                    f"Win rate {wr:.1%} is below {tighten_thr:.0%} threshold "
                    f"({closed} closed signals). Raising min_quality_score to filter "
                    f"lower-conviction signals."
                ),
                "metrics_snapshot": {
                    "closed_count": closed,
                    "win_rate": wr,
                    "avg_pnl": metrics.get("avg_pnl"),
                    "sl_rate": metrics.get("sl_rate"),
                },
            }
            config["single_wallet"]["min_quality_score"] = new_qs
            changes.append(change)
            log(f"AUTO-UPDATE: {change['change']} — {change['rationale'][:80]}")

    elif wr is not None and wr > relax_thr and current_qs > 0.6:
        # Only relax if we previously tightened (score above baseline 0.6)
        new_qs = max(0.6, round(current_qs - step, 3))
        if new_qs < current_qs:
            change = {
                "ts": now_iso,
                "field": "single_wallet.min_quality_score",
                "old": current_qs,
                "new": new_qs,
                "change": f"Lowered quality threshold {current_qs} → {new_qs}",
                "rationale": (
                    f"Win rate {wr:.1%} is above {relax_thr:.0%} threshold "
                    f"({closed} closed signals). Relaxing min_quality_score to "
                    f"increase signal volume while maintaining quality."
                ),
                "metrics_snapshot": {
                    "closed_count": closed,
                    "win_rate": wr,
                    "avg_pnl": metrics.get("avg_pnl"),
                },
            }
            config["single_wallet"]["min_quality_score"] = new_qs
            changes.append(change)
            log(f"AUTO-UPDATE: {change['change']} — {change['rationale'][:80]}")

    # Check quality tiers — if high-quality signals are outperforming, note it
    tiers = metrics.get("by_quality_tier", {})
    high_tier = tiers.get("high (>0.75)", {})
    low_tier  = tiers.get("low (<0.65)", {})
    if (high_tier.get("n", 0) >= 3 and low_tier.get("n", 0) >= 3 and
            high_tier.get("win_rate") is not None and low_tier.get("win_rate") is not None and
            len(changes) < max_changes):
        high_wr = high_tier["win_rate"]
        low_wr  = low_tier["win_rate"]
        if high_wr > low_wr + 0.20:
            # High quality is significantly better — worth noting in changelog
            note = {
                "ts": now_iso,
                "field": "observation",
                "change": f"Quality tier divergence confirmed",
                "rationale": (
                    f"High-quality signals (>0.75) WR={high_wr:.1%} vs "
                    f"low-quality (<0.65) WR={low_wr:.1%} — {(high_wr-low_wr):.0%} gap. "
                    f"Quality filter is working."
                ),
                "metrics_snapshot": {"high_tier": high_tier, "low_tier": low_tier},
            }
            changes.append(note)
            log(f"OBSERVATION: {note['rationale'][:100]}")

    # Wallet underperformance check — log but don't auto-exclude (too risky)
    if len(changes) < max_changes:
        wallet_stats = metrics.get("by_wallet", {})
        for wallet, stats in wallet_stats.items():
            if stats.get("n", 0) >= 5 and stats.get("win_rate") is not None:
                if stats["win_rate"] < 0.30:
                    note = {
                        "ts": now_iso,
                        "field": f"wallet_flag.{wallet}",
                        "change": f"Flagged {wallet} as underperforming",
                        "rationale": (
                            f"{wallet} WR={stats['win_rate']:.1%} over {stats['n']} signals. "
                            f"Below 30% threshold. Manual review recommended — "
                            f"consider adding to noisy_wallets list."
                        ),
                        "metrics_snapshot": stats,
                    }
                    changes.append(note)
                    log(f"FLAG: {note['rationale'][:100]}")
                    if len(changes) >= max_changes:
                        break

    if changes:
        # Add to config's changes_log (keep last 50)
        config.setdefault("changes_log", [])
        config["changes_log"].extend(changes)
        config["changes_log"] = config["changes_log"][-50:]
        save_config(config)

        # Also append to pipeline_changes.jsonl for external inspection
        with open(CHANGES_LOG, "a") as f:
            for c in changes:
                f.write(json.dumps(c) + "\n")

        log(f"Applied {len(changes)} strategy update(s) → saved to strategy_config.json")
    else:
        log(f"No strategy updates needed (WR={wr:.1%}, n={closed})" if wr else
            f"No strategy updates (insufficient data: n={closed})")

    return changes


# ── Step 4: Apply Research Config Patch ──────────────────────────────────────

# Allowed config sections and keys that research findings can modify.
# This whitelist prevents the research agent from changing arbitrary config.
PATCHABLE_KEYS = {
    "tp_sl": {"tp1_pct", "tp2_pct", "tp3_pct", "sl_pct"},
    "single_wallet": {"min_quality_score", "min_buy_usd", "volume_spike_min",
                       "min_market_cap", "min_liquidity", "max_pump_6h", "min_token_age_days"},
    "quality_filters": {"min_market_cap", "max_market_cap", "min_liquidity",
                         "volume_spike_min", "max_pump_1h", "min_token_age_days"},
}

# Bounds to prevent obviously wrong values
VALUE_BOUNDS = {
    "tp1_pct":  (0.001, 0.20),   # 0.1% to 20%
    "tp2_pct":  (0.005, 0.50),   # 0.5% to 50%
    "tp3_pct":  (0.01,  1.0),    # 1% to 100%
    "sl_pct":   (0.005, 0.30),   # 0.5% to 30%
    "min_quality_score": (0.30, 0.95),
    "min_buy_usd": (0, 10000),
    "volume_spike_min": (0.0, 10.0),
}


def apply_config_patch(patch: dict, rationale: str = "") -> list[dict]:
    """Apply a structured config patch from research findings to strategy_config.json.

    Args:
        patch: dict like {"tp_sl": {"tp1_pct": 0.008}, "single_wallet": {"min_quality_score": 0.5}}
        rationale: why these changes are being made

    Returns:
        list of change records (empty if nothing changed)
    """
    if not patch or not isinstance(patch, dict):
        return []

    config = load_config()
    changes = []
    now_iso = datetime.now(timezone.utc).isoformat()

    for section, section_patch in patch.items():
        if section not in PATCHABLE_KEYS:
            log(f"CONFIG PATCH: Skipping non-patchable section '{section}'")
            continue
        if not isinstance(section_patch, dict) or not section_patch:
            continue

        allowed_keys = PATCHABLE_KEYS[section]
        config.setdefault(section, {})

        for key, new_value in section_patch.items():
            if key not in allowed_keys:
                log(f"CONFIG PATCH: Skipping non-patchable key '{section}.{key}'")
                continue

            # Validate value type (must be numeric for all patchable keys)
            if not isinstance(new_value, (int, float)):
                log(f"CONFIG PATCH: Skipping non-numeric value for '{section}.{key}': {new_value}")
                continue

            # Apply bounds check
            if key in VALUE_BOUNDS:
                lo, hi = VALUE_BOUNDS[key]
                if not (lo <= new_value <= hi):
                    log(f"CONFIG PATCH: Value {new_value} for '{section}.{key}' out of bounds [{lo}, {hi}] — clamping")
                    new_value = max(lo, min(hi, new_value))

            old_value = config[section].get(key)
            if old_value == new_value:
                continue  # No change needed

            config[section][key] = new_value
            change = {
                "ts": now_iso,
                "field": f"{section}.{key}",
                "old": old_value,
                "new": new_value,
                "change": f"Research patch: {section}.{key} {old_value} → {new_value}",
                "rationale": rationale[:300] if rationale else "Applied from research findings config_patch",
                "source": "research_pipeline",
            }
            changes.append(change)
            log(f"CONFIG PATCH: {change['change']}")

    if changes:
        config.setdefault("changes_log", [])
        config["changes_log"].extend(changes)
        config["changes_log"] = config["changes_log"][-50:]
        save_config(config)

        # Also log to pipeline_changes.jsonl
        with open(CHANGES_LOG, "a") as f:
            for c in changes:
                f.write(json.dumps(c) + "\n")

        log(f"CONFIG PATCH: Applied {len(changes)} research finding(s) to strategy_config.json")
    else:
        log("CONFIG PATCH: No actionable changes in patch (all values same or invalid)")

    return changes


# ── Full execution ────────────────────────────────────────────────────────────

def run_implementation_cycle() -> dict:
    """
    Full implementation cycle:
    1. Close open signals via DexScreener
    2. Compute backtest metrics from closed signals
    3. Apply strategy updates if thresholds met
    Returns summary dict for inclusion in research context.
    """
    log("=== Implementation Cycle Start ===")

    # Step 1: Close open signals
    perf_summary = run_performance_check()
    log(f"Perf check: {perf_summary.get('update_line', perf_summary.get('error', 'done'))}")

    # Step 2: Compute metrics
    metrics = compute_backtest_metrics()
    closed = metrics.get("closed_count", 0)
    wr     = metrics.get("win_rate")
    log(
        f"Backtest metrics: {closed} closed, "
        f"WR={wr:.1%}" if wr else f"Backtest metrics: {closed} closed, WR=N/A"
    )

    # Step 3: Auto-update
    changes = apply_strategy_updates(metrics)

    summary = {
        "perf_check": perf_summary,
        "metrics":    metrics,
        "changes":    changes,
        "changes_count": len(changes),
    }

    log(f"=== Implementation Cycle Complete ({len(changes)} changes) ===")
    return summary


if __name__ == "__main__":
    import json as _json
    result = run_implementation_cycle()
    print("\n--- Implementation Summary ---")
    print(f"Closed signals: {result['metrics'].get('closed_count', 0)}")
    print(f"Win rate: {result['metrics'].get('win_rate', 'N/A')}")
    print(f"Changes applied: {result['changes_count']}")
    for c in result["changes"]:
        print(f"  → {c.get('change')}: {c.get('rationale', '')[:100]}")
