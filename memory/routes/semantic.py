from fastapi import APIRouter
from ..db import get_pool
from ..embeddings import get_embedding
from ..models import SemanticMemoryCreate, SemanticMemoryOut, SemanticSearchQuery

router = APIRouter(prefix="/semantic", tags=["semantic"])


@router.post("/remember", response_model=SemanticMemoryOut)
async def remember(req: SemanticMemoryCreate):
    embedding = await get_embedding(req.content)
    embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"

    pool = await get_pool()
    row = await pool.fetchrow(
        """INSERT INTO semantic_memories (content, category, confidence, source, embedding, embedding_hv, metadata)
           VALUES ($1, $2, $3, $4, $5::vector, $5::halfvec(1536), $6)
           RETURNING id, content, category, confidence, source, created_at""",
        req.content, req.category, req.confidence, req.source,
        embedding_str, req.metadata,
    )
    return SemanticMemoryOut(**dict(row))


@router.post("/search", response_model=list[SemanticMemoryOut])
async def search(req: SemanticSearchQuery):
    query_embedding = await get_embedding(req.query)
    embedding_str = "[" + ",".join(str(x) for x in query_embedding) + "]"

    pool = await get_pool()

    # Build dynamic WHERE clause
    conditions = []
    params: list = [embedding_str]
    idx = 2

    if req.min_confidence > 0:
        conditions.append(f"confidence >= ${idx}")
        params.append(req.min_confidence)
        idx += 1

    if req.category:
        conditions.append(f"category = ${idx}")
        params.append(req.category)
        idx += 1

    where = (" AND " + " AND ".join(conditions)) if conditions else ""
    params.append(req.limit)

    async with pool.acquire() as conn:
        # Enable iterative HNSW scan so WHERE-clause filtering doesn't over-skip candidates
        if conditions:
            await conn.execute("SET hnsw.iterative_scan = relaxed_order")
        rows = await conn.fetch(
            f"""SELECT id, content, category, confidence, source, created_at,
                       1 - (embedding_hv <=> $1::halfvec(1536)) AS score
                FROM semantic_memories
                WHERE embedding_hv IS NOT NULL{where}
                ORDER BY embedding_hv <=> $1::halfvec(1536)
                LIMIT ${idx}""",
            *params,
        )

        return [SemanticMemoryOut(**{**dict(r), "score": r["score"]}) for r in rows]
