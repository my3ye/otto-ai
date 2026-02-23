"""CAT context workspace — inter-heartbeat scratch pad.

Implements the context-as-a-tool pattern from CAT (arXiv 2512.22087):
agents explicitly read/write a structured workspace to maintain continuity
across heartbeat cycles. Each named artifact (key) is a persistent note
the current heartbeat leaves for the next one.

Endpoints:
    POST /workspace/write       — upsert a named artifact
    GET  /workspace/read?key=   — retrieve one artifact by key
    GET  /workspace/list        — all artifacts (newest first)
    DELETE /workspace/clear     — wipe the entire workspace
"""

from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from ..db import get_pool

router = APIRouter(prefix="/workspace", tags=["workspace"])


# --- Models ---

class WorkspaceWrite(BaseModel):
    key: str
    value: str
    metadata: dict = {}


class WorkspaceItem(BaseModel):
    key: str
    value: str
    metadata: dict
    created_at: datetime
    updated_at: datetime


# --- Routes ---

@router.post("/write", response_model=WorkspaceItem, status_code=200)
async def write_artifact(body: WorkspaceWrite):
    """Upsert a named artifact into the workspace."""
    pool = await get_pool()
    row = await pool.fetchrow(
        """INSERT INTO context_workspace (key, value, metadata, updated_at)
           VALUES ($1, $2, $3, NOW())
           ON CONFLICT (key) DO UPDATE
               SET value = EXCLUDED.value,
                   metadata = EXCLUDED.metadata,
                   updated_at = NOW()
           RETURNING key, value, metadata, created_at, updated_at""",
        body.key,
        body.value,
        body.metadata,
    )
    return dict(row)


@router.get("/read", response_model=WorkspaceItem)
async def read_artifact(key: str = Query(..., description="Artifact key")):
    """Retrieve a single workspace artifact by key."""
    pool = await get_pool()
    row = await pool.fetchrow(
        "SELECT key, value, metadata, created_at, updated_at FROM context_workspace WHERE key = $1",
        key,
    )
    if not row:
        raise HTTPException(status_code=404, detail=f"No workspace artifact with key '{key}'")
    return dict(row)


@router.get("/list", response_model=list[WorkspaceItem])
async def list_artifacts(limit: int = Query(50, ge=1, le=200)):
    """List all workspace artifacts, newest first."""
    pool = await get_pool()
    rows = await pool.fetch(
        "SELECT key, value, metadata, created_at, updated_at FROM context_workspace ORDER BY updated_at DESC LIMIT $1",
        limit,
    )
    return [dict(r) for r in rows]


@router.delete("/clear", status_code=200)
async def clear_workspace():
    """Delete all workspace artifacts."""
    pool = await get_pool()
    result = await pool.execute("DELETE FROM context_workspace")
    # result is like "DELETE 5"
    count = int(result.split()[-1]) if result else 0
    return {"deleted": count, "message": "Workspace cleared"}
