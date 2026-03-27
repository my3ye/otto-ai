# Unified Content Calendar — Architecture

## Design: Unified Calendar Data Model + Queue Logic

### Problem

Mev has 225 content items but no way to know "what do I post today?" The content hub is overwhelming — 87 articles (0 scheduled), 74 social posts (68 scheduled), and no single view that combines them into a daily posting rhythm. Two separate systems exist (`content` table + `social_calendar_posts` table) with no unified scheduling.

Mev's request: "organize the content hub into one calendar view so I can start posting articles and posts everyday."

### Approach

Add a thin **calendar_slots** table that references existing `content` rows. Each slot = one publishing action on one platform on one date. One content item can have multiple slots (e.g., article published on Paragraph + tweet announcing it).

This is a scheduling layer, NOT a content duplication layer. The content body stays in `content`. The slot says "publish content X on platform Y on date Z at position N."

### Key Decisions

- **Separate slots table** vs extending content.scheduled_at: Slots table, because one article needs multiple platform actions (publish on Paragraph + announce on X + share on Farcaster). `scheduled_at` on content is one value. Alternative: multiple `scheduled_at` columns per platform — messy, doesn't scale.

- **Reference content table** vs standalone: Reference. The 225 items already exist with bodies, tags, project_ids. Duplicating would create drift. Alternative: copy content into slots — rejected, violates single source of truth.

- **Daily slot position** (integer sort_order) vs time-of-day scheduling: Position-based. Mev doesn't need "post at 09:17" granularity right now — he needs "this is item 1 today, this is item 2." Time-of-day can be added later via `slot_time` column. Alternative: full datetime — over-engineered for current need.

- **Queue priority** computed vs stored: Computed at query time from status + content readiness + topic spread rules. No stored priority column that goes stale. Alternative: stored priority — rejected, requires re-computation on every content status change.

- **Migration number**: 077 (follows 076_content_version_label.sql).

### Data Model

#### Migration 077: `calendar_slots` table

```sql
-- Migration 077: Unified content calendar slots
CREATE TABLE IF NOT EXISTS calendar_slots (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    content_id      UUID NOT NULL REFERENCES content(id) ON DELETE CASCADE,
    slot_date       DATE NOT NULL,
    slot_position   INTEGER NOT NULL DEFAULT 0,        -- ordering within the day (0 = first)
    platform        TEXT NOT NULL DEFAULT 'paragraph',  -- paragraph, x, telegram, farcaster, linkedin, discord
    action          TEXT NOT NULL DEFAULT 'publish',     -- publish, announce, share, thread
    status          TEXT NOT NULL DEFAULT 'queued',      -- queued, ready, posted, skipped
    posted_at       TIMESTAMPTZ,                        -- when actually posted
    posted_by       TEXT,                                -- 'mev', 'otto', 'broadcast'
    notes           TEXT,                                -- per-slot notes (e.g., "needs Mev review first")
    pinned          BOOLEAN NOT NULL DEFAULT FALSE,      -- pinned to "start here" queue
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),

    UNIQUE(content_id, slot_date, platform)             -- one slot per content per platform per day
);

-- Indexes for the primary access patterns
CREATE INDEX idx_calendar_slots_date ON calendar_slots(slot_date, slot_position);
CREATE INDEX idx_calendar_slots_status ON calendar_slots(status, slot_date);
CREATE INDEX idx_calendar_slots_content ON calendar_slots(content_id);
CREATE INDEX idx_calendar_slots_pinned ON calendar_slots(pinned) WHERE pinned = TRUE;
CREATE INDEX idx_calendar_slots_platform ON calendar_slots(platform, slot_date);

-- Updated_at trigger
CREATE TRIGGER trg_calendar_slots_updated
    BEFORE UPDATE ON calendar_slots
    FOR EACH ROW EXECUTE FUNCTION update_content_updated_at();
```

#### Status Flow

```
queued → ready → posted
  ↓        ↓
skipped  skipped
```

- **queued**: Slot exists on the calendar, content may still be draft
- **ready**: Content is ready AND slot is confirmed for posting
- **posted**: Published to the platform
- **skipped**: Deliberately skipped (moved, deprioritized, etc.)

#### Slot Statuses vs Content Statuses

| Content Status | Slot Status | Meaning |
|---|---|---|
| draft | queued | Scheduled but content needs finishing |
| ready | ready | Ready to post right now |
| published | posted | Already published (slot completed) |
| any | skipped | Slot was removed from schedule |

### Queue Prioritization Rules

The calendar API returns items in this priority order for any given day:

```
1. pinned = TRUE                    (start-here items, always first)
2. content.status = 'ready'         (ready to publish RIGHT NOW)
3. content.status = 'published'     (already done — confirmation)
4. content.status = 'draft'         (needs work before posting)

Within each tier: ORDER BY slot_position ASC
```

#### Daily Mix Rules (applied by the queue-builder, NOT enforced by schema)

When auto-generating a schedule, apply these heuristics:

1. **1 article + 1-2 social posts per day** (articles are heavy; social is lightweight)
2. **No same-project back-to-back days** — if Day N has a KOINK article, Day N+1 should be different
3. **Ready-to-publish first** — articles with status=ready get the earliest open slots
4. **Alternate content pillars** — group by `project_id`, distribute evenly across weeks
5. **Weekend = lighter** — social posts only on Sat/Sun, articles on weekdays
6. **Pinned "start here" queue** — the first 5 items are manually pinned and always shown at the top of the calendar

#### Topic Spread Algorithm (for queue-builder)

```python
def spread_topics(items, days):
    """Distribute items across days, no same project on consecutive days."""
    by_project = group_by(items, key=lambda i: i.project_id)
    schedule = defaultdict(list)
    last_project = {}  # day -> last project placed

    # Round-robin across projects
    project_queues = {p: deque(items) for p, items in by_project.items()}
    day_idx = 0

    while any(project_queues.values()):
        day = days[day_idx % len(days)]
        # Find next project that wasn't used yesterday
        yesterday_project = last_project.get(day_idx - 1)

        for project_id, queue in project_queues.items():
            if not queue:
                continue
            if project_id == yesterday_project and len(project_queues) > 1:
                continue

            item = queue.popleft()
            schedule[day].append(item)
            last_project[day_idx] = project_id
            break

        day_idx += 1

    return schedule
```

### "Start Here Today" Pinned Queue

The pinned queue is the answer to "I don't know where to start." It's a short list (5-10 items) of the most impactful, immediately-actionable items.

**Initial pinned items** (from audit data — 4 ready articles):

| Order | Content | Platform | Action |
|---|---|---|---|
| 1 | "Before the Protocol, the Proof" | Paragraph.xyz | Deploy |
| 2 | "The Line That Cannot Be Cut" | Paragraph.xyz | Deploy |
| 3 | "ONEON: The Sovereign Layer No One Owns" | Paragraph.xyz | Deploy |
| 4 | "The Answer Cannot Be Nobody" | Paragraph.xyz | Deploy |
| 5 | Today's social post (from existing schedule) | X/Twitter | Post |

**Pinned queue rules:**
- Max 10 pinned items at once
- Auto-unpin when status changes to `posted`
- Pinned items appear at top of every view (day, week, month)
- Only Mev or heartbeat can pin/unpin (not auto-generated)

### API / Interface

#### New Endpoints: `/content-calendar/*`

```
GET  /content-calendar/slots
     ?date_from=2026-03-27&date_to=2026-04-30
     ?platform=x,paragraph
     ?status=queued,ready
     Returns: slots joined with content summary (title, type, project_id, content_status, tags)

GET  /content-calendar/today
     Returns: today's slots + pinned queue, priority-ordered
     This is the "start here" endpoint

GET  /content-calendar/queue
     ?days=7
     Returns: next N days of scheduled slots, priority-ordered per day
     Includes empty-day markers so frontend shows gaps

POST /content-calendar/slots
     Body: { content_id, slot_date, platform, action, slot_position?, pinned?, notes? }
     Creates a slot. Auto-computes position if not provided.

PUT  /content-calendar/slots/{id}
     Body: partial update (slot_date, platform, status, slot_position, pinned, notes)
     Moves/reschedules a slot

DELETE /content-calendar/slots/{id}
     Removes a slot (doesn't touch content)

POST /content-calendar/slots/{id}/post
     Marks slot as posted (sets posted_at, posted_by, status='posted')

POST /content-calendar/generate
     Body: { date_from, date_to, strategy: "balanced" | "launch_blitz" }
     Auto-generates slots for unscheduled ready/draft content
     Uses topic spread + daily mix rules
     Returns preview (doesn't commit) unless ?commit=true

POST /content-calendar/slots/reorder
     Body: { slot_ids: [uuid, uuid, ...] }
     Reorders slots within a day by array position

GET  /content-calendar/stats
     Returns: coverage stats (days with slots, gaps, posts per project, etc.)
```

#### Response Shape: Slot + Content Join

```json
{
  "id": "uuid",
  "slot_date": "2026-03-28",
  "slot_position": 0,
  "platform": "paragraph",
  "action": "publish",
  "status": "ready",
  "pinned": true,
  "notes": null,
  "posted_at": null,
  "content": {
    "id": "uuid",
    "title": "Before the Protocol, the Proof",
    "content_type": "article",
    "project_id": "MY3YE",
    "status": "ready",
    "tags": ["my3ye", "ecosystem", "inception"],
    "body_preview": "first 200 chars...",
    "word_count": 725
  }
}
```

#### "Today" Endpoint Response

```json
{
  "date": "2026-03-28",
  "pinned": [
    { "slot": {...}, "content": {...} }
  ],
  "scheduled": [
    { "slot": {...}, "content": {...} }
  ],
  "stats": {
    "total_today": 3,
    "ready_now": 2,
    "needs_work": 1
  }
}
```

### Frontend Integration

The OMS calendar view at `/content-calendar` (new page, replaces the scattered social-calendar views):

#### Views

1. **Month view** — calendar grid showing dot indicators per day (colored by content type)
2. **Week view** — expanded daily columns with slot cards
3. **Today view** — "Start here" pinned queue + today's schedule
4. **List view** — all upcoming slots as a sortable table

#### shadcn/ui Components

- `Calendar` (already installed) — month navigation
- `Card` — slot cards in day/week view
- `Badge` — status indicators (queued/ready/posted)
- `Sheet` — slide-out for slot details/editing
- `Select` — platform picker, action picker
- `Command` — content search when adding new slots
- `DropdownMenu` — slot actions (post, skip, move, unpin)
- `Tabs` — view switcher (month/week/today/list)
- `ScrollArea` — scrollable day columns
- `Separator` — between pinned and regular items
- `Tooltip` — hover previews on calendar dots

#### Drag-and-Drop

Not in v1. Add in v2 with `@dnd-kit/core` if Mev requests it. For now, reorder via dropdown menu or the reorder API.

### Seed Data

The audit produced `mev_start_here_schedule.csv` with 74 entries already mapped to dates. The `generate` endpoint should import this as the initial seed:

```sql
-- Seed from audit schedule (run once)
INSERT INTO calendar_slots (content_id, slot_date, platform, action, status, pinned)
SELECT
    c.id,
    s.date::date,
    CASE
        WHEN s.platform LIKE '%Paragraph%' THEN 'paragraph'
        WHEN s.platform LIKE '%Twitter%' THEN 'x'
        WHEN s.platform LIKE '%Telegram%' THEN 'telegram'
        WHEN s.platform LIKE '%Farcaster%' THEN 'farcaster'
        ELSE 'x'
    END,
    CASE s.action
        WHEN 'DEPLOY_TO_PARAGRAPH' THEN 'publish'
        WHEN 'PUBLISH' THEN 'publish'
        WHEN 'POST' THEN 'publish'
        WHEN 'SCHEDULE_THEN_POST' THEN 'publish'
        ELSE 'publish'
    END,
    CASE
        WHEN c.status = 'ready' THEN 'ready'
        WHEN c.status = 'published' THEN 'posted'
        ELSE 'queued'
    END,
    FALSE
FROM audit_schedule s
JOIN content c ON c.id = s.content_id::uuid
WHERE c.archived = FALSE;

-- Pin the 4 ready articles
UPDATE calendar_slots SET pinned = TRUE
WHERE content_id IN (
    SELECT id FROM content
    WHERE status = 'ready' AND content_type = 'article' AND archived = FALSE
);
```

### Migration from Legacy social_calendar_posts

The 195 rows in `social_calendar_posts` are an older system. The unified calendar uses the `content` table as its single source. Migration plan:

1. Verify all social_calendar_posts have corresponding entries in `content` table (they should, since the audit confirmed 74 social_post entries there)
2. Do NOT migrate social_calendar_posts into calendar_slots — the content table entries with their `scheduled_at` values are the canonical source
3. The seed script imports from the content table directly
4. social_calendar_posts remains read-only for the old UI until OMS fully switches to the unified calendar

### Implementation Plan

1. **Migration 077** — create `calendar_slots` table + indexes (5 min)
2. **Seed script** — import 74 entries from `mev_start_here_schedule.csv` into slots, pin 4 ready articles (10 min)
3. **Backend: `/content-calendar/*` router** — CRUD + today + queue + generate + reorder endpoints (45 min, ~$3)
4. **Frontend: `/content-calendar` page** — Today view + Month view using shadcn Calendar + Cards (45 min, ~$3)
5. **Wire sidebar** — add Content Calendar to OMS nav under Content group (5 min)

**Phase 2 (later):**
- Auto-post integration with Broadcast system (when credentials available)
- Drag-and-drop slot reordering
- Auto-generate schedule for new content on create
- "Coverage gap" alerts (days with no slots)

### Frontend Component Architecture

#### File Layout

```
interfaces/web-next/src/
├── app/content-calendar/
│   └── page.tsx                    # Main page (state, data fetching, layout)
├── components/calendar/
│   ├── UnifiedCalendarView.tsx     # Month/week grid adapted for CalendarSlot[]
│   ├── DayDetailPanel.tsx          # Sheet: day's posting queue with actions
│   ├── ContentSlotPicker.tsx       # Dialog: search content → schedule to date
│   └── UnscheduledSidebar.tsx      # Collapsible panel: unscheduled content backlog
└── lib/
    └── api-types.ts                # Add CalendarSlot + CalendarDayResponse types
```

#### Component Tree

```
ContentCalendarPage
├── Header (title + [Month|Week|Today] tabs + [Today] button + filters)
│   ├── Tabs (view switcher)
│   ├── Select (platform filter)
│   └── Select (status filter)
├── UnifiedCalendarView (month or week grid)
│   ├── MonthGrid → DayCells with slot dot indicators
│   └── WeekGrid → DayColumns with slot cards
├── DayDetailPanel (Sheet, opens on day click)
│   ├── Day header (date + Add Slot button)
│   ├── Pinned section (Separator + pinned slots)
│   ├── Slot list (ordered by position)
│   │   └── SlotCard per item
│   │       ├── Content title (link to content hub)
│   │       ├── Badge × 3 (platform, action, status)
│   │       ├── Move up/down buttons
│   │       └── DropdownMenu (Mark Ready, Mark Posted, Skip, Unpin, Remove)
│   └── Empty state ("No posts scheduled")
├── ContentSlotPicker (Dialog, opens from Add Slot)
│   ├── Command (search existing content)
│   ├── Select (platform)
│   ├── Select (action)
│   └── Button (Schedule)
└── UnscheduledSidebar (collapsible right panel or drawer)
    ├── Count badge
    ├── Filter by content_type
    └── Scrollable list of unscheduled items (click to schedule)
```

#### TypeScript Types

```typescript
// Add to api-types.ts
interface CalendarSlot {
  id: string
  content_id: string
  slot_date: string          // YYYY-MM-DD
  slot_position: number
  platform: string
  action: string
  status: string             // queued | ready | posted | skipped
  posted_at: string | null
  posted_by: string | null
  notes: string | null
  pinned: boolean
  created_at: string
  updated_at: string
  content: CalendarSlotContent
}

interface CalendarSlotContent {
  id: string
  title: string
  content_type: string
  status: string
  project_id: string | null
  character: string | null
  tags: string[]
  body_preview: string       // First 200 chars
}

interface CalendarDayResponse {
  date: string
  pinned: CalendarSlot[]
  scheduled: CalendarSlot[]
  stats: { total: number; ready: number; posted: number; queued: number }
}

interface CalendarStatsResponse {
  dates: Record<string, { total: number; posted: number; ready: number; queued: number }>
  coverage: { days_with_slots: number; total_days: number; gap_days: string[] }
}
```

#### Platform + Status Visual System

```typescript
const PLATFORM_COLORS: Record<string, string> = {
  paragraph: "bg-violet-500/10 text-violet-400 border-violet-500/20",
  x:         "bg-sky-500/10 text-sky-400 border-sky-500/20",
  telegram:  "bg-cyan-500/10 text-cyan-400 border-cyan-500/20",
  farcaster: "bg-purple-500/10 text-purple-400 border-purple-500/20",
  linkedin:  "bg-blue-500/10 text-blue-400 border-blue-500/20",
  discord:   "bg-indigo-500/10 text-indigo-400 border-indigo-500/20",
}

const SLOT_STATUS_COLORS: Record<string, string> = {
  queued:  "bg-muted/60 text-muted-foreground",
  ready:   "bg-amber-500/10 text-amber-400",
  posted:  "bg-green-500/10 text-green-400",
  skipped: "bg-red-500/10 text-red-400/60",
}

const ACTION_LABELS: Record<string, string> = {
  publish:  "Publish",
  announce: "Announce",
  share:    "Share",
  thread:   "Thread",
  deploy:   "Deploy",
}
```

#### shadcn/ui Component Usage

| Component | Where | Purpose |
|---|---|---|
| Tabs | Page header | Month/Week/Today view switcher |
| Select | Filters | Platform + status filters |
| Sheet | DayDetailPanel | Slide-in day queue |
| Dialog | ContentSlotPicker | Add content to calendar |
| Command | ContentSlotPicker | Search content by title |
| Card | SlotCard | Individual slot in day detail |
| Badge | SlotCard | Platform, action, status indicators |
| Button | Everywhere | Actions, navigation |
| ScrollArea | Day detail, sidebar | Scrollable lists |
| Separator | Day detail | Between pinned and regular slots |
| DropdownMenu | SlotCard | Per-slot actions menu |
| Tooltip | Calendar dots | Hover preview on month view |
| Skeleton | Loading states | Calendar + day panel |

#### CalendarView Adaptation Strategy

The existing `CalendarView.tsx` is 330 lines, tightly coupled to `SocialPost` type. Two options:

**Option A (chosen): Create `UnifiedCalendarView.tsx`** — Copy the rendering logic, change the data type to `CalendarSlot[]`, add platform color badges on dots. The existing CalendarView stays untouched for backward compat.

**Option B (rejected): Make CalendarView generic** — Would require changing the social calendar pages too. Higher blast radius for no gain.

### Backend Files to Create/Modify

| File | Action | Details |
|---|---|---|
| `memory/routes/calendar_routes.py` | CREATE | All 8 endpoints, prefix `/calendar` |
| `memory/api.py` | MODIFY | Register `calendar_routes.router` |
| Migration 077 | APPLY | `docker exec memory-postgres-1 psql -U otto -d memory -f /path/to/077` |
| Seed script | RUN | `docker exec memory-postgres-1 psql -U otto -d memory -f /path/to/seed` |

### Frontend Files to Create/Modify

| File | Action | Details |
|---|---|---|
| `app/content-calendar/page.tsx` | CREATE | Main page (~300 lines) |
| `components/calendar/UnifiedCalendarView.tsx` | CREATE | Adapted from CalendarView (~350 lines) |
| `components/calendar/DayDetailPanel.tsx` | CREATE | Sheet with slot list (~200 lines) |
| `components/calendar/ContentSlotPicker.tsx` | CREATE | Dialog with content search (~150 lines) |
| `components/calendar/UnscheduledSidebar.tsx` | CREATE | Backlog panel (~100 lines) |
| `lib/api-types.ts` | MODIFY | Add CalendarSlot types |
| `components/layout/app-sidebar.tsx` | MODIFY | Add Content Calendar nav item |

### Risks

- **Content table metadata gaps**: Most `metadata` JSONB is `{}`. The `platform_target` and `pillar` fields from the CSV exist only in the CSV export, not in the DB. Mitigation: queue logic uses `project_id` and `tags` for topic spread, not metadata. The generate endpoint can infer platform from `content_type` (article → paragraph, social_post → x).

- **Stale slots**: If content is deleted, the CASCADE handles it. If content status regresses (ready → draft), slots stay in current status. Mitigation: The `/today` endpoint joins with content and shows the actual content.status alongside slot.status, so Mev sees the truth.

- **195 legacy social_calendar_posts**: These are NOT connected to the content table. If Mev uses the old social calendar UI, changes won't appear in the unified calendar. Mitigation: deprecate the old UI once unified calendar ships. Don't create a complex sync layer.

- **Budget**: Backend + frontend together ~$6. This is a P1 task (Mev explicitly requested it). Worth the spend.
