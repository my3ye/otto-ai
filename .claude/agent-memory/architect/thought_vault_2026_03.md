---
name: thought_vault_architecture_2026_03
description: Thought Vault architecture: dedicated storage for Mev voice/thought dumps, OMS UI, Otto synthesis layer
type: project
---

Thought Vault designed 2026-03-20. Full doc at ~/otto/docs/thought-vault-architecture-2026-03-20.md.

**Why:** Mev voice dumps and long WhatsApp messages were being processed by kernel and lost — no dedicated store, no synthesis, no OMS view.

**Architecture:**
- Migration 063: `thought_vault` + `thought_synthesis` tables. GIN indexes on `tags[]` and `themes[]`. UNIQUE on `source_message_id` for dedup.
- Route: `memory/routes/thought_vault.py` — CRUD + `/synthesize` endpoint (LLM groups recent entries, creates synthesis records, max 20 entries/run)
- WhatsApp hook: Phase 5 post-processor in `kernel/ric.py` — auto-captures `[Voice]` messages AND long text (>300 chars) from Mev
- OMS: `/thought-vault/page.tsx` with 3 tabs (Entries / Synthesis / Stats)
- Sidebar: "Thought Vault" in Content group (Lightbulb icon)

**Key decisions:**
- Separate tables from content system (thoughts are raw/private, not publishable)
- Synthesis on-demand (Otto calls `/thought-vault/synthesize` from heartbeat) not a daemon
- Cleaned content field optional — fill later if voice transcription is partial
- `source_message_id` UNIQUE constraint prevents duplicate auto-capture on kernel retries

**Implementation plan (4 steps, ~$11.50):**
1. DB migration 063 (~$2)
2. Backend route + register in api.py (~$3)
3. WhatsApp hook in ric.py (~$2)
4. OMS page + sidebar (~$4.50)

**How to apply:** When building Thought Vault steps 1-4, reference this doc for exact schema, endpoint names, and file locations.
