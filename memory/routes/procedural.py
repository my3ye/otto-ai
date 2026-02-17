from fastapi import APIRouter, HTTPException
from ..db import get_pool
from ..models import ProcedureCreate, ProcedureOut, ProcedureOutcome

router = APIRouter(prefix="/procedural", tags=["procedural"])


@router.post("", response_model=ProcedureOut)
async def create_procedure(req: ProcedureCreate):
    pool = await get_pool()
    row = await pool.fetchrow(
        """INSERT INTO procedures (name, description, steps)
           VALUES ($1, $2, $3)
           ON CONFLICT (name) DO UPDATE
           SET description = EXCLUDED.description, steps = EXCLUDED.steps, updated_at = now()
           RETURNING id, name, description, steps, success_count, failure_count, last_used, created_at""",
        req.name, req.description, req.steps,
    )
    return ProcedureOut(**dict(row))


@router.put("/{name}/outcome", response_model=ProcedureOut)
async def record_outcome(name: str, req: ProcedureOutcome):
    pool = await get_pool()
    col = "success_count" if req.success else "failure_count"
    row = await pool.fetchrow(
        f"""UPDATE procedures
            SET {col} = {col} + 1, last_used = now(), updated_at = now()
            WHERE name = $1
            RETURNING id, name, description, steps, success_count, failure_count, last_used, created_at""",
        name,
    )
    if row is None:
        raise HTTPException(status_code=404, detail=f"Procedure '{name}' not found")
    return ProcedureOut(**dict(row))


@router.get("", response_model=list[ProcedureOut])
async def list_procedures():
    pool = await get_pool()
    rows = await pool.fetch(
        """SELECT id, name, description, steps, success_count, failure_count, last_used, created_at
           FROM procedures ORDER BY last_used DESC NULLS LAST""",
    )
    return [ProcedureOut(**dict(r)) for r in rows]
