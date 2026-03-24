-- Migration 074: Workflow Gating System
-- Adds first-class gate records with timeout, DAO support, and audit trail.
-- Gates are overlay records on workflow_instances — every pause is now a gate row.

BEGIN;

CREATE TABLE IF NOT EXISTS workflow_gates (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Owning workflow
    instance_id         UUID NOT NULL REFERENCES workflow_instances(id) ON DELETE CASCADE,
    step_position       INTEGER NOT NULL,           -- which step (matches steps[N].position)
    gate_position       TEXT NOT NULL DEFAULT 'post'
        CHECK (gate_position IN ('pre', 'post')),

    -- Gate identity
    gate_type           TEXT NOT NULL DEFAULT 'human'
        CHECK (gate_type IN ('human', 'dao')),

    -- State machine
    status              TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'approved', 'rejected', 'timed_out', 'skipped')),

    -- Timeout
    timeout_seconds     INTEGER NOT NULL DEFAULT 86400,
    expires_at          TIMESTAMPTZ NOT NULL,
    timeout_action      TEXT NOT NULL DEFAULT 'escalate'
        CHECK (timeout_action IN ('approve', 'reject', 'skip', 'escalate')),

    -- DAO config (NULL for human gates)
    quorum_required     INTEGER,                    -- minimum number of votes
    approval_threshold  NUMERIC(4,3) DEFAULT 0.500, -- fraction of non-abstain weight needed

    -- Resolution audit trail
    resolved_by         TEXT,
    resolved_at         TIMESTAMPTZ,
    resolution_reason   TEXT,

    -- Context for approver to review
    context_snapshot    JSONB NOT NULL DEFAULT '{}',
    metadata            JSONB NOT NULL DEFAULT '{}',

    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_wf_gates_instance
    ON workflow_gates(instance_id);
CREATE INDEX IF NOT EXISTS idx_wf_gates_pending
    ON workflow_gates(expires_at) WHERE status = 'pending';
CREATE INDEX IF NOT EXISTS idx_wf_gates_step
    ON workflow_gates(instance_id, step_position, gate_position);


-- DAO vote table: one row per voter per gate (UPSERT on conflict = vote change)
CREATE TABLE IF NOT EXISTS workflow_gate_votes (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    gate_id         UUID NOT NULL REFERENCES workflow_gates(id) ON DELETE CASCADE,

    -- Voter identity
    voter_address   TEXT NOT NULL,          -- wallet addr, user ID, or "agent:<name>"
    vote            TEXT NOT NULL
        CHECK (vote IN ('approve', 'reject', 'abstain')),
    weight          NUMERIC(18,8) NOT NULL DEFAULT 1.0,

    -- Phase 2 fields (nullable in Phase 1 — local vote trust)
    signature       TEXT,                   -- wallet signature over (gate_id + vote)
    token_snapshot  NUMERIC(18,8),          -- token balance at vote time (Phase 2)

    reason          TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- One active vote per voter per gate (voter can change mind before resolution)
    UNIQUE (gate_id, voter_address)
);

CREATE INDEX IF NOT EXISTS idx_wf_gate_votes_gate
    ON workflow_gate_votes(gate_id);


-- Fast pending-gate lookup on workflow instances
ALTER TABLE workflow_instances
    ADD COLUMN IF NOT EXISTS pending_gate_id UUID
        REFERENCES workflow_gates(id) ON DELETE SET NULL;

COMMIT;
