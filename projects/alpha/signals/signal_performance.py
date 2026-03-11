"""
Signal Performance Tracker — TP/SL Hit Detection + Reporting

Tracks open signals and evaluates them at 1h, 4h, 24h, 48h checkpoints.
Posts to Telegram when TP1/TP2/TP3 or SL is hit.
Publishes loss reports for transparency (top channels always show losses).

Usage:
    python signal_performance.py --check            # Check all open signals
    python signal_performance.py --check --dry-run  # Check without posting
    python signal_performance.py --report           # Print performance summary

Runs automatically via signal_publisher.py --check-perf
Also suitable as a cron job: run every hour to catch timely exits.
"""

import argparse
import asyncio
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

SIGNALS_DIR  = Path(__file__).parent
PERF_FILE    = SIGNALS_DIR / "signal_performance.jsonl"
SENT_FILE    = SIGNALS_DIR / "_sent_notifications.json"

# Load env
ENV_PATH = Path.home() / "memory" / ".env"


def load_env():
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

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHANNEL   = os.environ.get("TELEGRAM_CHANNEL", "")

# Signal is "stale" after 72h — close as timeout
TIMEOUT_HOURS = 72


# ---------------------------------------------------------------------------
# File I/O
# ---------------------------------------------------------------------------

def load_all_signals() -> list[dict]:
    """Load all entries from signal_performance.jsonl."""
    if not PERF_FILE.exists():
        return []
    entries = []
    for line in PERF_FILE.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            entries.append(json.loads(line))
        except Exception:
            continue
    return entries


def save_all_signals(entries: list[dict]):
    """Rewrite signal_performance.jsonl with updated entries."""
    with open(PERF_FILE, "w") as f:
        for e in entries:
            f.write(json.dumps(e) + "\n")


def get_open_signals() -> list[dict]:
    """Return only signals with status='open'."""
    return [e for e in load_all_signals() if e.get("status") == "open"]


# ---------------------------------------------------------------------------
# Sent notification tracking — dedup guard keyed by signal_id:event
# ---------------------------------------------------------------------------

def load_sent_notifications() -> set:
    """Load set of already-sent notification keys (e.g. 'abc123:tp1')."""
    if not SENT_FILE.exists():
        return set()
    try:
        data = json.loads(SENT_FILE.read_text())
        return set(data.get("sent", []))
    except Exception:
        return set()


def mark_notification_sent(key: str):
    """Persist a notification key so it is never re-fired."""
    try:
        if SENT_FILE.exists():
            data = json.loads(SENT_FILE.read_text())
        else:
            data = {"sent": []}
        sent = data.get("sent", [])
        if key not in sent:
            sent.append(key)
        data["sent"] = sent
        SENT_FILE.write_text(json.dumps(data, indent=2))
    except Exception:
        pass  # Don't crash the check loop on tracking failure


# ---------------------------------------------------------------------------
# Price fetching
# ---------------------------------------------------------------------------

async def fetch_current_price(token_address: str) -> float | None:
    """Fetch current price from DexScreener for a Solana token."""
    import httpx
    url = f"https://api.dexscreener.com/latest/dex/tokens/{token_address}"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(url)
        if r.status_code != 200:
            return None
        data = r.json()
        pairs = data.get("pairs") or []
        solana_pairs = [p for p in pairs if p.get("chainId") == "solana"]
        if not solana_pairs:
            return None
        best = max(solana_pairs, key=lambda p: p.get("liquidity", {}).get("usd", 0))
        price = float(best.get("priceUsd", 0) or 0)
        return price if price > 0 else None
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Telegram posting
# ---------------------------------------------------------------------------

async def post_to_telegram(text: str) -> bool:
    """Post outcome notification to Telegram."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHANNEL:
        return False
    import httpx
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id":                  TELEGRAM_CHANNEL,
        "text":                     text,
        "parse_mode":               "HTML",
        "disable_web_page_preview": True,
    }
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.post(url, json=payload)
        data = r.json()
        return r.status_code == 200 and data.get("ok", False)
    except Exception:
        return False


def format_price(price: float | None) -> str:
    if not price:
        return "N/A"
    if price >= 1:
        return f"${price:.4f}"
    elif price >= 0.001:
        return f"${price:.6f}"
    else:
        return f"${price:.8f}"


def format_pnl(pct: float) -> str:
    sign = "+" if pct >= 0 else ""
    return f"{sign}{pct:.1f}%"


# ---------------------------------------------------------------------------
# Outcome message builders
# ---------------------------------------------------------------------------

def build_tp_message(sig: dict, tp_level: int, current_price: float, pnl_pct: float) -> str:
    name   = sig.get("token_name", "Unknown")
    symbol = sig.get("token_symbol", "???")
    sig_id = sig.get("signal_id", "?")

    tp_emoji   = "✅✅✅" if tp_level == 3 else ("✅✅" if tp_level == 2 else "✅")
    tp_pct_str = {1: "+10%", 2: "+25%", 3: "+50%"}[tp_level]

    msg = f"""{tp_emoji} SIGNAL UPDATE — TP{tp_level} HIT

📍 Token: {name} ({symbol})
🎯 TP{tp_level}: {tp_pct_str} reached
💰 Entry: {format_price(sig.get('entry_price'))} → Now: {format_price(current_price)}
📈 PnL: {format_pnl(pnl_pct)}"""

    if tp_level == 1:
        msg += f"\n\n🔒 Stop moved to breakeven ({format_price(sig.get('entry_price'))})"
        msg += f"\n⏭️ Next target: TP2 ({format_price(sig.get('tp2_price'))})"
    elif tp_level == 2:
        msg += f"\n\n⏭️ Next target: TP3 ({format_price(sig.get('tp3_price'))})"
        msg += f"\n🔒 Trail your stop above breakeven"
    else:
        msg += f"\n\n🏆 Full target reached. Signal closed."

    msg += f"\n\n[Signal ID: {sig_id}]"
    return msg


def build_sl_message(sig: dict, current_price: float, pnl_pct: float) -> str:
    name   = sig.get("token_name", "Unknown")
    symbol = sig.get("token_symbol", "???")
    sig_id = sig.get("signal_id", "?")
    be_triggered = sig.get("stop_moved_to_be", False)

    if be_triggered:
        sl_label = "Breakeven stop"
        note = "TP1 was hit, stop was moved to breakeven — limited loss exposure."
    else:
        sl_label = "Stop Loss"
        note = "Signal did not work. Full -15% loss. We track every outcome, good and bad."

    msg = f"""❌ SIGNAL CLOSED — {sl_label} Hit

📍 Token: {name} ({symbol})
❌ {sl_label}: {format_price(sig.get('sl_price'))} reached
💰 Entry: {format_price(sig.get('entry_price'))} → Now: {format_price(current_price)}
📉 PnL: {format_pnl(pnl_pct)}

{note}

Transparency is how trust is built. We publish all results.

[Signal ID: {sig_id}]"""
    return msg


def build_timeout_message(sig: dict, current_price: float, pnl_pct: float) -> str:
    name   = sig.get("token_name", "Unknown")
    symbol = sig.get("token_symbol", "???")
    sig_id = sig.get("signal_id", "?")

    msg = f"""⏱️ SIGNAL CLOSED — 72h Timeout

📍 Token: {name} ({symbol})
❌ No TP or SL hit within 72h window
💰 Entry: {format_price(sig.get('entry_price'))} → Now: {format_price(current_price)}
📊 Exit PnL: {format_pnl(pnl_pct)}

Signal exited at timeout (not a stop hit). Review the chart for context.

[Signal ID: {sig_id}]"""
    return msg


# ---------------------------------------------------------------------------
# Core check loop
# ---------------------------------------------------------------------------

async def check_open_signals(dry_run: bool = False):
    """
    Check all open signals against current prices.
    Detects TP1/TP2/TP3 and SL hits, updates status, posts notifications.

    Checkpoint logic:
    - 1h:  Record where price is (no action needed unless already hit)
    - 4h:  Same — checkpoints for reporting
    - 24h: Evaluate — most signals should resolve here
    - 48h: Final evaluation before timeout
    - 72h: Force-close with timeout exit
    """
    now_ts = time.time()
    # Load sent-notification dedup set once per run
    sent_keys = load_sent_notifications()
    open_signals = get_open_signals()

    if not open_signals:
        print("[perf] No open signals to check.")
        return

    print(f"[perf] Checking {len(open_signals)} open signal(s)...")

    all_entries = load_all_signals()
    # Build index: signal_id → index in all_entries
    id_to_idx = {e.get("signal_id"): i for i, e in enumerate(all_entries)}

    updates_made = 0
    posts_sent   = 0

    for sig in open_signals:
        sig_id     = sig.get("signal_id", "?")
        token      = sig.get("token", "")
        published  = sig.get("published_ts", 0)
        entry_p    = sig.get("entry_price")
        tp1_p      = sig.get("tp1_price")
        tp2_p      = sig.get("tp2_price")
        tp3_p      = sig.get("tp3_price")
        sl_p       = sig.get("sl_price")
        name       = sig.get("token_name", token[:16])

        if not entry_p or not tp1_p or not sl_p:
            # Can't evaluate without price levels (e.g. signal published before prices were tracked)
            print(f"[perf] {sig_id}: no price levels — skipping")
            continue

        age_hours = (now_ts - published) / 3600
        print(f"[perf] {sig_id} ({name}): age={age_hours:.1f}h", end="")

        # Fetch current price
        current_price = await fetch_current_price(token)
        if current_price is None:
            print(f" | price fetch failed — skipping")
            continue

        print(f" | price={format_price(current_price)}", end="")

        # Compute current PnL
        pnl_pct = ((current_price - entry_p) / entry_p) * 100

        # Update checkpoint flags
        idx = id_to_idx.get(sig_id)
        if idx is None:
            continue

        updated_sig = all_entries[idx].copy()

        # Mark checkpoint flags
        if age_hours >= 1  and not updated_sig.get("checked_1h"):
            updated_sig["checked_1h"] = True
            updates_made += 1
        if age_hours >= 4  and not updated_sig.get("checked_4h"):
            updated_sig["checked_4h"] = True
            updates_made += 1
        if age_hours >= 24 and not updated_sig.get("checked_24h"):
            updated_sig["checked_24h"] = True
            updates_made += 1
        if age_hours >= 48 and not updated_sig.get("checked_48h"):
            updated_sig["checked_48h"] = True
            updates_made += 1

        # --- Timeout: 72h with no hit ---
        if age_hours >= TIMEOUT_HOURS:
            print(f" | TIMEOUT")
            updated_sig["status"]    = "timeout"
            updated_sig["final_pnl"] = pnl_pct
            updated_sig["closed_at"] = int(now_ts)
            all_entries[idx] = updated_sig
            updates_made += 1

            msg = build_timeout_message(sig, current_price, pnl_pct)
            print(msg)
            if not dry_run:
                ok = await post_to_telegram(msg)
                if ok:
                    posts_sent += 1
                await asyncio.sleep(1)
            continue

        # --- TP/SL detection (progressive) ---
        # We detect the *highest* TP hit so far to avoid double-posting.
        # Order: TP3 > TP2 > TP1 > SL

        outcome_msg  = None
        new_status   = None
        notify_key   = None  # sent-notification dedup key

        # TP3 hit (only if TP2 was already hit)
        if (tp3_p and current_price >= tp3_p
                and not updated_sig.get("tp3_hit")
                and updated_sig.get("tp2_hit")
                and f"{sig_id}:tp3" not in sent_keys):
            print(f" | TP3 HIT")
            updated_sig["tp3_hit"]   = True
            updated_sig["status"]    = "tp3_hit"
            updated_sig["final_pnl"] = pnl_pct
            updated_sig["closed_at"] = int(now_ts)
            new_status  = "tp3_hit"
            notify_key  = f"{sig_id}:tp3"
            outcome_msg = build_tp_message(sig, 3, current_price, pnl_pct)

        # TP2 hit (only if TP1 was already hit)
        elif (tp2_p and current_price >= tp2_p
                and not updated_sig.get("tp2_hit")
                and updated_sig.get("tp1_hit")
                and f"{sig_id}:tp2" not in sent_keys):
            print(f" | TP2 HIT")
            updated_sig["tp2_hit"] = True
            updated_sig["status"]  = "tp2_hit"
            notify_key  = f"{sig_id}:tp2"
            outcome_msg = build_tp_message(sig, 2, current_price, pnl_pct)

        # TP1 hit
        elif (tp1_p and current_price >= tp1_p
                and not updated_sig.get("tp1_hit")
                and f"{sig_id}:tp1" not in sent_keys):
            print(f" | TP1 HIT")
            updated_sig["tp1_hit"]          = True
            updated_sig["stop_moved_to_be"] = True
            # After TP1, move SL to breakeven
            updated_sig["sl_price"]         = entry_p
            updated_sig["status"]           = "tp1_hit"
            notify_key  = f"{sig_id}:tp1"
            outcome_msg = build_tp_message(sig, 1, current_price, pnl_pct)

        # SL hit — check against current effective SL (may be breakeven after TP1)
        elif (current_price <= updated_sig.get("sl_price", sl_p)
                and f"{sig_id}:sl" not in sent_keys):
            print(f" | SL HIT (effective SL={format_price(updated_sig.get('sl_price', sl_p))})")
            updated_sig["sl_hit"]    = True
            updated_sig["status"]    = "sl_hit"
            updated_sig["final_pnl"] = pnl_pct
            updated_sig["closed_at"] = int(now_ts)
            notify_key  = f"{sig_id}:sl"
            outcome_msg = build_sl_message(sig, current_price, pnl_pct)

        else:
            print(f" | open | pnl={format_pnl(pnl_pct)}")

        # Post and save if we have an outcome
        if outcome_msg:
            print(outcome_msg)
            updates_made += 1
            all_entries[idx] = updated_sig
            if not dry_run:
                # Mark as sent BEFORE posting to prevent concurrent re-fires
                if notify_key:
                    mark_notification_sent(notify_key)
                    sent_keys.add(notify_key)
                ok = await post_to_telegram(outcome_msg)
                if ok:
                    posts_sent += 1
                await asyncio.sleep(1)
        else:
            all_entries[idx] = updated_sig

    # Write all updates back
    if updates_made > 0:
        if not dry_run:
            save_all_signals(all_entries)
        print(f"\n[perf] Updated {updates_made} entries | Posted {posts_sent} notifications")
    else:
        print(f"\n[perf] No changes.")


# ---------------------------------------------------------------------------
# Performance report
# ---------------------------------------------------------------------------

def print_report():
    """Print a performance summary across all tracked signals."""
    entries = load_all_signals()
    if not entries:
        print("[perf] No signals tracked yet.")
        return

    total = len(entries)
    open_  = [e for e in entries if e.get("status") == "open"]
    tp1s   = [e for e in entries if e.get("tp1_hit")]
    tp2s   = [e for e in entries if e.get("tp2_hit")]
    tp3s   = [e for e in entries if e.get("tp3_hit")]
    sls    = [e for e in entries if e.get("sl_hit")]
    timeouts = [e for e in entries if e.get("status") == "timeout"]
    closed_pnl = [e["final_pnl"] for e in entries if e.get("final_pnl") is not None]

    print("\n" + "=" * 50)
    print("SIGNAL PERFORMANCE REPORT")
    print("=" * 50)
    print(f"Total signals tracked:  {total}")
    print(f"Open:                   {len(open_)}")
    print(f"TP1 reached:            {len(tp1s)} ({len(tp1s)/total*100:.0f}%)")
    print(f"TP2 reached:            {len(tp2s)} ({len(tp2s)/total*100:.0f}%)")
    print(f"TP3 reached:            {len(tp3s)} ({len(tp3s)/total*100:.0f}%)")
    print(f"Stop loss hit:          {len(sls)} ({len(sls)/total*100:.0f}%)")
    print(f"Timeout exits:          {len(timeouts)} ({len(timeouts)/total*100:.0f}%)")

    if closed_pnl:
        avg_pnl = sum(closed_pnl) / len(closed_pnl)
        wins = [p for p in closed_pnl if p > 0]
        losses = [p for p in closed_pnl if p <= 0]
        win_rate = len(wins) / len(closed_pnl) * 100 if closed_pnl else 0
        print(f"\nClosed signals PnL:")
        print(f"  Win rate:            {win_rate:.0f}%")
        print(f"  Avg PnL (closed):    {format_pnl(avg_pnl)}")
        if wins:
            print(f"  Avg win:             {format_pnl(sum(wins)/len(wins))}")
        if losses:
            print(f"  Avg loss:            {format_pnl(sum(losses)/len(losses))}")

    print("=" * 50)

    # Show recent signals
    print("\nRecent signals:")
    for e in sorted(entries, key=lambda x: x.get("published_ts", 0), reverse=True)[:10]:
        sig_id = e.get("signal_id", "?")
        name   = e.get("token_name", "?")
        status = e.get("status", "?")
        pnl    = e.get("final_pnl")
        ts     = e.get("published_ts", 0)
        time_str = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M")
        pnl_str = format_pnl(pnl) if pnl is not None else "open"
        tp_str = ""
        if e.get("tp1_hit"): tp_str += "✅TP1 "
        if e.get("tp2_hit"): tp_str += "✅TP2 "
        if e.get("tp3_hit"): tp_str += "✅TP3 "
        if e.get("sl_hit"):  tp_str += "❌SL "
        print(f"  {time_str} | {name:15s} | {status:10s} | {pnl_str:8s} | {tp_str}")


def format_pnl(pct: float) -> str:
    if pct is None:
        return "N/A"
    sign = "+" if pct >= 0 else ""
    return f"{sign}{pct:.1f}%"


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Signal Performance Tracker")
    parser.add_argument("--check",   action="store_true", help="Check all open signals")
    parser.add_argument("--dry-run", action="store_true", help="Check without posting to Telegram")
    parser.add_argument("--report",  action="store_true", help="Print performance summary")
    args = parser.parse_args()

    if args.report:
        print_report()
        return

    if args.check:
        asyncio.run(check_open_signals(dry_run=args.dry_run))
        return

    # Default: run a check
    asyncio.run(check_open_signals(dry_run=args.dry_run))


if __name__ == "__main__":
    main()
