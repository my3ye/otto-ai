---
name: MCP Externalization Architecture
description: MCP server design for Otto — in-process on :8100, SSE transport, 15 curated tools wrapping existing routes. Phase 1 ~$3-4, no migration.
type: project
---

MCP Externalization designed (2026-03-28). In-process FastMCP server mounted on existing :8100 Memory API. SSE transport only (no stdio — Otto is remote server). 15 curated tools across 5 domains: Memory (5), Tasks (4), Communication (2), System (2), Content (2). Bearer token auth. No new DB tables in Phase 1. ~250 lines new code (mcp_server.py + mcp_auth.py + 4 lines in api.py).

**Why:** STEM Agent gap analysis identified FULL GAP — static skill registry blocks external interop, dynamic discovery, and cross-system composition. TrustGraph synthesis confirmed MCP as the missing interface layer.

**How to apply:** Phase 1 prerequisite for Dynamic Tool Composition (separate gap). When implementing, use `mcp` Python SDK (Anthropic official), pin version, wrap in try/except to prevent Memory API crashes. Full spec at ~/otto/docs/arch-mcp-externalization.md.
