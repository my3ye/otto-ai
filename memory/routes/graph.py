import httpx
from fastapi import APIRouter, Request, Response
from ..config import settings

router = APIRouter(prefix="/graph", tags=["graph"])


@router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy_graphiti(path: str, request: Request):
    """Proxy requests to the Graphiti API."""
    url = f"{settings.graphiti_url}/{path}"

    body = await request.body()
    headers = {
        k: v for k, v in request.headers.items()
        if k.lower() not in ("host", "content-length")
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.request(
            method=request.method,
            url=url,
            content=body,
            headers=headers,
            params=dict(request.query_params),
        )

    return Response(
        content=resp.content,
        status_code=resp.status_code,
        headers=dict(resp.headers),
    )
