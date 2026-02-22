from datetime import datetime
from uuid import UUID
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from typing import Optional
from ..db import get_pool

router = APIRouter(prefix="/working", tags=["working-memory"])


class CoreMemorySlot(BaseModel):
    id: UUID
    slot: str
    content: str
    max_tokens: int
    priority: int
    protected: bool
    updated_at: datetime


class CoreMemoryUpdate(BaseModel):
    content: str


@router.get("/memory", response_model=list[CoreMemorySlot])
async def get_working_memory():
    """Return all core memory slots, ordered by priority descending."""
    pool = await get_pool()
    rows = await pool.fetch(
        "SELECT id, slot, content, max_tokens, priority, protected, updated_at "
        "FROM core_memory ORDER BY priority DESC"
    )
    return [CoreMemorySlot(**dict(r)) for r in rows]


@router.put("/memory/{slot}", response_model=CoreMemorySlot)
async def update_working_memory(
    slot: str,
    body: CoreMemoryUpdate,
    x_caller: Optional[str] = Header(default=None),
):
    """Upsert a core memory slot. Protected slots (like purpose) can only be
    updated by Admin (x-caller: admin) or manual intervention."""
    pool = await get_pool()

    # Check if slot is protected
    existing = await pool.fetchrow(
        "SELECT protected FROM core_memory WHERE slot = $1", slot
    )
    if existing and existing["protected"] and x_caller != "admin":
        raise HTTPException(
            status_code=403,
            detail=f"Slot '{slot}' is protected. Only Admin can update it. "
                   f"Send header 'X-Caller: admin' to override.",
        )

    row = await pool.fetchrow(
        """INSERT INTO core_memory (slot, content, updated_at)
           VALUES ($1, $2, now())
           ON CONFLICT (slot) DO UPDATE
               SET content = EXCLUDED.content,
                   updated_at = now()
           RETURNING id, slot, content, max_tokens, priority, protected, updated_at""",
        slot, body.content,
    )
    if not row:
        raise HTTPException(status_code=500, detail="Upsert failed")
    return CoreMemorySlot(**dict(row))


@router.delete("/memory/{slot_id}")
async def delete_working_memory_slot(slot_id: UUID):
    """Delete a core memory slot by ID. Cannot delete protected slots."""
    pool = await get_pool()
    existing = await pool.fetchrow(
        "SELECT protected, slot FROM core_memory WHERE id = $1", slot_id
    )
    if not existing:
        raise HTTPException(status_code=404, detail="Slot not found")
    if existing["protected"]:
        raise HTTPException(
            status_code=403,
            detail=f"Slot '{existing['slot']}' is protected and cannot be deleted.",
        )
    await pool.execute("DELETE FROM core_memory WHERE id = $1", slot_id)
    return {"deleted": str(slot_id), "slot": existing["slot"]}


@router.post("/memory/{slot}/append", response_model=CoreMemorySlot)
async def append_working_memory(
    slot: str,
    body: CoreMemoryUpdate,
    x_caller: Optional[str] = Header(default=None),
):
    """Append text to an existing slot (creates slot if missing).
    Protected slots require X-Caller: admin header."""
    pool = await get_pool()

    existing = await pool.fetchrow(
        "SELECT protected FROM core_memory WHERE slot = $1", slot
    )
    if existing and existing["protected"] and x_caller != "admin":
        raise HTTPException(
            status_code=403,
            detail=f"Slot '{slot}' is protected. Only Admin can modify it.",
        )

    row = await pool.fetchrow(
        """INSERT INTO core_memory (slot, content, updated_at)
           VALUES ($1, $2, now())
           ON CONFLICT (slot) DO UPDATE
               SET content = core_memory.content || ' ' || EXCLUDED.content,
                   updated_at = now()
           RETURNING id, slot, content, max_tokens, priority, protected, updated_at""",
        slot, body.content,
    )
    if not row:
        raise HTTPException(status_code=500, detail="Append failed")
    return CoreMemorySlot(**dict(row))


@router.get("/directives")
async def get_active_directives():
    """Return active mission directives ordered by priority."""
    pool = await get_pool()
    rows = await pool.fetch(
        """SELECT id, directive, priority, category, status, source, created_at, notes
           FROM mission_directives
           WHERE status = 'active'
           ORDER BY priority DESC, created_at ASC"""
    )
    return [dict(r) for r in rows]


@router.post("/directives")
async def add_directive(directive: str, priority: int = 5, category: str = "general", source: str = "whatsapp"):
    """Add a new mission directive from Mev."""
    pool = await get_pool()
    row = await pool.fetchrow(
        """INSERT INTO mission_directives (directive, priority, category, source)
           VALUES ($1, $2, $3, $4)
           RETURNING id, directive, priority, category, status, source, created_at""",
        directive, priority, category, source,
    )
    return dict(row)
