# Otto Improvement Roadmap — Prioritized with Implementation Plans

**Version:** 1.0
**Date:** 2026-03-28
**Status:** Active Roadmap
**Prioritized by:** Impact x Effort (highest ROI first)
**Sources:** System context benchmarks, competitive comparison vs 9 AI harnesses, STEM gap analysis, features/learnings doc, 119-failure taxonomy, operational logs

---

## Current Baselines (What We're Improving From)

| KPI | Current | Target | Gap |
|---|---|---|---|
| RL2F accuracy (50-cycle) | 40% | 70%+ | 30pp (partially idle-inflated) |
| Task failure rate (7d) | 11.7% | <5% | 6.7pp |
| QA approval rate (7d) | 83% | 95%+ | 12pp |
| Workflow completion rate | 91% | 95%+ | 4pp |
| Reasoning chain match rate | 28% full / 78% non-miss | 50%+ full | 22pp |
| WebAssist LCP | 4.85s | <2.5s | Fix applied, needs re-audit |
| WebAssist Accessibility | 54/100 | 90+ | 36 points |
| Observability | Logs only | Structured tracing | Full gap |
| A2A protocol | DB polling only | Real-time agent comms | Full gap |
| MCP server | 15 tools on :8100/mcp | Industry-standard discovery | Partial |
| Caller profiling | None | 5-8 dim structured | Full gap |

---

## Tier 1: Quick Wins (< $2 each, 1-2 cycles, immediate ROI)

### 1.1 RL2F Idle-Cycle Tagging

**Priority:** P1 | **Effort:** ~$1 | **Impact:** Medium | **ROI:** Highest (removes metric inflation)

**Problem:** RL2F accuracy at 40% is partially inflated by idle periods where predictions are trivially correct ("queue stays empty"). MARS flagged this. We cannot trust the accuracy number or measure real improvement without separating idle vs active cycles.

**Solution:** Add `idle_cycle` boolean to RL2F feedback entries. Tag predictions made when 0 tasks were running and 0 were launched as idle. Report `accuracy_active` and `accuracy_idle` separately. Only target 70% on `accuracy_active`.

**Success Criteria:**
- RL2F feedback entries include `idle_cycle` boolean
- `/rl2f/accuracy` endpoint returns `accuracy_all`, `accuracy_active`, `accuracy_idle`
- Heartbeat logs active vs idle accuracy separately
- Active-workload accuracy becomes the primary metric

**Implementation Steps:**
1. Add `idle_cycle BOOLEAN DEFAULT FALSE` to `rl2f_feedback` table (ALTER TABLE, no migration needed)
2. In heartbeat.md RL2F scoring step: set `idle_cycle=true` when 0 tasks reviewed + 0 tasks created + 0 tasks launched
3. In `routes/rl2f.py`: modify accuracy calculation to return all three metrics
4. Update reflection.md MARS section to reference `accuracy_active` instead of raw accuracy
5. Update working memory slot `rl2f_accuracy` to show active rate

**Files Changed:** `routes/rl2f.py`, `agents/heartbeat.md`, `agents/reflection.md`

---

### 1.2 Directive Auto-Extraction

**Priority:** P2 | **Effort:** ~$1.50 | **Impact:** High | **ROI:** Very High (fixes recurring gap)

**Problem:** When Mev gives directives via WhatsApp, the kernel responds but does NOT auto-extract the directive into semantic memory or working memory. This caused 26 stagnation flags and is the root cause of the "goldfish memory" pattern for directives. Currently requires manual extraction.

**Solution:** Add a lightweight post-hook in RIC's post-process pipeline that classifies outgoing responses for directive content, and auto-stores detected directives to semantic memory with category `directive`.

**Success Criteria:**
- New directives from Mev auto-stored within 1 RIC cycle
- No manual extraction needed
- Working memory `active_mission` updated when directive detected
- Zero false positives on non-directive messages (tuned threshold)

**Implementation Steps:**
1. In `kernel/ric.py` post-process pipeline (after `_persist_response`): add `_extract_directive` hook
2. The hook sends a 1-shot LLM call (Gemini, cheapest): "Is this a directive from Admin? If yes, extract the core instruction. If no, return null."
3. On positive extraction: `POST /semantic/remember` with `category=directive`, `confidence=0.90`
4. On positive extraction: `PUT /working/memory/active_mission` to append
5. Rate-limit: max 1 extraction per 5 minutes to prevent spam

**Files Changed:** `kernel/ric.py` (~20 lines in post-process chain)

---

### 1.3 HiClaw GAP-3 — Plan-Classifier Check in Heartbeat

**Priority:** P3 | **Effort:** ~$1 | **Impact:** Medium | **ROI:** High (prevents bypassed orchestration)

**Problem:** Heartbeat sometimes creates tasks directly for multi-step work, bypassing the plan system entirely. This means dependency injection and output flow between tasks doesn't happen, reducing quality of multi-step work.

**Solution:** Add a plan-classifier check to heartbeat.md at the task creation step. Before creating any task, check if the instruction warrants a plan (multi-step, multiple agents needed). If yes, create a plan instead of a single task.

**Success Criteria:**
- Heartbeat multi-step work always routes through plan system
- Single-step work still creates single tasks (no overhead)
- Plan creation rate from heartbeat increases from ~0% to expected ~20% of task creations

**Implementation Steps:**
1. In `agents/heartbeat.md` Step 5 (task creation): add check: "Does this require multiple agents or sequential steps? If yes, use POST /task-plans instead of POST /tasks"
2. Add example plan creation to heartbeat.md showing the API call format
3. Verify by checking next 5 heartbeat cycles for plan vs task routing

**Files Changed:** `agents/heartbeat.md` (~10 lines added to Step 5)

---

### 1.4 S-MMU Near-Miss Threshold

**Priority:** P4 | **Effort:** ~$1 | **Impact:** Medium | **ROI:** Good (reduces context noise)

**Problem:** S-MMU injects all L2 slices above any similarity threshold into context. Near-miss slices (similarity 0.50-0.69) add noise without adding value, consuming limited L1 token budget and potentially causing position-bias degradation.

**Solution:** Apply `similarity_threshold=0.70` floor to L2 slice injection. Slices below 0.70 cosine similarity are not promoted to L1.

**Success Criteria:**
- L2→L1 slice injection filtered at 0.70 threshold
- Average L1 token utilization decreases by ~10-15%
- No regression in kernel response quality (measured via RL2F over 10 cycles)

**Implementation Steps:**
1. In `kernel/smmu.py` `_promote_l2_to_l1()`: add `if slice.similarity < 0.70: continue`
2. Log filtered slices count to metrics for monitoring
3. Run 10-cycle A/B via AutoEvolve to validate no quality regression

**Files Changed:** `kernel/smmu.py` (~3 lines)

---

## Tier 2: High-Impact Improvements ($3-5 each, 1-2 weeks)

### 2.1 Caller Profiler for Mev

**Priority:** P5 | **Effort:** ~$4 | **Impact:** High | **ROI:** High (novel capability, reduces clarification loops)

**Problem:** Zero structured user profiling. Otto doesn't track Mev's preferred response length, time-of-day activity patterns, task category preferences, communication register, or approval patterns by task type. This causes unnecessary clarification loops and imprecise task scoping. STEM gap analysis confirmed this as the highest-novelty gap.

**Solution:** Build a lightweight Caller Profiler that tracks 6 behavioral dimensions for Mev, updates on every WhatsApp interaction and task review, and injects a summary into heartbeat context.

**Success Criteria:**
- 6 dimensions tracked: (1) preferred_response_length, (2) active_hours, (3) task_categories_requested, (4) agent_types_preferred, (5) communication_register (terse/detailed), (6) approval_rate_by_category
- Profile auto-updates on every interaction
- Profile injected into heartbeat context briefing
- Measurable reduction in Mev clarification loops (track via pending questions rate)

**Implementation Steps:**
1. Create `routes/profiler.py` with 3 endpoints: `GET /profiler/mev`, `POST /profiler/update`, `GET /profiler/summary`
2. Schema: JSON stored in `semantic_memories` with `category=caller_profile` (no new table needed)
3. In `kernel/ric.py` post-process: after responding to Mev, extract response_length, time_of_day, detected_register → POST /profiler/update
4. In `routes/tasks.py` review endpoint: extract task_category, agent_type, approval → POST /profiler/update
5. In `routes/context.py` briefing assembly: include profiler summary in context injection
6. Bootstrap: seed initial profile from last 50 interactions retroactively

**Files Changed:** New `routes/profiler.py` (~120 lines), `kernel/ric.py` (~10 lines), `routes/context.py` (~5 lines)

---

### 2.2 VISTA Structured Failure Categorization

**Priority:** P6 | **Effort:** ~$3 | **Impact:** High | **ROI:** High (reduces 11.7% failure rate)

**Problem:** Task failure rate is 11.7% (7d), with failures categorized only by free-text output. Smart retry exists but retry prompts don't include typed failure information. From the 119-failure taxonomy: zombie (high), rate-limit (high), process-died (medium), budget-exhaustion (medium), QA-false-reject (low). Without typed categories, retries can't apply category-specific corrections.

**Solution:** Categorize failures into 5 typed buckets at task completion. Inject failure type + category-specific correction hypothesis into retry prompt.

**Success Criteria:**
- All failed tasks tagged with one of: `zombie`, `rate_limit`, `budget_exhaustion`, `process_died`, `qa_rejection`, `unknown`
- Retry prompts include typed failure context + correction strategy
- 7-day failure rate drops from 11.7% to <8% within 2 weeks
- New `failure_type` column on tasks table

**Implementation Steps:**
1. Add `failure_type VARCHAR(50)` column to `tasks` table (ALTER TABLE)
2. In `task_runner.sh` trap EXIT handler: classify exit code + output pattern → failure_type
   - Exit 124 → `timeout`; Exit 141 → `sigpipe`; "rate limit" in output → `rate_limit`; "budget" → `budget_exhaustion`; no PID → `zombie`; QA reject → `qa_rejection`; else → `unknown`
3. In `routes/tasks.py` retry endpoint: inject failure_type + correction map:
   - `budget_exhaustion` → "Previous attempt ran out of budget. Be more focused, skip exploratory work."
   - `rate_limit` → "Previous attempt hit API rate limit. Batch API calls, add delays."
   - `zombie` → "Previous attempt had no live process. Ensure task_runner.sh trap EXIT is working."
   - `qa_rejection` → "Previous attempt was rejected by QA: {qa_feedback}. Address specific feedback."
4. In reflection.md: add failure-type distribution monitoring (weekly)

**Files Changed:** `task_runner.sh` (~15 lines), `routes/tasks.py` (~20 lines), `agents/reflection.md` (~5 lines)

---

### 2.3 DGM-H Reflection Unfreeze (Self-Rewriting Reflection)

**Priority:** P7 | **Effort:** ~$5 | **Impact:** Very High | **ROI:** High (removes hard ceiling on self-improvement)

**Problem:** `reflection.md` is a static file. AutoEvolve can mutate heartbeat.md and other prompts, but reflection.md itself — the agent responsible for proposing improvements — cannot evolve. This creates a hard ceiling: the reflection agent can only propose changes it was written to propose. HyperAgents paper (arXiv 2603.19461) shows 20pp improvement when reflection can self-modify (DGM-H pattern).

**Solution:** Allow AutoEvolve to target `reflection.md` as an experiment subject. Reflection proposes a diff to its own prompt, heartbeat applies it to a staging copy, runs N evaluation cycles, keeps if RL2F improves.

**Success Criteria:**
- AutoEvolve can create experiments targeting `agents/reflection.md`
- Staging copy at `agents/reflection.staging.md` used during experiment
- After N=10 cycles: if `accuracy_active` improved → KEEP (replace reflection.md); else → DISCARD
- Constitutional guardrail: MARS adversarial check, CONSTITUTION.md, and personality.md are NEVER modifiable
- First successful self-modification within 20 cycles of deployment

**Implementation Steps:**
1. In `routes/autoevolve.py`: extend `valid_targets` to include `agents/reflection.md`
2. Add staging mechanism: when experiment targets reflection.md, copy to `reflection.staging.md`
3. In `reflection.sh`: if `reflection.staging.md` exists AND active experiment targets it → use staging copy
4. Add constitutional lock: AutoEvolve MUST NOT modify CONSTITUTION.md, personality.md, or any file in `otto_core/`
5. In `agents/reflection.md`: add step "If RL2F active accuracy < target AND no active experiment: propose a self-improvement hypothesis for reflection.md via AutoEvolve"
6. Guardrails:
   - 48h veto window before any self-modification is committed (existing from EMRS design)
   - MARS adversarial check on proposed diff before apply
   - Max 1 active reflection experiment at a time
   - Auto-rollback if any metric degrades >5pp during experiment

**Files Changed:** `routes/autoevolve.py` (~30 lines), `reflection.sh` (~10 lines), `agents/reflection.md` (~15 lines)

---

### 2.4 Skills Auto-Maturation (Pattern Crystallization)

**Priority:** P8 | **Effort:** ~$3 | **Impact:** High | **ROI:** Good (compounds capability automatically)

**Problem:** When Mev asks for the same type of task 5+ times, each one is dispatched independently. No detection of recurring patterns that should become reusable workflow templates. Otto's capability library only grows through manual template authoring, not through usage patterns. STEM identifies this as the highest compound-leverage gap.

**Solution:** Add pattern detection to reflection agent that queries completed tasks for recurring `agent_type + prompt_structure` combos (3+ occurrences). When detected, propose workflow template crystallization.

**Success Criteria:**
- Reflection detects recurring task patterns (3+ similar tasks)
- Proposes new workflow template via `/workflows/propose`
- Template proposal flagged for Mev approval before activation
- At least 1 auto-proposed template within first month

**Implementation Steps:**
1. Create `POST /workflows/propose` endpoint that creates a template in `draft` status
2. In `agents/reflection.md` (step 3d — task plan monitoring): add pattern detection query:
   - "SELECT agent_type, COUNT(*) FROM tasks WHERE status='completed' AND created_at > now()-interval '14 days' GROUP BY agent_type HAVING COUNT(*) >= 3"
   - For each pattern: extract common prompt structure → propose template
3. In OMS: surface draft templates in `/workflows` page with "Approve" button
4. On approval: activate template, make it available for dispatch

**Files Changed:** New logic in `routes/workflows.py` (~40 lines), `agents/reflection.md` (~10 lines)

---

## Tier 3: Strategic Improvements ($5-10+ each, 2-4 weeks)

### 3.1 OpenTelemetry Observability Pipeline

**Priority:** P9 | **Effort:** ~$8 | **Impact:** Very High | **ROI:** Medium (infrastructure investment)

**Problem:** Otto's biggest competitive gap. Every Tier-1 framework (LangGraph, Pydantic AI, Strands, Google ADK, Mastra) ships native OpenTelemetry. Otto has rich observability *data* (reasoning chains, MARS scores, metrics) but no standardized trace/span pipeline. Debugging multi-agent workflows at scale requires grepping log files. As plan complexity increases, this becomes a reliability liability.

**Solution:** Add OpenTelemetry instrumentation to task execution and workflow engine. Use Jaeger (Docker) as trace backend. Expose traces in OMS.

**Success Criteria:**
- Every task execution generates a trace with spans for: preflight, CLI execution, QA review, completion
- Every workflow instance generates a parent trace with child spans per step
- Traces queryable via Jaeger UI (:16686)
- OMS `/observability` page links to relevant traces per task/workflow
- Mean time to debug a cross-agent failure drops from ~30min to <5min

**Implementation Steps:**
1. Add `opentelemetry-api`, `opentelemetry-sdk`, `opentelemetry-exporter-otlp` to Memory API requirements
2. Add Jaeger to `~/memory/docker-compose.yml` (all-in-one image, :16686 UI, :4317 OTLP)
3. Create `memory/telemetry.py`: tracer provider, span creation helpers, context propagation
4. Instrument `routes/tasks.py`: span per task lifecycle event (created, running, completed, failed)
5. Instrument `routes/workflows.py`: parent span per instance, child span per step
6. Instrument `kernel/ric.py`: span per interrupt processing cycle
7. Pass trace context through task_runner.sh via environment variable (`OTEL_TRACE_ID`)
8. Add `/observability` route to OMS with trace links per task

**Files Changed:** New `memory/telemetry.py` (~80 lines), `routes/tasks.py` (~30 lines), `routes/workflows.py` (~20 lines), `kernel/ric.py` (~15 lines), `docker-compose.yml` (~10 lines), `task_runner.sh` (~5 lines)

---

### 3.2 A2A Protocol Upgrade (Agent Card + Handshake)

**Priority:** P10 | **Effort:** ~$6 | **Impact:** Very High | **ROI:** Medium (enables next-gen coordination)

**Problem:** Otto's A2A is PostgreSQL mailbox with HTTP polling (`routes/a2a.py`). Agents can't discover each other's capabilities, negotiate protocols, or coordinate in real-time. Google ADK ships native A2A as the industry standard for 2026. Otto's plan DAGs handle sequential coordination, but real-time multi-agent collaboration (e.g., architect + coder reviewing each other's work mid-task) is impossible.

**Solution:** Implement Agent Card discovery endpoint + handshake protocol. Each active agent advertises capabilities via a structured card. Agents can discover peers, request collaboration, and exchange structured messages with typed schemas.

**Success Criteria:**
- Each agent type has an Agent Card (capabilities, input/output schemas)
- `GET /a2a/cards` returns all active agent cards
- `POST /a2a/handshake` initiates a typed collaboration session
- At least one plan type uses real-time A2A (e.g., architect↔coder review loop)
- Message latency < 2s for channel-scoped communication

**Implementation Steps:**
1. Define Agent Card schema: `{agent_type, capabilities: [], input_schema, output_schema, status}`
2. Auto-generate cards from agent Markdown files (parse ## sections for capabilities)
3. Add `GET /a2a/cards` and `GET /a2a/cards/{agent_type}` endpoints
4. Add `POST /a2a/handshake` that creates a scoped channel + notifies target agent
5. Add WebSocket upgrade path for real-time messaging (optional, can start with polling)
6. Modify `task_runner.sh` to inject A2A channel info into agent context when part of a plan
7. Create example: architect + reviewer agents collaborating on a feature design

**Files Changed:** `routes/a2a.py` (~80 lines), `task_runner.sh` (~10 lines), new Agent Card schema

---

### 3.3 MCP Server Hardening (Industry-Standard Discovery)

**Priority:** P11 | **Effort:** ~$5 | **Impact:** High | **ROI:** Medium (external interop)

**Problem:** Otto has an MCP server (`mcp_server.py` with 15 tools, 4 resources, 3 prompts on :8100/mcp`) but it's internal-only. No external discovery, no versioning, no auth beyond bearer token. In 2026, MCP is the industry standard for tool interop — LangGraph, ADK, Strands, Mastra all ship native MCP clients. Otto's MCP needs to be externally discoverable for others to build on Otto's infrastructure.

**Solution:** Harden MCP server with versioned tool schemas, health endpoint, rate limiting, and external discovery endpoint. This positions Otto as infrastructure others can build on.

**Success Criteria:**
- MCP server exposes `/.well-known/mcp` discovery document
- All 15 tools have versioned schemas with input/output types
- Rate limiting: 100 req/min per client
- Auth: Bearer token + optional API key per client
- At least one external MCP client successfully connects

**Implementation Steps:**
1. Add `/.well-known/mcp` route returning server capabilities, tool list, version
2. Add rate limiting middleware to MCP routes (100 req/min, Redis or in-memory)
3. Add API key table: `mcp_api_keys` (key, client_name, rate_limit, created_at)
4. Version tool schemas: each tool gets a `version` field, breaking changes bump version
5. Add health probe: `GET /mcp/health` returns tool availability status
6. Document: create MCP integration guide for external developers

**Files Changed:** `memory/mcp_server.py` (~50 lines), `memory/mcp_auth.py` (~20 lines), new `routes/mcp_keys.py` (~40 lines)

---

### 3.4 Multi-LLM Provider Expansion

**Priority:** P12 | **Effort:** ~$4 | **Impact:** Medium | **ROI:** Medium (resilience + cost optimization)

**Problem:** Otto is Claude-primary with 3 provider types. Single-provider dependency is a resilience risk. OpenAI SDK supports 100+ LLMs; Pydantic AI supports 25+. When Claude rate-limits, Otto's only fallback is Gemini (for QA) and Kimi (for kernel). No ability to route tasks to cheaper models for simple work or use local models for privacy-sensitive operations.

**Solution:** Extend `provider.py` to support Ollama (local models) and Bedrock (AWS multi-model). Add model routing logic: simple tasks → cheaper model; complex tasks → Claude; privacy-sensitive → local Ollama.

**Success Criteria:**
- Provider registry supports 5+ model backends
- Task creation accepts optional `model_preference` hint
- Simple tasks (content review, formatting) route to cheaper models when available
- Fallback chain: Claude → Gemini → Ollama for resilience
- Cost reduction: 15-20% on simple task categories

**Implementation Steps:**
1. In `kernel/provider.py`: add `OllamaProvider` class (HTTP to localhost:11434)
2. In `kernel/provider.py`: add `BedrockProvider` class (boto3 bedrock-runtime)
3. Create model routing config in `config.py`: task_category → preferred_model mapping
4. In `routes/tasks.py` task creation: respect `model_preference` field
5. Install Ollama on VM, pull llama3-8b or equivalent for simple tasks
6. Add fallback chain logic: if primary fails with 429/500 → try next in chain

**Files Changed:** `kernel/provider.py` (~100 lines), `config.py` (~15 lines), `routes/tasks.py` (~10 lines)

---

## Tier 4: Long-Term Strategic (1-3 months, > $10)

### 4.1 AOP Governance Layer

**Priority:** P13 | **Effort:** ~$12 | **Impact:** High when multi-tenant

**Problem:** No per-agent policy enforcement, capability restriction, or audit trails. All 21 agents have the same permissions. As Otto serves multiple users (WebAssist customers) or onboards community operators, agent governance becomes critical.

**Solution:** Implement CrewAI-style Agent Operations Platform: role-based capability matrix, per-agent policy enforcement, audit trail per action, policy violations surface in OMS.

**Trigger:** Implement when multi-tenant support begins (tied to WebAssist agent serving).

---

### 4.2 Deriver Pattern (Honcho-Style Async Profiler)

**Priority:** P14 | **Effort:** ~$8 | **Impact:** High

**Problem:** Caller Profiler (2.1) tracks surface-level behavioral dimensions. Honcho's Deriver pattern goes deeper: async background processor builds working representations from full interaction history. Store→Reason→Retrieve with entity-specific representations, not global context injection.

**Solution:** After Caller Profiler proves value, evolve into Deriver: background process that builds a rich Mev-representation from all interactions, tasks, and outcomes.

**Trigger:** After Caller Profiler (2.1) is live and has 30+ days of data.

---

### 4.3 AgentOS Multi-Tenant Kernel

**Priority:** P15 | **Effort:** ~$20+ | **Impact:** Very High (revenue enabler)

**Problem:** Single-VM, single-operator architecture. Cannot serve multiple users simultaneously. Required for WebAssist to offer AI-powered website management to customers, and for any multi-user product.

**Solution:** Extend kernel to support user contexts (one S-MMU L1 per user), tenant isolation in PostgreSQL (row-level security), and per-tenant resource limits.

**Trigger:** When WebAssist has paying customers who need AI features.

---

## Implementation Schedule

### Phase 1: Quick Wins (This Week)
| Day | Item | Cost | Who |
|---|---|---|---|
| 1 | 1.1 RL2F idle tagging | ~$1 | coder |
| 1 | 1.2 Directive auto-extraction | ~$1.50 | coder |
| 2 | 1.3 HiClaw GAP-3 plan-classifier | ~$1 | coder |
| 2 | 1.4 S-MMU near-miss threshold | ~$1 | coder |
| **Total** | **4 items** | **~$4.50** | |

### Phase 2: High-Impact (Weeks 2-3)
| Week | Item | Cost | Who |
|---|---|---|---|
| 2 | 2.1 Caller Profiler | ~$4 | architect → coder |
| 2 | 2.2 VISTA failure categorization | ~$3 | coder |
| 3 | 2.3 DGM-H reflection unfreeze | ~$5 | architect → coder |
| 3 | 2.4 Skills auto-maturation | ~$3 | coder |
| **Total** | **4 items** | **~$15** | |

### Phase 3: Strategic (Weeks 4-8)
| Week | Item | Cost | Who |
|---|---|---|---|
| 4-5 | 3.1 OpenTelemetry pipeline | ~$8 | architect → coder |
| 5-6 | 3.2 A2A protocol upgrade | ~$6 | architect → coder |
| 6-7 | 3.3 MCP server hardening | ~$5 | coder |
| 7-8 | 3.4 Multi-LLM expansion | ~$4 | coder |
| **Total** | **4 items** | **~$23** | |

**Grand Total Estimated Cost: ~$42.50 across 12 improvements over 8 weeks**

---

## Risk Register

| Risk | Probability | Impact | Mitigation |
|---|---|---|---|
| DGM-H self-modification introduces regressions | Medium | High | 48h veto window, MARS check, auto-rollback on >5pp degradation, constitutional lock |
| OTel instrumentation adds latency to hot paths | Low | Medium | Async span export, sampling (1/10 for routine events, 1/1 for errors) |
| Caller Profiler overfits to idle-period patterns | Medium | Low | Only update on genuine interactions, not automated cycles |
| Multi-LLM expansion increases operational complexity | Medium | Medium | Start with Ollama only (local, no external dependency), add others incrementally |
| Skills auto-maturation proposes low-quality templates | Low | Low | Mev approval gate before activation, minimum 3 successful pattern instances |
| A2A upgrade breaks existing plan DAG flow | Low | High | A2A is additive — existing plan DAGs unchanged, A2A is opt-in per plan type |

---

## Dependency Graph

```
Phase 1 (parallel, no dependencies):
  1.1 RL2F idle tagging ─────────────────────────────────┐
  1.2 Directive auto-extraction ─────────────────────────┤
  1.3 HiClaw GAP-3 ─────────────────────────────────────┤
  1.4 S-MMU near-miss ──────────────────────────────────┤
                                                         │
Phase 2 (1.1 must complete first for accurate metrics):  │
  2.1 Caller Profiler ←── no deps ──────────────────────┤
  2.2 VISTA failure cat ←── no deps ────────────────────┤
  2.3 DGM-H reflection ←── 1.1 (needs accurate RL2F) ──┘
  2.4 Skills maturation ←── no deps

Phase 3 (2.x should be live for full value):
  3.1 OTel ←── no deps (can start anytime)
  3.2 A2A upgrade ←── no deps
  3.3 MCP hardening ←── no deps
  3.4 Multi-LLM ←── no deps

Phase 4 (strategic triggers):
  4.1 AOP Governance ←── multi-tenant need
  4.2 Deriver ←── 2.1 Caller Profiler (30d data)
  4.3 Multi-tenant ←── paying customers
```

---

## Competitive Impact Summary

After completing Phases 1-3, Otto's competitive position shifts:

| Dimension | Before (Current) | After (Phase 3) | Competitor Benchmark |
|---|---|---|---|
| Memory | 5/5 | 5/5 (maintained) | All others: 1-2/5 |
| Self-Improvement | 5/5 | 5/5 (deepened with DGM-H) | All others: 0/5 |
| Observability | 2/5 | 4/5 (OTel + Jaeger) | LangGraph: 5/5, Pydantic AI: 5/5 |
| A2A Protocol | 3/5 | 4/5 (Agent Cards + handshake) | Google ADK: 5/5 |
| MCP Support | 3/5 | 4/5 (hardened + discoverable) | ADK: 5/5, Mastra: 4/5 |
| Multi-LLM | 2/5 | 3/5 (Ollama + Bedrock) | OpenAI SDK: 5/5 |
| Tool Use | 4/5 | 4/5 (maintained) | ADK: 5/5 |
| Cost Control | 4/5 | 5/5 (typed failures + profiler) | All others: 3/5 |

**Net effect:** Closes the two biggest competitive gaps (observability, A2A) while deepening moats (self-improvement, memory). Otto moves from "category-leading on 2 dimensions, lagging on 2" to "category-leading on 3, competitive on all."

---

*Generated by architect agent | Task: Build prioritized improvement roadmap with implementation plans | 2026-03-28*
