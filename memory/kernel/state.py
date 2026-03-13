"""Cognitive state — serializable kernel state for save/restore across RIC cycles.

Reference: arXiv 2602.20934v1 §4 (Cognitive State Management)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4

log = logging.getLogger("otto.kernel.state")


@dataclass
class CognitiveState:
    """Snapshot of the kernel's cognitive state at a point in time.

    Used by:
    - RIC save/restore: capture state before processing an interrupt
    - Sync Pulses: snapshot for drift measurement and recovery
    - L1 cache tracking: which slices are loaded
    """

    # Unique snapshot identifier
    snapshot_id: UUID = field(default_factory=uuid4)

    # L1 cache: list of slice IDs currently loaded
    l1_slice_ids: list[UUID] = field(default_factory=list)

    # Total tokens used in L1
    l1_token_count: int = 0

    # Current drift measurement
    drift_value: float = 0.0

    # Number of interrupts processed since last sync
    interrupts_since_sync: int = 0

    # Trigger that created this snapshot
    trigger: str = "manual"  # manual, drift, scheduled, maintenance, session_boundary

    # Timestamp
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    # Arbitrary extra data (e.g., active conversation context)
    extra: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Serialize for DB storage (cognitive_snapshots.snapshot_data)."""
        return {
            "snapshot_id": str(self.snapshot_id),
            "l1_slice_ids": [str(sid) for sid in self.l1_slice_ids],
            "l1_token_count": self.l1_token_count,
            "drift_value": self.drift_value,
            "interrupts_since_sync": self.interrupts_since_sync,
            "trigger": self.trigger,
            "created_at": self.created_at.isoformat(),
            "extra": self.extra,
        }

    @classmethod
    def from_dict(cls, data: dict) -> CognitiveState:
        """Deserialize from DB storage."""
        return cls(
            snapshot_id=UUID(data["snapshot_id"]) if data.get("snapshot_id") else uuid4(),
            l1_slice_ids=[UUID(s) for s in data.get("l1_slice_ids", [])],
            l1_token_count=data.get("l1_token_count", 0),
            drift_value=data.get("drift_value", 0.0),
            interrupts_since_sync=data.get("interrupts_since_sync", 0),
            trigger=data.get("trigger", "restored"),
            extra=data.get("extra", {}),
        )

    async def save(self, pool, agent_id: str = "otto") -> UUID:
        """Persist this snapshot to cognitive_snapshots table."""
        row = await pool.fetchrow(
            """INSERT INTO cognitive_snapshots
               (l1_slice_ids, drift_value, trigger, snapshot_data, agent_id)
               VALUES ($1, $2, $3, $4, $5)
               RETURNING id""",
            self.l1_slice_ids,
            self.drift_value,
            self.trigger,
            self.to_dict(),
            agent_id,
        )
        db_id = row["id"]
        log.info(f"Saved cognitive snapshot {db_id} (agent={agent_id}, trigger={self.trigger}, drift={self.drift_value:.3f})")
        return db_id

    @classmethod
    async def load_latest(cls, pool) -> CognitiveState | None:
        """Load most recent snapshot from DB."""
        row = await pool.fetchrow(
            """SELECT id, l1_slice_ids, drift_value, trigger, snapshot_data, created_at
               FROM cognitive_snapshots
               ORDER BY created_at DESC LIMIT 1"""
        )
        if not row:
            return None
        state = cls.from_dict(row["snapshot_data"] or {})
        state.created_at = row["created_at"]
        return state
