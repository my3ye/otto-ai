# Design: Live Services Monitoring System

> Authored by architect agent — 2026-03-15
> Status: FINAL — ready for implementation

---

## Problem

Otto has two fundamentally different kinds of work:

1. **Tasks** — finite Claude Code CLI sessions that start, do something, and end. Current system handles these well.
2. **Live Services** — persistent processes with no natural end: signal watcher, alpha heartbeat, broadcast adapter, WhatsApp bridge, systemd services. These run indefinitely and need a different monitoring model.

The Wink monitor watches task *output* for stalls. That works for tasks. It doesn't work for live services because:
- There's no expected completion — stalling is expected
- Some services produce output only when triggered (broadcast adapter)
- A service can appear healthy (process running) while silently failing (no output, dead connection)

Mev's directive: *"For such tasks, since they have no ceilings, you can have a system to monitor them instead maybe with heartbeats."*

---

## Approach

### Two-Tier Model

```
Tier 1: Task Queue (existing)
├── Finite work — has a start and an expected end
├── Claude Code CLI processes
├── Wink monitor (output stall detection)
├── Status: pending → running → completed/failed
└── UI: /tasks (existing)

Tier 2: Live Services (new)
├── Persistent processes — no expected end
├── systemd services, Docker containers, HTTP APIs, scripts
├── Service Monitor (periodic health check daemon)
├── Status: healthy → degraded → down → recovering
└── UI: /services (new)
```

### What Counts as a Live Service

| Service | Type | Check Method |
|---|---|---|
| otto-memory | systemd | `systemctl is-active` |
| whatsapp | systemd | `systemctl is-active` + HTTP ping :3001 |
| otto-heartbeat.timer | systemd | `systemctl is-active` |
| otto-reflection.timer | systemd | `systemctl is-active` |
| memory-postgres-1 | docker | `docker inspect` status |
| memory-neo4j-1 | docker | `docker inspect` status |
| memory-graphiti-1 | docker | `docker inspect` status + HTTP :8000 |
| Memory API | http | GET /health → 200 |
| Signal publisher | process | lock file + PID alive + last_output_at |
| Alpha heartbeat | process | last run timestamp |
| Broadcast adapter | process | last dispatch timestamp |

### Health Check Semantics

Each service defines how to check itself:

```
healthy   — check passed, service responding normally
degraded  — check passed but output flow is stalled (data flow issue)
down      — check failed (process dead, HTTP 5xx/timeout, container stopped)
recovering — was down, just came back up
unknown   — no check run yet, or check itself errored
```

### Alert Logic

```
consecutive_failures >= failure_threshold (default: 3)
  → episodic event (wink_alert, importance=8)
  → status set to "down"

down for >= 30 minutes AND service.alert_mev = true
  → WhatsApp alert via tools/whatsapp_send.sh

service recovers (check passes after being down)
  → episodic event (service_recovered, importance=6)
  → status set to "recovering" then "healthy"

data flow stall (no output for expected_output_interval_s)
  → status set to "degraded"
  → episodic event (data_flow_stall, importance=7)
```

### Service Monitor Daemon

`service_monitor.sh` — lightweight bash script, no Claude needed.

- Runs as systemd timer: `otto-service-monitor.timer` every 5 minutes
- Calls `GET /services` to get all registered services
- Runs health check per service type
- Calls `POST /services/{id}/heartbeat` with result
- Logs to `~/otto/logs/service-monitor.log`

**Why bash, not Python?**
- No Claude budget consumed
- No dependencies to break
- Trivially auditable
- Fast (sub-second per service)

**Why 5-minute interval?**
- Frequent enough to catch outages before they affect work
- Not so frequent it generates noise (daily: 288 checks per service)
- Matches typical alerting SLOs for non-critical infrastructure

---

## Key Decisions

- **Separate table from tasks**: `live_services` + `service_health_logs`. Rationale: different lifecycle, different queries, different UI. Alternative rejected: adding a `service_type` flag to tasks — would pollute the task model.
- **Bash daemon, not Python**: Budget discipline. A 5-minute check loop costs $0. Alternative: Python FastAPI background task — adds complexity, restarts on API restart.
- **systemd timer, not cron**: Consistent with Otto's existing infrastructure. Alternative: cron — less observable, harder to manage.
- **Service registration via API, not config file**: Live services can be promoted by tasks at runtime. Alternative: static config — requires code changes to add services.
- **failure_threshold=3 default**: 3 consecutive failures = 15 minutes of confirmed downtime before alert. Avoids alert storms from transient restarts. Alternative: fail-fast (1 failure) — too noisy.
- **Data flow monitoring via last_output_at**: Simple timestamp-based stall detection. Alternative: parsing output logs — fragile, service-specific.

---

## API Contract

### Endpoints

```
GET    /services                  — list all services with current status
POST   /services                  — register a new live service
GET    /services/{id}             — get single service + recent health log
PUT    /services/{id}             — update service config
DELETE /services/{id}             — deregister service
POST   /services/{id}/heartbeat   — record a health check result (called by monitor)
POST   /services/{id}/output      — record data flow activity (called by service itself)
GET    /services/summary          — counts by status (for OMS dashboard widget)
```

### Service Registration Body

```json
{
  "name": "signal-publisher",
  "display_name": "Signal Publisher",
  "service_type": "process",        // systemd | docker | http | process | script
  "description": "Publishes crypto signals to @OttoSignals Telegram",

  // Health check config
  "check_method": "process",
  "check_target": "signal_publisher.py",   // process name, URL, systemd unit, container name
  "check_timeout_s": 10,
  "failure_threshold": 3,                  // consecutive failures before down
  "heartbeat_interval_s": 300,             // expected check interval (5 min)

  // Data flow monitoring (optional)
  "expected_output_interval_s": 3600,      // alert if no output for 1h (null = disabled)

  // Alerting
  "alert_mev": true,                       // WhatsApp Mev if down > 30min
  "priority": 7,                           // 1-10, influences alert urgency

  // Auto-restart
  "auto_restart": false,                   // attempt restart on failure (systemd only)
  "restart_command": null
}
```

### Heartbeat Body (from monitor)

```json
{
  "status": "healthy",              // healthy | degraded | down | unknown
  "response_time_ms": 12,
  "details": "systemctl: active (running) since 2026-03-15T08:00:00Z",
  "checked_at": "2026-03-15T14:30:00Z"
}
```

---

## Database Schema

```sql
-- live_services: registered persistent services
CREATE TABLE live_services (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL UNIQUE,
  display_name TEXT,
  service_type TEXT NOT NULL,        -- systemd | docker | http | process | script
  description TEXT,

  -- Health check config
  check_method TEXT NOT NULL,
  check_target TEXT NOT NULL,        -- URL, unit name, process name, container name
  check_timeout_s INT NOT NULL DEFAULT 10,
  failure_threshold INT NOT NULL DEFAULT 3,
  heartbeat_interval_s INT NOT NULL DEFAULT 300,

  -- Data flow
  expected_output_interval_s INT,    -- NULL = not monitored
  last_output_at TIMESTAMPTZ,

  -- Current state
  status TEXT NOT NULL DEFAULT 'unknown',  -- healthy | degraded | down | recovering | unknown
  consecutive_failures INT NOT NULL DEFAULT 0,
  last_check_at TIMESTAMPTZ,
  last_healthy_at TIMESTAMPTZ,
  down_since TIMESTAMPTZ,

  -- Alerting
  alert_mev BOOLEAN NOT NULL DEFAULT TRUE,
  mev_alerted_at TIMESTAMPTZ,       -- when we last WhatsApp'd Mev about this
  priority INT NOT NULL DEFAULT 5,

  -- Lifecycle
  enabled BOOLEAN NOT NULL DEFAULT TRUE,
  auto_restart BOOLEAN NOT NULL DEFAULT FALSE,
  restart_command TEXT,

  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  metadata JSONB DEFAULT '{}'::jsonb
);

-- service_health_logs: rolling health check history
CREATE TABLE service_health_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  service_id UUID NOT NULL REFERENCES live_services(id) ON DELETE CASCADE,
  status TEXT NOT NULL,
  response_time_ms INT,
  details TEXT,
  checked_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_service_health_service_id ON service_health_logs (service_id, checked_at DESC);
```

---

## service_monitor.sh Design

```bash
#!/bin/bash
# Otto Service Monitor — checks all registered live services
# Called by otto-service-monitor.timer every 5 minutes
# No Claude, no budget. Pure bash health checks.

for each service in GET /services:
  case service_type:
    systemd  → systemctl is-active <unit>
    docker   → docker inspect --format='{{.State.Status}}' <container>
    http     → curl -sf --max-time <timeout> <url>
    process  → pgrep -f <process_name> || cat <pidfile>
    script   → bash <script_path>

  POST /services/{id}/heartbeat with result

  if status == "down" AND consecutive_failures >= failure_threshold:
    POST /episodic/events (wink_critical)
    if down_since > 30min AND alert_mev AND not alerted_recently:
      whatsapp_send.sh "⚠️ Service down: <name> (30+ min)"
```

---

## OMS UI Spec: /services — Live Systems

### Layout

```
┌─────────────────────────────────────────────────────────┐
│  Live Systems                          [+ Register]      │
│  Last checked: 2 min ago               [Refresh]         │
├─────────────────────────────────────────────────────────┤
│  ● 8 healthy   ⚠ 1 degraded   ✗ 0 down                  │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  INFRASTRUCTURE                                          │
│  ┌──────────────────────────────────────────────────┐   │
│  │ ● otto-memory       systemd   healthy   < 1ms    │   │
│  │ ● postgres          docker    healthy   < 1ms    │   │
│  │ ● neo4j             docker    healthy   3ms      │   │
│  │ ● graphiti          docker    healthy   5ms      │   │
│  │ ● whatsapp          systemd   healthy   < 1ms    │   │
│  └──────────────────────────────────────────────────┘   │
│                                                          │
│  AUTOMATION                                              │
│  ┌──────────────────────────────────────────────────┐   │
│  │ ● heartbeat.timer   systemd   healthy   < 1ms    │   │
│  │ ● reflection.timer  systemd   healthy   < 1ms    │   │
│  │ ⚠ signal-publisher  process   degraded  --       │   │
│  │   └ No output for 2h 14m (expected: 1h)          │   │
│  └──────────────────────────────────────────────────┘   │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

### Status Indicators
- `●` green — healthy
- `⚠` amber — degraded (process alive but data flow stalled)
- `✗` red — down (check failed)
- `↻` blue — recovering

### Service Row (expanded)
Clicking a service row shows:
- Last 24h health timeline (bar chart — each bar = one check)
- Last 10 health log entries
- `last_output_at` if data flow monitored
- `down_since` if down
- Manual action buttons: [Check Now] [Restart] (if auto_restart enabled)

### Difference from /tasks

| | Task Queue | Live Systems |
|---|---|---|
| Lifecycle | finite (start → end) | infinite (start → runs forever) |
| Review | needs human review | no review — autonomous monitoring |
| Budget | tracks $ spent | no budget concept |
| Alert | heartbeat reviews | daemon monitors |
| History | full output | health log samples |
| Action | create/review/launch | register/check/restart |

---

## Implementation Plan

### Phase 1: Foundation (implement now)
1. `migrations/045_live_services.sql` — tables
2. `memory/routes/services.py` — CRUD + heartbeat endpoints
3. Register in `memory/api.py`
4. Pre-seed infrastructure services (postgres, neo4j, otto-memory, etc.)

### Phase 2: Monitor Daemon
5. `service_monitor.sh` — bash health check loop
6. `otto-service-monitor.service` + `.timer` — systemd units (5min)
7. Test: manually trigger, verify episodic events fire

### Phase 3: OMS UI
8. `/services` page in web-next — Live Systems view
9. Service detail drawer
10. Dashboard widget (summary counts)

### Phase 4: Task → Service Promotion (optional, later)
11. `POST /services/promote/{task_id}` — when a task completes that creates a persistent service, promote it
12. heartbeat.sh integration — include service summary in WM context

---

## Risks

- **Monitor daemon false positives**: systemd services restart quickly; a check during restart window will report "down". Mitigation: failure_threshold=3 (15 min buffer).
- **Data flow stall noise**: signal publisher only fires when there are signals — may go hours without output legitimately. Mitigation: make expected_output_interval_s configurable per service, NULL = no data flow monitoring.
- **service_health_logs table growth**: 288 checks/day per service × 10 services = 2,880 rows/day. Mitigation: add to maintenance job to prune > 7 days.
- **Auto-restart loop**: if a service keeps failing, auto_restart could hammer it. Mitigation: auto_restart=false by default, only enable for proven stable services.
