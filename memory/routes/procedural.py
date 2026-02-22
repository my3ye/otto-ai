import asyncio
import json
import logging

from fastapi import APIRouter, HTTPException, Query
from ..db import get_pool
from ..models import ProcedureCreate, ProcedureOut, ProcedureOutcome
from ..config import settings

log = logging.getLogger("otto.procedural")
router = APIRouter(prefix="/procedural", tags=["procedural"])

# TAME executor memory: trust_score delta per outcome
# On success: trust_score += DELTA * (1 - trust_score)  — bounded EMA-style increase
# On failure: trust_score -= DELTA * trust_score         — bounded EMA-style decrease
_TRUST_DELTA = 0.1

SELECT_COLS = """id, name, description, steps, success_count, failure_count,
                 trust_score, last_used, created_at"""


@router.post("", response_model=ProcedureOut)
async def create_procedure(req: ProcedureCreate):
    pool = await get_pool()
    row = await pool.fetchrow(
        f"""INSERT INTO procedures (name, description, steps)
           VALUES ($1, $2, $3)
           ON CONFLICT (name) DO UPDATE
           SET description = EXCLUDED.description, steps = EXCLUDED.steps, updated_at = now()
           RETURNING {SELECT_COLS}""",
        req.name, req.description, req.steps,
    )
    return ProcedureOut(**dict(row))


@router.put("/{name}/outcome", response_model=ProcedureOut)
async def record_outcome(name: str, req: ProcedureOutcome):
    """Record success or failure and update trust_score via bounded EMA.

    TAME executor memory update rule:
    - Success: trust_score += 0.1 * (1 - trust_score)  → bounded push toward 1.0
    - Failure: trust_score -= 0.1 * trust_score          → bounded push toward 0.0
    """
    pool = await get_pool()
    col = "success_count" if req.success else "failure_count"

    if req.success:
        trust_update = f"trust_score + {_TRUST_DELTA} * (1.0 - trust_score)"
    else:
        trust_update = f"trust_score - {_TRUST_DELTA} * trust_score"

    row = await pool.fetchrow(
        f"""UPDATE procedures
            SET {col} = {col} + 1,
                trust_score = GREATEST(0.0, LEAST(1.0, {trust_update})),
                last_used = now(), updated_at = now()
            WHERE name = $1
            RETURNING {SELECT_COLS}""",
        name,
    )
    if row is None:
        raise HTTPException(status_code=404, detail=f"Procedure '{name}' not found")
    return ProcedureOut(**dict(row))


@router.get("/suggest", response_model=list[ProcedureOut])
async def suggest_procedures(
    task_description: str = Query(..., description="Task description to match against existing procedures"),
):
    """Return up to 3 most relevant procedures for the given task description.

    Uses Gemini Flash to rank procedures by semantic relevance.
    Falls back to returning the top 3 by trust_score if Gemini is unavailable.
    """
    pool = await get_pool()
    rows = await pool.fetch(
        f"""SELECT {SELECT_COLS}
           FROM procedures ORDER BY trust_score DESC, success_count DESC, created_at DESC""",
    )
    if not rows:
        return []

    procedures = [dict(r) for r in rows]

    # Primary path: trust_score-based top 3 (no external API dependency)
    # This ensures suggest always works even when Gemini is down
    trust_based = [ProcedureOut(**p) for p in procedures[:3]]

    if not settings.gemini_api_key or len(procedures) <= 3:
        return trust_based

    # Optional: use Gemini for smarter semantic ranking
    proc_lines = "\n".join(
        f"{i+1}. name={p['name']}: {p['description'] or 'no description'} (trust={p['trust_score']:.2f})"
        for i, p in enumerate(procedures)
    )

    gemini_prompt = (
        f"Given this task description:\n\"{task_description}\"\n\n"
        f"Which of these existing procedures are most relevant and useful?\n{proc_lines}\n\n"
        "Return ONLY a JSON array of up to 3 procedure names that are genuinely relevant "
        "(no markdown, no code fences). Example: [\"name1\", \"name2\"]. "
        "Return [] if none are relevant."
    )

    top_names: list[str] = []
    try:
        import google.generativeai as genai
        genai.configure(api_key=settings.gemini_api_key)
        model = genai.GenerativeModel(
            "gemini-2.0-flash",
            generation_config={"temperature": 0.0},
        )
        response = await asyncio.to_thread(model.generate_content, gemini_prompt)
        text = response.text.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        parsed = json.loads(text)
        if isinstance(parsed, list):
            top_names = [str(n) for n in parsed[:3]]
    except Exception as e:
        log.warning(f"Gemini ranking failed for suggest (using trust_score fallback): {e}")
        return trust_based

    # Map names back to full procedure objects
    proc_by_name = {p["name"]: p for p in procedures}
    result = []
    for name in top_names:
        if name in proc_by_name:
            result.append(ProcedureOut(**proc_by_name[name]))

    return result if result else trust_based


@router.get("", response_model=list[ProcedureOut])
async def list_procedures():
    """List all procedures sorted by trust_score (TAME executor memory ranking)."""
    pool = await get_pool()
    rows = await pool.fetch(
        f"""SELECT {SELECT_COLS}
           FROM procedures ORDER BY trust_score DESC, last_used DESC NULLS LAST""",
    )
    return [ProcedureOut(**dict(r)) for r in rows]
