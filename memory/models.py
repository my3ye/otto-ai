from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel
import uuid


# ── Sessions ────────────────────────────────────────────────────────────────

class SessionStart(BaseModel):
    agent_id: Optional[str] = "default"
    context: Optional[dict] = None


class SessionOut(BaseModel):
    id: str
    agent_id: str
    started_at: datetime
    ended_at: Optional[datetime] = None
    summary: Optional[str] = None


class SessionEnd(BaseModel):
    summary: Optional[str] = None


# ── Semantic Memory ──────────────────────────────────────────────────────────

class SemanticMemoryCreate(BaseModel):
    content: str
    category: Optional[str] = "general"
    confidence: Optional[float] = 0.8
    source: Optional[str] = None
    metadata: Optional[dict] = None


class SemanticMemoryOut(BaseModel):
    id: str
    content: str
    category: str
    confidence: float
    source: Optional[str]
    created_at: datetime
    relevance: Optional[float] = None


class SemanticSearchQuery(BaseModel):
    query: str
    limit: Optional[int] = 10
    min_confidence: Optional[float] = 0.0
    category: Optional[str] = None


# ── Episodic Events ──────────────────────────────────────────────────────────

class EpisodicEventCreate(BaseModel):
    session_id: Optional[str] = None
    content: str
    event_type: Optional[str] = "general"
    importance: Optional[float] = 0.5
    metadata: Optional[dict] = None


class EpisodicEventOut(BaseModel):
    id: str
    session_id: Optional[str]
    content: str
    event_type: str
    importance: float
    created_at: datetime


class TimelineQuery(BaseModel):
    session_id: Optional[str] = None
    event_type: Optional[str] = None
    min_importance: Optional[float] = 0.0
    limit: Optional[int] = 50


# ── Procedural Memory ────────────────────────────────────────────────────────

class ProcedureCreate(BaseModel):
    name: str
    description: str
    steps: list[str]
    category: Optional[str] = "general"


class ProcedureOut(BaseModel):
    id: str
    name: str
    description: str
    steps: list[str]
    category: str
    trust_score: float
    use_count: int
    success_count: int
    created_at: datetime


class ProcedureOutcome(BaseModel):
    success: bool
    notes: Optional[str] = None


# ── Tasks ────────────────────────────────────────────────────────────────────

class TaskCreate(BaseModel):
    title: str
    prompt: str
    priority: Optional[int] = 5
    budget_usd: Optional[float] = 1.0
    timeout_seconds: Optional[int] = 300
    agent_type: Optional[str] = "general-purpose"
    model: Optional[str] = "sonnet"
    created_by: Optional[str] = "user"
    metadata: Optional[dict] = None


class TaskOut(BaseModel):
    id: str
    title: str
    prompt: str
    priority: int
    status: str
    budget_usd: float
    agent_type: str
    model: str
    created_by: str
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    output: Optional[str] = None
    exit_code: Optional[int] = None


class TaskQueueStatus(BaseModel):
    pending: int
    running: int
    completed_24h: int
    failed_24h: int
