---
name: Landing Page Workflow Architecture
description: Landing page generation workflow design — 5-step workflow template, landing_pages DB table, nginx serving at otto.505.systems, OMS UI. Phase 1 ~$4-5 implementation.
type: project
---

Landing page generation workflow designed (2026-04-06). Reuses existing workflow engine — no custom pipeline. 5 steps: Business Research (researcher) → Market/Competitors (researcher) → Design Synthesis (landing-page-creator, post human gate) → HTML Generation (landing-page-creator) → Deploy & Notify (coder). New landing_pages table (slug, business_name, research_data JSONB, competitor_data JSONB, design_decisions JSONB, html_path, preview_url, status machine, workflow_instance_id). Serve at otto.505.systems/landing-pages/{slug}/ via existing nginx config. OMS page at /landing-pages (list + generate dialog + detail with Research/Design/Preview tabs). Template JSON ready for API insert. $5-8 per generation, Phase 1 ~$4-5 implementation.

**Why:** WebAssist core product needs automated landing page generation. Mev requested full pipeline from business research through HTML generation.

**How to apply:** This is the reference design for implementing the landing page system. All decisions trace back to this doc at ~/otto/docs/landing-page-workflow-architecture-2026-04-06.md.
