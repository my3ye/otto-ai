from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field


# ── Sessions ───────────────────────────────────────────────────────
class SessionStart(BaseModel):
    session_type: str = "claude_code"
    metadata: dict = Field(default_factory=dict)


class SessionEnd(BaseModel):
    summary: str
    key_decisions: list[str] = Field(default_factory=list)


class SessionOut(BaseModel):
    id: UUID
    session_type: str
    started_at: datetime
    ended_at: datetime | None = None
    summary: str | None = None
    key_decisions: list = Field(default_factory=list)


# ── Episodic Events ───────────────────────────────────────────────
class EpisodicEventCreate(BaseModel):
    session_id: UUID | None = None
    content: str
    event_type: str = "observation"
    importance: int = Field(default=5, ge=1, le=10)
    metadata: dict = Field(default_factory=dict)


class EpisodicEventOut(BaseModel):
    id: UUID
    session_id: UUID | None = None
    content: str
    event_type: str
    importance: int
    created_at: datetime


class TimelineQuery(BaseModel):
    limit: int = 20
    min_importance: int = 1
    event_type: str | None = None
    session_id: UUID | None = None


# ── Semantic Memories ──────────────────────────────────────────────
class SemanticMemoryCreate(BaseModel):
    content: str
    category: str = "general"
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)
    source: str | None = None
    metadata: dict = Field(default_factory=dict)


class SemanticMemoryOut(BaseModel):
    id: UUID
    content: str
    category: str
    confidence: float
    source: str | None = None
    created_at: datetime
    score: float | None = None  # similarity score for search results


class SemanticSearchQuery(BaseModel):
    query: str
    limit: int = 10
    min_confidence: float = 0.0
    category: str | None = None


# ── Procedures ─────────────────────────────────────────────────────
class ProcedureCreate(BaseModel):
    name: str
    description: str | None = None
    steps: list[str] = Field(default_factory=list)


class ProcedureOut(BaseModel):
    id: UUID
    name: str
    description: str | None = None
    steps: list
    success_count: int
    failure_count: int
    last_used: datetime | None = None
    created_at: datetime


class ProcedureOutcome(BaseModel):
    success: bool
    notes: str | None = None


# ── Context Briefing ───────────────────────────────────────────────
class ContextBriefing(BaseModel):
    session: SessionOut | None = None
    last_session: SessionOut | None = None
    identity_facts: list[SemanticMemoryOut] = Field(default_factory=list)
    high_confidence_facts: list[SemanticMemoryOut] = Field(default_factory=list)
    recent_events: list[EpisodicEventOut] = Field(default_factory=list)
    procedures: list[ProcedureOut] = Field(default_factory=list)
    graph_facts: list[dict] = Field(default_factory=list)


# ── Pending Questions ─────────────────────────────────────────────
class PendingQuestionCreate(BaseModel):
    question: str
    intent: str = "general"  # mission, goal, decision, clarification, general
    context: str | None = None
    channel: str = "whatsapp"


class PendingQuestionOut(BaseModel):
    id: UUID
    question: str
    intent: str
    context: str | None = None
    channel: str
    asked_at: datetime
    resolved_at: datetime | None = None
    answer: str | None = None
    direction: str = "claude_to_gemini"
    source_brain: str = "claude"


class CrossBrainNote(BaseModel):
    content: str
    note_type: str = "context"  # directive, task, goal, decision, context, priority_change
    urgency: str = "normal"  # normal, high, critical
    source_summary: str | None = None


# ── WhatsApp ───────────────────────────────────────────────────────
class WhatsAppIncoming(BaseModel):
    from_jid: str
    message: str
    push_name: str | None = None
