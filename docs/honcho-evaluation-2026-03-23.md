# Honcho Fit Evaluation: WebAssist & Otto Client-Facing Products
**Date:** 2026-03-23
**Task:** Evaluate Honcho by Plastic Labs for integration into Otto ecosystem

---

## 1. How Honcho Compares to Otto's Existing Memory Infrastructure

### What Otto Has Today

| Layer | System | Scope |
|---|---|---|
| Semantic memory | PostgreSQL + pgvector, `/semantic/remember` | **Otto-only** (Mev's facts, procedures, decisions) |
| Episodic memory | PostgreSQL, `/episodic/events` | **Otto-only** (Otto's own conversation events) |
| Knowledge graph | Neo4j + Graphiti | **Otto-only** (Mev relationship modeling) |
| Session state | Supabase (WebAssist) | Email-keyed wizard state, NO AI memory |
| S-MMU / L1 | Kernel context paging | **Otto-only** (slices of Otto's own memory) |
| oms_contacts | PostgreSQL | **Mev-facing only** — WebAssist prospect tracking |

**Critical gap**: Otto has zero per-user AI memory for *external users* (WebAssist visitors, future app users, Athena prospects). Every WebAssist user starts from scratch on every visit.

### What Honcho Offers

| Honcho Component | Maps to Otto | Gap Filled |
|---|---|---|
| Peer cards | Nothing equivalent for external users | ✅ YES — per-user persistent representation |
| Deriver (async worker) | Nothing equivalent | ✅ YES — ambient learning from interaction history |
| Dialectic API | Nothing equivalent | ✅ YES — natural language query of user knowledge |
| Working Representation | S-MMU (but Otto-only) | ✅ YES — user-specific context injection |
| Sessions + Messages | Supabase session_data | ⚠️ OVERLAP — Supabase already handles session persistence |
| PostgreSQL + pgvector | Otto's existing DB | ⚠️ OVERLAP — same infra, redundant if self-hosted |
| Workspace hierarchy | OMS project structure | ⚠️ PARTIAL — different abstraction |

### Honest Overlap Assessment

Honcho's storage and retrieval primitives **duplicate** what Otto already has. Where it provides genuine novel value is:
1. **The Deriver pattern** — async background extraction of user representations from raw conversation
2. **Peer-scoped working representations** — context injection *tuned to the specific user* rather than global context
3. **Dialectic API** — reasoning over what is known about a user to answer meta-questions ("what matters to Alice?")

Otto's S-MMU is architecturally similar to Honcho's context management, but S-MMU models **Otto's own knowledge** — not external user profiles. That's the core gap.

---

## 2. Concrete Integration Opportunities

### Priority 1: WebAssist AI Chat (Highest Value)

**Current state**: WebAssist has an Athena AI agent for prospect qualification. Every prospect conversation is stateless — Athena has zero memory of previous conversations with the same person.

**Problem Honcho solves**: A returning prospect who already told Athena their business type, budget, and timeline gets asked the same questions again. This kills conversion.

**What integration looks like**:
- Each WebAssist prospect gets a `peer_id` (keyed to email or session)
- Athena calls `get_context(peer_id, session_id)` before each LLM call
- Deriver runs after each session, updating peer card with: business type, budget signals, objections raised, stage in buying journey
- On return visit: Athena greets with "Welcome back — last time you mentioned you're building an e-commerce site for ~$3K. Ready to continue?"

**Impact**: Direct conversion improvement. Prospect feels remembered. Reduces qualification friction on repeat visits.

### Priority 2: WebAssist Wizard Personalization

**Current state**: The onboarding wizard is linear — same questions, same order, same copy for everyone.

**Problem Honcho solves**: A user who abandoned the wizard at step 3 returns and has to start over. A user who selected "e-commerce" still gets generic questions.

**What integration looks like**:
- Peer card built from wizard interaction (which steps completed, which skipped, what answers given)
- Wizard starting state pre-populated from peer card on return
- LLM-generated copy variants per user segment derived from peer representation
- "You mentioned wanting a portfolio site — here's what that typically costs"

**Impact**: Reduced abandonment on return visits. More relevant experience.

### Priority 3: Otto's Own Mev Modeling (Kernel Enhancement)

**Current state**: Otto models Mev through semantic memory + Graphiti, but there's no structured "Mev representation" that gets automatically built from conversation history.

**Problem Honcho solves**: The Deriver pattern could run after every WhatsApp conversation, extracting structured facts: Mev's communication style, recurring priorities, decision patterns, emotional state signals.

**What integration looks like**:
- Mev = one peer in Honcho workspace
- After each kernel interrupt processed, Deriver updates Mev peer card
- S-MMU loads Mev working representation as part of L1 context
- Dialectic query used when kernel needs to reason about Mev: "Given what I know about Mev's preferences, how should I frame this decision?"

**Impact**: Better context continuity for Mev. Reduced goldfish memory. More anticipatory responses.

### Priority 4: Future Multi-User Products

**Current state**: All planned Otto products (Otto Travel, Otto Music, SOS Systems) will need per-user personalization at scale.

**What integration looks like**:
- Honcho workspace per product
- Common peer modeling infrastructure shared across products
- User representations transfer across Otto ecosystem (aligned with Honcho's roadmap for identity portability)

---

## 3. Build vs. Integrate Tradeoff

### Option A: Full Self-Hosted Honcho
- Deploy Honcho Docker image alongside existing memory infra
- Same PostgreSQL can be reused (separate schema)
- Run Deriver as separate systemd service
- **Effort**: ~2 days
- **Cost**: Infrastructure only (~$0 incremental on existing VM)
- **Sovereignty**: Full — no external data flow
- **Risk**: Maintaining another service, upstream Honcho changes

### Option B: pip install honcho-ai (Managed SDK)
- Install `honcho-ai` Python SDK
- Point at app.honcho.dev managed service
- $100 free credits to start
- **Effort**: ~4 hours to first working call
- **Cost**: After free tier — unclear pricing, SaaS dependency
- **Sovereignty**: LOW — user interaction data flows to Plastic Labs servers
- **Risk**: Violates Otto's sovereignty principles for a system built around sovereign AI

### Option C: Implement the Deriver Pattern Natively (Recommended)
- Build lightweight peer modeling layer in Otto's existing Memory API
- New table: `peer_cards` (peer_id, facts JSONB, last_updated)
- New route: `POST /peers/{id}/derive` — async extraction from recent sessions
- New route: `GET /peers/{id}/context` — returns working representation
- Reuse existing pgvector for similarity search
- **Effort**: ~3-4 days (migration + routes + background worker)
- **Cost**: $0 incremental
- **Sovereignty**: Full
- **Honcho dependency**: Zero — inspired by, not dependent on

### Verdict

**Option B is ruled out** on sovereignty grounds. Otto's mission is sovereign AI infrastructure — shipping user data to a third-party SaaS contradicts that at the architectural level, regardless of how good Honcho's product is.

**Option A (self-hosted Honcho) vs Option C (native implementation)** is the real decision.

| Criterion | Option A (Self-hosted Honcho) | Option C (Native) |
|---|---|---|
| Time to value | 2 days | 3-4 days |
| Infrastructure overhead | Another service to monitor | Zero — extends existing API |
| Honcho API surface | Full (Dialectic, Dream, etc.) | Start minimal, expand as needed |
| Upgrade path | Pull Honcho updates | Build what's needed |
| Alignment with Otto | Conceptually aligned | Architecturally native |
| Data schema | Honcho's (workspace/peer/session) | Otto's conventions |

**Recommendation: Option C — native Deriver implementation, starting with WebAssist.**

Honcho's innovation is the *pattern*, not the infrastructure. Otto already has the stack (FastAPI, PostgreSQL, pgvector, async workers). The value is:
1. **Peer cards** — trivial to implement natively
2. **Deriver async extraction** — Otto has task_runner.sh, can run post-session derivation as a background task
3. **Working representation** — extend S-MMU to support external peer context injection

Shipping a dependency on Honcho's server (even self-hosted) adds maintenance overhead. Shipping the pattern natively compounds into Otto's existing infrastructure.

---

## 4. Implementation Plan

### Phase 1: WebAssist Athena Memory (2-3 days, ~$0)
1. Migration: `peer_cards` table (peer_id, source, facts JSONB, embedding vector, updated_at)
2. Route: `POST /peers/{id}/observe` — store a structured observation
3. Route: `GET /peers/{id}/context` — retrieve working representation (top-K similar facts + recent history)
4. WebAssist: on Athena session start, call `GET /peers/{email}/context`, prepend to system prompt
5. WebAssist: on Athena session end, call `POST /peers/{email}/observe` with session summary

### Phase 2: Deriver Worker (3-4 days)
1. Background task type: `peer_derive` — extracts structured facts from raw session messages
2. Triggered automatically after WebAssist session close
3. Uses Claude Haiku to extract: business type, budget range, timeline, pain points, objections
4. Stores structured facts to peer_cards
5. Builds cumulative peer representation across visits

### Phase 3: Mev Peer Modeling (1-2 days)
1. Create `mev` peer in system
2. After each kernel interrupt, queue a `peer_derive` for Mev
3. S-MMU loads Mev working representation alongside standard L1 slices
4. Kernel `ric.py` uses peer context when constructing Mev-facing responses

---

## 5. Use-Case Priority Ranking

| Priority | Use Case | Value | Effort | Start |
|---|---|---|---|---|
| 1 | WebAssist Athena memory (returning prospects) | 🔴 HIGH — direct conversion | LOW | Phase 1 |
| 2 | WebAssist wizard state recovery | 🟠 MEDIUM — abandonment reduction | LOW | Phase 1 |
| 3 | Mev peer modeling in kernel | 🟠 MEDIUM — better Mev continuity | MEDIUM | Phase 3 |
| 4 | Multi-product shared peer layer | 🟡 FUTURE — scales all products | HIGH | Phase 2+ |

---

## Summary

**Honcho's unique contribution to Otto**: The Deriver pattern + per-user peer modeling. Everything else overlaps with existing infrastructure.

**Recommendation**: Implement the Deriver pattern natively in Otto's Memory API, starting with WebAssist Athena. Do not integrate the Honcho SDK or self-hosted service — the pattern is the value, not the dependency.

**Time to first value**: 2-3 days for Phase 1 (Athena memory for returning WebAssist prospects).

**Estimated task budget**: $15-20 (migration + 2 routes + WebAssist frontend changes).

**Sovereignty**: Full — no external data flow, no third-party dependency.
