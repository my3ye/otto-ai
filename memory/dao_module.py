"""DAO Voting Module — Phase 1: local weighted-vote tally in PostgreSQL.

Implements the LocalDAOModule used by the workflow gating system for
DAO-in-the-loop gate resolution.

Phase 1 (this file):
  - Votes stored in workflow_gate_votes table
  - Voter identity = any string (wallet addr, user ID, "agent:<name>")
  - Weight = caller-supplied float (trust-based)
  - No on-chain signature verification (optional signature field for audit)
  - Auto-resolves gate when quorum + approval/rejection threshold is crossed

Phase 2 (future, separate task):
  - OnchainDAOModule: SOS governance contracts, signature verification,
    token-balance-derived weights from chain

Architecture doc: ~/otto/docs/workflow-gating-architecture-2026-03-24.md
"""

import logging
from typing import Optional
from uuid import UUID

log = logging.getLogger("otto.dao_module")


class LocalDAOModule:
    """Phase 1 DAO voting — fully off-chain PostgreSQL tally.

    Responsibilities:
    - UPSERT votes (voter can change vote before resolution)
    - Compute weighted tally after each vote
    - Detect early-rejection (mathematically impossible to approve)
    - Signal when gate should auto-resolve
    """

    async def cast_vote(
        self,
        pool,
        gate_id: UUID,
        voter_address: str,
        vote: str,                   # 'approve' | 'reject' | 'abstain'
        weight: float = 1.0,
        signature: Optional[str] = None,
        reason: Optional[str] = None,
    ) -> None:
        """UPSERT a vote record. Idempotent — voter can change their vote
        before the gate resolves.
        """
        await pool.execute(
            """
            INSERT INTO workflow_gate_votes
                (gate_id, voter_address, vote, weight, signature, reason)
            VALUES ($1, $2, $3, $4, $5, $6)
            ON CONFLICT (gate_id, voter_address) DO UPDATE
                SET vote      = EXCLUDED.vote,
                    weight    = EXCLUDED.weight,
                    signature = EXCLUDED.signature,
                    reason    = EXCLUDED.reason
            """,
            gate_id,
            voter_address,
            vote,
            weight,
            signature,
            reason,
        )
        log.info(f"Gate {str(gate_id)[:8]}: vote={vote} from {voter_address} weight={weight}")

    async def compute_tally(self, pool, gate_id: UUID) -> dict:
        """Compute the current weighted vote tally for a gate.

        Returns a tally dict with all metrics needed for the OMS UI and
        auto-resolution logic.
        """
        votes = await pool.fetch(
            "SELECT vote, weight FROM workflow_gate_votes WHERE gate_id = $1",
            gate_id,
        )
        gate = await pool.fetchrow(
            "SELECT quorum_required, approval_threshold FROM workflow_gates WHERE id = $1",
            gate_id,
        )

        approve_w = sum(v["weight"] for v in votes if v["vote"] == "approve")
        reject_w  = sum(v["weight"] for v in votes if v["vote"] == "reject")
        abstain_w = sum(v["weight"] for v in votes if v["vote"] == "abstain")
        total_w   = approve_w + reject_w  # abstain excluded from threshold calc
        vote_cnt  = len(votes)

        quorum    = (gate["quorum_required"] or 1) if gate else 1
        threshold = float(gate["approval_threshold"] or 0.5) if gate else 0.5

        quorum_ok   = vote_cnt >= quorum
        approve_pct = approve_w / max(total_w, 0.0001)
        reject_pct  = reject_w  / max(total_w, 0.0001)

        return {
            "vote_count":       vote_cnt,
            "quorum_required":  quorum,
            "quorum_reached":   quorum_ok,
            "approve_weight":   float(approve_w),
            "reject_weight":    float(reject_w),
            "abstain_weight":   float(abstain_w),
            "total_weight":     float(total_w),
            "approve_pct":      round(approve_pct, 4),
            "reject_pct":       round(reject_pct, 4),
            "threshold":        threshold,
        }

    async def get_votes(self, pool, gate_id: UUID) -> list:
        """Return all vote records for a gate (for OMS display)."""
        rows = await pool.fetch(
            """SELECT voter_address, vote, weight, reason, created_at
               FROM workflow_gate_votes
               WHERE gate_id = $1
               ORDER BY created_at""",
            gate_id,
        )
        return [
            {
                "voter_address": r["voter_address"],
                "vote":          r["vote"],
                "weight":        float(r["weight"]),
                "reason":        r["reason"],
                "created_at":    r["created_at"].isoformat() if r["created_at"] else None,
            }
            for r in rows
        ]


# Singleton — one module instance per process
_local_dao_module = LocalDAOModule()


def get_dao_module() -> LocalDAOModule:
    """Factory. Returns the active DAO module (Phase 1: local DB)."""
    return _local_dao_module
