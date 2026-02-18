"""
Research API routes — papers and notes storage/retrieval.
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from ..db import get_pool

router = APIRouter(prefix="/research", tags=["research"])


# --- Models ---

class PaperCreate(BaseModel):
    title: str
    arxiv_id: Optional[str] = None
    authors: Optional[str] = None
    abstract: Optional[str] = None
    tags: Optional[List[str]] = None
    relevance_notes: Optional[str] = None
    source_url: Optional[str] = None
    local_pdf_path: Optional[str] = None
    added_by: str = "otto"


class NoteCreate(BaseModel):
    topic: str
    title: str
    content: str
    action_items: Optional[List[str]] = None
    paper_ids: Optional[List[str]] = None
    importance: int = 5
    implemented: bool = False


class NoteUpdate(BaseModel):
    content: Optional[str] = None
    action_items: Optional[List[str]] = None
    importance: Optional[int] = None
    implemented: Optional[bool] = None


# --- Papers ---

@router.get("/papers")
async def list_papers(tag: Optional[str] = None):
    """List all research papers, optionally filtered by tag."""
    pool = await get_pool()
    if tag:
        rows = await pool.fetch(
            "SELECT * FROM research_papers WHERE $1 = ANY(tags) ORDER BY added_at DESC",
            tag
        )
    else:
        rows = await pool.fetch("SELECT * FROM research_papers ORDER BY added_at DESC")
    return [dict(r) for r in rows]


@router.post("/papers", status_code=201)
async def add_paper(paper: PaperCreate):
    """Add a new research paper."""
    pool = await get_pool()
    row = await pool.fetchrow(
        """
        INSERT INTO research_papers
            (title, arxiv_id, authors, abstract, tags, relevance_notes, source_url, local_pdf_path, added_by)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
        ON CONFLICT (arxiv_id) DO UPDATE SET
            title = EXCLUDED.title,
            authors = EXCLUDED.authors,
            abstract = EXCLUDED.abstract,
            tags = EXCLUDED.tags,
            relevance_notes = EXCLUDED.relevance_notes,
            source_url = EXCLUDED.source_url,
            local_pdf_path = EXCLUDED.local_pdf_path
        RETURNING *
        """,
        paper.title, paper.arxiv_id, paper.authors, paper.abstract,
        paper.tags or [], paper.relevance_notes, paper.source_url,
        paper.local_pdf_path, paper.added_by
    )
    return dict(row)


@router.get("/papers/{paper_id}")
async def get_paper(paper_id: str):
    """Get a single paper by UUID or arxiv_id."""
    pool = await get_pool()
    row = await pool.fetchrow(
        "SELECT * FROM research_papers WHERE id = $1::uuid OR arxiv_id = $1",
        paper_id
    )
    if not row:
        raise HTTPException(status_code=404, detail="Paper not found")
    return dict(row)


# --- Notes ---

@router.get("/notes")
async def list_notes(topic: Optional[str] = None, unimplemented_only: bool = False):
    """List research notes, optionally filtered by topic or implementation status."""
    pool = await get_pool()
    conditions = []
    params = []
    if topic:
        params.append(topic)
        conditions.append(f"topic = ${len(params)}")
    if unimplemented_only:
        conditions.append("implemented = false")
    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    rows = await pool.fetch(
        f"SELECT * FROM research_notes {where} ORDER BY importance DESC, created_at DESC",
        *params
    )
    return [dict(r) for r in rows]


@router.post("/notes", status_code=201)
async def add_note(note: NoteCreate):
    """Add a new research note."""
    pool = await get_pool()
    paper_ids = [str(p) for p in (note.paper_ids or [])]
    row = await pool.fetchrow(
        """
        INSERT INTO research_notes
            (topic, title, content, action_items, paper_ids, importance, implemented)
        VALUES ($1, $2, $3, $4, $5::uuid[], $6, $7)
        RETURNING *
        """,
        note.topic, note.title, note.content,
        note.action_items or [], paper_ids,
        note.importance, note.implemented
    )
    return dict(row)


@router.get("/notes/{note_id}")
async def get_note(note_id: str):
    """Get a single research note by UUID."""
    pool = await get_pool()
    row = await pool.fetchrow("SELECT * FROM research_notes WHERE id = $1::uuid", note_id)
    if not row:
        raise HTTPException(status_code=404, detail="Note not found")
    return dict(row)


@router.patch("/notes/{note_id}")
async def update_note(note_id: str, update: NoteUpdate):
    """Update a research note (mark implemented, update content, etc.)."""
    pool = await get_pool()
    fields = []
    params = []
    if update.content is not None:
        params.append(update.content)
        fields.append(f"content = ${len(params)}")
    if update.action_items is not None:
        params.append(update.action_items)
        fields.append(f"action_items = ${len(params)}")
    if update.importance is not None:
        params.append(update.importance)
        fields.append(f"importance = ${len(params)}")
    if update.implemented is not None:
        params.append(update.implemented)
        fields.append(f"implemented = ${len(params)}")
    if not fields:
        raise HTTPException(status_code=400, detail="No fields to update")
    params.append(note_id)
    row = await pool.fetchrow(
        f"UPDATE research_notes SET {', '.join(fields)} WHERE id = ${len(params)}::uuid RETURNING *",
        *params
    )
    if not row:
        raise HTTPException(status_code=404, detail="Note not found")
    return dict(row)


# --- Stats ---

@router.get("/stats")
async def research_stats():
    """Summary of research DB."""
    pool = await get_pool()
    papers = await pool.fetchrow("SELECT COUNT(*) as total FROM research_papers")
    notes = await pool.fetchrow(
        "SELECT COUNT(*) as total, COUNT(*) FILTER (WHERE implemented) as implemented FROM research_notes"
    )
    top_notes = await pool.fetch(
        "SELECT id, topic, title, importance, implemented FROM research_notes ORDER BY importance DESC LIMIT 5"
    )
    return {
        "papers": papers["total"],
        "notes": {
            "total": notes["total"],
            "implemented": notes["implemented"],
            "pending": notes["total"] - notes["implemented"],
        },
        "top_priority_notes": [dict(r) for r in top_notes],
    }
