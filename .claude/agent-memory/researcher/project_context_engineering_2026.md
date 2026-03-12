---
name: context_engineering_2026
description: State of the art in context engineering, agent memory architectures, tool use frameworks, and multi-agent context sharing as of March 2026. Directly applicable to Otto's architecture.
type: project
---

## Context Engineering 2026 — State of the Art

### Primary Framework: 4 Strategies (LangChain/Anthropic Consensus)

The field has converged on four strategies for managing agent context:

1. **Write** — persist information outside context window (scratchpads, memory stores)
2. **Select** — retrieve only relevant information at each step (RAG, embedding search)
3. **Compress** — summarize/trim when context grows large (auto-compact at 95% capacity)
4. **Isolate** — split tasks across sub-agents with focused context windows

Sources:
- https://blog.langchain.com/context-engineering-for-agents/
- https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents

### Core Principles (Anthropic Engineering)

- Treat context as a finite resource — every token depletes the "attention budget"
- "Lost in the middle": performance degrades 30%+ when critical info is buried mid-context. Position matters: beginning and end of context have highest recall.
- RoPE positional encoding causes long-term decay — models de-emphasize tokens far from start/end
- Signal-to-noise ratio is the overarching goal: smallest set of high-signal tokens for desired outcome
- Context failure modes: poisoning, distraction, confusion, clash — all are real production risks
- "Do the simplest thing that works" — minimal prompts + iterate based on failure modes, not speculation

### Agent Memory Architecture Research (2026)

**AgeMem (arXiv 2601.01885, Jan 2026):**
- Unified LTM+STM: exposes memory operations (store/retrieve/update/summarize/discard) as tool actions
- Agent autonomously decides what to remember via reinforcement learning (GRPO)
- Outperforms baselines on 5 long-horizon benchmarks
- Key insight: memory management should be LEARNED, not rule-based

**A-MEM (arXiv 2502.12110, NeurIPS 2025):**
- Zettelkasten-inspired: atomic notes with cross-links and keyword tags
- Dynamic memory evolution: new memories trigger updates to related historical memories
- Works across 6 LLM backbones
- Key insight: memory should be a living knowledge GRAPH, not a flat store

**HiAgent (hierarchical working memory):**
- Chunks working memory using subgoals
- Summarizes fine-grained action-observation pairs once a subgoal is completed
- Prevents working memory from filling with low-salience trace data

### Tool/Skill Design Principles

**Progressive Disclosure for Tools:**
- Never load all tools simultaneously — overwhelming the model degrades selection accuracy
- Tool RAG: semantically retrieve only relevant tools from a registry based on current task
- 3x improvement in tool selection accuracy when using RAG over full tool listing
- Invest in tool DESCRIPTIONS — these are the semantic signals for routing, not documentation

**Tool Design Rules (Anthropic):**
- Minimize overlap — each tool must have one unambiguous purpose
- Tools must promote token efficiency in their return values
- Human engineers should be able to definitively state when to use each tool
- Tool descriptions act like few-shot examples — they shape behavior as much as the function itself

**Agent Skills (Agent Skills for Context Engineering repo):**
- Skills are loaded on demand, not all upfront
- Each skill: SKILL.md (instructions) + scripts/ (demos) + references/
- BDI mental state modeling is a valid formalism for deliberative agents

### Multi-Agent Context Sharing

**Emerging protocols (2026):**
- MCP (Model Context Protocol): universal standard for tool/resource exposure. 97M+ monthly SDK downloads. Anthropic, OpenAI, Google, Microsoft all adopted.
- A2A (Agent-to-Agent Protocol): HTTP + JSON-RPC, handles state across agent boundaries
- ACP (Agent Communication Protocol): federated, secure, autonomous orchestration
- ANP (Agent Network Protocol): discovery + capability verification + economic negotiation

**Key patterns:**
- Sub-agents return condensed summaries (1,000-2,000 tokens), not raw exploration logs
- 15x more tokens consumed in multi-agent vs single-agent — offset by better task quality
- Isolated context per sub-agent = key advantage (each window allocated to narrow sub-task)
- Handoff notes / workspace handoff (Otto already implements CAT protocol) = best practice

**Beyond Context Sharing (arXiv 2602.15055):**
- Proposes unified ACP for discovery, capability verification, SLA negotiation, secure execution
- The gap in 2026: agents can share context via MCP, but no robust protocol for autonomous coalition formation

### Context Degradation Solutions

- Keep context < 50% full when possible — after 50%, decay accelerates
- Position critical facts at start or end of context, never buried in middle
- Two-stage retrieval: broad recall → cross-encoder reranking → strategic ordering (top evidence at start AND end)
- Hybrid search (semantic + BM25) beats pure vector search for precision
- Auto-compact at 95% capacity: preserve architectural decisions + unresolved issues, discard redundant tool outputs
- Ms-PoE: plug-and-play positional encoding fix for "lost in the middle" — no fine-tuning needed

### Six Pillars of Context Engineering (Weaviate synthesis)

1. Agents — orchestrators deciding what/when to retrieve
2. Query augmentation — reformulating user input for different retrieval targets
3. Retrieval — chunking strategy (small chunks = precision, large = richness)
4. Prompting — CoT, ReAct, structured output frameworks
5. Memory — layered (short-term window, long-term vector DB, working space)
6. Tools — standardized interfaces (MCP), thought-action-observation cycles

### What Otto Already Does Right (vs 2026 consensus)

- L1/L2/L3 S-MMU hierarchy = matches the hierarchical memory architecture consensus
- Semantic slices with centroid-similarity retrieval = matches "Select" strategy
- Auto-compact safety valve in SMMU = matches "Compress" strategy
- Sub-agents (heartbeat/reflection/task workers) = matches "Isolate" strategy
- Always-resident slots (purpose/priorities) = matches "position critical info at start" principle
- CAT protocol (workspace handoff) = matches multi-agent context sharing best practice
- HyMem dual-granularity + ARAG blended retrieval = matches hybrid search recommendation

### Gaps vs 2026 Consensus

1. **Tool RAG not implemented**: All agent tools loaded simultaneously. Should use semantic retrieval to expose only relevant tools for the current task step.
2. **Memory evolution not implemented**: A-MEM shows that new memories should trigger updates to related existing memories. Otto's memories are append-only.
3. **No learned memory management**: AgeMem approach (RL-driven decide-what-to-remember) vs Otto's heuristic decay. Gap is significant for long-horizon tasks.
4. **Position bias not explicitly addressed**: Critical facts should always be at start or end of L1. Current SMMU ordering puts always-resident first (good) but dynamic slices may end up in middle.
5. **Sub-agent output compression**: Task workers return full output, not 1,000-2,000 token summaries. Heartbeat must read and manually extract — token waste.
6. **Tool descriptions as prompts**: Agent skills exist but tool descriptions are not systematically crafted as semantic routing signals.
