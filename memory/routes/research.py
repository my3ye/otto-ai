"""
Research API routes — papers, notes, and triage scoring.

Paper triage system: every paper gets scored on 5 dimensions before
Otto decides whether to implement it. This prevents blind implementation
of every paper found in research sweeps.

Scoring dimensions (each 1-10):
  relevance:   Does this solve a problem Otto actually has RIGHT NOW?
  overlap:     How unique is this vs existing implementations? (10=novel, 1=redundant)
  impact:      How much would Otto improve if this shipped? (10=transformative, 1=marginal)
  complexity:  How hard to implement on our stack? (10=trivial, 1=needs new infra)
  futureproof: Fundamental technique or narrow hack? (10=foundational, 1=brittle)

Composite = impact(30%) + relevance(25%) + futureproof(20%) + overlap(15%) + complexity(10%)

Status flow: unscored → scored → implement|skip → implemented|superseded
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
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
    published_date: Optional[str] = None


class PaperScore(BaseModel):
    """Score a paper for implementation triage."""
    score_relevance: int = Field(ge=1, le=10, description="Solves a current Otto problem? (10=critical need)")
    score_overlap: int = Field(ge=1, le=10, description="Novel vs existing impls? (10=nothing like it, 1=already have this)")
    score_impact: int = Field(ge=1, le=10, description="How much would Otto improve? (10=transformative)")
    score_complexity: int = Field(ge=1, le=10, description="How hard to build? (10=easy, 1=needs new infra)")
    score_futureproof: int = Field(ge=1, le=10, description="Fundamental technique? (10=foundational, 1=brittle hack)")
    score_reasoning: str = Field(description="Why these scores — what does it overlap with, what problem it solves")
    overlaps_with: Optional[List[str]] = Field(default=None, description="arxiv_ids or impl names this overlaps")
    status: Optional[str] = Field(default="scored", description="scored|implement|skip")


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
async def list_papers(tag: Optional[str] = None, status: Optional[str] = None):
    """List all research papers, optionally filtered by tag or status."""
    pool = await get_pool()
    conditions = []
    params = []
    if tag:
        params.append(tag)
        conditions.append(f"${len(params)} = ANY(tags)")
    if status:
        params.append(status)
        conditions.append(f"status = ${len(params)}")
    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    rows = await pool.fetch(
        f"SELECT * FROM research_papers {where} ORDER BY composite_score DESC NULLS LAST, added_at DESC",
        *params
    )
    return [dict(r) for r in rows]


@router.post("/papers", status_code=201)
async def add_paper(paper: PaperCreate):
    """Add a new research paper."""
    pool = await get_pool()
    row = await pool.fetchrow(
        """
        INSERT INTO research_papers
            (title, arxiv_id, authors, abstract, tags, relevance_notes,
             source_url, local_pdf_path, added_by, published_date)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10::date)
        ON CONFLICT (arxiv_id) DO UPDATE SET
            title = EXCLUDED.title,
            authors = EXCLUDED.authors,
            abstract = EXCLUDED.abstract,
            tags = EXCLUDED.tags,
            relevance_notes = EXCLUDED.relevance_notes,
            source_url = EXCLUDED.source_url,
            local_pdf_path = EXCLUDED.local_pdf_path,
            published_date = COALESCE(EXCLUDED.published_date, research_papers.published_date)
        RETURNING *
        """,
        paper.title, paper.arxiv_id, paper.authors, paper.abstract,
        paper.tags or [], paper.relevance_notes, paper.source_url,
        paper.local_pdf_path, paper.added_by, paper.published_date
    )
    return dict(row)


@router.get("/papers/{paper_id}")
async def get_paper(paper_id: str):
    """Get a single paper by UUID or arxiv_id."""
    pool = await get_pool()
    row = await pool.fetchrow(
        "SELECT * FROM research_papers WHERE id::text = $1 OR arxiv_id = $1",
        paper_id
    )
    if not row:
        raise HTTPException(status_code=404, detail="Paper not found")
    return dict(row)


# --- Triage Scoring ---

@router.put("/papers/{paper_id}/score")
async def score_paper(paper_id: str, score: PaperScore):
    """Score a paper for implementation triage. Composite score computed automatically."""
    pool = await get_pool()
    status = score.status or "scored"
    if status not in ("scored", "implement", "skip"):
        raise HTTPException(status_code=400, detail="status must be scored|implement|skip")

    row = await pool.fetchrow(
        """
        UPDATE research_papers SET
            score_relevance = $2,
            score_overlap = $3,
            score_impact = $4,
            score_complexity = $5,
            score_futureproof = $6,
            score_reasoning = $7,
            overlaps_with = $8,
            status = $9
        WHERE id::text = $1 OR arxiv_id = $1
        RETURNING id, arxiv_id, title, composite_score, status,
                  score_relevance, score_overlap, score_impact,
                  score_complexity, score_futureproof, score_reasoning, overlaps_with
        """,
        paper_id,
        score.score_relevance, score.score_overlap, score.score_impact,
        score.score_complexity, score.score_futureproof, score.score_reasoning,
        score.overlaps_with or [], status
    )
    if not row:
        raise HTTPException(status_code=404, detail="Paper not found")
    return dict(row)


@router.patch("/papers/{paper_id}/status")
async def update_paper_status(paper_id: str, status: str):
    """Update paper status: implement, skip, implemented, superseded."""
    valid = ("unscored", "scored", "implement", "skip", "implemented", "superseded")
    if status not in valid:
        raise HTTPException(status_code=400, detail=f"status must be one of {valid}")
    pool = await get_pool()
    row = await pool.fetchrow(
        "UPDATE research_papers SET status = $2 WHERE id::text = $1 OR arxiv_id = $1 RETURNING id, title, status",
        paper_id, status
    )
    if not row:
        raise HTTPException(status_code=404, detail="Paper not found")
    return dict(row)


@router.get("/triage")
async def triage_papers(min_score: float = 0.0, status: Optional[str] = None):
    """Get papers ranked by composite score for implementation decisions.

    Returns scored papers sorted by composite_score DESC.
    Use min_score to filter (e.g. 7.0 = only high-impact papers).
    Use status to filter (e.g. 'scored' = needs decision, 'implement' = approved).
    """
    pool = await get_pool()
    conditions = ["composite_score IS NOT NULL", "composite_score >= $1"]
    params = [min_score]
    if status:
        params.append(status)
        conditions.append(f"status = ${len(params)}")
    where = "WHERE " + " AND ".join(conditions)
    rows = await pool.fetch(
        f"""
        SELECT id, arxiv_id, title, tags, published_date, status,
               score_relevance, score_overlap, score_impact,
               score_complexity, score_futureproof, composite_score,
               score_reasoning, overlaps_with
        FROM research_papers
        {where}
        ORDER BY composite_score DESC
        """,
        *params
    )
    return [dict(r) for r in rows]


@router.get("/triage/unscored")
async def unscored_papers():
    """Get papers that haven't been scored yet — the triage backlog."""
    pool = await get_pool()
    rows = await pool.fetch(
        """
        SELECT id, arxiv_id, title, tags, abstract, relevance_notes, published_date
        FROM research_papers
        WHERE status = 'unscored'
        ORDER BY added_at DESC
        """
    )
    return [dict(r) for r in rows]


@router.get("/triage/summary")
async def triage_summary():
    """Overview of the triage pipeline — how many papers at each stage."""
    pool = await get_pool()
    counts = await pool.fetch(
        "SELECT status, COUNT(*) as count FROM research_papers GROUP BY status ORDER BY status"
    )
    avg = await pool.fetchrow(
        "SELECT AVG(composite_score) as avg_score, MAX(composite_score) as max_score, MIN(composite_score) as min_score FROM research_papers WHERE composite_score IS NOT NULL"
    )
    top3 = await pool.fetch(
        """
        SELECT arxiv_id, title, composite_score, status
        FROM research_papers
        WHERE composite_score IS NOT NULL AND status IN ('scored', 'implement')
        ORDER BY composite_score DESC LIMIT 3
        """
    )
    return {
        "pipeline": {r["status"]: r["count"] for r in counts},
        "scores": {
            "avg": round(avg["avg_score"], 2) if avg["avg_score"] else None,
            "max": round(avg["max_score"], 2) if avg["max_score"] else None,
            "min": round(avg["min_score"], 2) if avg["min_score"] else None,
        },
        "top_candidates": [dict(r) for r in top3],
    }


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
    """Summary of research DB including triage pipeline."""
    pool = await get_pool()
    papers = await pool.fetchrow(
        """SELECT COUNT(*) as total,
                  COUNT(*) FILTER (WHERE status = 'unscored') as unscored,
                  COUNT(*) FILTER (WHERE status = 'scored') as scored,
                  COUNT(*) FILTER (WHERE status = 'implement') as to_implement,
                  COUNT(*) FILTER (WHERE status = 'implemented') as implemented,
                  COUNT(*) FILTER (WHERE status = 'skip') as skipped,
                  COUNT(*) FILTER (WHERE status = 'superseded') as superseded
           FROM research_papers"""
    )
    notes = await pool.fetchrow(
        "SELECT COUNT(*) as total, COUNT(*) FILTER (WHERE implemented) as implemented FROM research_notes"
    )
    top = await pool.fetch(
        """SELECT arxiv_id, title, composite_score, status
           FROM research_papers
           WHERE status IN ('scored', 'implement')
           ORDER BY composite_score DESC NULLS LAST LIMIT 5"""
    )
    return {
        "papers": {
            "total": papers["total"],
            "unscored": papers["unscored"],
            "scored": papers["scored"],
            "to_implement": papers["to_implement"],
            "implemented": papers["implemented"],
            "skipped": papers["skipped"],
            "superseded": papers["superseded"],
        },
        "notes": {
            "total": notes["total"],
            "implemented": notes["implemented"],
            "pending": notes["total"] - notes["implemented"],
        },
        "top_candidates": [dict(r) for r in top],
    }
