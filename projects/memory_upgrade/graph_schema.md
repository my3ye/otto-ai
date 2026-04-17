# G2CP Cross-Brain Graph Schema
*Implemented: 2026-02-22 | Based on: G2CP paper (arXiv 2602.13370)*

## Overview

G2CP (Graph-Grounded Context Protocol) replaces free-text inter-agent messaging with structured
graph operations over a shared knowledge graph. Otto's two brains (Claude and Gemini) write
typed nodes instead of lossy text summaries, eliminating semantic drift.

**Results from paper:** 73% fewer tokens, 34% better accuracy, zero cascading hallucinations.

## Storage Layer

Structured nodes are stored in PostgreSQL (`cross_brain_graph` table) as the primary reliable store.
Additionally, structured messages are ingested to Graphiti for entity/relationship extraction.

Both brains read from the same `cross_brain_graph` table via the Memory API.

## Node Types

### DirectiveNode
A mission-level or behavioral directive from Mev.

```json
{
  "node_type": "directive",
  "name": "short label (max 100 chars)",
  "content": {
    "text": "full directive content",
    "priority": 8,
    "category": "directive|mission|goal|priority_change"
  },
  "source_brain": "gemini|claude",
  "priority": 8
}
```

### DecisionNode
A decision made by Mev or Otto about how to proceed.

```json
{
  "node_type": "decision",
  "name": "short decision label",
  "content": {
    "text": "full decision text",
    "decided_by": "mev|otto",
    "context": "what prompted this decision"
  },
  "source_brain": "gemini|claude",
  "priority": 7
}
```

### TaskStateNode
Structured state for a task (created, updated, completed).

```json
{
  "node_type": "task_state",
  "name": "task title",
  "content": {
    "task_id": "uuid or string",
    "title": "full task title",
    "status": "pending|running|completed|failed",
    "summary": "what happened / what was built"
  },
  "source_brain": "claude",
  "priority": 5
}
```

### ContextNode
A working memory key/value pair shared between brains.

```json
{
  "node_type": "context",
  "name": "key",
  "content": {
    "key": "slot name",
    "value": "slot content"
  },
  "source_brain": "gemini|claude",
  "priority": 5
}
```

## Database Schema

```sql
CREATE TABLE cross_brain_graph (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    node_type VARCHAR(50) NOT NULL,     -- directive, decision, task_state, context
    name VARCHAR(255) NOT NULL,          -- short label/identifier
    content JSONB NOT NULL,              -- typed structured fields (see above)
    source_brain VARCHAR(50) DEFAULT 'gemini',  -- which brain wrote this
    priority INTEGER DEFAULT 5,          -- 1-10, higher = more important
    active BOOLEAN DEFAULT TRUE,         -- soft delete / supersede
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

## Context Integration

Both brains receive a `[Otto] Structured Graph:` tier in their context text showing:
- Recent active DirectiveNodes (last 5)
- Recent active DecisionNodes (last 3)
- Recent active ContextNodes (last 5)

This tier appears between Knowledge Graph (Tier 7) and Procedures (Tier 8).

## Write Flow (WhatsApp → Graph)

1. Mev sends WhatsApp message
2. Gemini classifies: `note_type` ∈ {mission, directive, goal, decision, task, approval}
3. Cross-brain note written to `pending_questions` (existing text flow — preserved)
4. **NEW:** Structured node written to `cross_brain_graph` via `write_directive()` or `write_decision()`
5. Context briefing for both Claude and Gemini includes `cross_brain_graph` tier

## Read Flow (Context Briefing)

```
GET /context/inject?source=startup   → Claude context (includes cross_brain_graph)
GET /context/inject?source=whatsapp  → Gemini context (includes cross_brain_graph)
GET /context/unified                 → includes structured_graph field
```

## API Endpoints (Memory API :8100)

| Endpoint | Method | Purpose |
|---|---|---|
| `/graph/nodes` | POST | Write a structured graph node |
| `/graph/nodes` | GET | List recent active nodes |
| `/graph/nodes/{id}/deactivate` | POST | Soft-delete a node |

## Graphiti Integration

In addition to PostgreSQL, nodes are also ingested to Graphiti (`:8000`) as structured messages
for entity/relationship extraction. This enriches the NLP-based knowledge graph with typed context.

Group IDs used:
- `otto_directives` — mission/directive nodes
- `otto_decisions` — decision nodes
- `otto_context` — context/working memory nodes
