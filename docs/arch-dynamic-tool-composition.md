# Architecture: Dynamic Tool Composition

**Date**: 2026-03-28
**Source**: STEM Agent gap analysis (GAP P8 — Dynamic Tool Composition)
**Priority**: P7 (low) — LLM-mediated selection works at current scale (21 agents)
**Estimated cost**: ~$2-3 (Phase 1 only)

---

## Design: Dynamic Tool Composition

### Problem

Otto selects agents via two paths:
1. **Dispatch classifier** (`classifiers.py`) — LLM picks ONE agent per task from a hardcoded list of 9 types in the system prompt
2. **Tool RAG** (`skills.py`) — keyword scoring against a static 21-entry `SKILL_REGISTRY`

Neither path supports **composition** — assembling a chain of agents whose outputs feed into each other at task-selection time. If a task needs "research → architect → coder", the system either:
- Relies on the plan classifier (separate LLM call) to decompose manually, OR
- Uses a pre-built workflow template (only 4 exist)

The gap: no structured capability introspection. The LLM guesses agent fit from descriptions; it can't reason about input/output compatibility or automatically chain agents whose capabilities compose.

### Why Now (and Why Not Later)

**Now**: The foundation is cheap (~$2) and unlocks composition for plan creation, Tool RAG, and future MCP externalization. Once capability declarations exist, every consumer gets smarter for free.

**Not urgent**: LLM-based selection works at 21 agents. This becomes critical at 50+ agents or when agents need to be discoverable by external systems (MCP).

### Approach

Three layers, each independently useful:

#### Layer 1: Capability Declarations (data layer)

Extend `SKILL_REGISTRY` entries with structured metadata:

```python
{
    "name": "researcher",
    "description": "...",           # existing
    "keywords": [...],              # existing
    "skill_type": "agent",          # existing
    "agent_type": "researcher",     # existing
    "cost": "medium",               # existing
    # ── NEW FIELDS ──
    "inputs": ["question", "topic", "url"],       # what this agent accepts
    "outputs": ["research_report", "findings"],    # what it produces
    "capabilities": ["web_search", "paper_analysis", "api_investigation"],
    "max_context_tokens": 100000,                  # operational constraint
}
```

**Type vocabulary** (shared across all agents):

| Type | Description | Example Producers | Example Consumers |
|---|---|---|---|
| `question` | Natural language question/instruction | user, heartbeat | researcher, architect |
| `topic` | Subject for investigation | user, classifier | researcher, content-creator |
| `url` | External resource reference | user | researcher |
| `research_report` | Structured findings | researcher | architect, content-creator, reviewer |
| `findings` | Raw research output | researcher, research-synthesizer | reviewer, coder |
| `architecture_spec` | System design document | architect | coder, reviewer |
| `code` | Source code / implementation | coder, debugger | reviewer, debugger |
| `code_review` | Review feedback | reviewer | coder, debugger |
| `content_draft` | Written content | content-creator | reviewer |
| `security_report` | Security findings | security-audit | coder, debugger |
| `social_content` | Social media posts/threads | twitter-engager, social-media-strategist | reviewer |
| `growth_strategy` | Growth plan | growth-hacker | content-creator |
| `memory_report` | Memory status/findings | memory-curator | heartbeat |
| `debug_report` | Bug diagnosis | debugger | coder |

Rules:
- Every agent must declare at least one input and one output
- Types are simple strings — no schema validation (keep it lightweight)
- `question` is the universal input (every agent accepts questions)

#### Layer 2: Composition Engine (logic layer)

New module: `memory/composition.py` (~80 lines)

```python
def find_compositions(
    task_description: str,
    required_output: str | None = None,
    max_chain_length: int = 3,
    registry: list[dict] | None = None,
) -> list[CompositionChain]:
    """Find valid agent chains that can solve the task.

    Algorithm:
    1. Score each agent's relevance to the task (reuse _score_skill)
    2. If required_output specified, find agents that produce it
    3. Walk backwards: for each producer, find agents that produce its inputs
    4. Return chains sorted by (relevance_score_sum, chain_length)

    Returns at most 3 chains (top compositions).
    """
```

Data structure:
```python
@dataclass
class CompositionStep:
    agent_type: str
    role: str             # what this agent does in the chain
    inputs_from: str      # "user" or previous agent_type
    output_type: str      # what this step produces

@dataclass
class CompositionChain:
    steps: list[CompositionStep]
    total_relevance: float
    reasoning: str        # human-readable explanation
```

**How it works** — backward chaining:

```
Task: "Research DeFi protocols and build an integration"
Required output: "code"

Step 1: Who produces "code"? → coder (relevance: 0.8)
Step 2: What does coder need? → ["architecture_spec", "code_review", "question"]
Step 3: Who produces "architecture_spec"? → architect (relevance: 0.7)
Step 4: What does architect need? → ["research_report", "question"]
Step 5: Who produces "research_report"? → researcher (relevance: 0.9)
Step 6: researcher accepts "question" (terminal — from user)

Result chain: researcher → architect → coder (total: 2.4)
```

Constraints:
- Max chain length: 3 (configurable, default 3 — matches workflow step limits)
- No cycles (agent can't appear twice in a chain)
- Single path only (no branching — that's what plan DAGs are for)
- If no valid chain found, return empty list (caller falls back to single-agent)

#### Layer 3: Integration Points (wiring)

Three consumers of composition data:

**3a. Enhanced `/skills/suggest` endpoint**

Add optional `?compose=true` parameter:

```
GET /skills/suggest?task=Research+DeFi+and+build+integration&compose=true

{
  "task": "Research DeFi and build integration",
  "top_n": 3,
  "skills": [...],           // existing single-agent suggestions
  "compositions": [          // NEW — only if compose=true
    {
      "steps": [
        {"agent_type": "researcher", "role": "investigate DeFi protocols", "output_type": "research_report"},
        {"agent_type": "architect", "role": "design integration", "output_type": "architecture_spec"},
        {"agent_type": "coder", "role": "implement integration", "output_type": "code"}
      ],
      "total_relevance": 2.4,
      "reasoning": "researcher→architect→coder: research first, then design, then implement"
    }
  ]
}
```

**3b. Plan classifier hint injection**

In `task_plans.py`, before the LLM plan-decomposition call, query `find_compositions()` and inject the result as a hint in the system prompt:

```
Current system prompt for plan classifier:
"Decompose this instruction into tasks..."

Enhanced:
"Decompose this instruction into tasks...

COMPOSITION HINTS (from capability analysis):
- Suggested chain: researcher → architect → coder
- researcher outputs: research_report (consumed by architect)
- architect outputs: architecture_spec (consumed by coder)

You may use these hints or ignore them if the task needs different decomposition."
```

This is a **soft hint**, not a hard constraint. The LLM still decides the final decomposition.

**3c. Dispatch classifier enrichment**

In `classifiers.py`, enrich the `_DISPATCH_SYSTEM` prompt with the top composition chain when a task looks like it needs multiple agents. This helps the classifier recommend `workflow_template` selection instead of single-agent dispatch.

### Key Decisions

- **Extend SKILL_REGISTRY in-place** (not a new DB table) because: (a) 21 agents, no need for dynamic discovery yet, (b) single file is easier to audit and version, (c) no migration needed. Alternative: DB table with API CRUD — deferred to MCP externalization phase.

- **Backward chaining** (from desired output) instead of forward chaining (from available inputs) because: most tasks have a clear desired outcome (code, content, report) but fuzzy inputs. Alternative: LLM-based composition — rejected because the whole point is to avoid LLM for this decision.

- **Soft hints to plan classifier** instead of hard-wiring composition into plan execution because: the LLM decomposer is already good — it just lacks structured capability knowledge. A hint makes it better without constraining it. Alternative: bypass plan classifier entirely — rejected because composition chains are linear while real tasks often need DAGs.

- **No new database tables or migrations** because: capability declarations are code (not data), composition is computed on-the-fly, and results are transient. Alternative: store composition results for learning — deferred to Phase 2.

- **Max chain length 3** because: this matches the practical limit of sequential workflow steps before quality degrades. Longer chains should be plan DAGs with parallel branches.

### API / Interface

#### Modified endpoint

```
GET /skills/suggest?task={description}&top_n=3&compose=true
```

Response adds `compositions` field (list of `CompositionChain`). Only present when `compose=true`.

#### New internal function (not an endpoint)

```python
# memory/composition.py
find_compositions(task_description, required_output=None, max_chain_length=3) -> list[CompositionChain]
```

Called by:
1. `/skills/suggest` when `compose=true`
2. Plan classifier in `task_plans.py` for hint injection
3. (Future) MCP server for external tool discovery

#### Data Flow

```
Task arrives (WhatsApp/API/heartbeat)
        │
        ▼
  ┌─────────────┐
  │ classify_for │─── single agent? ──→ existing path (no change)
  │  _dispatch   │
  └──────┬──────┘
         │ multi-step detected
         ▼
  ┌─────────────┐     ┌────────────────┐
  │    plan      │◄────│ find_compositions│  ← NEW: composition hints
  │  classifier  │     │  (backward chain)│     injected into LLM prompt
  └──────┬──────┘     └────────────────┘
         │
         ▼
  ┌─────────────┐
  │  plan DAG    │  ← tasks with agent_type set (informed by composition)
  │  executor    │
  └─────────────┘
```

### Files Changed

| File | Change | Lines |
|---|---|---|
| `memory/composition.py` | **NEW** — composition engine (CompositionStep, CompositionChain, find_compositions) | ~80 |
| `memory/routes/skills.py` | Add `inputs`, `outputs`, `capabilities` to all 21 SKILL_REGISTRY entries. Add `compose` param to `/suggest`. | ~60 |
| `memory/routes/task_plans.py` | Import `find_compositions`, inject hints into plan classifier prompt | ~15 |

Total: ~155 lines across 3 files. No migration. No new service.

### Implementation Plan

**Phase 1** (~$2, single task):
1. Add capability declarations to all 21 entries in `SKILL_REGISTRY`
2. Create `memory/composition.py` with `find_compositions()`
3. Add `?compose=true` to `/skills/suggest`
4. Test: `curl /skills/suggest?task=research+and+build&compose=true`

**Phase 2** (~$1, separate task — deferred):
5. Inject composition hints into plan classifier
6. Enrich dispatch classifier with composition awareness
7. Test: send multi-step instruction via WhatsApp, verify plan uses composition hints

**Phase 3** (future — when MCP externalization happens):
8. Expose capability declarations via MCP tool introspection
9. External agents can discover Otto's capabilities and compose with them

### Risks

- **Over-engineering at 21 agents**: Mitigated by keeping Phase 1 minimal (data + simple function, no infrastructure). If we never grow past 30 agents, the composition engine is still useful as plan-classifier hints.

- **Stale capability declarations**: If new agents are added to SKILL_REGISTRY without inputs/outputs, composition silently degrades. Mitigated by: (a) validation in `/skills` list endpoint that flags incomplete entries, (b) composition engine gracefully skips agents without declarations.

- **Composition chains that don't match task intent**: The backward-chaining algorithm is naive — it can suggest "researcher → coder" for a task that only needs a coder. Mitigated by: (a) relevance scoring filters out low-relevance agents, (b) chains are soft hints (LLM decides), (c) max chain length caps cost.

- **Budget impact**: Composition computation is O(agents² × max_chain_length) — at 21 agents and max_length=3, that's <1000 iterations. Negligible. At 100+ agents, may need indexing.

### Capability Declarations for All 21 Agents

For reference, here are the declarations for each current agent:

```python
# researcher
{"inputs": ["question", "topic", "url"], "outputs": ["research_report", "findings"], "capabilities": ["web_search", "paper_analysis", "api_investigation"]}

# coder
{"inputs": ["question", "architecture_spec", "code_review", "debug_report"], "outputs": ["code"], "capabilities": ["implementation", "feature_building", "bug_fixing"]}

# debugger
{"inputs": ["question", "code", "error_log"], "outputs": ["debug_report", "code"], "capabilities": ["root_cause_analysis", "error_tracing", "minimal_fixes"]}

# reviewer
{"inputs": ["code", "content_draft", "architecture_spec"], "outputs": ["code_review"], "capabilities": ["code_review", "quality_assessment", "security_check"]}

# architect
{"inputs": ["question", "research_report", "findings"], "outputs": ["architecture_spec"], "capabilities": ["system_design", "api_design", "tradeoff_analysis"]}

# content-creator
{"inputs": ["question", "topic", "research_report"], "outputs": ["content_draft"], "capabilities": ["article_writing", "brand_voice", "copy_writing"]}

# memory-curator
{"inputs": ["question"], "outputs": ["memory_report"], "capabilities": ["deduplication", "consolidation", "decay_management"]}

# twitter-engager
{"inputs": ["topic", "content_draft", "growth_strategy"], "outputs": ["social_content"], "capabilities": ["thread_creation", "engagement", "viral_content"]}

# social-media-strategist
{"inputs": ["topic", "growth_strategy"], "outputs": ["social_content", "growth_strategy"], "capabilities": ["content_calendar", "campaign_planning", "audience_growth"]}

# growth-hacker
{"inputs": ["question", "research_report"], "outputs": ["growth_strategy"], "capabilities": ["viral_loops", "conversion_optimization", "growth_channels"]}

# landing-page
{"inputs": ["question", "content_draft", "architecture_spec"], "outputs": ["code"], "capabilities": ["web_design", "html_css", "landing_pages"]}

# security-audit
{"inputs": ["code", "architecture_spec"], "outputs": ["security_report"], "capabilities": ["vulnerability_assessment", "code_audit", "hardening"]}

# research-synthesizer
{"inputs": ["findings", "research_report"], "outputs": ["research_report"], "capabilities": ["synthesis", "cross_referencing", "confidence_scoring"]}

# memory-query (tool, not agent)
{"inputs": ["question"], "outputs": ["memory_report"], "capabilities": ["semantic_search", "episodic_query", "knowledge_retrieval"]}

# workflow-operations (tool)
{"inputs": ["question"], "outputs": ["workflow_status"], "capabilities": ["workflow_management", "agent_activation"]}

# task-creation (tool)
{"inputs": ["question"], "outputs": ["task_spec"], "capabilities": ["task_queue_management"]}

# api-development (tool)
{"inputs": ["question", "architecture_spec"], "outputs": ["code"], "capabilities": ["fastapi_patterns", "endpoint_creation"]}

# debug-workflow (tool)
{"inputs": ["error_log", "question"], "outputs": ["debug_report"], "capabilities": ["service_diagnosis", "log_analysis"]}

# otto-conventions (tool)
{"inputs": ["question"], "outputs": ["findings"], "capabilities": ["codebase_patterns", "style_guidance"]}

# sprint-prioritizer (not in registry yet — auto-employed agent)
# solidity-smart-contract-engineer (not in registry — auto-employed)
# blockchain-security-auditor (not in registry — auto-employed)
```

### Relationship to Other Systems

| System | Relationship |
|---|---|
| **MCP Externalization** (parallel task) | Composition engine provides the capability data that MCP would expose externally. Phase 3 wires them together. |
| **A2A Protocol** (parallel task) | A2A is agent-to-agent communication. Composition is agent chain planning. Orthogonal — A2A handles runtime messaging, composition handles pre-execution planning. |
| **Plan Classifier** | Composition provides hints to the plan classifier. Plan classifier remains the decision-maker. |
| **AdaptOrch Routing** | Routing handles per-task resource allocation (model, budget, timeout). Composition handles which agents to use. No conflict. |
| **Workflow Templates** | Workflows are pre-built chains. Composition is ad-hoc chains. Composition can suggest which workflow template matches, or propose a new chain when no template fits. |
| **AutoEvolve** | Future: AutoEvolve could propose new capability declarations or new type vocabulary entries based on task outcomes. |
