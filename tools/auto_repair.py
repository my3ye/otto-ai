#!/usr/bin/env python3
"""
Otto Auto-Repair: Detects repeat error/notification patterns and spawns fix tasks.
Called by heartbeat.sh after each orchestrator cycle.

Logic:
  - Query the last 6h of episodic events
  - Find content snippets appearing 3+ times (filtered to error/notification events)
  - Skip patterns that already have a fix task created in the last 24h
  - Auto-create and launch a debugger task for each new repeat pattern
  - Cap at 3 auto-repair tasks per run to avoid cascade
"""
import json
import sys
import urllib.request
import urllib.error
from collections import Counter
from datetime import datetime, timezone, timedelta

API = "http://localhost:8100"
TS = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
LOG_PREFIX = f"[auto-repair @ {TS}]"

# Event types to always scan (even without error keywords)
SCAN_TYPES = {"notification", "error", "alert"}

# Event types to always skip (routine orchestration noise)
SKIP_TYPES = {
    "heartbeat", "reflection", "sync", "mars_sweep", "anomaly_check",
    "self_critique", "adversarial_check", "mars_reflection", "auto_repair",
    "system", "whatsapp_sent", "conversation",
}

# Keywords that promote an event into the scan pool regardless of event_type
ERROR_KEYWORDS = [
    "error", "failed", "unattainable", "exception", "traceback",
    "broken", "alert", "http 4", "http 5", "exit code",
]


def api_post(path, data):
    try:
        body = json.dumps(data).encode()
        req = urllib.request.Request(
            f"{API}{path}",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        resp = urllib.request.urlopen(req, timeout=15)
        return json.loads(resp.read())
    except Exception as e:
        print(f"{LOG_PREFIX} POST {path} failed: {e}", file=sys.stderr)
        return None


def api_get(path):
    try:
        resp = urllib.request.urlopen(f"{API}{path}", timeout=15)
        return json.loads(resp.read())
    except Exception as e:
        print(f"{LOG_PREFIX} GET {path} failed: {e}", file=sys.stderr)
        return None


def find_repeat_patterns(hours=6, min_count=3):
    """Return list of (snippet, count) for patterns appearing min_count+ times."""
    events = api_post("/episodic/timeline", {"limit": 200, "hours": hours})
    if not events:
        return []

    snippets = []
    for e in events:
        content = e.get("content", "").strip()
        etype = e.get("event_type", "")

        if etype in SKIP_TYPES:
            continue

        content_lower = content.lower()
        if etype in SCAN_TYPES or any(kw in content_lower for kw in ERROR_KEYWORDS):
            # Normalize: lowercase + truncate for matching
            snippets.append(content_lower[:120])

    counts = Counter(snippets)
    repeated = [(s, c) for s, c in counts.items() if c >= min_count]
    repeated.sort(key=lambda x: -x[1])
    return repeated


def has_existing_fix_task(pattern_key):
    """Return True if a heartbeat-auto-repair task for this pattern exists in last 24h."""
    tasks = api_get("/tasks?limit=100")
    if not tasks:
        return False

    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    search_key = pattern_key[:40]

    for t in tasks:
        if t.get("created_by") != "heartbeat-auto-repair":
            continue
        try:
            created_at = datetime.fromisoformat(t["created_at"].replace("Z", "+00:00"))
            if created_at < cutoff:
                continue
        except Exception:
            continue
        if search_key in t.get("prompt", "").lower():
            return True
    return False


def spawn_fix_task(pattern, count):
    """Create and launch a debugger task to fix a repeat pattern. Returns task_id or None."""
    task_data = {
        "title": f"[P7] [AUTO-REPAIR] Fix repeat pattern: {pattern[:60]}",
        "prompt": f"""A repeating error/notification pattern was auto-detected {count} times in the last 6 hours by the heartbeat monitor. This task was spawned automatically — do NOT notify Mev.

Detected pattern ({count}x occurrences):
  {pattern}

Your goal: find and fix the root cause so this pattern stops recurring.

Steps:
1. Grep the codebase for code that generates this content — check memory API routes, heartbeat agents, signal/notification code, alert systems
2. Identify the root cause: missing dedup? no cooldown? loop condition? repeated failing check?
3. Implement the minimal fix — proper dedup, cooldown guard, or eliminate the loop
4. Do NOT just suppress the message — fix the underlying cause
5. Verify the fix won't break other functionality
6. Commit when done

Key files to check:
  ~/otto/memory/routes/ (API notification routes)
  ~/otto/.claude/agents/ (heartbeat/reflection agent prompts)
  ~/otto/projects/alpha/signals/ (signal notification code)
  ~/otto/projects/alpha/paper_trader.py (trading alerts)
""",
        "priority": 7,
        "model": "sonnet",
        "cli": "claude",
        "agent_type": "debugger",
        "max_budget_usd": 5.0,
        "timeout_seconds": 3600,
        "created_by": "heartbeat-auto-repair",
        "metadata": {
            "pattern": pattern,
            "repeat_count": count,
            "auto_spawned": True,
        },
    }

    task = api_post("/tasks", task_data)
    if not task:
        print(f"{LOG_PREFIX} ERROR: Failed to create fix task for: {pattern[:60]}", file=sys.stderr)
        return None

    task_id = task.get("id")
    print(f"{LOG_PREFIX} Created fix task {task_id} ({count}x pattern): {pattern[:60]}")

    # Launch immediately
    run_resp = api_post(f"/tasks/{task_id}/run", {})
    if run_resp:
        print(f"{LOG_PREFIX} Launched fix task {task_id}")
    else:
        print(f"{LOG_PREFIX} WARNING: Failed to launch fix task {task_id} — it is created but not running", file=sys.stderr)

    # Log to episodic memory
    api_post(
        "/episodic/events",
        {
            "content": f"Auto-repair: spawned fix task {task_id} for repeat pattern ({count}x): {pattern[:80]}",
            "event_type": "auto_repair",
            "importance": 7,
        },
    )

    return task_id


def main():
    print(f"{LOG_PREFIX} Scanning for repeat error patterns (last 6h, threshold=3)...")

    patterns = find_repeat_patterns(hours=6, min_count=3)

    if not patterns:
        print(f"{LOG_PREFIX} No repeat patterns detected. System clean.")
        return 0

    print(f"{LOG_PREFIX} {len(patterns)} repeat pattern(s) found:")
    for pattern, count in patterns:
        print(f"  [{count}x] {pattern[:80]}")

    tasks_spawned = 0
    for pattern, count in patterns[:3]:  # Cap at 3 auto-repair tasks per cycle
        if has_existing_fix_task(pattern):
            print(f"{LOG_PREFIX} Already has fix task (last 24h), skipping: {pattern[:60]}")
            continue

        task_id = spawn_fix_task(pattern, count)
        if task_id:
            tasks_spawned += 1

    print(f"{LOG_PREFIX} Done. Spawned {tasks_spawned} fix task(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
