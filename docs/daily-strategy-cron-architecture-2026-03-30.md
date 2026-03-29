# Design: Daily Strategic Cron

## Problem

Mev wants a daily automated strategic review that answers three questions:
1. **Mission**: What is the most important thing to advance the mission?
2. **Public-ready**: What is the most important thing to get the system ready for public?
3. **Core system**: What is the most important thing to improve the core system?

Each answer should produce actionable tasks dispatched to the right agents. Currently, strategic thinking only happens reactively (when Mev asks) or as a side-effect of heartbeat cycles. There is no dedicated, recurring strategic planning process.

## Approach

A single daily Claude Code session running a `strategist` agent. One session, three analyses, actionable output. Follows the exact same pattern as heartbeat/reflection (shell script + systemd timer + agent prompt).

### Why one session, not three parallel tasks?

- **Budget discipline**: One session ~$1.50-2.00 vs three parallel ~$3.50-4.50. Saves ~$60/month.
- **Shared context**: The three questions overlap — mission priorities inform public-readiness which informs core system improvements. One agent reasoning across all three produces more coherent strategy.
- **Simplicity**: One timer, one service, one log, one lock file. Same pattern as every other cron.

### Data Flow

```
┌─────────────────────────────────────────────────────────┐
│ otto-strategy.timer (daily, 05:00 IST / 23:30 UTC)     │
│   → otto-strategy.service                               │
│     → daily_strategy.sh                                 │
│       ├── Rate limit check                              │
│       ├── Lock acquisition                              │
│       ├── Fetch unified context from kernel              │
│       ├── claude --agent strategist --model sonnet       │
│       │   ├── Phase 1: GATHER (read current state)      │
│       │   │   ├── GET /tasks/queue/status               │
│       │   │   ├── GET /context/inject                   │
│       │   │   ├── GET /pending/open                     │
│       │   │   ├── GET /semantic/search (directives)     │
│       │   │   ├── GET /task-plans/dashboard/status      │
│       │   │   ├── curl public sites (health)            │
│       │   │   └── git log --since=24h                   │
│       │   ├── Phase 2: ANALYZE (three deep dives)       │
│       │   │   ├── Q1: Mission advancement               │
│       │   │   ├── Q2: Public readiness                  │
│       │   │   └── Q3: Core system improvement           │
│       │   ├── Phase 3: ACT (dispatch tasks)             │
│       │   │   ├── POST /tasks (1-3 tasks per analysis)  │
│       │   │   └── POST /task-plans (for multi-step)     │
│       │   └── Phase 4: REPORT                           │
│       │       ├── POST /semantic/remember (daily brief) │
│       │       └── whatsapp_send.sh (summary to Mev)     │
│       ├── Rate limit detection                          │
│       └── Post-processing + log cleanup                 │
└─────────────────────────────────────────────────────────┘
```

## Key Decisions

1. **Single session vs. task plan with 3 items**: Single session because shared context produces more coherent cross-cutting strategy, and it's 40% cheaper. Alternative: task plan with 3 parallel items + synthesis step — better parallelism but loses cross-analysis coherence and costs more.

2. **Model: Sonnet (not Opus)**: Strategic analysis benefits from reasoning depth but Opus at ~2x cost daily adds up. Sonnet with `--effort high` provides good strategic reasoning at acceptable cost. Alternative: Opus would be higher quality but ~$3-4/day instead of ~$1.50-2.

3. **Time: 05:00 IST (23:30 UTC)**: Early morning before Mev's work day. Mev wakes up to strategic recommendations. Alternative: midnight (too early, tasks from yesterday may not be complete), or 09:00 (too late, Mev is already working).

4. **Max tasks per analysis: 3**: Cap of 9 total tasks created per day (3 analyses × 3 tasks max). This prevents runaway task creation while allowing meaningful work. Tasks that need decomposition use task plans internally.

5. **WhatsApp summary**: Daily brief sent to Mev as a concise message. Each analysis gets 2-3 lines: what was identified, what was dispatched. Alternative: no message (but this defeats the purpose — Mev should see the strategic thinking).

6. **Budget: $2.00 per run**: Enough for deep analysis + task creation API calls. The agent itself costs ~$1.50, task creation via curl is free. Alternative: $1.00 (too tight for three deep analyses).

## Files to Create/Modify

### 1. `/home/web3relic/otto/.claude/agents/strategist.md` (NEW)

Agent prompt for the daily strategist. Core structure:

```markdown
# Otto Daily Strategist

You are Otto's strategic planning engine. You run once daily to identify and dispatch
the most impactful work across three dimensions.

## Your Mission

Answer three questions with deep analysis, then create actionable tasks:

### Q1: Mission Advancement
"What is the most important thing we can work on RIGHT NOW to advance our mission?"
- Review: active directives (P10/P9), current blockers, recent completions
- Consider: WebAssist revenue, ONEON network, SOS Systems, Tusita, capital paths
- Weight: revenue-generating and user-facing work over infrastructure

### Q2: Public Readiness
"What is the most important thing to get our system ready for public?"
- Review: all public sites (health, content, SEO), security posture, user onboarding flows
- Consider: what would embarrass us if someone found it? What's the critical path to launch?
- Weight: things visible to users over internal tooling

### Q3: Core System Improvement
"What is the most important thing to improve our core system?"
- Review: reliability metrics, error rates, performance, technical debt
- Consider: heartbeat health, task queue efficiency, memory system, API stability
- Weight: operational reliability over new features

## Protocol

### Phase 1: GATHER
Read the current state. Do not skip any of these:

```bash
# Task queue state
curl -sf http://localhost:8100/tasks/queue/status

# Current directives and priorities
curl -sf http://localhost:8100/context/inject

# Open blockers / questions for Mev
curl -sf http://localhost:8100/pending/open

# Recent task completions (last 24h)
curl -sf "http://localhost:8100/tasks?status=completed&since=24h&limit=20"

# Recent failures (last 24h)
curl -sf "http://localhost:8100/tasks?status=failed&since=24h&limit=10"

# Plan execution dashboard
curl -sf http://localhost:8100/task-plans/dashboard/status

# Recent semantic memories (strategic category)
curl -sf -X POST http://localhost:8100/semantic/search \
  -H 'Content-Type: application/json' \
  -d '{"query": "strategic priority mission advancement", "limit": 5}'

# Yesterday's strategy brief (avoid repeating)
curl -sf -X POST http://localhost:8100/semantic/search \
  -H 'Content-Type: application/json' \
  -d '{"query": "daily strategic brief", "category": "strategy", "limit": 1}'

# Git activity last 24h
git log --since="24 hours ago" --oneline | head -20

# Public site health
for site in webassist.ink my3ye.xyz otto.lk mev.otto.lk oneon.ink tusita.xyz; do
  code=$(curl -sf -o /dev/null -w "%{http_code}" --max-time 5 "https://$site" 2>/dev/null || echo "000")
  echo "$site: $code"
done
```

### Phase 2: ANALYZE
For each question, write a structured analysis:

```
## Q[N]: [Question]

### Current State
[2-3 sentences on where we are]

### Gap Analysis
[What's missing, broken, or suboptimal]

### Recommendation
**THE most important thing**: [One clear recommendation]

### Why This, Not Something Else
[Brief justification — why this over other candidates]

### Tasks to Dispatch
1. [Task title] — agent: [type], priority: [P1-P10], budget: $[X]
   Prompt: [clear, specific instruction]
2. ...
```

### Phase 3: ACT
Create tasks via the API. Rules:
- Max 3 tasks per analysis (9 total maximum)
- Set priority matching the directive it serves (P10 for WebAssist, P9 for OMS, etc.)
- Use agent_type that matches the work (coder, architect, debugger, researcher, etc.)
- For multi-step work, create a task plan instead of individual tasks
- NEVER create tasks that duplicate already-pending or running tasks
- Check task queue before creating — respect the 5-concurrent limit
- Set realistic budgets ($1-3 for implementation, $0.50-1 for research/review)

```bash
# Single task
curl -sf -X POST http://localhost:8100/tasks \
  -H 'Content-Type: application/json' \
  -d '{
    "title": "...",
    "prompt": "...",
    "priority": 8,
    "agent_type": "coder",
    "model": "sonnet",
    "max_budget_usd": 2.0,
    "working_directory": "/home/web3relic/otto",
    "created_by": "daily_strategy"
  }'

# Multi-step plan
curl -sf -X POST http://localhost:8100/task-plans \
  -H 'Content-Type: application/json' \
  -d '{
    "title": "...",
    "instruction": "...",
    "items": [...],
    "created_by": "daily_strategy"
  }'
```

### Phase 4: REPORT
1. Store a strategic brief in semantic memory:
```bash
curl -sf -X POST http://localhost:8100/semantic/remember \
  -H 'Content-Type: application/json' \
  -d '{
    "content": "Daily strategic brief [DATE]: Q1 Mission: [recommendation]. Q2 Public: [recommendation]. Q3 Core: [recommendation]. Tasks created: [count].",
    "category": "strategy",
    "confidence": 0.9
  }'
```

2. Send WhatsApp summary to Mev:
```bash
/home/web3relic/otto/tools/whatsapp_send.sh "📋 Daily Strategy Brief

🎯 Mission: [one-liner recommendation]
→ [task(s) dispatched]

🌐 Public-Ready: [one-liner recommendation]
→ [task(s) dispatched]

⚙️ Core System: [one-liner recommendation]
→ [task(s) dispatched]

[total] tasks queued. Details at mev.otto.lk/tasks"
```

## Rules
- Do NOT do implementation work yourself. Your job is to THINK and DISPATCH.
- Do NOT create tasks that are already running or pending.
- Do NOT repeat yesterday's recommendations unless they remain the top priority.
- Justify every recommendation against the active directives.
- If the system is idle and healthy, acknowledge it — don't invent busywork.
- Be specific in task prompts. "Fix the thing" is useless. Include file paths, error details, expected outcomes.
- When in doubt about priority, check the directive list: P10 WebAssist > P9 OMS > P9 ONEON/Capital > P8 Ship > P8 Budget.
```

### 2. `/home/web3relic/otto/daily_strategy.sh` (NEW)

Shell script following the heartbeat.sh pattern exactly:

```bash
#!/bin/bash
# Otto Daily Strategy Runner
# Called by systemd timer once daily. Runs 3 strategic deep-dives and dispatches tasks.

set -euo pipefail

OTTO_DIR="/home/web3relic/otto"
LOCK_FILE="/tmp/otto-strategy.lock"
LOG_DIR="${OTTO_DIR}/logs"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="${LOG_DIR}/strategy-${TIMESTAMP}.log"
API="http://localhost:8100"

mkdir -p "$LOG_DIR"

# Lock
if [ -f "$LOCK_FILE" ]; then
    LOCK_PID=$(cat "$LOCK_FILE" 2>/dev/null || echo "")
    if [ -n "$LOCK_PID" ] && kill -0 "$LOCK_PID" 2>/dev/null; then
        echo "$(date -Iseconds) Strategy already running (PID $LOCK_PID), skipping." >> "$LOG_FILE"
        exit 0
    else
        rm -f "$LOCK_FILE"
    fi
fi

# Rate limit check (same pattern as heartbeat)
RATE_LIMITED=$(curl -sf "${API}/kernel/providers/rate-limited" 2>/dev/null | \
    python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('rate_limited','false'))" 2>/dev/null || echo "false")
if [ "$RATE_LIMITED" = "True" ] || [ "$RATE_LIMITED" = "true" ]; then
    echo "$(date -Iseconds) SKIP: Rate limit active." >> "$LOG_FILE"
    exit 0
fi

echo $$ > "$LOCK_FILE"
trap 'rm -f "$LOCK_FILE"' EXIT

echo "$(date -Iseconds) Otto daily strategy starting..." >> "$LOG_FILE"

# Unified context (same as heartbeat)
UNIFIED_CONTEXT=""
UNIFIED_CONTEXT_JSON=$(curl -sf "${API}/kernel/context?role=strategist&max_tokens=10000" 2>/dev/null || echo "")
if [ -n "$UNIFIED_CONTEXT_JSON" ]; then
    UNIFIED_CONTEXT=$(echo "$UNIFIED_CONTEXT_JSON" | python3 -c "
import json, sys
try:
    d = json.load(sys.stdin)
    ctx = d.get('context_text', '')
    if ctx: print(ctx)
except: pass
" 2>>"$LOG_FILE" || echo "")
fi

PROMPT=""
if [ -n "$UNIFIED_CONTEXT" ]; then
    PROMPT="[UNIFIED BRAIN CONTEXT]
${UNIFIED_CONTEXT}
[END UNIFIED CONTEXT]

"
fi
PROMPT="${PROMPT}Run your daily strategic analysis. Answer the three questions, dispatch tasks, send the brief to Mev."

cd "$OTTO_DIR"
export OTTO_SESSION_TYPE=strategy

timeout 900s /home/web3relic/.local/bin/claude \
    --print \
    --agent strategist \
    --dangerously-skip-permissions \
    --model sonnet \
    --effort high \
    --no-session-persistence \
    -p "$PROMPT" \
    >> "$LOG_FILE" 2>&1
EXIT_CODE=$?

if [ $EXIT_CODE -eq 124 ]; then
    echo "$(date -Iseconds) Strategy TIMED OUT after 900s" >> "$LOG_FILE"
elif [ $EXIT_CODE -ne 0 ]; then
    echo "$(date -Iseconds) Strategy failed with exit code $EXIT_CODE" >> "$LOG_FILE"
fi

# Rate limit detection
if grep -qE "HTTP 429|RateLimitError|overloaded_error|too_many_requests|rate_limit_exceeded" "$LOG_FILE" 2>/dev/null; then
    date +%s > /tmp/otto-rate-limited
    echo "$(date -Iseconds) Rate limit detected — sentinel written." >> "$LOG_FILE"
fi

echo "$(date -Iseconds) Otto daily strategy completed (exit=$EXIT_CODE)." >> "$LOG_FILE"

# Clean old logs (keep 30 days — strategic briefs are reference material)
find "$LOG_DIR" -name "strategy-*.log" -mtime +30 -delete 2>/dev/null || true
```

### 3. systemd timer + service (NEW)

**`/etc/systemd/system/otto-strategy.timer`**:
```ini
[Unit]
Description=Otto Daily Strategy Timer

[Timer]
OnCalendar=*-*-* 05:00:00
Persistent=true
RandomizedDelaySec=300

[Install]
WantedBy=timers.target
```

**`/etc/systemd/system/otto-strategy.service`**:
```ini
[Unit]
Description=Otto Daily Strategic Analysis
After=otto-memory.service
Wants=otto-memory.service

[Service]
Type=oneshot
User=web3relic
Group=web3relic
WorkingDirectory=/home/web3relic/otto
ExecStart=/home/web3relic/otto/daily_strategy.sh
Environment=HOME=/home/web3relic
Environment=PATH=/home/web3relic/.local/bin:/usr/local/bin:/usr/bin:/bin
TimeoutStartSec=1200

[Install]
WantedBy=multi-user.target
```

### 4. Modify `heartbeat.sh` (EXISTING)

Add self-healing check for the strategy timer (same pattern as existing sibling timers):

```bash
# In the self-healing block, add:
for TIMER in otto-reflection.timer otto-maintenance.timer otto-security-audit.timer otto-vuln-sync.timer otto-strategy.timer; do
```

## Task Dispatch Logic

The strategist agent decides what to dispatch based on analysis. The key constraint is: **it must not duplicate work that's already queued**.

### Pre-dispatch check (built into agent prompt):
```bash
# Before creating any task, check existing queue
EXISTING=$(curl -sf "http://localhost:8100/tasks?status=pending,running" | \
  python3 -c "import json,sys; tasks=json.load(sys.stdin); [print(t['title']) for t in tasks]")
```

### Dispatch routing table:

| Analysis | Likely Agent Types | Typical Tasks |
|---|---|---|
| Q1 Mission | coder, architect, content-creator, growth-hacker | Ship features, write content, build integrations |
| Q2 Public | frontend-developer, security-engineer, seo-specialist | Fix UI, harden security, optimize SEO |
| Q3 Core | debugger, backend-architect, sre | Fix bugs, improve reliability, optimize performance |

### Budget caps per task:
- Implementation (coder, frontend-developer): $2.00
- Architecture (architect): $1.50
- Research (researcher): $1.00
- Review (reviewer, security-engineer): $1.00
- Content (content-creator): $1.50

## Risks

1. **Runaway task creation**: Strategist creates too many tasks, overwhelming the queue.
   - Mitigation: Hard cap of 9 tasks/day in the agent prompt. Pre-dispatch queue check.

2. **Stale strategy**: Agent repeats the same recommendation daily because nothing changed.
   - Mitigation: Agent reads yesterday's brief and must justify repetition.

3. **Budget overrun**: $2/day × 30 = $60/month just for the strategy cron.
   - Mitigation: Sonnet model (not Opus), $2.00 session cap, 900s timeout. Can be disabled via timer if budget is tight.

4. **Conflict with heartbeat**: Strategy cron creates tasks that conflict with heartbeat's task management.
   - Mitigation: `created_by: "daily_strategy"` tag on all tasks. Heartbeat already respects existing queue. Strategy runs at 05:00, heartbeat at :00/:30 — they don't overlap.

5. **Hallucinated state**: Agent claims tasks exist or sites are down when they're not.
   - Mitigation: All analysis is API-call driven (curl commands in the prompt). Agent gathers evidence before analyzing.

## Implementation Plan

1. **Create `strategist.md` agent prompt** — the core intelligence. (~30 min)
2. **Create `daily_strategy.sh` shell script** — copy heartbeat.sh pattern, adapt. (~15 min)
3. **Create systemd timer + service** — two small files. (~5 min)
4. **Add strategy timer to heartbeat self-healing** — one-line edit. (~2 min)
5. **Enable and test** — `systemctl enable --now otto-strategy.timer`, manual trigger to verify. (~10 min)

Total estimated cost: ~$1.50 implementation + $2.00/day operating.

## Cost Analysis

| Component | One-time | Daily | Monthly |
|---|---|---|---|
| Implementation | ~$1.50 | — | — |
| Strategy session (Sonnet) | — | ~$1.50-2.00 | ~$45-60 |
| Tasks dispatched (avg 5/day) | — | ~$5-10 | ~$150-300 |

The strategy session cost is fixed. The task cost depends on what gets dispatched — but those tasks would be created anyway (just by heartbeat reacting to Mev's requests instead of proactively). The cron shifts task creation from reactive to proactive.
