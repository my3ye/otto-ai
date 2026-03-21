import json
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException
from ..db import get_pool
from ..embeddings import get_embedding
from ..models import (
    SemanticMemoryCreate,
    SemanticMemoryOut,
    SemanticSearchQuery,
)

router = APIRouter(prefix="/semantic", tags=["semantic"])


@router.post("/remember", response_model=SemanticMemoryOut)
async def remember(req: SemanticMemoryCreate):
    """Store a memory with semantic embedding for later retrieval.

    The content is embedded using OpenAI text-embedding-3-small and stored
    alongside the raw text for vector similarity search.
    """
    pool = await get_pool()
    embedding = await get_embedding(req.content)
    embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"
    meta_str = json.dumps(req.metadata) if req.metadata else None

    row = await pool.fetchrow(
        """INSERT INTO semantic_memories
               (content, category, confidence, source, embedding, metadata)
           VALUES ($1, $2, $3, $4, $5::text::vector, $6::jsonb)
           RETURNING id, content, category, confidence, source, created_at""",
        req.content,
        req.category or "general",
        req.confidence or 0.8,
        req.source,
        embedding_str,
        meta_str,
    )
    return SemanticMemoryOut(**dict(row))


@router.post("/search", response_model=list[SemanticMemoryOut])
async def search(req: SemanticSearchQuery):
    """Search semantic memories by vector similarity.

    Returns the most relevant memories for the given query, ranked by
    cosine similarity of their embeddings.
    """
    pool = await get_pool()
    embedding = await get_embedding(req.query)
    embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"

    conditions = ["archived = FALSE", "deleted_at IS NULL"]
    params: list = [embedding_str, req.limit or 10]
    idx = 3

    if req.min_confidence and req.min_confidence > 0:
        conditions.append(f"confidence >= ${idx}")
        params.append(req.min_confidence)
        idx += 1

    if req.category:
        conditions.append(f"category = ${idx}")
        params.append(req.category)
        idx += 1

    where = " AND ".join(conditions)

    rows = await pool.fetch(
        f"""SELECT id, content, category, confidence, source, created_at,
                   1 - (embedding <=> $1::text::vector) AS relevance
            FROM semantic_memories
            WHERE {where}
            ORDER BY embedding <=> $1::text::vector
            LIMIT $2""",
        *params,
    )
    return [SemanticMemoryOut(**dict(r)) for r in rows]


@router.post("/forget/{memory_id}")
async def forget(memory_id: str):
    """Archive a memory so it no longer appears in search results."""
    pool = await get_pool()
    result = await pool.execute(
        "UPDATE semantic_memories SET archived = TRUE, deleted_at = NOW() WHERE id = $1",
        memory_id,
    )
    if result == "UPDATE 0":
        raise HTTPException(status_code=404, detail="Memory not found")
    return {"status": "archived", "id": memory_id}
