# Continuous Task Dispatcher — Architecture Design
**Date:** 2026-03-25
**Status:** Design (ready for implementation)
**Author:** Architect agent

---

## Design: Continuous Task Dispatcher

### Problem

The current architecture relies on the hourly heartbeat to launch queued tasks. A task created at 12:01 waits up to 59 minutes before a heartbeat cycle picks it up. Mev noticed this directly: "There are a lot of tasks in the queue — how can we ensure that they get actioned on without waiting for the heartbeat?"

The heartbeat is an LLM process — it runs Claude Code CLI with a full reasoning prompt, reviews results, creates tasks, messages Mev. It was never meant to be the dispatch mechanism. It happens to launch tasks as a side effect. Separating dispatch from reasoning is the right architecture.

**Goal:** Tasks in `pending` status should start executing within ≤30 seconds of a slot opening up — without changing the heartbeat's role or adding risk to the existing system.

---

### Approach

A **lightweight polling service** (`task_dispatcher.py`) runs as a persistent systemd service alongside the existing infrastructure. Every 15 seconds it:

1. Checks whether slots are available (via existing `/tasks/queue/status`)
2. If yes, fetches the highest-priority eligible pending task
3. Calls `POST /tasks/{id}/run` to spawn it
4. Backs off one interval, then loops

That's it. No LLM. No reasoning. No state. The entire dispatch logic is ~50 lines of Python.

**Why this is the right model:**

The `/tasks/{id}/run` API already handles:
- Concurrency limits (max 5 total, 3 claude / 1 gemini / 1 kimi)
- Per-CLI slot enforcement
- Status guard ("must be pending to run")
- Process spawning and PID tracking

The dispatcher doesn't need to replicate any of this — it just calls the API. The API is the lock. The dispatcher is a loop.

---

### Key Decisions

**Poll interval — 15s**: Chosen because:
- Task runtimes are minutes to hours. A 15s wake latency is negligible.
- Sub-second latency (via LISTEN/NOTIFY) isn't needed and adds complexity.
- Low CPU overhead: one HTTP request per cycle when idle.
- Alternative: 30s is also fine. 5s is unnecessary and slightly wasteful.

**External process, not embedded in FastAPI**: An independent systemd service is independently observable, restartable, and monitored. If it crashes, systemd restarts it in 10s. If the memory API crashes and restarts, the dispatcher reconnects on its next poll. The concerns stay clean.
- Alternative rejected: asyncio background task inside FastAPI — harder to observe, dies with the API, can't be restarted independently.

**Polling, not PostgreSQL LISTEN/NOTIFY**: LISTEN/NOTIFY would give zero latency but requires:
- Adding `NOTIFY` calls (or DB triggers) to `create_task`, `complete_task`, `on_plan_task_complete`, and workflow advancement — at least 4 code locations
- Maintaining a persistent asyncpg connection with reconnect logic
- Testing edge cases (missed notifies during reconnect)
Polling is simpler, and 15s is fast enough.
- Chosen: polling. Alternative: NOTIFY (Phase 2 option if 15s proves too slow, which is unlikely).

**Dependency-safe dispatch**: The DAG plan system (`on_plan_task_complete`) only sets downstream tasks to `pending` when their dependencies are met. So `pending` already means "ready to run" for plan tasks. Standalone tasks have no `depends_on`. The dispatcher can safely launch any `pending` task without dependency checking.
- Risk: if this assumption changes (new task types with depends_on outside plans), add a DB-side "ready" view. Document this as the known extension point.

**Heartbeat still creates tasks; dispatcher only launches them**: This is the separation of concerns. The heartbeat remains the reasoning layer (review → create → communicate). The dispatcher is a pure mechanical executor (pending → run). They don't compete because:
- If the heartbeat tries to launch a task the dispatcher already started, the API returns 409. The heartbeat handles it gracefully (it already does per the existing logic).
- If the dispatcher tries to launch a task that hits the concurrency cap, it gets 429 and retries in 15s.

---

### API / Interface

The dispatcher uses only existing Memory API endpoints:

```
GET  /tasks/queue/status
  → returns { pending, running_alive, can_run_more, cli_capacity, ... }

GET  /tasks?status=pending&limit=20
  → returns tasks ordered by priority desc, created_at asc

POST /tasks/{id}/run
  → spawns task_runner.sh, returns { pid, status }
  → 409 if already running, 429 if at capacity

GET  /kernel/providers/rate-limited
  → returns { rate_limited: bool, remaining_seconds: int }
```

No new endpoints required for Phase 1.

**Optional Phase 2 addition**: `GET /tasks/queue/next` — server-side logic to return the single best task to run next (considering priority, CLI availability, dependencies). Moves selection logic server-side and makes the dispatcher even simpler.

---

### Process Model

```
otto-task-dispatcher.service (systemd, restart=always)
│
└─ task_dispatcher.py
    │
    ├── loop every 15s:
    │   ├── GET /kernel/providers/rate-limited → skip if rate-limited
    │   ├── GET /tasks/queue/status → skip if not can_run_more
    │   ├── GET /tasks?status=pending&limit=20
    │   ├── for each task (priority order):
    │   │   ├── skip if task_id in in_flight set
    │   │   ├── POST /tasks/{id}/run
    │   │   │   ├── 200 → add to in_flight, log success, break (one dispatch per loop)
    │   │   │   ├── 409 → task already running, skip
    │   │   │   ├── 429 → CLI at capacity, stop trying this CLI type, try next
    │   │   │   └── 5xx → log warning, continue
    │   │   └── (continue to next task only if CLI was at capacity)
    │   └── sleep 15s
    │
    └── in_flight set: cleared every 60s (tasks that launched are now 'running')
```

**Concurrency safety note**: The `in_flight` set prevents the dispatcher from calling `/run` twice on the same task in the same session. But the real guard is the API's status check: a task transitions from `pending` → `running` atomically. Even without `in_flight`, double-dispatch just gets a 409. The set is defensive hygiene, not load-bearing.

---

### Implementation Plan

**Phase 1: Core dispatcher (1-2 hours, ~$2)**

**Step 1 — `task_dispatcher.py`** (new file at `~/otto/task_dispatcher.py`):
```python
#!/usr/bin/env python3
"""
Otto Continuous Task Dispatcher
Polls the task queue every 15s and launches ready tasks immediately.
Stateless — the Memory API is the source of truth.
"""
import time, requests, logging, os
from collections import defaultdict

API = "http://localhost:8100"
POLL_INTERVAL = 15          # seconds
BACKOFF_ON_RATELIMIT = 120  # seconds to pause when rate-limited
CLI_BACKOFF = defaultdict(int)  # cli_type → timestamp of last 429

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [dispatcher] %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
log = logging.getLogger("dispatcher")

def is_rate_limited() -> bool:
    try:
        r = requests.get(f"{API}/kernel/providers/rate-limited", timeout=5)
        return r.json().get("rate_limited", False)
    except Exception:
        # Fallback: check sentinel file
        sentinel = "/tmp/otto-rate-limited"
        if os.path.exists(sentinel):
            ts = int(open(sentinel).read().strip().split()[0])
            return (time.time() - ts) < 3600
        return False

def get_queue_status() -> dict:
    r = requests.get(f"{API}/tasks/queue/status", timeout=5)
    return r.json()

def get_pending_tasks() -> list[dict]:
    r = requests.get(f"{API}/tasks?status=pending&limit=20", timeout=5)
    data = r.json()
    # Handle both list response and paginated response
    return data if isinstance(data, list) else data.get("tasks", [])

def dispatch_task(task_id: str) -> str:
    """Returns: 'ok', 'skip' (409), 'capacity' (429), 'error'"""
    r = requests.post(f"{API}/tasks/{task_id}/run", timeout=10)
    if r.status_code == 200:
        return "ok"
    elif r.status_code == 409:
        return "skip"
    elif r.status_code == 429:
        return "capacity"
    else:
        return "error"

def run():
    log.info("Task dispatcher started. Poll interval: %ds", POLL_INTERVAL)
    in_flight: set[str] = set()
    in_flight_ts: dict[str, float] = {}

    while True:
        try:
            # Clear stale in_flight entries (older than 60s — task is now 'running')
            now = time.time()
            stale = [tid for tid, ts in in_flight_ts.items() if now - ts > 60]
            for tid in stale:
                in_flight.discard(tid)
                in_flight_ts.pop(tid, None)

            # Skip if API rate-limited (no Claude slots anyway)
            if is_rate_limited():
                log.debug("Rate-limited — skipping dispatch cycle")
                time.sleep(POLL_INTERVAL)
                continue

            # Check if slots available
            status = get_queue_status()
            if not status.get("can_run_more", False):
                log.debug("No slots available (running=%d)", status.get("running_alive", 0))
                time.sleep(POLL_INTERVAL)
                continue

            if status.get("pending", 0) == 0:
                log.debug("No pending tasks")
                time.sleep(POLL_INTERVAL)
                continue

            # Get pending tasks (already ordered by priority desc, created_at asc)
            tasks = get_pending_tasks()
            cli_capacity = status.get("cli_capacity", {})

            dispatched = False
            for task in tasks:
                task_id = str(task["id"])
                task_cli = task.get("cli") or "claude"

                if task_id in in_flight:
                    continue

                # Skip if this CLI type is at capacity
                if cli_capacity.get(task_cli, 0) <= 0:
                    continue

                # Skip if we recently got a 429 for this CLI type (30s backoff)
                if time.time() - CLI_BACKOFF[task_cli] < 30:
                    continue

                result = dispatch_task(task_id)
                if result == "ok":
                    log.info("Dispatched task %s (%s) [cli=%s priority=%s]",
                             task_id[:8], task.get("title", "")[:50],
                             task_cli, task.get("priority", "?"))
                    in_flight.add(task_id)
                    in_flight_ts[task_id] = time.time()
                    dispatched = True
                    break  # one dispatch per loop — check queue again next cycle
                elif result == "capacity":
                    log.debug("CLI '%s' at capacity — backing off 30s", task_cli)
                    CLI_BACKOFF[task_cli] = time.time()
                elif result == "skip":
                    # Task already running — it'll drop from pending query next time
                    in_flight.add(task_id)
                    in_flight_ts[task_id] = time.time()
                # "error" — log already done, just continue

            if dispatched:
                log.debug("Dispatched one task. Waiting %ds before next check.", POLL_INTERVAL)

        except requests.RequestException as e:
            log.warning("API unreachable: %s — will retry in %ds", e, POLL_INTERVAL)
        except Exception as e:
            log.exception("Unexpected error in dispatch loop: %s", e)

        time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    run()
```

**Step 2 — `otto-task-dispatcher.service`** (at `/etc/systemd/system/`):
```ini
[Unit]
Description=Otto Continuous Task Dispatcher
Documentation=https://github.com/my3ye/otto-ai
After=otto-memory.service network.target
Wants=otto-memory.service

[Service]
Type=simple
User=web3relic
WorkingDirectory=/home/web3relic/otto
ExecStart=/usr/bin/python3 /home/web3relic/otto/task_dispatcher.py
Restart=on-failure
RestartSec=10s
StandardOutput=append:/home/web3relic/otto/logs/task-dispatcher.log
StandardError=append:/home/web3relic/otto/logs/task-dispatcher.log
Environment=HOME=/home/web3relic
Environment=USER=web3relic

[Install]
WantedBy=multi-user.target
```

**Step 3 — Enable and start**:
```bash
sudo systemctl daemon-reload
sudo systemctl enable otto-task-dispatcher
sudo systemctl start otto-task-dispatcher
systemctl status otto-task-dispatcher
```

**Step 4 — Self-healing integration** in `heartbeat.sh`:
Add `otto-task-dispatcher.service` to the self-healing loop:
```bash
for TIMER in otto-reflection.timer otto-maintenance.timer otto-security-audit.timer otto-vuln-sync.timer; do
```
→ Replace with checking both timers and services:
```bash
SERVICES_TO_HEAL=(otto-reflection.timer otto-maintenance.timer otto-security-audit.timer otto-vuln-sync.timer otto-task-dispatcher.service)
for SVC in "${SERVICES_TO_HEAL[@]}"; do ...
```

**Step 5 — OMS visibility** (optional, ~30 min):
Add a small status indicator on the OMS tasks page showing the dispatcher is running and last dispatch time. Store a heartbeat event to episodic memory every 10 dispatches or every 15 minutes of idle.

---

### Phase 2 Options (post-validation)

**2a. Server-side `/tasks/queue/next` endpoint**: Move selection logic (priority, CLI availability, dependency check) into the API. Dispatcher becomes `while True: run /tasks/queue/next → run → sleep 5s`. Cleaner separation.

**2b. PostgreSQL LISTEN/NOTIFY**: When `can_run_more` transitions true (task completes), emit `NOTIFY task_ready`. Dispatcher switches from polling to event-driven. Latency drops from 15s to <1s. Worth doing if 15s proves too slow in practice.

**2c. Multiple dispatch per cycle**: Currently dispatches one task per 15s cycle. If queue has 5 pending tasks and 5 empty slots simultaneously (e.g., at startup), this takes 5×15s = 75s to fill. Phase 2 can batch: dispatch up to `can_run_more` count per cycle. Adds minor complexity but worthwhile for fast queue draining.

---

### Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| **Double-dispatch race** (dispatcher + heartbeat both call `/run`) | Low | API status guard makes second call return 409. Handled gracefully. No actual problem. |
| **API unreachable at startup** | Medium | `After=otto-memory.service` in systemd + retry loop in the dispatcher. |
| **Rate limit not respected** | Low | Both API check and sentinel file check in `is_rate_limited()`. Same logic as heartbeat. |
| **Dispatcher launches low-priority tasks over high-priority ones** | Low | `GET /tasks?status=pending` already ordered by `priority DESC, created_at ASC`. |
| **Task runner dies immediately** (budget exhausted, bad prompt) | Normal | This is normal behavior. `task_runner.sh` marks it failed. Dispatcher sees `pending` count drop on next poll. |
| **Memory leak in in_flight dict** | Negligible | Cleared every 60s. Max 20 entries at any time. |
| **Dispatcher logs filling disk** | Low | Log rotation via logrotate or `StandardOutput` truncation. Add to maintenance script. |

---

### Coexistence with Heartbeat

The dispatcher and heartbeat have **orthogonal responsibilities**:

| Responsibility | Dispatcher | Heartbeat |
|---|---|---|
| Launch pending tasks | ✅ | Still does this as fallback |
| Create new tasks | ❌ | ✅ |
| Review completed tasks | ❌ | ✅ |
| Message Mev | ❌ | ✅ |
| Memory consolidation | ❌ | Reflection heartbeat ✅ |

The heartbeat should continue trying to launch pending tasks as before. The dispatcher just means the heartbeat almost always finds 0 pending tasks at cycle start (they've already been launched). The heartbeat's launch logic becomes a safety net rather than the primary mechanism — no code changes needed.

---

### Deployment Checklist

- [ ] Create `~/otto/task_dispatcher.py`
- [ ] Create `/etc/systemd/system/otto-task-dispatcher.service`
- [ ] `sudo systemctl daemon-reload && sudo systemctl enable --now otto-task-dispatcher`
- [ ] Verify: `systemctl status otto-task-dispatcher`
- [ ] Monitor first 5 minutes: `tail -f ~/otto/logs/task-dispatcher.log`
- [ ] Confirm a task dispatches within 15s of creation: create a test task and watch the log
- [ ] Add `otto-task-dispatcher.service` to heartbeat.sh self-healing loop
- [ ] Store episodic memory confirming deployment

---

### Estimated Cost

- Phase 1 implementation: ~$2-3 (coder task)
- Ongoing operational cost: ~$0 (Python process, no LLM calls)
- Runtime overhead: ~4 HTTP requests/minute — negligible on local loopback
