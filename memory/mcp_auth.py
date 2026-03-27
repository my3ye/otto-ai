"""MCP bearer-token authentication middleware.

Validates X-MCP-Token header against settings.mcp_token.
Skips auth if mcp_token is empty (dev mode).
"""

import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

logger = logging.getLogger("otto.mcp.auth")


class MCPAuthMiddleware(BaseHTTPMiddleware):
    """Validates bearer token on /mcp/* routes only."""

    def __init__(self, app, token: str):
        super().__init__(app)
        self.token = token

    async def dispatch(self, request: Request, call_next):
        # Only guard MCP endpoints
        if not request.url.path.startswith("/mcp"):
            return await call_next(request)

        # Dev mode: no auth if token is empty
        if not self.token:
            return await call_next(request)

        # Validate token from header
        provided = request.headers.get("X-MCP-Token", "")
        if provided != self.token:
            logger.warning(f"MCP auth failed from {request.client.host if request.client else 'unknown'}")
            return JSONResponse({"error": "Invalid or missing MCP token"}, status_code=401)

        return await call_next(request)
