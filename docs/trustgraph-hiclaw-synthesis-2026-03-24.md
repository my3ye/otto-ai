# TrustGraph × HiClaw: Decision-Support Brief
**Date:** 2026-03-24
**Purpose:** Cross-reference synthesis for Mev — where these frameworks complement, overlap, integrate, or conflict with each other and with Otto's current stack.

---

## TL;DR

**TrustGraph = what agents know.** Knowledge infrastructure: structured storage, versioned context bundles, multi-strategy retrieval, provenance.
**HiClaw = how agents work together.** Coordination infrastructure: Manager-Worker hierarchy, DAG planning, dynamic provisioning, isolated execution.
**Otto already has both cores.** The question is which specific patterns from each are worth lifting.

---

## 1. Complementary Capabilities

These two frameworks solve different layers — they are naturally additive, not competing.

| Layer | HiClaw | TrustGraph | Otto Today |
|---|---|---|---|
| **Coordination** | Manager-Worker DAG, @mention routing | Not present | ✅ Task DAG + Workflow engine |
| **Knowledge storage** | Not present | Cassandra + Qdrant + KG | ✅ Postgres + pgvector + Neo4j |
| **Retrieval** | Not present | DocumentRAG + GraphRAG + OntologyRAG | ✅ A-RAG (3-strategy) |
| **Context packaging** | Not present | Context Cores (versioned bundles) | ❌ Gap — S-MMU is session-only |
| **Provenance** | Not present | Per-thought RDF triples | ❌ Gap — episodic events, but not thought-level |
| **Agent comms** | Matrix/Element protocol | MCP server | ✅ WhatsApp + Memory API (simpler) |
| **Tool discovery** | Not present | MCP standardized | ❌ Gap — no MCP endpoint |

**The complementary layer that matters most:**
TrustGraph's **Context Cores** (portable versioned knowledge bundles) fills the exact gap HiClaw's coordination model exposes: when a Manager spawns Workers, what do the Workers know? HiClaw is silent on this. TrustGraph answers it. Otto has neither — our agents get context only from the session briefing + S-MMU, which is runtime-assembled, not versioned or portable.

---

## 2. Overlapping Concerns

Both frameworks touch these areas — they approach differently.

### Memory & Context
- **HiClaw:** Per-project working memory (context injected per session, not persisted across agents)
- **TrustGraph:** Context Cores — persistent, versioned, importable by any agent
- **Otto:** S-MMU L1/L2/L3 paging + Graphiti KG. Same concept as both but single-instance, not portable.

**Verdict:** Overlap is real but not blocking — Otto's stack is more sophisticated than HiClaw's, roughly comparable to TrustGraph's retrieval story. The Context Cores portability concept is genuinely missing.

### Tool Orchestration
- **HiClaw:** Manager routes tasks to Workers based on capability; Workers are created dynamically
- **TrustGraph:** ReAct agent (tool loop) with MCP as the tool discovery/invocation standard
- **Otto:** Workflow engine + agent auto-employment (139 agents in agency-agents repo). No MCP.

**Verdict:** HiClaw's dynamic Worker creation maps to Otto's agent auto-employment. TrustGraph's MCP layer is Otto's missing interface — it would let Claude Desktop, Cursor, and external agents call Otto tools natively.

### Knowledge Graph
- **HiClaw:** No knowledge graph component
- **TrustGraph:** Full KG pipeline (entity extraction → Cassandra-backed graph → GraphRAG + OntologyRAG + SPARQL)
- **Otto:** Neo4j + Graphiti (temporal KG). We have the graph; we lack OntologyRAG and SPARQL.

**Verdict:** TrustGraph's OntologyRAG is genuinely additive over Otto's current Graphiti usage. We'd benefit from schema-enforced retrieval for structured domain queries (e.g., "find all WebAssist clients in X region with Y property").

---

## 3. Integration Potential (Concrete)

Ranked by value vs. implementation cost for Otto:

### HIGH VALUE — Context Cores Pattern (~$3-5 to implement)
**What:** Package Otto's domain knowledge (WebAssist processes, Koink protocol, SOS architecture, OWS contracts) into versioned, portable knowledge bundles. Any agent can `import` a bundle rather than relying on session briefing assembly.
**How:** Add a `context_cores` table to Postgres (schema: domain, version, ontology_json, graph_snapshot_id, embedding_index_ref, retrieval_policy, provenance). Add `/context/cores/*` endpoints to Memory API. Heartbeat agents request the relevant core at startup.
**Impact:** Solves context drift — agents working on WebAssist always get the same base knowledge regardless of session state. Survives compaction.
**HiClaw connection:** When a plan spawns multiple Worker-equivalent tasks, each gets the same versioned context core. Eliminates inconsistency across parallel agents.

### MEDIUM VALUE — MCP Server for Otto (~$4-6 to implement)
**What:** Expose Otto's Memory API tools via the Model Context Protocol standard.
**How:** Create `otto/mcp_server/` using `trustgraph-mcp` as reference (or `mcp` Python SDK directly). Expose: `/semantic/search`, `/episodic/events`, `/tasks`, `/graph/search`, `/context/briefing` as MCP tools.
**Impact:** Any MCP-compatible client (Claude Desktop, Cursor, external agents) can call Otto's memory and task system directly. Critical for Otto's public SDK story (otto-ai GitHub repo).
**TrustGraph connection:** TrustGraph's MCP layer is production-grade reference implementation — clone the pattern, not the Cassandra-specific code.

### MEDIUM VALUE — OntologyRAG for Structured Domains (~$5-8 to implement)
**What:** Add schema-enforced retrieval layer over Graphiti — define domain ontologies (WebAssist client schema, Koink token schema, SOS beneficiary schema) and support SPARQL-style structured queries.
**How:** Define ontology files per domain (OWL/SHACL-lite or simpler JSON schema). Add a query endpoint that enforces schema constraints before vector retrieval. Route domain queries through ontology matcher first, fall back to A-RAG.
**Impact:** Precision retrieval for structured knowledge — eliminates hallucinated property values in domain-specific agent tasks.
**HiClaw connection:** When Manager decomposes tasks, tool selection accuracy improves when the routing query is schema-grounded.

### LOW VALUE — Per-thought RDF Provenance (~$6-10 to implement, low ROI)
**What:** Store every agent reasoning step as RDF triples (session → iteration → thought → observation → action).
**How:** Add `agent_provenance` table with RDF-style subject/predicate/object columns. Emit one row per ReAct loop iteration from task_runner.sh.
**Impact:** Full audit trail of agent reasoning. Useful for debugging, less useful for day-to-day operation.
**Assessment:** Otto already has episodic events + task logs. The marginal value of per-thought RDF is low unless Otto starts running regulated/audited processes (e.g., financial decisions, medical triage for SOS). Defer.

---

## 4. Competitive Tension

### Where they conflict or force a choice:

**Storage substrate**
TrustGraph is built on Cassandra + Qdrant. Otto uses Postgres + pgvector + Neo4j. These are incompatible at the infrastructure level. TrustGraph's open PostgreSQL issue (#675) shows they're moving toward pgvector/AGE, but not there yet.
**Decision:** Don't adopt TrustGraph's storage layer. Adopt its *patterns* (Context Cores, OntologyRAG) implemented on Otto's existing Postgres stack.

**Agent communication**
HiClaw uses Matrix/Element protocol (~500MB runtime, separate IM server). Otto uses WhatsApp + Memory API.
**Decision:** Reject Matrix adoption firmly. Otto's WhatsApp channel is simpler, already live, and serves Mev directly. The Matrix overhead is unjustified for a single-operator system.

**ReAct agent runtime**
TrustGraph ships its own ReAct agent loop (service.py, agent_manager.py). Otto uses Claude Code CLI as its compute engine.
**Decision:** Don't replace Otto's ReAct with TrustGraph's. Claude Code CLI is more powerful (file editing, bash exec, full tool use). TrustGraph's ReAct is for knowledge-grounded query agents, not general-purpose builders.

**Deployment complexity**
TrustGraph's full stack requires Cassandra + Qdrant + Pulsar + Kubernetes/Docker Compose generation. On 4 vCPU / 16GB RAM with no swap, this is borderline unrunnable alongside Otto's existing stack.
**Decision:** Run nothing from TrustGraph's stack natively. Lift patterns and concepts only.

---

## 5. Recommended Integration Sequence

```
Phase 1 (now, ~$5):
  → Context Cores pattern → implement on Postgres
     Priority domains: WebAssist, Koink, SOS, OWS
     Unlocks: context stability for parallel agent tasks

Phase 2 (next sprint, ~$5):
  → MCP Server for Otto
     Expose: semantic search, task queue, context briefing
     Unlocks: otto-ai public SDK story, Claude Desktop interop

Phase 3 (when structured queries needed, ~$6):
  → OntologyRAG for domain queries
     Start with WebAssist client schema
     Unlocks: precision retrieval for domain agents

Skip permanently:
  → TrustGraph storage layer (Cassandra/Qdrant) — incompatible infra
  → Matrix/Element protocol from HiClaw — overengineered
  → HiClaw ZeroClaw/NanoClaw runtimes — in development, no value
  → Per-thought RDF provenance — low ROI until regulated use cases
```

---

## 6. Otto Architecture Assessment (Bottom Line)

Otto today **structurally matches both frameworks** at the coordination and retrieval layers. We built the same capabilities independently:

| Capability | HiClaw | TrustGraph | Otto |
|---|---|---|---|
| DAG task orchestration | ✅ | — | ✅ |
| Multi-agent coordination | ✅ | — | ✅ |
| Knowledge graph | — | ✅ | ✅ |
| Vector retrieval | — | ✅ | ✅ |
| Multi-strategy RAG | — | ✅ | ✅ |
| Context packaging (versioned) | — | ✅ | ❌ |
| MCP interface | — | ✅ | ❌ |
| Schema-enforced retrieval | — | ✅ | ❌ |
| Agent provenance | — | ✅ | partial |

**The two gaps worth closing are Context Cores and MCP.** Both are implementable in 1-2 tasks each on Otto's existing stack without adding infrastructure.

HiClaw is a validation that Otto's architecture is correct. TrustGraph has 3 specific patterns worth borrowing. Neither framework should be adopted wholesale.
