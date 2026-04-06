# Landing Page Generation Workflow — Architecture

**Date:** 2026-04-06
**Author:** Architect Agent
**Status:** Design Complete — Ready for Implementation

---

## Design: Landing Page Generator

### Problem

WebAssist needs to generate high-quality landing pages for client businesses. Today this requires manual research, design decisions, and coding. The entire pipeline — from "I need a landing page for X" to a live, hosted page — should be automated as a multi-agent workflow that Otto can execute end-to-end, with a human review gate before publishing.

Mev's request: business research → market/competitor research → design synthesis → HTML generation, all orchestrated as a workflow with OMS visibility.

### Approach

**Reuse the existing workflow engine.** The workflow engine already handles step sequencing, variable interpolation (`{prev_output}`, `{step_N_output}`), artifact references, human gates, auto-eval, and cost tracking. A landing page workflow is just a new template — no engine changes needed.

**Add a thin `landing_pages` table** for product-level tracking. The workflow handles orchestration; the landing_pages table is the business entity — it holds the aggregated research, design decisions, and serves as the query target for the OMS dashboard and public-facing API.

**Serve generated HTML via nginx** at `otto.505.systems/landing-pages/{slug}/`. This route already exists in the nginx config and `/var/www/html/landing-pages/` already has 2 pages. No nginx changes needed.

---

### Key Decisions

1. **Workflow engine reuse vs. custom pipeline**: Reuse existing workflow engine. It has everything we need (step sequencing, variable flow, gates, eval, cost tracking). Building a custom pipeline would duplicate 80% of its functionality. *Alternative: Custom async job queue — rejected because it duplicates orchestration logic and fragments visibility.*

2. **Separate `landing_pages` table vs. workflow-only**: Separate table. Workflows are execution records; landing pages are product entities with their own lifecycle (draft → published → archived) and query patterns (list all pages, filter by status, search by business name). *Alternative: Query workflow instances directly — rejected because coupling product queries to workflow internals makes the API fragile.*

3. **Where to serve**: `otto.505.systems/landing-pages/{slug}/` via nginx static serving. Already configured, already has SSL, already has 2 pages. *Alternative: Vercel deployment under webassist.ink — adds complexity, requires Vercel API integration, and generated HTML is vanilla (not Next.js). Alternative: S3/GCS — external dependency we don't need.*

4. **Research agents**: Use the `researcher` agent type for Steps 0-1. It has web search tools and the b2b_landscape_research_pipeline procedure. *Alternative: Dedicated research-synthesizer — overkill for a quick business lookup; researcher already does web retrieval + synthesis.*

5. **HTML generation agent**: Use the existing `landing-page-creator` agent (`landing-page.md`). It has a comprehensive 5-phase methodology (sensory DNA, unconventional layout, conversion architecture, anti-slop, technical quality). *Alternative: Generic coder — would lose the specialized design intelligence.*

6. **Human gate placement**: Post-Step 2 (Design Synthesis). Mev reviews concept proposals and picks one before HTML generation begins. This prevents wasting $5+ on generating HTML from a rejected concept. *Alternative: Post-Step 3 (after HTML) — wastes budget if concept is wrong. Alternative: No gate — risks generating pages that miss the mark.*

7. **File writing approach**: The HTML generation step (Step 3) writes directly to `/var/www/html/landing-pages/{slug}/index.html`. The agent has filesystem access. Slug is derived from business name (kebab-case, max 60 chars). *Alternative: API writes file after step completes — adds indirection with no benefit since the agent already has write access.*

---

### Workflow Template: `landing-page-generator`

```
Step 0: Business Research        → researcher agent
Step 1: Market & Competitor Scan → researcher agent  
Step 2: Design Synthesis         → landing-page-creator agent  [POST-GATE: human]
Step 3: HTML Generation          → landing-page-creator agent
Step 4: Deploy & Notify          → coder agent (verify + update DB)
```

**Total estimated cost:** $5-8 per landing page

#### Step 0 — Business Research ($1, 900s)

Agent: `researcher`

Prompt template:
```
Research the business "{business_name}" to build a comprehensive profile for landing page creation.

Business URL: {business_url}
Description provided: {description}
Target audience: {target_audience}

Tasks:
1. Visit {business_url} (if provided) — extract: tagline, value proposition, products/services, 
   pricing (if visible), brand colors, tone of voice, existing imagery style
2. Search the web for "{business_name}" — find: social media presence, reviews, press mentions, 
   industry category, founding story, team size/notable people
3. Identify the business's core differentiator — what makes them different from competitors

Output as JSON:
{
  "business_name": "...",
  "industry": "...",
  "tagline": "...",
  "value_proposition": "...",
  "products_services": ["..."],
  "pricing_tier": "budget|mid|premium|luxury",
  "brand_colors": ["#hex", ...],
  "tone_of_voice": "...",
  "target_audience": "...",
  "differentiator": "...",
  "social_presence": {"platform": "url", ...},
  "notable_reviews_or_press": ["..."],
  "existing_site_assessment": "none|basic|decent|professional",
  "raw_notes": "..."
}
```

#### Step 1 — Market & Competitor Research ($1.50, 900s)

Agent: `researcher`

Prompt template:
```
Analyze the competitive landscape for {business_name} in the {step_0_output.industry} industry.

Business profile from previous research:
{prev_output}

Tasks:
1. Identify 3-5 direct competitors — find their websites, analyze their landing page approach
2. For each competitor note: visual style, messaging strategy, CTA approach, unique elements, weaknesses
3. Identify market trends in this industry's web presence — what's working, what's stale
4. Find positioning gaps — opportunities for {business_name} to stand out visually and messaging-wise

Output as JSON:
{
  "competitors": [
    {
      "name": "...",
      "url": "...",
      "visual_style": "...",
      "messaging_strategy": "...",
      "cta_approach": "...",
      "strengths": ["..."],
      "weaknesses": ["..."]
    }
  ],
  "market_trends": ["..."],
  "positioning_gaps": ["..."],
  "recommended_angles": ["..."],
  "visual_direction_notes": "...",
  "messaging_direction_notes": "..."
}
```

#### Step 2 — Design Synthesis ($2, 1200s) + Human Gate

Agent: `landing-page-creator`

Prompt template:
```
You are creating a landing page for {business_name}. You have research data — now synthesize it 
into 2-3 creative concepts.

BUSINESS RESEARCH:
{step_0_output}

MARKET & COMPETITOR ANALYSIS:
{step_1_output}

TARGET AUDIENCE: {target_audience}

Execute Phase 1 (Creative Intelligence) from your methodology:
- Sensory Translation: temperature, texture, movement, sound, emotion of this brand
- Experiential Design: what interactive browser experience captures this business's soul?
- Signature Moment: the ONE scroll-stopping element
- Concept Proposals: 2-3 distinct creative directions

For each concept provide:
1. Concept name
2. Sensory DNA (the 5 properties)
3. Signature interactive moment
4. 2-3 unique micro-experiences specific to THIS business
5. Font pairing + color palette (hex values) — remember: Inter, Roboto, Arial, Open Sans, 
   Lato, Montserrat, Poppins, Space Grotesk are BANNED
6. Section flow (which sections in what order)
7. Layout strategy (asymmetric, grid-breaking, spatial rhythm)
8. One-sentence description of how the page will FEEL

Also provide a CONVERSION BRIEF:
- Primary CTA text and placement strategy
- Key objections to address
- Social proof approach
- Recommended section count (6-10)

Output the concepts clearly numbered so the reviewer can say "Concept 2" to select one.
```

**Post-step gate config:**
```json
{
  "type": "human",
  "position": "post",
  "timeout_seconds": 172800,
  "timeout_action": "approve"
}
```

The gate pauses the workflow. Mev reviews concepts in the OMS workflow detail page and approves (optionally adding `context_snapshot.selected_concept = "2"` or feedback). If no response in 48h, auto-approves with Concept 1.

#### Step 3 — HTML Generation ($3, 1800s)

Agent: `landing-page-creator`

Prompt template:
```
Build the full landing page for {business_name}.

SELECTED CONCEPT AND DESIGN DIRECTION:
{prev_output}

BUSINESS RESEARCH:
{step_0_output}

COMPETITOR ANALYSIS:
{step_1_output}

IMPLEMENTATION REQUIREMENTS:
- Single self-contained HTML file with inline CSS and JavaScript
- Follow your Phase 2-5 methodology exactly (Layout, Conversion, Anti-Slop, Technical)
- Google Fonts via <link>, external CDN only from cdnjs.cloudflare.com
- Mobile-first responsive (375px / 768px / 1440px)
- Core Web Vitals optimized
- SEO meta tags (title, description, OG, Twitter Card)
- Accessibility (WCAG AA, skip-to-content, focus states, prefers-reduced-motion)
- IntersectionObserver for scroll animations
- The signature moment MUST be implemented

IMPORTANT: Write the complete HTML file to this exact path:
  /var/www/html/landing-pages/{slug}/index.html

Create the directory first:
  mkdir -p /var/www/html/landing-pages/{slug}

After writing, verify the file exists and output:
[ARTIFACT: /var/www/html/landing-pages/{slug}/index.html]

Also include a brief summary of what was built (sections, animations, fonts used, colors).
```

#### Step 4 — Deploy & Notify ($0.50, 300s)

Agent: `coder`

Prompt template:
```
Verify and finalize the landing page deployment for {business_name}.

Generated page path: /var/www/html/landing-pages/{slug}/index.html
Preview URL: https://otto.505.systems/landing-pages/{slug}/

Tasks:
1. Verify the HTML file exists and is valid (check file size > 1KB)
2. Curl the preview URL and confirm 200 response
3. Update the landing page record via API:
   curl -sf -X PATCH http://localhost:8100/landing-pages/{landing_page_id}/status \
     -H 'Content-Type: application/json' \
     -d '{{"status": "published", "preview_url": "https://otto.505.systems/landing-pages/{slug}/"}}'
4. Output the final URL for notification

If the file doesn't exist or URL returns non-200, report the error clearly.

Final output: The preview URL and a one-line summary.
```

Notify action follows (WhatsApp to Mev):
```
Landing page ready: {business_name}
Preview: https://otto.505.systems/landing-pages/{slug}/
```

---

### DB Schema

**Migration: `0XX_landing_pages.sql`** (next available migration number)

```sql
-- Landing page product entity — orchestrated by workflow, served by nginx
CREATE TABLE IF NOT EXISTS landing_pages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slug TEXT NOT NULL UNIQUE,
    business_name TEXT NOT NULL,
    business_url TEXT,
    description TEXT,
    target_audience TEXT,
    
    -- Aggregated research (populated by workflow callbacks)
    research_data JSONB DEFAULT '{}',
    competitor_data JSONB DEFAULT '{}',
    design_decisions JSONB DEFAULT '{}',
    
    -- Generated output
    html_path TEXT,                  -- /var/www/html/landing-pages/{slug}/index.html
    preview_url TEXT,                -- https://otto.505.systems/landing-pages/{slug}/
    
    -- Lifecycle
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending','researching','designing','generating','review','published','archived')),
    
    -- Workflow link
    workflow_instance_id UUID,       -- FK to workflow_instances
    
    -- Metadata
    created_by TEXT DEFAULT 'otto',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_landing_pages_status ON landing_pages(status);
CREATE INDEX IF NOT EXISTS idx_landing_pages_slug ON landing_pages(slug);
CREATE INDEX IF NOT EXISTS idx_landing_pages_workflow ON landing_pages(workflow_instance_id);

-- Trigger for updated_at
CREATE OR REPLACE FUNCTION update_landing_pages_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_landing_pages_updated_at
    BEFORE UPDATE ON landing_pages
    FOR EACH ROW
    EXECUTE FUNCTION update_landing_pages_updated_at();
```

**Status machine:**
```
pending → researching → designing → generating → review → published
                                                       ↘ archived
published → archived
```

- `pending`: Record created, workflow not started yet
- `researching`: Steps 0-1 running (business + market research)
- `designing`: Step 2 running (design synthesis)
- `generating`: Step 3 running (HTML generation)
- `review`: Step 3 complete, human gate active (concept or HTML review)
- `published`: HTML deployed, URL live
- `archived`: Soft-deleted / superseded

---

### API Surface

**Route file:** `~/otto/memory/routes/landing_pages.py`
**Prefix:** `/landing-pages`

#### POST `/landing-pages/generate`

Create a landing page and start the workflow.

**Request:**
```json
{
  "business_name": "Cafe Kinross",
  "business_url": "https://cafekinross.com",
  "description": "Artisan coffee shop in Kinross, Scotland. Specialty single-origin beans, house-baked pastries.",
  "target_audience": "Local professionals, students, coffee enthusiasts aged 25-45"
}
```

**Response (201):**
```json
{
  "id": "uuid",
  "slug": "cafe-kinross",
  "status": "pending",
  "workflow_instance_id": "uuid",
  "preview_url": null,
  "message": "Landing page generation started. Estimated completion: 15-25 minutes (excluding review gate)."
}
```

**Logic:**
1. Generate slug from business_name (kebab-case, dedup with `-2` suffix if exists)
2. INSERT into `landing_pages`
3. Start workflow instance: `POST /workflows/start` with template `landing-page-generator` and variables `{business_name, business_url, description, target_audience, slug, landing_page_id}`
4. UPDATE `landing_pages` with `workflow_instance_id`
5. Return response

#### GET `/landing-pages`

List all landing pages.

**Query params:** `?status=published&limit=20&offset=0`

**Response:**
```json
{
  "count": 5,
  "landing_pages": [
    {
      "id": "uuid",
      "slug": "cafe-kinross",
      "business_name": "Cafe Kinross",
      "status": "published",
      "preview_url": "https://otto.505.systems/landing-pages/cafe-kinross/",
      "created_at": "2026-04-06T10:00:00Z",
      "updated_at": "2026-04-06T10:25:00Z"
    }
  ]
}
```

#### GET `/landing-pages/{id}`

Full landing page detail including research data.

**Response:**
```json
{
  "id": "uuid",
  "slug": "cafe-kinross",
  "business_name": "Cafe Kinross",
  "business_url": "https://cafekinross.com",
  "description": "...",
  "target_audience": "...",
  "research_data": { /* Step 0 output */ },
  "competitor_data": { /* Step 1 output */ },
  "design_decisions": { /* Step 2 output */ },
  "html_path": "/var/www/html/landing-pages/cafe-kinross/index.html",
  "preview_url": "https://otto.505.systems/landing-pages/cafe-kinross/",
  "status": "published",
  "workflow_instance_id": "uuid",
  "created_by": "otto",
  "created_at": "...",
  "updated_at": "..."
}
```

#### GET `/landing-pages/{id}/status`

Lightweight status check (for polling).

**Response:**
```json
{
  "id": "uuid",
  "status": "generating",
  "current_step": 3,
  "total_steps": 5,
  "step_name": "HTML Generation",
  "elapsed_seconds": 120,
  "preview_url": null
}
```

**Logic:** Joins to `workflow_instances` to get `current_step` and step name from template.

#### PATCH `/landing-pages/{id}/status`

Update landing page status (called by Step 4 agent and admin actions).

**Request:**
```json
{
  "status": "published",
  "preview_url": "https://otto.505.systems/landing-pages/cafe-kinross/"
}
```

#### DELETE `/landing-pages/{id}`

Archive a landing page (soft delete — sets status to `archived`).

---

### Workflow-to-Landing-Page Sync

The workflow engine already calls back on step completion. We hook into this to keep the `landing_pages` table in sync:

**In `landing_pages.py`**, register a callback function:

```python
async def on_workflow_step_complete(instance_id: str, step_position: int, output: str):
    """Called by workflow engine when a step completes for a landing-page workflow."""
    pool = await get_pool()
    
    # Find the landing page linked to this workflow
    row = await pool.fetchrow(
        "SELECT id FROM landing_pages WHERE workflow_instance_id = $1",
        instance_id
    )
    if not row:
        return
    
    lp_id = row["id"]
    
    if step_position == 0:
        await pool.execute(
            "UPDATE landing_pages SET research_data = $1::jsonb, status = 'researching' WHERE id = $2",
            output, lp_id
        )
    elif step_position == 1:
        await pool.execute(
            "UPDATE landing_pages SET competitor_data = $1::jsonb, status = 'designing' WHERE id = $2",
            output, lp_id
        )
    elif step_position == 2:
        await pool.execute(
            "UPDATE landing_pages SET design_decisions = $1::jsonb, status = 'review' WHERE id = $2",
            output, lp_id
        )
    elif step_position == 3:
        slug = await pool.fetchval("SELECT slug FROM landing_pages WHERE id = $1", lp_id)
        await pool.execute(
            """UPDATE landing_pages SET 
                html_path = $1, status = 'generating' 
               WHERE id = $2""",
            f"/var/www/html/landing-pages/{slug}/index.html", lp_id
        )
```

**Integration point:** In `workflows.py → _advance_workflow()`, after storing step output, check if the workflow template is `landing-page-generator` and call the callback. This is the same pattern used by plan tasks (`on_plan_task_complete`).

Alternatively (simpler, preferred): **The Step 4 agent** does the final status update via the PATCH endpoint. The intermediate status transitions (`researching` → `designing` → `generating`) can be handled by a lightweight post-completion hook in the `/landing-pages/generate` endpoint's workflow start call, or by polling in the status endpoint (derive status from `workflow_instances.current_step`).

**Recommended approach:** Derive status from workflow state in the GET endpoints, don't try to keep it in sync. The `landing_pages.status` column is only explicitly set for terminal states (`published`, `archived`). For in-progress states, the GET endpoint queries `workflow_instances.current_step` and maps it:

```python
STEP_TO_STATUS = {
    0: "researching", 1: "researching",
    2: "designing", 3: "generating", 4: "generating"
}
```

This eliminates the sync problem entirely. Research/competitor/design data is populated from `workflow_instances.step_outputs` in the GET response — no need to copy it to the landing_pages table during execution. The JSONB columns on `landing_pages` serve as a cache populated once the workflow completes.

---

### File Storage

```
/var/www/html/landing-pages/
├── {slug}/
│   └── index.html          # Self-contained HTML (inline CSS/JS, Google Fonts CDN)
├── cafe-kinross/
│   └── index.html
└── otto-music.html          # Legacy (pre-workflow)
```

- **nginx route**: Already configured on `otto.505.systems` → `alias /var/www/html/landing-pages/`
- **Permissions**: The agent runs as `web3relic` which has write access to `/var/www/html/`
- **No subdomain per page**: All pages live under a single route. Clean, simple, no DNS management.
- **Max file size**: ~200KB typical for a well-optimized self-contained HTML page

**Serving URL:** `https://otto.505.systems/landing-pages/{slug}/`

For client delivery, these URLs work as-is. If a client later needs a custom domain, nginx can add a `server_name` block pointing to the same directory — but that's a separate, future concern.

---

### OMS Test Trigger UI

**Location:** New page at `mev.otto.lk/landing-pages`

**Components** (all shadcn/ui):

#### List View
```
┌─────────────────────────────────────────────────────────┐
│ Landing Pages                              [+ Generate] │
│─────────────────────────────────────────────────────────│
│ Filter: [All ▾] [Published ▾] [In Progress ▾]          │
│                                                         │
│ ┌─────────────────────────────────────────────────────┐ │
│ │ ☕ Cafe Kinross                          Published  │ │
│ │ otto.505.systems/landing-pages/cafe-kinross/        │ │
│ │ Created 2 hours ago                    [View] [···] │ │
│ └─────────────────────────────────────────────────────┘ │
│ ┌─────────────────────────────────────────────────────┐ │
│ │ 🔄 Giovanni's Restaurant              Generating    │ │
│ │ Step 3/5: HTML Generation (45s)                     │ │
│ │ Created 5 minutes ago                  [View] [···] │ │
│ └─────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

**shadcn components:** Card, Badge (status), Button, DropdownMenu (overflow actions: archive, regenerate), Select (filter), Dialog (generate form)

#### Generate Dialog
```
┌───────────────────────────────────────┐
│ Generate Landing Page                 │
│                                       │
│ Business Name *                       │
│ [________________________]            │
│                                       │
│ Website URL                           │
│ [________________________]            │
│                                       │
│ Description *                         │
│ [________________________]            │
│ [________________________]            │
│                                       │
│ Target Audience *                     │
│ [________________________]            │
│                                       │
│         [Cancel]  [Generate]          │
└───────────────────────────────────────┘
```

**shadcn components:** Dialog, Input, Textarea, Button, Label

#### Detail View

Accessed via `/landing-pages?id={uuid}` or clicking a card.

```
┌─────────────────────────────────────────────────────────┐
│ ← Back    Cafe Kinross                      [Published] │
│─────────────────────────────────────────────────────────│
│                                                         │
│ Tabs: [Overview] [Research] [Design] [Preview]          │
│                                                         │
│ ┌─ Overview ──────────────────────────────────────────┐ │
│ │ Business: Cafe Kinross                              │ │
│ │ URL: cafekinross.com                                │ │
│ │ Audience: Local professionals, 25-45                │ │
│ │ Status: Published                                   │ │
│ │ Preview: otto.505.systems/landing-pages/cafe-kin... │ │
│ │ Cost: $7.20                                         │ │
│ │ Generated: 2 hours ago                              │ │
│ └─────────────────────────────────────────────────────┘ │
│                                                         │
│ ┌─ Workflow Progress ─────────────────────────────────┐ │
│ │ ✓ Research → ✓ Competitors → ✓ Design → ✓ HTML → ✓ │ │
│ └─────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

**Research tab:** Renders `research_data` and `competitor_data` JSON as readable cards.
**Design tab:** Shows concept proposals from `design_decisions`.
**Preview tab:** Full-width iframe of the generated page (`<iframe src={preview_url}>`).

**shadcn components:** Tabs, Card, Badge, Button, Separator, ScrollArea

#### Workflow Integration

The existing OMS Workflow UI at `/workflows` already shows running instances. The landing page workflow will appear there automatically. The `/landing-pages` page is a product-focused view that links through to the workflow detail for step-level debugging.

---

### Implementation Plan

#### Phase 1 — Core ($4-5 estimated implementation cost)

1. **Migration** — Create `landing_pages` table (1 SQL file)
2. **Route module** — `landing_pages.py` with 5 endpoints (generate, list, get, get/status, patch/status, delete)
3. **Workflow template** — Insert `landing-page-generator` template via API (5 steps as specified above)
4. **Directory setup** — Ensure `/var/www/html/landing-pages/` exists with correct permissions
5. **OMS page** — `src/app/landing-pages/page.tsx` with list view + generate dialog + detail view
6. **Test** — Generate a landing page for one of the existing sample businesses (e.g., Cafe Kinross)

#### Phase 2 — Polish ($2-3)

7. **Regeneration** — "Regenerate" button that creates a new workflow for an existing landing page
8. **Custom domain support** — API to associate a custom domain, auto-generate nginx server block
9. **Template evolution** — Let the workflow auto-eval system evolve prompt quality over runs
10. **Batch generation** — Generate pages for multiple businesses from a CSV/list

#### Phase 3 — Client-Facing ($3-4)

11. **Public gallery** — `/review/{slug}` page where clients can preview and approve
12. **Revision workflow** — Client feedback → revision cycle (new workflow template)
13. **Integration with intake** — When a new lead submits via `/start`, auto-start landing page generation

---

### Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| HTML generation quality varies | Medium | High | The landing-page agent has strict design rules. Auto-eval after each run. Human gate catches bad output. Evolution improves prompts over time. |
| Research steps return thin data for obscure businesses | Medium | Medium | Fallback to description-only mode. Step 0 prompt instructs agent to work with what's available. |
| File permission issues on `/var/www/html/` | Low | Medium | Verify permissions in Phase 1 setup. Agent runs as web3relic which owns the directory. |
| Slug collision | Low | Low | Dedup with `-2` suffix. UNIQUE constraint catches edge cases. |
| Gate timeout auto-approves bad concept | Low | Medium | 48h timeout is generous. WhatsApp notification on gate creation. Default to Concept 1 (first is usually strongest). |
| Cost overrun on complex pages | Low | Medium | Budget caps per step ($1 + $1.50 + $2 + $3 + $0.50 = $8 max). Workflow-level cost tracking. |

---

### Cost Summary

| Component | Estimated Cost |
|-----------|---------------|
| Per landing page generation | $5-8 (5 agent steps) |
| Phase 1 implementation | $4-5 (migration + routes + template + OMS page) |
| Phase 2 polish | $2-3 |
| Phase 3 client-facing | $3-4 |

---

### Data Flow Diagram

```
Mev (OMS or WhatsApp)
  │
  ▼
POST /landing-pages/generate
  │ {business_name, business_url, description, target_audience}
  │
  ├── INSERT landing_pages (status: pending)
  ├── POST /workflows/start (template: landing-page-generator)
  │
  ▼
┌────────────────────────────────────────────────────────────┐
│ Workflow Engine                                             │
│                                                            │
│  Step 0: Business Research ──→ research_data JSON          │
│       │                                                    │
│  Step 1: Market/Competitors ──→ competitor_data JSON       │
│       │                                                    │
│  Step 2: Design Synthesis ──→ 2-3 concept proposals        │
│       │                                                    │
│  ┌─ HUMAN GATE ─┐                                         │
│  │ Mev reviews   │  ← OMS workflow detail page             │
│  │ picks concept │  ← WhatsApp notification                │
│  └───────────────┘                                         │
│       │                                                    │
│  Step 3: HTML Generation ──→ /var/www/html/landing-pages/  │
│       │                                  {slug}/index.html │
│  Step 4: Deploy & Notify ──→ verify + update DB + notify   │
│                                                            │
└────────────────────────────────────────────────────────────┘
  │
  ▼
https://otto.505.systems/landing-pages/{slug}/  ← nginx serves static HTML
```

---

### Appendix: Template JSON for API Insert

```json
{
  "name": "landing-page-generator",
  "description": "Research a business, analyze competitors, synthesize design concepts, generate a high-conversion landing page, and deploy it. Includes human review gate for concept selection.",
  "steps": [
    {
      "position": 0,
      "name": "Business Research",
      "agent_type": "researcher",
      "prompt_template": "Research the business \"{business_name}\" to build a comprehensive profile for landing page creation.\n\nBusiness URL: {business_url}\nDescription provided: {description}\nTarget audience: {target_audience}\n\nTasks:\n1. Visit {business_url} (if provided) — extract: tagline, value proposition, products/services, pricing (if visible), brand colors, tone of voice, existing imagery style\n2. Search the web for \"{business_name}\" — find: social media presence, reviews, press mentions, industry category, founding story, team size/notable people\n3. Identify the business's core differentiator\n\nOutput as JSON with keys: business_name, industry, tagline, value_proposition, products_services, pricing_tier, brand_colors, tone_of_voice, target_audience, differentiator, social_presence, notable_reviews_or_press, existing_site_assessment, raw_notes",
      "review_mode": "auto",
      "max_budget_usd": 1.0,
      "max_turns": 30,
      "timeout_seconds": 900,
      "on_failure": "retry_once"
    },
    {
      "position": 1,
      "name": "Market & Competitor Research",
      "agent_type": "researcher",
      "prompt_template": "Analyze the competitive landscape for {business_name}.\n\nBusiness profile from previous research:\n{prev_output}\n\nTasks:\n1. Identify 3-5 direct competitors — find their websites, analyze landing page approach\n2. For each competitor: visual style, messaging strategy, CTA approach, strengths, weaknesses\n3. Market trends in this industry's web presence\n4. Positioning gaps — opportunities for {business_name} to stand out\n\nOutput as JSON with keys: competitors (array of {name, url, visual_style, messaging_strategy, cta_approach, strengths, weaknesses}), market_trends, positioning_gaps, recommended_angles, visual_direction_notes, messaging_direction_notes",
      "review_mode": "auto",
      "max_budget_usd": 1.5,
      "max_turns": 30,
      "timeout_seconds": 900,
      "on_failure": "retry_once"
    },
    {
      "position": 2,
      "name": "Design Synthesis",
      "agent_type": "landing-page-creator",
      "prompt_template": "Create 2-3 creative concept proposals for a landing page for {business_name}.\n\nBUSINESS RESEARCH:\n{step_0_output}\n\nMARKET & COMPETITOR ANALYSIS:\n{step_1_output}\n\nTARGET AUDIENCE: {target_audience}\n\nExecute Phase 1 (Creative Intelligence) from your methodology:\n- Sensory Translation (temperature, texture, movement, sound, emotion)\n- Experiential Design (product metaphor, scroll narrative, living proof, micro-delights)\n- Signature Moment (ONE unforgettable element)\n\nFor each concept provide:\n1. Concept name\n2. Sensory DNA\n3. Signature interactive moment\n4. 2-3 unique micro-experiences\n5. Font pairing + color palette (hex) — BANNED: Inter, Roboto, Arial, Open Sans, Lato, Montserrat, Poppins, Space Grotesk\n6. Section flow\n7. Layout strategy\n8. One-sentence feel description\n\nAlso provide a CONVERSION BRIEF: primary CTA, key objections, social proof approach, section count.\n\nNumber concepts clearly (Concept 1, Concept 2, etc.) for selection.",
      "review_mode": "auto",
      "max_budget_usd": 2.0,
      "max_turns": 40,
      "timeout_seconds": 1200,
      "on_failure": "pause",
      "gate": {
        "type": "human",
        "position": "post",
        "timeout_seconds": 172800,
        "timeout_action": "approve"
      }
    },
    {
      "position": 3,
      "name": "HTML Generation",
      "agent_type": "landing-page-creator",
      "prompt_template": "Build the full landing page for {business_name}.\n\nSELECTED CONCEPT AND DESIGN DIRECTION:\n{prev_output}\n\nBUSINESS RESEARCH:\n{step_0_output}\n\nCOMPETITOR ANALYSIS:\n{step_1_output}\n\nIMPLEMENTATION REQUIREMENTS:\n- Single self-contained HTML file with inline CSS and JavaScript\n- Follow Phase 2-5 methodology (Layout, Conversion, Anti-Slop, Technical)\n- Google Fonts via <link>, external CDN only from cdnjs.cloudflare.com\n- Mobile-first responsive (375px / 768px / 1440px)\n- Core Web Vitals optimized\n- SEO meta tags (title, description, OG, Twitter Card)\n- Accessibility (WCAG AA, skip-to-content, focus states, prefers-reduced-motion)\n- IntersectionObserver for scroll animations\n- The signature moment MUST be implemented\n\nWrite the complete HTML file to: /var/www/html/landing-pages/{slug}/index.html\nCreate directory first: mkdir -p /var/www/html/landing-pages/{slug}\n\nAfter writing, verify the file exists and output:\n[ARTIFACT: /var/www/html/landing-pages/{slug}/index.html]\n\nInclude a brief summary: sections built, animations, fonts, colors, file size.",
      "review_mode": "auto",
      "max_budget_usd": 3.0,
      "max_turns": 60,
      "timeout_seconds": 1800,
      "on_failure": "pause"
    },
    {
      "position": 4,
      "name": "Deploy & Notify",
      "agent_type": "coder",
      "prompt_template": "Verify and finalize the landing page for {business_name}.\n\nGenerated page: /var/www/html/landing-pages/{slug}/index.html\nPreview URL: https://otto.505.systems/landing-pages/{slug}/\n\nTasks:\n1. Verify HTML file exists and size > 1KB\n2. Curl the preview URL, confirm 200 response\n3. Update status: curl -sf -X PATCH http://localhost:8100/landing-pages/{landing_page_id}/status -H 'Content-Type: application/json' -d '{\"status\": \"published\", \"preview_url\": \"https://otto.505.systems/landing-pages/{slug}/\"}'\n4. Output final URL\n\nIf file missing or URL non-200, report error.",
      "action": null,
      "notify_template": "Landing page ready: {business_name}\nPreview: https://otto.505.systems/landing-pages/{slug}/",
      "review_mode": "auto",
      "max_budget_usd": 0.5,
      "max_turns": 15,
      "timeout_seconds": 300,
      "on_failure": "pause"
    }
  ],
  "default_priority": 8,
  "default_working_dir": "/home/web3relic/otto",
  "tags": ["webassist", "landing-page", "generation"]
}
```
