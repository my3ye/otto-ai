from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException
from ..db import get_pool
from ..models import ProcedureCreate, ProcedureOut, ProcedureOutcome

router = APIRouter(prefix="/procedural", tags=["procedural"])


@router.post("", response_model=ProcedureOut)
async def create_procedure(req: ProcedureCreate):
    """Create a procedural memory — a named sequence of steps your agent has learned.

    Procedures accumulate a trust score based on success/failure outcomes.
    High-trust procedures are surfaced preferentially when agents plan similar tasks.
    """
    pool = await get_pool()
    import json
    steps_json = json.dumps(req.steps)

    row = await pool.fetchrow(
        """INSERT INTO procedural_memories
               (name, description, steps, category, trust_score, use_count, success_count)
           VALUES ($1, $2, $3::jsonb, $4, 0.5, 0, 0)
           RETURNING id, name, description, steps, category, trust_score, use_count, success_count, created_at""",
        req.name,
        req.description,
        steps_json,
        req.category or "general",
    )
    return ProcedureOut(**dict(row))


@router.get("", response_model=list[ProcedureOut])
async def list_procedures(category: str = None, limit: int = 20):
    """List procedures, optionally filtered by category. Ordered by trust score."""
    pool = await get_pool()

    if category:
        rows = await pool.fetch(
            """SELECT id, name, description, steps, category, trust_score, use_count, success_count, created_at
               FROM procedural_memories
               WHERE category = $1
               ORDER BY trust_score DESC
               LIMIT $2""",
            category, limit,
        )
    else:
        rows = await pool.fetch(
            """SELECT id, name, description, steps, category, trust_score, use_count, success_count, created_at
               FROM procedural_memories
               ORDER BY trust_score DESC
               LIMIT $1""",
            limit,
        )
    return [ProcedureOut(**dict(r)) for r in rows]


@router.put("/{name}/outcome")
async def record_outcome(name: str, req: ProcedureOutcome):
    """Record a success or failure for a procedure.

    Updates the trust score using exponential moving average:
    - Success nudges score toward 1.0
    - Failure nudges score toward 0.0

    Returns the updated trust score.
    """
    pool = await get_pool()

    row = await pool.fetchrow(
        "SELECT id, trust_score, use_count, success_count FROM procedural_memories WHERE name = $1",
        name,
    )
    if not row:
        raise HTTPException(status_code=404, detail=f"Procedure '{name}' not found")

    new_use_count = row["use_count"] + 1
    new_success_count = row["success_count"] + (1 if req.success else 0)

    # Exponential moving average: alpha=0.1, bias toward recent outcomes
    alpha = 0.1
    outcome_val = 1.0 if req.success else 0.0
    new_trust = row["trust_score"] * (1 - alpha) + outcome_val * alpha

    await pool.execute(
        """UPDATE procedural_memories
           SET trust_score = $1, use_count = $2, success_count = $3
           WHERE name = $4""",
        new_trust, new_use_count, new_success_count, name,
    )

    return {
        "name": name,
        "success": req.success,
        "trust_score": round(new_trust, 4),
        "use_count": new_use_count,
    }
