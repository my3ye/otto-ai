# Otto Self-Improvement Proposals
*Generated: 2026-02-19 | Sources: MIRIX, Mem0, ReflAct, MAR, Acon, Instructor*

Ranked by impact/effort ratio (highest first).

---

## 1. Instructor Validation + Retry Loop for Tool Calls
**Impact: High | Effort: Low | Source: python.useinstructor.com**

Wrap every Claude API call that produces structured output with `instructor` — a 1-line client wrapper that validates responses against Pydantic schemas and auto-retries on failure with the validation error fed back to the model. Otto currently has no structured output validation, meaning malformed tool responses or API payloads silently fail or require manual error handling. This directly reduces tool hallucinations and invalid JSON responses across the memory API, heartbeat orchestrator, and task runners.

**Implementation:** `pip install instructor anthropic` → wrap client: `instructor.from_anthropic(anthropic.Anthropic())` → define Pydantic models for key structured outputs (task creation, memory entries, lead scoring). Estimated: 2-4 hours across the codebase.

---

## 2. ReflAct State-Tracking Loop in Heartbeat Agent
**Impact: High | Effort: Low | Source: EMNLP 2025, ReflAct paper**

Replace the heartbeat's current Thought→Action reasoning pattern with a Reflect→State→Act loop that maintains a running "current state vs. goal" block in every reasoning step. ReflAct beats ReAct by 27.7% on task benchmarks by preventing agents from losing track of where they are in a multi-step workflow — exactly the failure mode Otto hits in long heartbeat cycles (losing budget, forgetting earlier findings, drift). No fine-tuning required — implemented as a system prompt modification.

**Implementation:** Add a structured `## Current State` scratchpad section to `heartbeat.md` and `alpha_heartbeat.md` agent prompts. Instruct the agent to update it at every step before deciding next action. Estimated: 30 minutes.

---

## 3. Threshold-Based Context Compression in /context/briefing
**Impact: High | Effort: Medium | Source: Acon, arxiv 2510.00615**

Add a token-threshold middleware to the `/context/briefing` endpoint: when assembled context exceeds ~12k tokens, run a compression pass that summarizes episodic events into a rolling digest while preserving semantic facts and procedures verbatim. Acon achieves 26-54% peak token reduction with no task performance loss. Otto's heartbeat currently receives a fixed context dump — adding adaptive compression would reduce per-heartbeat costs and prevent context budget bleed on long-running sessions.

**Implementation:** Add a `compress_if_needed(context, threshold=12000)` function in `memory/routes/context.py`. Use a simple Haiku call to summarize episodic events older than 24h into bullet digests. Cache the digest so it's not recomputed each cycle. Estimated: 4-6 hours.

---

## 4. MIRIX-Style Meta Memory Manager Routing
**Impact: High | Effort: Medium | Source: arxiv 2507.07957**

Add pre-retrieval topic generation to every context briefing: before assembling the context, Otto generates a 3-5 word topic query describing the current task, uses it to selectively retrieve from the relevant memory tier (episodic for recent events, semantic for facts, procedural for how-to), and skips irrelevant tiers. MIRIX achieves 35% accuracy improvement and 99.9% storage reduction over naive RAG. Otto currently dumps all tiers regardless of relevance — targeted retrieval would sharpen context quality and reduce token waste.

**Implementation:** Add a `topic_query` optional field to `/context/briefing` POST. When provided, filter retrieval per tier by relevance to the query. The heartbeat and task agents pass their current goal as `topic_query`. Estimated: 6-8 hours.

---

## 5. Mem0 Integration for WhatsApp Conversation Memory
**Impact: Medium | Effort: Medium | Source: arxiv 2504.19413, mem0ai library**

Replace the current naive "store every message" approach in `/whatsapp/incoming` with Mem0's three-phase cycle: extract salient facts from each conversation, deduplicate against existing memories, and store only meaningful delta information in graph + vector stores. Mem0 benchmarks at 26% accuracy improvement over OpenAI's approach with 90% token cost reduction in retrieval. Otto currently over-stores raw messages and under-extracts structured facts from Mev's WhatsApp directives.

**Implementation:** `pip install mem0ai` → configure with existing Postgres + Neo4j backends → wrap the WhatsApp incoming handler to run Mem0 extraction before raw storage. Estimated: 4-6 hours including backend config.

---

## 6. Multi-Agent Critic Loop for Failed Tasks
**Impact: Medium | Effort: Medium | Source: arxiv 2512.20845, MAR**

When a task in the queue fails or returns low-confidence output, spawn 2 lightweight critic subagents (skeptic + domain expert personas) to analyze the failure from different angles before retrying. MAR directly fixes confirmation bias in single-agent Reflexion — where the agent essentially repeats the same wrong reasoning on retry. This is exactly what happens when Otto's tasks hit budget limits and retry with the same approach. The critic agents produce a structured failure analysis that seeds the retry prompt.

**Implementation:** Add a `failure_analysis(task_result)` step to the task orchestrator in the heartbeat. On task failure, run two Haiku calls with different system prompts, synthesize their critique, prepend to retry context. Estimated: 3-5 hours.

---

*Note: ChunkKV (KV cache compression) was evaluated but requires inference-layer access — not applicable to Claude API usage. Skipped.*
