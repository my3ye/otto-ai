-- Migration 060: BANKR schema hardening — triggers + CHECK constraints
-- Addendum to 058_bankr.sql (already applied). Fixes:
--   1. updated_at auto-triggers for bankr_trades and bankr_jobs
--   2. CHECK constraints on status + job_type columns

-- ── updated_at trigger function (shared by both BANKR tables) ─────────────────

CREATE OR REPLACE FUNCTION update_bankr_updated_at()
RETURNS TRIGGER AS $$
BEGIN NEW.updated_at = NOW(); RETURN NEW; END;
$$ LANGUAGE plpgsql;

-- ── bankr_trades ──────────────────────────────────────────────────────────────

CREATE TRIGGER trg_bankr_trades_ts
    BEFORE UPDATE ON bankr_trades
    FOR EACH ROW EXECUTE FUNCTION update_bankr_updated_at();

-- Status constraint (validate=false to avoid locking on large tables)
ALTER TABLE bankr_trades
    ADD CONSTRAINT chk_bankr_trades_status
    CHECK (status IN ('pending', 'completed', 'failed', 'cancelled'))
    NOT VALID;

ALTER TABLE bankr_trades VALIDATE CONSTRAINT chk_bankr_trades_status;

-- ── bankr_jobs ────────────────────────────────────────────────────────────────

CREATE TRIGGER trg_bankr_jobs_ts
    BEFORE UPDATE ON bankr_jobs
    FOR EACH ROW EXECUTE FUNCTION update_bankr_updated_at();

ALTER TABLE bankr_jobs
    ADD CONSTRAINT chk_bankr_jobs_status
    CHECK (status IN ('pending', 'completed', 'failed', 'cancelled'))
    NOT VALID;

ALTER TABLE bankr_jobs VALIDATE CONSTRAINT chk_bankr_jobs_status;

ALTER TABLE bankr_jobs
    ADD CONSTRAINT chk_bankr_jobs_job_type
    CHECK (job_type IN ('trade', 'limit', 'dca', 'stop_loss', 'launch', 'portfolio'))
    NOT VALID;

ALTER TABLE bankr_jobs VALIDATE CONSTRAINT chk_bankr_jobs_job_type;
