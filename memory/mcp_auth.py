"""MCP bearer-token authentication middleware (pure ASGI).

Validates X-MCP-Token header against settings.mcp_token.
Skips auth if mcp_token is empty (dev mode).

Uses raw ASGI (not BaseHTTPMiddleware) to avoid breaking SSE streaming.
"""

import hmac
import json
import logging

logger = logging.getLogger("otto.mcp.auth")


class MCPAuthMiddleware:
    """Pure ASGI middleware — validates bearer token on all requests."""

    def __init__(self, app, token: str):
        self.app = app
        self.token = token

    async def __call__(self, scope, receive, send):
        # Only guard HTTP requests; let lifespan/websocket pass through
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Dev mode: no auth if token is empty
        if not self.token:
            await self.app(scope, receive, send)
            return

        # Extract X-MCP-Token from headers
        headers = dict(scope.get("headers", []))
        provided = headers.get(b"x-mcp-token", b"").decode("utf-8", errors="ignore")

        if not hmac.compare_digest(provided, self.token):
            client = scope.get("client", ("unknown", 0))
            logger.warning(f"MCP auth failed from {client[0]}")
            # Send 401 response directly
            body = json.dumps({"error": "Invalid or missing MCP token"}).encode()
            await send({
                "type": "http.response.start",
                "status": 401,
                "headers": [
                    [b"content-type", b"application/json"],
                    [b"content-length", str(len(body)).encode()],
                ],
            })
            await send({
                "type": "http.response.body",
                "body": body,
            })
            return

        await self.app(scope, receive, send)
