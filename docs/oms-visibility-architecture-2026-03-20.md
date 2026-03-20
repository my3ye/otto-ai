# OMS Visibility Coverage — Architecture Design
**Date:** 2026-03-20
**Author:** Otto (architect agent)
**Task:** [WF] Audit OMS visibility coverage and build missing display surfaces

---

## Design: OMS Visibility Gap Remediation

### Problem

Otto generates many artifacts that Mev cannot see from the OMS. The most critical gap: 2,273 outreach messages sitting in `outreach_queue` with status=`pending` — awaiting Mev review — with no OMS UI to review or approve them. Secondary gaps: grant draft documents are invisible (buried in Content Hub without filtering), 18 project roadmaps are in the DB but the OMS Roadmap page shows static hardcoded content, and 2,580 agent activity log entries have no display surface.

**Full audit findings:**

| Data | DB Table | API Route | OMS Page | Gap Severity |
|------|----------|-----------|----------|--------------|
| Outreach queue (2273 pending) | `outreach_queue` | `GET /outreach/queue` | ❌ None | **CRITICAL** |
| Grant drafts (6 docs) | `content` (type=research/plan) | `GET /content` | ⚠️ Content Hub (no filter) | HIGH |
| Project roadmaps (18 entries) | `content` (type=roadmap) | `GET /content` | ⚠️ /roadmap is static | HIGH |
| Agent activity (2580 entries) | `agent_activity_log` | ❌ No route | ❌ None | MEDIUM |
| Task outputs | `tasks` | `GET /tasks/{id}` | ✅ /tasks/detail | OK |
| Memory writes | `semantic_memories` | `GET /semantic` | ✅ /memory | OK |
| Content pipeline status | `content` + `workflow_instances` | existing | ⚠️ No workflow linkage | LOW |

**What's already adequate:**
- Task outputs: `/tasks/detail` shows output, error, QA tabs — fine
- Memory: `/memory` has semantic, episodic, working memory, principles, procedures — comprehensive
- Workflows: `/workflows` shows pipeline state with step progress

---

### Approach

Four targeted additions, in priority order:

**1. Outreach Queue page** — New page at `/webassist/outreach`
Add to sidebar under Products group. Calls existing `/outreach/queue` and `/outreach/stats` API. Shows tabbed view by status (pending/approved/rejected/sent). Approve/reject actions inline.

**2. Grant Drafts surface** — Filter in Content Hub
Add "Grants" quick-filter button to the existing Content Hub page (`/content-hub`). Filter by `content_type IN ('research','plan')` and title keyword search. No new page needed.

**3. Live Project Roadmap** — Connect `/roadmap` to DB content
Fetch `content` items where `content_type='roadmap'` and surface them as expandable cards alongside (or replacing) the static phase data. 18 universe project roadmaps become browseable.

**4. Agent Activity feed** — Tab on `/agents` page
Add an "Activity" tab to the existing agents page. New API endpoint `GET /agents/activity` that queries `agent_activity_log` with pagination.

**5. Auto-surfacing config** — Heartbeat + task runner changes
Update task runner to log completion events to `agent_activity_log`. Ensure research tasks store outputs in `research_notes` table (not just task output field). This is a config/policy change, not UI.

---

### Key Decisions

- **Outreach as `/webassist/outreach` not `/contacts/outreach`**: The outreach queue is for WebAssist lead outreach, not general contacts. Keeps the Products group coherent. Alternative: `/contacts/outreach` — rejected because outreach_queue rows reference `web_assist_leads`.

- **Grant filter in Content Hub, not a new page**: Grant docs are content items. A dedicated page would duplicate the Content Hub's functionality. A quick-filter button is 20 lines of code vs a whole new page. Alternative: `/capital/grants` — rejected (over-engineering, same data).

- **Roadmap: augment static + live, don't replace**: The static phase data (Phase 0, 1, 2, 3 with milestones) is valuable — it's the release plan. The 18 DB roadmaps are per-project roadmaps. Show both: static release phases at top, DB project roadmaps below in a filterable grid. Alternative: replace static — rejected (loses release plan visibility).

- **Agent activity as a tab on /agents, not a new page**: /agents already exists. A tab costs one API call and ~50 lines. Alternative: `/agents/activity` new page — rejected (sidebar is already long).

- **No new DB tables**: All data already exists. This is purely a UI/API surface problem.

---

### API / Interface

#### New: `GET /agents/activity`
```
Query params:
  agent_id: optional string filter
  event_type: optional string filter
  limit: int (default 50)
  offset: int (default 0)

Response:
{
  "total": 2580,
  "entries": [
    {
      "id": "uuid",
      "agent_id": "heartbeat",
      "event_type": "task_completed",
      "details": {...},
      "created_at": "2026-03-20T..."
    }
  ]
}
```

#### Existing (already available, just needs OMS page):
- `GET /outreach/queue?status=pending&limit=50` → outreach messages
- `GET /outreach/stats` → counts by status/channel/lead_type
- `POST /outreach/{id}/approve` → `{"action": "approve"|"reject"}`
- `GET /content?content_type=research&limit=50` → grant docs filter
- `GET /content?content_type=roadmap&limit=50` → project roadmaps

---

### Implementation Plan

#### Step 1: Outreach Queue page (HIGHEST PRIORITY)
1. Create `/home/web3relic/interfaces/web-next/src/app/webassist/outreach/page.tsx`
2. Add API types for `OutreachMessage` to `src/lib/api-types.ts`
3. Page structure: stats bar (pending/approved/sent counts) + tab view per status + message cards with approve/reject buttons
4. Add sidebar entry: `{ title: "Outreach Queue", href: "/webassist/outreach", icon: Send }` in Products group
5. Commit and verify build

#### Step 2: Grant Drafts filter in Content Hub
1. Edit `/home/web3relic/interfaces/web-next/src/app/content-hub/page.tsx`
2. Add "Grant Apps" quick-filter button that sets `content_type` to `['research','plan']`
3. Add badge count showing how many grant docs exist
4. Commit and verify build

#### Step 3: Live Roadmap augmentation
1. Edit `/home/web3relic/interfaces/web-next/src/app/roadmap/page.tsx`
2. Add `useApi` call to fetch `GET /content?content_type=roadmap`
3. Add "Project Roadmaps" section below static phases — grid of 18 project cards with expand-to-read body
4. Add type filter (by project/character field) if available
5. Commit and verify build

#### Step 4: Agent Activity feed
1. Add `GET /agents/activity` route to `/home/web3relic/otto/memory/routes/agents.py`
2. Register in API (check `api.py` for route inclusion)
3. Edit `/home/web3relic/interfaces/web-next/src/app/agents/page.tsx`
4. Add "Activity" tab with paginated event log
5. Commit and verify build

#### Step 5: Auto-surfacing policy
1. Update task runner `task_runner.sh`: after successful completion, log to `agent_activity_log` via `POST /agents/activity` (add this endpoint)
2. Update heartbeat agent prompt: ensure research task outputs are stored to `research_notes`, not just task output field
3. Add semantic memory auto-categorization for `grant` keyword → store with `category=project`
4. Commit

---

### Risks

- **Outreach queue 2273 rows**: Page must handle pagination gracefully. Recommend 50/page with server-side pagination. Risk of overwhelming Mev with 2273 items — mitigate with default filter to pending + sort by lead_score DESC.

- **Content Hub filter complexity**: Content Hub is already complex (350+ lines). Adding a filter button risks breaking existing filter logic. Mitigation: read the filter state management carefully before editing.

- **Roadmap static vs live conflict**: If the static phase data gets stale vs DB content, Mev will see inconsistency. Mitigate: add "Last updated" timestamp from DB items.

- **Build failures**: OMS is deployed on Vercel via ottomev/web-next. Each step must pass `npm run build` before committing. Budget: $3/session is tight — keep steps focused.

---

### Files to Modify

| File | Change |
|------|--------|
| `interfaces/web-next/src/app/webassist/outreach/page.tsx` | CREATE |
| `interfaces/web-next/src/lib/api-types.ts` | ADD OutreachMessage type |
| `interfaces/web-next/src/components/layout/app-sidebar.tsx` | ADD Outreach Queue nav item |
| `interfaces/web-next/src/app/content-hub/page.tsx` | ADD grant filter button |
| `interfaces/web-next/src/app/roadmap/page.tsx` | ADD live roadmap section |
| `interfaces/web-next/src/app/agents/page.tsx` | ADD activity tab |
| `otto/memory/routes/agents.py` | ADD GET /agents/activity endpoint |
| `otto/task_runner.sh` | ADD activity log on completion |
