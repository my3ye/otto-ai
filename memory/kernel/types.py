"""AgentOS type definitions — interrupt types, priorities, and cognitive addresses.

Reference: arXiv 2602.20934v1 §3 (Interrupt-Driven Processing)
"""

from enum import IntEnum, Enum
from uuid import UUID
from typing import NewType

# ── Semantic identifiers ─────────────────────────────────────────────────────

SliceID = NewType("SliceID", UUID)
CognitiveAddress = NewType("CognitiveAddress", str)  # e.g. "L1:purpose", "L2:slice-abc"


# ── Interrupt Types (IVT codes) ──────────────────────────────────────────────

class InterruptType(str, Enum):
    """Interrupt signal codes for the Interrupt Vector Table.

    Naming follows OS signal conventions: SIG_ prefix for clarity.
    Hex codes in comments for paper alignment.
    """
    # 0x01 — Message from Admin (Mev)
    SIG_MSG_ADMIN = "sig_msg_admin"
    # 0x02 — L1 capacity reached during paging
    SIG_CONTEXT_FULL = "sig_context_full"
    # 0x03 — Cognitive drift Δψ exceeds threshold
    SIG_SYNC_DRIFT = "sig_sync_drift"
    # 0x04 — LLM output failed perception alignment
    SIG_PERCEPTION_ERR = "sig_perception_err"
    # 0x05 — Queued task finished successfully
    SIG_TASK_COMPLETE = "sig_task_complete"
    # 0x06 — Queued task errored
    SIG_TASK_FAILED = "sig_task_failed"
    # 0x07 — Hourly orchestrator/reflection heartbeat
    SIG_HEARTBEAT = "sig_heartbeat"
    # 0x08 — Nightly maintenance/decay
    SIG_MAINTENANCE = "sig_maintenance"
    # 0x09 — Mev resolved a decision proposal
    SIG_PROPOSAL_RESOLVED = "sig_proposal_resolved"
    # 0x0A — Mev issued a directive
    SIG_DIRECTIVE = "sig_directive"


# ── Priority Levels ──────────────────────────────────────────────────────────

class Priority(IntEnum):
    """Interrupt priority: lower number = higher priority (OS convention).

    Range 0-10. Critical (0) always preempts. Background (10) runs when idle.
    """
    CRITICAL = 0        # System failure, perception errors
    PERCEPTION_ERR = 1  # LLM output failed alignment
    ADMIN_MSG = 2       # Message from Mev
    DIRECTIVE = 2       # Mev directive
    SYNC_DRIFT = 3      # Drift threshold exceeded
    CONTEXT_FULL = 3    # L1 capacity reached
    TASK_COMPLETE = 4   # Task finished
    PROPOSAL_RESOLVED = 4  # Decision resolved
    HEARTBEAT = 5       # Scheduled heartbeat
    TASK_FAILED = 3     # Task errored (urgent)
    MAINTENANCE = 7     # Nightly maintenance
    BACKGROUND = 10     # Low-priority background work


# Default priority mapping for each interrupt type
INTERRUPT_PRIORITIES: dict[InterruptType, int] = {
    InterruptType.SIG_MSG_ADMIN: Priority.ADMIN_MSG,
    InterruptType.SIG_CONTEXT_FULL: Priority.CONTEXT_FULL,
    InterruptType.SIG_SYNC_DRIFT: Priority.SYNC_DRIFT,
    InterruptType.SIG_PERCEPTION_ERR: Priority.PERCEPTION_ERR,
    InterruptType.SIG_TASK_COMPLETE: Priority.TASK_COMPLETE,
    InterruptType.SIG_TASK_FAILED: Priority.TASK_FAILED,
    InterruptType.SIG_HEARTBEAT: Priority.HEARTBEAT,
    InterruptType.SIG_MAINTENANCE: Priority.MAINTENANCE,
    InterruptType.SIG_PROPOSAL_RESOLVED: Priority.PROPOSAL_RESOLVED,
    InterruptType.SIG_DIRECTIVE: Priority.DIRECTIVE,
}


# ── Interrupt Status ─────────────────────────────────────────────────────────

class InterruptStatus(str, Enum):
    """Lifecycle states for an interrupt in the queue."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    EXPIRED = "expired"


# ── Memory Levels ────────────────────────────────────────────────────────────

class MemoryLevel(str, Enum):
    """S-MMU memory hierarchy levels."""
    L1 = "L1"  # Active context (in-memory, token-budgeted)
    L2 = "L2"  # Warm storage (pgvector semantic_memories + semantic_slices)
    L3 = "L3"  # Cold storage (Neo4j graph, archived memories)


# ── Provider Types ───────────────────────────────────────────────────────────

class ProviderType(str, Enum):
    """LLM provider backend types."""
    OPENAI_COMPATIBLE = "openai_compatible"  # Kimi, OpenRouter, etc.
    CLAUDE_CLI = "claude_cli"               # Claude Code CLI fallback
