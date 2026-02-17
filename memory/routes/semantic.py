from uuid import uuid4
from fastapi import APIRouter
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import PointStruct, Distance, VectorParams
from ..db import get_pool
from ..config import settings
from ..embeddings import get_embedding
from ..models import SemanticMemoryCreate, SemanticMemoryOut, SemanticSearchQuery

router = APIRouter(prefix="/semantic", tags=["semantic"])

COLLECTION = "semantic_memories"

_qdrant: AsyncQdrantClient | None = None


async def _get_qdrant() -> AsyncQdrantClient:
    global _qdrant
    if _qdrant is None:
        _qdrant = AsyncQdrantClient(
            url=f"http://{settings.qdrant_host}:{settings.qdrant_port}",
            api_key=settings.qdrant_api_key,
        )
        # Ensure collection exists
        collections = await _qdrant.get_collections()
        names = [c.name for c in collections.collections]
        if COLLECTION not in names:
            await _qdrant.create_collection(
                collection_name=COLLECTION,
                vectors_config=VectorParams(size=1536, distance=Distance.COSINE),
            )
    return _qdrant


@router.post("/remember", response_model=SemanticMemoryOut)
async def remember(req: SemanticMemoryCreate):
    embedding = await get_embedding(req.content)

    # Write to Postgres — pgvector expects a string like '[0.1, 0.2, ...]'
    embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"

    pool = await get_pool()
    row = await pool.fetchrow(
        """INSERT INTO semantic_memories (content, category, confidence, source, embedding, metadata)
           VALUES ($1, $2, $3, $4, $5::vector, $6)
           RETURNING id, content, category, confidence, source, created_at""",
        req.content, req.category, req.confidence, req.source,
        embedding_str, req.metadata,
    )
    mem = SemanticMemoryOut(**dict(row))

    # Write to Qdrant
    qdrant = await _get_qdrant()
    await qdrant.upsert(
        collection_name=COLLECTION,
        points=[PointStruct(
            id=str(mem.id),
            vector=embedding,
            payload={
                "content": req.content,
                "category": req.category,
                "confidence": req.confidence,
                "source": req.source,
                "postgres_id": str(mem.id),
            },
        )],
    )

    return mem


@router.post("/search", response_model=list[SemanticMemoryOut])
async def search(req: SemanticSearchQuery):
    query_embedding = await get_embedding(req.query)

    qdrant = await _get_qdrant()

    # Build filter conditions
    must = []
    if req.min_confidence > 0:
        must.append({"key": "confidence", "range": {"gte": req.min_confidence}})
    if req.category:
        must.append({"key": "category", "match": {"value": req.category}})

    results = await qdrant.search(
        collection_name=COLLECTION,
        query_vector=query_embedding,
        limit=req.limit,
        query_filter={"must": must} if must else None,
    )

    # Fetch full records from Postgres
    if not results:
        return []

    pool = await get_pool()
    ids = [r.payload["postgres_id"] for r in results]
    scores = {r.payload["postgres_id"]: r.score for r in results}

    rows = await pool.fetch(
        """SELECT id, content, category, confidence, source, created_at
           FROM semantic_memories WHERE id = ANY($1::uuid[])""",
        ids,
    )

    out = []
    for row in rows:
        mem = SemanticMemoryOut(**dict(row))
        mem.score = scores.get(str(mem.id))
        out.append(mem)

    # Sort by score descending
    out.sort(key=lambda m: m.score or 0, reverse=True)
    return out
