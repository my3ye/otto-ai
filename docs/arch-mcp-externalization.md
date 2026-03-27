# Architecture: MCP Externalization

**Date**: 2026-03-28
**Source**: STEM Agent gap analysis (P2: Tool Management), TrustGraph synthesis (MCP layer)
**Status**: Design complete, ready for implementation

---

## Design: MCP Externalization

### Problem

Otto's 21 skills are locked in a static Python list (`skills.py:SKILL_REGISTRY`) with keyword-based scoring. No external system can discover or invoke Otto's capabilities programmatically. This blocks:

1. **External agent interop** — Claude Desktop, Cursor, other MCP-aware agents can't use Otto's tools
2. **Dynamic discovery** — adding a new skill requires editing code and restarting the service
3. **Cross-system composition** — STEM Agent's dynamic tool composition pattern requires tools to be introspectable, not just listed
4. **Developer onboarding** — the otto-ai public repo can't expose a standard tool interface for contributors

The gap analysis rated this P6 (medium-term) because the static registry works at 21 skills. The priority increases as Otto heads toward public developer access and multi-agent collaboration.

### Approach

**Wrap Otto's existing Memory API endpoints as MCP tools using the `mcp` Python SDK (Anthropic's official SDK).** The MCP server runs as a FastAPI sub-application on the existing :8100 service — no new process, no new port.

This is an **incremental bridge** — every MCP tool is a thin wrapper around an existing HTTP endpoint. The skill registry stays as the source of truth for internal routing. MCP adds an external-facing protocol layer on top.

#### Architecture Diagram

```
                    External Clients
                    ┌──────────────┐
                    │ Claude Desktop│
                    │ Cursor IDE   │
                    │ Other Agents │
                    └──────┬───────┘
                           │ SSE transport (HTTP)
                           ▼
                ┌─────────────────────┐
                │  /mcp/sse endpoint  │  ← FastAPI route on :8100
                │  (SSE transport)    │
                └──────────┬──────────┘
                           │
                ┌──────────▼──────────┐
                │   MCP Server Core   │  ← mcp Python SDK
                │   (tool registry)   │
                │                     │
                │  tools/list → 15    │
                │  tools/call → route │
                │  resources/list     │
                │  prompts/list       │
                └──────────┬──────────┘
                           │ direct function calls (in-process)
                ┌──────────▼──────────┐
                │  Otto Memory API    │  ← existing FastAPI routes
                │  (60+ route files)  │
                │  PostgreSQL/Neo4j   │
                └─────────────────────┘
```

### Key Decisions

- **In-process vs separate service**: In-process (mounted on :8100). Because: no new port to manage, no new systemd unit, shares the asyncpg pool. Alternative: standalone service on :8101 — rejected because it adds operational complexity for zero architectural benefit.

- **`mcp` SDK vs raw SSE implementation**: `mcp` SDK (Anthropic's official Python package). Because: handles protocol negotiation, tool schema generation, and transport automatically. Alternative: hand-rolling SSE + JSON-RPC — rejected because it's 500+ lines of protocol code that the SDK already handles.

- **Which tools to expose**: Curated subset of 15 tools (see below), not all 60+ routes. Because: MCP clients get overwhelmed by large tool sets (same reason Tool RAG exists). Start small, expand based on demand. Alternative: expose everything — rejected because it creates noise and security surface.

- **Transport**: SSE over HTTP only (no stdio). Because: all target clients (Claude Desktop, Cursor, external agents) use HTTP. Otto is a remote server, not a local CLI tool. stdio would only serve local integrations that already have direct API access. Alternative: dual transport — rejected as unnecessary complexity.

- **Auth**: Bearer token via `X-MCP-Token` header, validated against a single shared secret stored in `~/memory/.env`. Because: simple, sufficient for the current trust model (Mev + Otto's own agents). Alternative: OAuth2 / API key per client — premature for current scale, easy to add later.

- **DB migration**: None needed. MCP tools call existing endpoints, no new tables.

### Tools to Externalize (Phase 1: 15 tools)

Organized by capability domain. Each tool wraps an existing route.

#### Memory (5 tools)
| MCP Tool | Wraps | Purpose |
|---|---|---|
| `semantic_search` | `POST /semantic/search` | Vector similarity search over Otto's knowledge |
| `semantic_remember` | `POST /semantic/remember` | Store a fact with embedding |
| `graph_search` | `POST /graph/search` | Knowledge graph query |
| `episodic_timeline` | `POST /episodic/timeline` | Query event history |
| `episodic_log` | `POST /episodic/events` | Log an event |

#### Tasks (4 tools)
| MCP Tool | Wraps | Purpose |
|---|---|---|
| `task_create` | `POST /tasks` | Create a task in the queue |
| `task_status` | `GET /tasks/{id}` | Get task status and output |
| `task_queue` | `GET /tasks/queue/status` | Queue summary |
| `task_plan_create` | `POST /task-plans` | Create a DAG plan |

#### Communication (2 tools)
| MCP Tool | Wraps | Purpose |
|---|---|---|
| `whatsapp_send` | `POST /whatsapp/send` | Send WhatsApp message (Mev only) |
| `email_send` | `POST /email/send` | Send email via Zoho |

#### System (2 tools)
| MCP Tool | Wraps | Purpose |
|---|---|---|
| `health` | `GET /health` | System health check |
| `kernel_status` | `GET /kernel/status` | Kernel state, queue depth, drift |

#### Content (2 tools)
| MCP Tool | Wraps | Purpose |
|---|---|---|
| `skill_suggest` | `GET /skills/suggest` | Tool RAG — find relevant skills for a task |
| `workflow_start` | `POST /workflows/start` | Start a multi-agent workflow |

### MCP Resources (read-only context)

MCP resources provide contextual data that clients can read but not modify.

| Resource URI | Source | Content |
|---|---|---|
| `otto://context/briefing` | `POST /context/briefing` | Full context aggregation |
| `otto://identity/constitution` | `~/otto/CONSTITUTION.md` | Otto's identity spec |
| `otto://identity/personality` | `~/otto/otto_core/personality.md` | Voice and tone |
| `otto://tasks/queue` | `GET /tasks/queue/status` | Current queue state |

### MCP Prompts (reusable prompt templates)

| Prompt Name | Purpose |
|---|---|
| `research_task` | Template for creating a research task with proper structure |
| `content_pipeline` | Template for starting a content publishing workflow |
| `bug_report` | Template for creating a debugging task from an error description |

### API / Interface

#### Server Setup (single file: `memory/mcp_server.py`)

```python
from mcp.server.fastmcp import FastMCP

mcp = FastMCP(
    "Otto Memory API",
    description="Otto's autonomous intelligence tools — memory, tasks, communication",
)

# Tool registration follows pattern:
@mcp.tool()
async def semantic_search(query: str, top_k: int = 5, category: str | None = None) -> str:
    """Search Otto's semantic memory for relevant facts and knowledge."""
    # Calls existing route logic directly (in-process)
    ...
```

#### Mount on existing FastAPI app (`api.py`)

```python
from .mcp_server import mcp
from mcp.server.sse import SseServerTransport

# Mount SSE transport at /mcp/sse
sse = SseServerTransport("/mcp/messages/")
app.mount("/mcp/sse", sse.handle_sse)
app.mount("/mcp/messages/", sse.handle_post_message)
```

#### Client Configuration (Claude Desktop example)

```json
{
  "mcpServers": {
    "otto": {
      "transport": "sse",
      "url": "http://otto-machine:8100/mcp/sse",
      "headers": {
        "X-MCP-Token": "{{OTTO_MCP_TOKEN}}"
      }
    }
  }
}
```

### Data Flow

```
1. Client connects → GET /mcp/sse (SSE stream opens)
2. Client sends → POST /mcp/messages/ (JSON-RPC request)
3. MCP Server receives → validates auth token
4. tools/list → returns 15 tool schemas with descriptions
5. tools/call → routes to handler function
6. Handler → calls existing route logic (asyncpg pool, no HTTP hop)
7. Response → JSON-RPC result → SSE event → client
```

### File Structure

```
otto/memory/
├── mcp_server.py          # MCP server definition + all tool handlers (~200 lines)
├── mcp_auth.py            # Bearer token middleware (~30 lines)
└── api.py                 # Add 4 lines: import + mount SSE endpoints
```

Total new code: ~250 lines across 2 new files + 4 lines in api.py.

### Implementation Plan

#### Phase 1: Core MCP Server (~$3-4)

1. **Install `mcp` SDK**: `pip install mcp` in the Memory API venv
2. **Create `mcp_server.py`**: Define FastMCP instance + 15 tool handlers
3. **Create `mcp_auth.py`**: Bearer token validation middleware
4. **Mount in `api.py`**: Add SSE transport endpoints
5. **Add `OTTO_MCP_TOKEN` to `~/memory/.env`**: Generate random 32-byte hex token
6. **Test**: `curl` against `/mcp/sse` to verify SSE stream, then use MCP Inspector (`npx @modelcontextprotocol/inspector`)
7. **Restart otto-memory**: `sudo systemctl restart otto-memory`

#### Phase 2: Resources + Prompts (~$1-2)

8. **Add 4 MCP resources**: context briefing, constitution, personality, queue state
9. **Add 3 MCP prompts**: research_task, content_pipeline, bug_report
10. **Test with Claude Desktop**: Configure MCP client and verify tool discovery

#### Phase 3: Dynamic Registration (~$2-3, future)

11. **DB-backed tool registry**: Migrate from `SKILL_REGISTRY` list to a `mcp_tools` table
12. **Hot-reload**: New tools register via API without service restart
13. **Auto-sync**: When a new agent is activated (agent auto-employment), auto-register its MCP tool

### Constraints & Guardrails

- **No new port**: MCP shares :8100 with the Memory API
- **No new process**: In-process, shares the asyncpg pool
- **No new DB tables** (Phase 1): Tool definitions live in code
- **Auth required**: Every MCP request validates the bearer token
- **Rate limited**: Inherits the existing SlowAPI rate limiter on :8100
- **WhatsApp guard**: `whatsapp_send` tool validates recipient = Mev only (existing guard)
- **Read-before-write**: Tools that modify state (task_create, semantic_remember) log to episodic memory for audit trail

### Relationship to Other STEM Gaps

| Gap | Depends on MCP? | Notes |
|---|---|---|
| Dynamic Tool Composition | **Yes** — prerequisite | Composition needs introspectable tool schemas. MCP provides these. |
| Caller Profiler | No | Independent — tracks Mev behavioral dims |
| Skills Maturation | Partially | Crystallized skills could auto-register as MCP tools (Phase 3) |
| A2A Protocol | Partially | Agent-to-agent comms could use MCP as transport (future) |

### Risks

- **SDK stability**: `mcp` Python SDK is pre-1.0 (rapid iteration). Mitigation: pin version, wrap SDK calls in try/except so failures don't crash the Memory API.
- **SSE connection management**: Long-lived SSE connections consume memory. Mitigation: set 30-minute idle timeout, limit to 10 concurrent SSE connections via SlowAPI.
- **Tool surface security**: Exposing task creation and WhatsApp to external clients. Mitigation: bearer token auth + per-tool permission checks (Phase 2 can add scoped tokens if needed).
- **Context window inflation**: MCP tool schemas add to client context. Mitigation: curated 15-tool set (not all 60+ routes). Tool RAG remains the internal routing mechanism.

### Success Criteria

1. `npx @modelcontextprotocol/inspector sse http://localhost:8100/mcp/sse` shows 15 tools
2. Claude Desktop can connect and call `semantic_search` successfully
3. No regression on existing Memory API endpoints (all route tests pass)
4. Zero additional systemd services or Docker containers
5. Memory API startup time increases by <500ms

### Cost Estimate

- Phase 1: ~$3-4 (single task, coder agent)
- Phase 2: ~$1-2 (single task)
- Phase 3: ~$2-3 (future, when dynamic registration is needed)
- Total: ~$6-9 across all phases
