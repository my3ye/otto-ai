#!/usr/bin/env python3
"""
Progressive Research Pipeline — Capital Growth Strategy Optimizer

Runs every 3 hours. Each cycle:
  1. Load state from previous runs (hypotheses, findings, iteration count)
  2. Analyze current signals data (quality, volume, wallet performance)
  3. Analyze signal performance (TP/SL outcomes)
  4. Run Claude research agent with full context + previous findings
  5. Extract new findings and update hypotheses
  6. Save state for compounding across runs
  7. Notify Mev on first run or HIGH-significance findings

State file: ~/otto/projects/alpha/research_state.json
"""

import json
import os
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────────
ALPHA_DIR     = Path(__file__).parent
STATE_FILE    = ALPHA_DIR / "research_state.json"
SIGNALS_FILE  = ALPHA_DIR / "signals.jsonl"
PERF_FILE     = ALPHA_DIR / "signals" / "signal_performance.jsonl"
WA_SEND       = Path.home() / "otto" / "tools" / "whatsapp_send.sh"
LOG_FILE      = Path.home() / "otto" / "logs" / "research_pipeline.log"

CLAUDE_CLI    = Path.home() / ".local" / "bin" / "claude"
MAX_BUDGET    = "0.15"        # USD per run — 8 runs/day = $1.20/day
MAX_FINDINGS  = 20            # Cap stored findings to avoid state bloat


# ── Logging ────────────────────────────────────────────────────────────────
def log(msg: str):
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")


# ── State ──────────────────────────────────────────────────────────────────
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
        "hypotheses": [
            "SM_10 is the only real directional trader (83% WR) — focus signals on SM_10 solo",
            "24h exit horizon outperforms 1h/4h — implement TP/SL instead of fixed time exits",
            "Wallet pool needs re-qualification: 17/18 wallets may be LP/bot positions",
            "Convergence signals (2+ wallets on same token) are more reliable than single-wallet",
        ],
        "findings": [],
        "confirmed_actions": [],
        "action_items": [
            "Re-qualify wallet pool using Birdeye API (blocked on API key from Mev)",
            "Implement TP1/SL exits: TP1=+10%, SL=-15%",
            "Track signal performance TP/SL hit rates automatically",
        ],
    }


def save_state(state: dict):
    # Cap findings to avoid bloat
    state["findings"] = state["findings"][-MAX_FINDINGS:]
    state["last_run"] = datetime.now(timezone.utc).isoformat()
    STATE_FILE.write_text(json.dumps(state, indent=2))


# ── Signal Analysis ────────────────────────────────────────────────────────
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
    token_counts:  dict = defaultdict(int)

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
                # signals.jsonl uses ISO timestamp string, not unix ts
                ts_str = s.get("timestamp", "")
                if not ts_str:
                    continue
                try:
                    ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00")).timestamp()
                except Exception:
                    continue

                # Use token as dedup key (signals.jsonl has no signal_id)
                token = s.get("token", "")
                wallets_raw = s.get("wallets", "")
                sid = f"{token}:{wallets_raw}"

                if ts >= cutoff_24h:
                    if sid not in seen_ids_24h:
                        seen_ids_24h.add(sid)
                        signals_24h.append(s)
                        # wallets field can be string (space-sep) or list
                        if isinstance(wallets_raw, list):
                            wallet_list = wallets_raw
                        elif isinstance(wallets_raw, str):
                            wallet_list = wallets_raw.split()
                        else:
                            wallet_list = []
                        for w in wallet_list:
                            wallet_counts[w.strip()] += 1
                        token_counts[s.get("token", "?")] += 1
                    if ts >= cutoff_3h and sid not in seen_ids_3h:
                        seen_ids_3h.add(sid)
                        signals_3h.append(s)

        def signal_breakdown(sigs):
            counts: dict = defaultdict(int)
            for s in sigs:
                counts[s.get("signal", "unknown")] += 1
            return dict(counts)

        top_wallets = sorted(wallet_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        top_tokens  = sorted(token_counts.items(), key=lambda x: x[1], reverse=True)[:5]

        total_lines = sum(1 for _ in open(SIGNALS_FILE))

        def avg_usd(sigs):
            amounts = []
            for s in sigs:
                try:
                    v = float(s.get("amount_usd_est", 0) or 0)
                    if v > 0:
                        amounts.append(v)
                except Exception:
                    pass
            return round(sum(amounts) / len(amounts), 2) if amounts else 0

        return {
            "last_3h":  {
                "count": len(signals_3h),
                "signal_breakdown": signal_breakdown(signals_3h),
                "avg_usd_est": avg_usd(signals_3h),
            },
            "last_24h": {
                "count": len(signals_24h),
                "signal_breakdown": signal_breakdown(signals_24h),
                "avg_usd_est": avg_usd(signals_24h),
            },
            "top_wallets_24h": top_wallets,
            "top_tokens_24h":  top_tokens[:5],
            "total_signals_in_file": total_lines,
        }
    except Exception as e:
        return {"error": str(e)}


def analyze_performance() -> dict:
    """Parse signal_performance.jsonl and compute TP/SL stats."""
    if not PERF_FILE.exists():
        return {"error": "signal_performance.jsonl not found"}

    open_signals   = []
    closed_signals = []
    tp_hits = {"tp1": 0, "tp2": 0, "tp3": 0}
    sl_hits = 0

    seen = set()
    try:
        with open(PERF_FILE) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    s = json.loads(line)
                except Exception:
                    continue
                sid = s.get("signal_id", "")
                if sid in seen:
                    continue
                seen.add(sid)

                status = s.get("status", "open")
                if status == "open":
                    open_signals.append(s)
                else:
                    closed_signals.append(s)
                    if s.get("tp1_hit"):
                        tp_hits["tp1"] += 1
                    if s.get("tp2_hit"):
                        tp_hits["tp2"] += 1
                    if s.get("tp3_hit"):
                        tp_hits["tp3"] += 1
                    if s.get("sl_hit"):
                        sl_hits += 1

        # PnL from closed signals
        pnls = [s.get("final_pnl") for s in closed_signals if s.get("final_pnl") is not None]
        avg_pnl = round(sum(pnls) / len(pnls), 3) if pnls else None
        wins = [p for p in pnls if p > 0]
        win_rate = round(len(wins) / len(pnls) * 100, 1) if pnls else None

        return {
            "open_signals":   len(open_signals),
            "closed_signals": len(closed_signals),
            "tp1_hits": tp_hits["tp1"],
            "tp2_hits": tp_hits["tp2"],
            "tp3_hits": tp_hits["tp3"],
            "sl_hits":  sl_hits,
            "avg_pnl_pct": avg_pnl,
            "win_rate_pct": win_rate,
        }
    except Exception as e:
        return {"error": str(e)}


# ── Research ───────────────────────────────────────────────────────────────
def build_research_prompt(state: dict, signal_stats: dict, perf_stats: dict) -> str:
    prev_findings = state["findings"][-5:] if state["findings"] else []
    findings_text = "\n".join(f"  - [{f.get('iteration','?')}] {f.get('finding','')}" for f in prev_findings) or "  (none yet)"
    hypotheses_text = "\n".join(f"  {i+1}. {h}" for i, h in enumerate(state["hypotheses"]))
    actions_text = "\n".join(f"  - {a}" for a in state["action_items"])

    return f"""You are Otto's Progressive Research Agent for capital growth through crypto signals.
This is iteration {state['iteration'] + 1} of an ongoing progressive research loop.

## Current Signal Stats (last 3h)
{json.dumps(signal_stats.get('last_3h', {}), indent=2)}

## Signal Stats (last 24h)
{json.dumps(signal_stats.get('last_24h', {}), indent=2)}

## Top Wallets (last 24h)
{json.dumps(signal_stats.get('top_wallets_24h', []), indent=2)}

## Signal Performance (TP/SL tracking)
{json.dumps(perf_stats, indent=2)}

## Current Hypotheses Being Tested
{hypotheses_text}

## Recent Findings (previous iterations)
{findings_text}

## Outstanding Action Items
{actions_text}

## Your Task
1. Analyze the data above. What patterns do you see?
2. Which hypotheses are confirmed, refuted, or need more data?
3. Identify the single highest-impact improvement to pursue RIGHT NOW to grow capital
4. Propose 1-2 new hypotheses to test in the next cycle
5. Are there any NEW strategies (wallet discovery, signal types, execution improvements) worth exploring?

Focus on CONCRETE, ACTIONABLE findings only. No speculation without data backing.

## Output Format (strict JSON)
```json
{{
  "primary_finding": "One sentence — the most important insight from this iteration",
  "significance": "LOW|MEDIUM|HIGH",
  "significance_reason": "Why this significance level — HIGH only if actionable breakthrough",
  "hypothesis_updates": [
    {{"hypothesis": "exact text", "verdict": "CONFIRMED|REFUTED|NEEDS_MORE_DATA", "evidence": "brief"}}
  ],
  "new_hypotheses": ["hypothesis 1", "hypothesis 2"],
  "top_action": "The single best action to take right now",
  "additional_observations": ["observation 1", "observation 2"]
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

        # Extract JSON from output
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


# ── Notification ────────────────────────────────────────────────────────────
def send_whatsapp(msg: str):
    if not WA_SEND.exists():
        log(f"WhatsApp send script not found: {WA_SEND}")
        return
    try:
        subprocess.run([str(WA_SEND), msg], timeout=30, check=False)
        log("WhatsApp notification sent")
    except Exception as e:
        log(f"WhatsApp send failed: {e}")


# ── Main ───────────────────────────────────────────────────────────────────
def main():
    log(f"=== Research Pipeline Starting ===")

    state = load_state()
    iteration = state["iteration"] + 1
    log(f"Iteration {iteration} | Previous findings: {len(state['findings'])}")

    # 1. Gather data
    log("Analyzing signals data...")
    signal_stats = analyze_signals()
    perf_stats   = analyze_performance()
    log(f"Signals last 3h: {signal_stats.get('last_3h', {}).get('count', 0)} | "
        f"Signals last 24h: {signal_stats.get('last_24h', {}).get('count', 0)} | "
        f"Open signals: {perf_stats.get('open_signals', '?')}")

    # 2. Research
    log("Running Claude research agent...")
    prompt   = build_research_prompt(state, signal_stats, perf_stats)
    findings = run_claude_research(prompt)

    if findings is None:
        log("Research agent produced no output — saving data stats only")
        findings = {
            "primary_finding": "No research output this cycle (Claude error or no data)",
            "significance": "LOW",
            "new_hypotheses": [],
            "top_action": "Investigate Claude CLI connectivity",
            "additional_observations": [],
        }

    log(f"Finding: [{findings.get('significance', '?')}] {findings.get('primary_finding', '')[:100]}")

    # 3. Update state
    state["iteration"] = iteration

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
            log(f"Hypothesis REFUTED and removed: {hyp[:60]}")
        elif verdict == "CONFIRMED":
            log(f"Hypothesis CONFIRMED: {hyp[:60]}")

    # Add new hypotheses
    for new_hyp in findings.get("new_hypotheses", []):
        if new_hyp not in state["hypotheses"]:
            state["hypotheses"].append(new_hyp)
            log(f"New hypothesis added: {new_hyp[:80]}")

    # Update action items
    top_action = findings.get("top_action", "")
    if top_action and top_action not in state["action_items"]:
        state["action_items"].append(top_action)

    save_state(state)
    log(f"State saved — iteration {iteration} | hypotheses: {len(state['hypotheses'])}")

    # 4. Notify Mev?
    significance = findings.get("significance", "LOW")
    is_first_run = not state.get("first_run_done", False)

    if is_first_run:
        # First run summary
        s24 = signal_stats.get("last_24h", {})
        perf_summary = ""
        if perf_stats.get("closed_signals"):
            perf_summary = f"\nPerformance: {perf_stats.get('win_rate_pct', '?')}% WR on {perf_stats.get('closed_signals')} closed signals"

        msg = (
            f"[Research Pipeline] First cycle complete (iter {iteration})\n"
            f"Signals 24h: {s24.get('count', 0)} | avg quality: {s24.get('avg_quality', 0)}"
            f"{perf_summary}\n"
            f"Finding [{significance}]: {findings.get('primary_finding', '')[:200]}\n"
            f"Top action: {findings.get('top_action', '')[:150]}\n"
            f"Pipeline runs every 3h. Will only notify on HIGH significance findings next."
        )
        send_whatsapp(msg)
        state["first_run_done"] = True
        save_state(state)

    elif significance == "HIGH":
        # High significance — notify Mev
        msg = (
            f"[Research Pipeline - HIGH] Iteration {iteration}\n"
            f"Finding: {findings.get('primary_finding', '')[:200]}\n"
            f"Action: {findings.get('top_action', '')[:150]}\n"
            f"Reason: {findings.get('significance_reason', '')[:100]}"
        )
        send_whatsapp(msg)

    log(f"=== Research Pipeline Complete (iter {iteration}) ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
