#!/usr/bin/env python3
"""
Otto Continuous Task Dispatcher
Polls the task queue every 15s and launches ready tasks immediately.
Stateless — the Memory API is the source of truth and the concurrency lock.

Architecture: ~/otto/docs/continuous-task-dispatcher-architecture-2026-03-25.md
"""
import os
import sys
import time
import logging
import signal
from collections import defaultdict

import requests

API_BASE = os.environ.get("OTTO_API", "http://localhost:8100")
POLL_INTERVAL = int(os.environ.get("DISPATCHER_POLL_INTERVAL", "15"))  # seconds
INFLIGHT_TTL = 60       # seconds before assuming a task transitioned to 'running'
CLI_BACKOFF_S = 30      # seconds to skip a CLI type after a 429 response
STARTUP_DELAY = 10      # seconds to wait before first poll (let API come up)

# Per-CLI timestamp of last 429 response
_cli_backoff: dict[str, float] = defaultdict(float)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [dispatcher] %(levelname)s %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
    stream=sys.stdout,
)
log = logging.getLogger("dispatcher")

_shutdown = False


def _handle_signal(signum, frame):
    global _shutdown
    log.info("Signal %d received — shutting down gracefully", signum)
    _shutdown = True


def is_rate_limited() -> bool:
    """Check rate-limit state via API, fall back to sentinel file."""
    try:
        r = requests.get(f"{API_BASE}/kernel/providers/rate-limited", timeout=5)
        r.raise_for_status()
        return bool(r.json().get("rate_limited", False))
    except Exception:
        pass
    # Sentinel file fallback (written by heartbeat.sh)
    sentinel = "/tmp/otto-rate-limited"
    try:
        if os.path.exists(sentinel):
            ts = int(open(sentinel).read().strip().split()[0])
            return (time.time() - ts) < 3600
    except Exception:
        pass
    return False


def get_queue_status() -> dict:
    r = requests.get(f"{API_BASE}/tasks/queue/status", timeout=5)
    r.raise_for_status()
    return r.json()


def get_pending_tasks(limit: int = 20) -> list:
    r = requests.get(f"{API_BASE}/tasks?status=pending&limit={limit}", timeout=5)
    r.raise_for_status()
    data = r.json()
    # API returns a list directly
    return data if isinstance(data, list) else data.get("tasks", [])


def dispatch_task(task_id: str) -> str:
    """
    Call /tasks/{id}/run. Returns:
      'ok'       — task launched successfully
      'skip'     — already running (409)
      'capacity' — CLI at capacity (429)
      'error'    — unexpected error
    """
    try:
        r = requests.post(f"{API_BASE}/tasks/{task_id}/run", timeout=10)
        if r.status_code == 200:
            return "ok"
        elif r.status_code == 409:
            return "skip"
        elif r.status_code == 429:
            return "capacity"
        else:
            log.warning("Unexpected status %d dispatching task %s: %s",
                        r.status_code, task_id[:8], r.text[:200])
            return "error"
    except requests.RequestException as e:
        log.warning("Request error dispatching task %s: %s", task_id[:8], e)
        return "error"


def run_dispatch_cycle(in_flight: dict[str, float], status: dict) -> int:
    """
    Run one dispatch cycle. Returns number of tasks dispatched.
    Dispatches up to `can_run_more` tasks (fills all open slots in one cycle).
    """
    dispatched = 0
    cli_capacity: dict[str, int] = dict(status.get("cli_capacity", {}))
    slots_remaining = sum(max(0, v) for v in cli_capacity.values())

    if slots_remaining == 0:
        return 0

    tasks = get_pending_tasks(limit=20)
    if not tasks:
        return 0

    for task in tasks:
        if slots_remaining <= 0:
            break

        task_id = str(task["id"])
        task_cli = task.get("cli") or "claude"

        # Skip tasks already dispatched this session (defensive — API's status guard is real lock)
        if task_id in in_flight:
            continue

        # Skip if this CLI type is at capacity per status snapshot
        if cli_capacity.get(task_cli, 0) <= 0:
            continue

        # Skip if we recently got a 429 for this CLI type
        if time.time() - _cli_backoff[task_cli] < CLI_BACKOFF_S:
            log.debug("Skipping task %s — CLI '%s' in backoff", task_id[:8], task_cli)
            continue

        result = dispatch_task(task_id)

        if result == "ok":
            title = (task.get("title") or "")[:60]
            log.info("Dispatched %s '%s' [cli=%s priority=%s]",
                     task_id[:8], title, task_cli, task.get("priority", "?"))
            in_flight[task_id] = time.time()
            cli_capacity[task_cli] = max(0, cli_capacity.get(task_cli, 0) - 1)
            slots_remaining -= 1
            dispatched += 1

        elif result == "capacity":
            log.debug("CLI '%s' at capacity — backing off %ds", task_cli, CLI_BACKOFF_S)
            _cli_backoff[task_cli] = time.time()
            cli_capacity[task_cli] = 0  # don't try this CLI type again this cycle

        elif result == "skip":
            # Already running — add to in_flight so we don't re-try
            in_flight[task_id] = time.time()

        # "error" — already logged in dispatch_task, just continue

    return dispatched


def run():
    """Main dispatcher loop. Runs until SIGTERM/SIGINT."""
    global _shutdown
    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    log.info("Otto Task Dispatcher starting. API=%s poll=%ds", API_BASE, POLL_INTERVAL)
    log.info("Waiting %ds for API to be ready...", STARTUP_DELAY)
    time.sleep(STARTUP_DELAY)

    # in_flight: task_id → dispatch timestamp
    in_flight: dict[str, float] = {}
    idle_cycles = 0
    was_rate_limited = False

    while not _shutdown:
        try:
            # Evict stale in_flight entries (tasks are now 'running' in the DB)
            now = time.time()
            stale = [tid for tid, ts in in_flight.items() if now - ts > INFLIGHT_TTL]
            for tid in stale:
                del in_flight[tid]

            # Skip if rate-limited — log state transitions only (not every cycle)
            if is_rate_limited():
                if not was_rate_limited:
                    log.info("Rate-limited — pausing dispatch until limit clears")
                    was_rate_limited = True
                _sleep_interruptible(POLL_INTERVAL)
                continue
            if was_rate_limited:
                log.info("Rate limit cleared — resuming dispatch")
                was_rate_limited = False

            # Check queue status
            status = get_queue_status()
            pending_count = status.get("pending", 0)
            can_run = status.get("can_run_more", False)
            running = status.get("running_alive", 0)

            if pending_count == 0 or not can_run:
                if idle_cycles % 20 == 0:  # log every ~5 min of idling
                    log.debug("Idle — pending=%d running=%d can_run_more=%s",
                              pending_count, running, can_run)
                idle_cycles += 1
                _sleep_interruptible(POLL_INTERVAL)
                continue

            idle_cycles = 0

            # Dispatch tasks to fill open slots
            n = run_dispatch_cycle(in_flight, status)
            if n == 0:
                log.debug("Cycle complete — no tasks dispatched (pending=%d running=%d)",
                          pending_count, running)

        except requests.ConnectionError as e:
            log.warning("API unreachable: %s — will retry in %ds", e, POLL_INTERVAL)
        except requests.RequestException as e:
            log.warning("API error: %s — will retry in %ds", e, POLL_INTERVAL)
        except Exception as e:
            log.exception("Unexpected error in dispatch loop: %s", e)

        _sleep_interruptible(POLL_INTERVAL)

    log.info("Task dispatcher stopped.")


def _sleep_interruptible(seconds: float):
    """Sleep in small increments so signal handling is responsive."""
    end = time.time() + seconds
    while not _shutdown and time.time() < end:
        time.sleep(min(1.0, end - time.time()))


if __name__ == "__main__":
    run()
