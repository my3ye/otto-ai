from datetime import datetime, timezone
from fastapi import APIRouter
from ..db import get_pool

router = APIRouter(tags=["health"])


@router.get("/health")
async def health():
    """System health check. Returns status of the API and database."""
    try:
        pool = await get_pool()
        await pool.fetchval("SELECT 1")
        db_status = "healthy"
    except Exception as e:
        db_status = f"error: {e}"

    return {
        "status": "ok" if db_status == "healthy" else "degraded",
        "db": db_status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
