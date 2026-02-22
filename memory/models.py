from datetime import datetime, timezone
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
    # AgeMem: optional overrides — auto-computed if not supplied
    importance_score: float | None = Field(default=None, ge=0.0, le=1.0)
    ttl_days: int | None = None


class SemanticMemoryOut(BaseModel):
    id: UUID
    content: str
    category: str
    confidence: float
    source: str | None = None
    created_at: datetime
    score: float | None = None  # similarity score for search results
    importance_score: float | None = None  # AgeMem importance weight


class SemanticSearchQuery(BaseModel):
    query: str
    limit: int = 10
    min_confidence: float = 0.0
    category: str | None = None


# ── AgeMem: explicit memory management ────────────────────────────

class SemanticForgetRequest(BaseModel):
    memory_id: UUID | None = None          # soft-delete by ID
    query: str | None = None               # or by semantic similarity
    threshold: float = Field(default=0.95, ge=0.0, le=1.0)


class SemanticForgetResponse(BaseModel):
    affected: int


class SemanticUpdateRequest(BaseModel):
    memory_id: UUID
    content: str
    category: str | None = None


class SemanticSummarizeRequest(BaseModel):
    memory_ids: list[UUID] | None = None   # explicit list
    category: str | None = None            # or by category
    older_than_days: int | None = None     # combined with category


class SemanticSummarizeResponse(BaseModel):
    summary_memory: SemanticMemoryOut
    originals_deleted: int


class DuplicateGroup(BaseModel):
    ids: list[UUID]
    contents: list[str]
    max_similarity: float


class SemanticMergeRequest(BaseModel):
    threshold: float = Field(default=0.92, ge=0.5, le=1.0)
    category: str | None = None
    dry_run: bool = True


class SemanticMergeResponse(BaseModel):
    groups_found: int
    groups: list[DuplicateGroup]
    merged: int  # number of memories soft-deleted (0 if dry_run)


# ── A-Mem: Associative Memory Linking ─────────────────────────────

class NoteLink(BaseModel):
    id: UUID
    source_id: UUID
    target_id: UUID
    link_strength: float
    created_at: datetime
    linked_content: str | None = None    # content of the linked memory (if joined)
    linked_category: str | None = None


class SemanticMemoryWithLinks(BaseModel):
    """A search result memory with its 1-hop associative context."""
    memory: SemanticMemoryOut
    linked_context: list[SemanticMemoryOut] = Field(default_factory=list)


class SemanticSearchWithLinksResult(BaseModel):
    """Response from POST /semantic/search when include_links=True."""
    results: list[SemanticMemoryOut]               # primary results (unchanged format)
    linked_context: list[SemanticMemoryOut] = Field(default_factory=list)  # 1-hop neighbours


class LinkMemoryResponse(BaseModel):
    links_created: int
    memory_id: UUID


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
    trust_score: float = 0.5
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


# ── Tasks ─────────────────────────────────────────────────────────
class TaskCreate(BaseModel):
    title: str
    prompt: str
    context: str | None = None
    priority: int = Field(default=5, ge=1, le=10)
    model: str = "sonnet"
    cli: str = "claude"  # which CLI backend: claude | gemini | kimi
    max_budget_usd: float = 5.00  # Min $5 for big tasks (Mev directive 2026-02-19)
    max_turns: int = 50
    timeout_seconds: int = 600
    working_directory: str = "/home/web3relic/otto"
    created_by: str = "heartbeat"
    session_id: UUID | None = None
    metadata: dict = Field(default_factory=dict)


class TaskOut(BaseModel):
    id: UUID
    title: str
    prompt: str
    context: str | None = None
    priority: int
    status: str
    model: str
    cli: str = "claude"  # which CLI backend: claude | gemini | kimi
    max_budget_usd: float
    max_turns: int
    timeout_seconds: int
    working_directory: str
    pid: int | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    output: str | None = None
    error: str | None = None
    exit_code: int | None = None
    reviewed: bool
    reviewed_at: datetime | None = None
    created_by: str
    session_id: UUID | None = None
    created_at: datetime
    updated_at: datetime
    metadata: dict = Field(default_factory=dict)
    # QA fields (migration 028)
    qa_status: str | None = None      # pending_qa | approved | rejected | committed
    qa_output: str | None = None      # QA agent's review text
    qa_reviewer: str | None = None    # which CLI did the QA
    commit_hash: str | None = None    # git commit SHA if committed


class TaskComplete(BaseModel):
    output: str | None = None
    error: str | None = None
    exit_code: int = 0
    metadata: dict = Field(default_factory=dict)


class TaskRunResponse(BaseModel):
    id: UUID
    status: str
    pid: int
    message: str


# ── Heartbeat Metrics ──────────────────────────────────────────────
class HeartbeatMetricCreate(BaseModel):
    heartbeat_type: str = "orchestrator"  # orchestrator | reflection | alpha
    duration_s: float | None = None
    budget_used: float | None = None
    tasks_created: int = 0
    tasks_launched: int = 0
    tasks_reviewed: int = 0
    messages_sent: int = 0
    errors: list = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)


class HeartbeatMetricOut(BaseModel):
    id: UUID
    timestamp: datetime
    heartbeat_type: str
    duration_s: float | None = None
    budget_used: float | None = None
    tasks_created: int
    tasks_launched: int
    tasks_reviewed: int
    messages_sent: int
    errors: list
    metadata: dict


class HeartbeatTrend(BaseModel):
    heartbeat_type: str
    current_week: dict   # avg metrics for current 7 days
    prior_week: dict     # avg metrics for prior 7 days
    deltas: dict         # current - prior (positive = improvement)


# ── Reasoning Chain ────────────────────────────────────────────────
class ReasoningEntryCreate(BaseModel):
    heartbeat_type: str = "orchestrator"  # orchestrator | reflection | alpha
    reasoning: str                         # WHY: key reasoning this cycle
    decisions: str | None = None           # WHAT: decisions made
    expected: str | None = None            # EXPECTED: what should happen next
    metadata: dict = Field(default_factory=dict)


class ReasoningEntryOut(BaseModel):
    id: UUID
    heartbeat_type: str
    cycle_ts: datetime
    reasoning: str
    decisions: str | None = None
    expected: str | None = None
    actual: str | None = None
    outcome_match: str  # pending | matched | partial | miss


class ReasoningOutcomeUpdate(BaseModel):
    actual: str                # what actually happened
    outcome_match: str         # matched | partial | miss
    prior_entry_id: UUID | None = None  # the entry being updated (optional shorthand)


# ── Metrics Summary ────────────────────────────────────────────────
class MetricsSummary(BaseModel):
    tasks: dict          # total, completed, failed, pending, avg_completion_s, success_rate
    heartbeats: dict     # total, avg_duration_s, avg_budget_used
    communication: dict  # open_questions, resolved_questions
    memory: dict         # total_semantic, total_episodic
    generated_at: datetime


# ── Principles (MARS self-improvement) ─────────────────────────────
class PrincipleCreate(BaseModel):
    principle: str
    category: str = "general"  # memory_ops, task_execution, alpha_trading, outreach, general
    source_events: list[UUID] = Field(default_factory=list)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)


class PrincipleOut(BaseModel):
    id: UUID
    principle: str
    category: str
    source_events: list[UUID]
    confidence: float
    times_applied: int
    times_violated: int
    created_at: datetime
    updated_at: datetime


# ── LATS Task Planning ─────────────────────────────────────────────
class TaskPlanRequest(BaseModel):
    goal: str                        # What needs to be accomplished
    context: str | None = None       # Relevant background context
    priority: int = Field(default=5, ge=1, le=10)
    n_approaches: int = Field(default=3, ge=2, le=4)  # How many alternatives to generate


class ApproachCandidate(BaseModel):
    title: str                       # Short name for this approach
    prompt: str                      # The full task prompt if selected
    success_probability: float       # 0.0–1.0 estimated chance of success
    estimated_cost: float            # Relative cost (0.0=cheap, 1.0=expensive)
    priority_alignment: float        # 0.0–1.0 how well it serves Otto's priorities
    composite_score: float           # Weighted combination of the above
    reasoning: str                   # Why this approach was rated this way
    failure_fallback: str | None = None  # What to try if this approach fails


class TaskPlanResponse(BaseModel):
    goal: str
    approaches: list[ApproachCandidate]
    selected_index: int              # Index of recommended approach (highest composite_score)
    selected: ApproachCandidate      # Convenience: the recommended approach
    model_used: str = "gemini-2.0-flash"
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ── APC Plan Cache ──────────────────────────────────────────────────

class PlanCacheStore(BaseModel):
    """Request to store a successful plan in the cache."""
    task_id: UUID | None = None
    task_title: str
    task_prompt: str
    selected_plan: str                   # The winning approach prompt
    plan_metadata: dict = Field(default_factory=dict)  # scores, reasoning, etc.
    success: bool = True
    execution_time_s: int | None = None
    model_used: str = "gemini-2.0-flash"


class PlanCacheMatch(BaseModel):
    """Request to find a cached plan for a new task."""
    task_prompt: str
    threshold: float = Field(default=0.85, ge=0.0, le=1.0)
    limit: int = Field(default=3, ge=1, le=10)


class PlanCacheEntry(BaseModel):
    """A single cached plan entry returned from a match."""
    id: UUID
    task_title: str
    task_prompt: str
    selected_plan: str
    plan_metadata: dict
    success: bool
    similarity: float
    used_count: int
    created_at: datetime


class PlanCacheMatchResponse(BaseModel):
    """Response from POST /plans/match."""
    matched: bool
    entries: list[PlanCacheEntry]
    best_similarity: float | None = None


# ── AdaptOrch Task Routing ──────────────────────────────────────────

class TaskRouteRequest(BaseModel):
    """Task characteristics for AdaptOrch routing. Provide task_id OR inline fields."""
    task_id: UUID | None = None
    title: str | None = None
    prompt: str | None = None
    priority: int = Field(default=5, ge=1, le=10)
    max_budget_usd: float = 5.0
    max_turns: int = 50
    timeout_seconds: int = 600
    metadata: dict = Field(default_factory=dict)
    apply: bool = False  # If True + task_id given, update task record with recommended params


class ExecutionStrategy(BaseModel):
    """AdaptOrch recommended execution strategy for a task."""
    strategy: str           # express | research_chunked | full_budget_build | eval_focused | lats_fallback | standard
    task_type: str          # research | build | lookup | eval | standard
    recommended_model: str
    recommended_max_turns: int
    recommended_timeout_seconds: int
    recommended_max_budget_usd: float
    reasoning: str
    lats_fallback_prompt: str | None = None


class TaskRouteResponse(BaseModel):
    """Response from the AdaptOrch /tasks/route endpoint."""
    strategy: ExecutionStrategy
    applied: bool = False
    task_id: UUID | None = None


# ── PreFlect Prospective Reflection ────────────────────────────────
class PreflectResult(BaseModel):
    """PreFlect critique result stored in task metadata before execution."""
    risk_score: float = Field(..., ge=0.0, le=1.0)   # 0=safe, 1=high risk
    risk_factors: list[str]                           # detected risk factors
    suggested_modifications: str | None = None        # how to mitigate if high risk
    failure_patterns_matched: list[str] = Field(default_factory=list)  # matched pattern names


class PreflectResultOut(BaseModel):
    task_id: UUID
    risk_score: float
    risk_factors: list[str]
    suggested_modifications: str | None = None
    failure_patterns_matched: list[str]
    stored_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ── A-RAG Hierarchical Retrieval ──────────────────────────────────

class ARAGSearchRequest(BaseModel):
    """Request for A-RAG hierarchical retrieval (arxiv 2602.03442).

    Runs semantic (pgvector), keyword (pg_trgm), and structured (SQL) strategies
    in parallel, merges by ID, and returns a weighted-ranked result list.
    """
    query: str
    limit: int = 10
    min_confidence: float = 0.0
    # Optional structured filters (used by structured_query strategy)
    category: str | None = None
    min_importance: float | None = Field(default=None, ge=0.0, le=1.0)
    date_after: datetime | None = None
    date_before: datetime | None = None
    # Strategy weights (default: A-RAG paper recommendation)
    semantic_weight: float = Field(default=0.5, ge=0.0, le=1.0)
    keyword_weight: float = Field(default=0.3, ge=0.0, le=1.0)
    structured_weight: float = Field(default=0.2, ge=0.0, le=1.0)


class ARAGResult(BaseModel):
    """A single memory returned from A-RAG search with per-strategy scores."""
    id: UUID
    content: str
    category: str
    confidence: float
    source: str | None = None
    created_at: datetime
    importance_score: float | None = None
    arag_score: float               # combined weighted score (0.0–1.0)
    semantic_score: float = 0.0    # normalized pgvector cosine contribution
    keyword_score: float = 0.0     # normalized pg_trgm trigram contribution
    structured_score: float = 0.0  # normalized structured/importance contribution
    retrieval_strategies: list[str] = Field(default_factory=list)  # which strategies found this


class ARAGSearchResponse(BaseModel):
    """Response from POST /semantic/arag_search."""
    results: list[ARAGResult]
    query: str
    strategies_used: list[str]
    total_candidates: int    # unique memories across all strategies before trim
    semantic_count: int      # candidates from semantic strategy
    keyword_count: int       # candidates from keyword strategy
    structured_count: int    # candidates from structured strategy


# ── WhatsApp ───────────────────────────────────────────────────────
class WhatsAppIncoming(BaseModel):
    from_jid: str
    message: str
    push_name: str | None = None
