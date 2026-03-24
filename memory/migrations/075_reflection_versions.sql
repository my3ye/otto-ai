-- Migration 075: reflection_versions
-- Tracks self-modifications to core agent files for auditability + auto-rollback

CREATE TABLE IF NOT EXISTS reflection_versions (
    id              UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    version         INTEGER NOT NULL,
    target_file     TEXT NOT NULL,
    content_hash    TEXT NOT NULL,
    diff            TEXT NOT NULL,
    patch_summary   TEXT NOT NULL,
    hypothesis      TEXT,
    experiment_id   UUID,  -- no FK constraint — experiments table may not exist

    rl2f_before     FLOAT,
    rl2f_after      FLOAT,

    status          TEXT NOT NULL DEFAULT 'pending_veto',
    -- pending_veto | active | rolled_back | kept | auto_rolled_back | vetoed

    applied_at      TIMESTAMPTZ,
    veto_expires_at TIMESTAMPTZ,
    evaluated_at    TIMESTAMPTZ,
    reverted_at     TIMESTAMPTZ,
    revert_reason   TEXT,

    source          TEXT DEFAULT 'autoevolve',
    approved_by     TEXT,

    created_at      TIMESTAMPTZ DEFAULT NOW(),
    deleted_at      TIMESTAMPTZ DEFAULT NULL,
    archived        BOOLEAN DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS idx_rv_target ON reflection_versions(target_file);
CREATE INDEX IF NOT EXISTS idx_rv_status ON reflection_versions(status);
CREATE INDEX IF NOT EXISTS idx_rv_version ON reflection_versions(version, target_file);

CREATE OR REPLACE VIEW rollback_candidates AS
    SELECT *
    FROM reflection_versions
    WHERE status = 'active'
      AND rl2f_after IS NOT NULL
      AND rl2f_before IS NOT NULL
      AND (rl2f_before - rl2f_after) > 0.15
      AND archived = FALSE
      AND deleted_at IS NULL;
