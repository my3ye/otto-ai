-- Migration 026: TAME executor memory — add trust_score to procedures
-- Part of TAME dual-memory architecture (arXiv:2602.03224)
-- Executor memory: generalizable task methodologies with trust scores
-- trust_score increases on task success, decreases on failure (Bayesian-style)

ALTER TABLE procedures
    ADD COLUMN IF NOT EXISTS trust_score FLOAT NOT NULL DEFAULT 0.5
        CHECK (trust_score >= 0.0 AND trust_score <= 1.0);

CREATE INDEX IF NOT EXISTS idx_procedures_trust_score ON procedures (trust_score DESC);

-- Seed trust_score from existing success/failure history for procedures that have been used
UPDATE procedures
SET trust_score = CASE
    WHEN (success_count + failure_count) = 0 THEN 0.5
    ELSE ROUND(
        CAST(success_count AS NUMERIC) / CAST(success_count + failure_count AS NUMERIC),
        4
    )::FLOAT
END
WHERE success_count + failure_count > 0;
