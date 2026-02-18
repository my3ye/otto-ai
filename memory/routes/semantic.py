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

    # Build dynamic WHERE clause — always exclude archived facts
    conditions = ["archived = FALSE"]
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

    where = " AND ".join(conditions)
    # Fetch 3x the requested limit for two-phase re-ranking, then trim
    fetch_limit = req.limit * 3
    params.append(fetch_limit)

    async with pool.acquire() as conn:
        # Enable iterative HNSW scan so WHERE-clause filtering doesn't over-skip candidates
        await conn.execute("SET hnsw.iterative_scan = relaxed_order")
        rows = await conn.fetch(
            f"""SELECT id, content, category, confidence, source, created_at,
                       utility_score, relevance_score,
                       1 - (embedding_hv <=> $1::halfvec(1536)) AS similarity
                FROM semantic_memories
                WHERE embedding_hv IS NOT NULL AND {where}
                ORDER BY embedding_hv <=> $1::halfvec(1536)
                LIMIT ${idx}""",
            *params,
        )

        # Phase 2: re-rank by combined score (similarity * utility * relevance), take top limit
        def combined_score(r):
            return float(r["similarity"]) * float(r["utility_score"]) * float(r["relevance_score"])

        ranked = sorted(rows, key=combined_score, reverse=True)[: req.limit]

        # Update last_retrieved_at and bump utility_score via EMA: Q += 0.1 * (1 - Q)
        ids = [r["id"] for r in ranked]
        if ids:
            await conn.execute(
                """UPDATE semantic_memories
                   SET last_retrieved_at = NOW(),
                       utility_score = LEAST(1.0, utility_score + 0.1 * (1.0 - utility_score))
                   WHERE id = ANY($1::uuid[])""",
                ids,
            )

        return [
            SemanticMemoryOut(**{**dict(r), "score": combined_score(r)})
            for r in ranked
        ]
