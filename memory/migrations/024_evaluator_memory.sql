-- Migration 024: TAME-inspired evaluator memory
-- Dual-memory architecture: executor memory (semantic_memories) + evaluator memory (this table)
-- Evaluator memory stores safety/utility assessments from historical feedback
-- Inspired by: TAME — Trustworthy Test-Time Evolution of Agent Memory (arXiv:2602.03224)

CREATE TABLE IF NOT EXISTS evaluator_memories (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    category    TEXT NOT NULL,          -- quality_check | safety_flag | performance_pattern | failure_mode
    criterion   TEXT NOT NULL,          -- The rule/pattern being captured
    evidence    TEXT NOT NULL,          -- Concrete observed evidence supporting this criterion
    confidence  FLOAT NOT NULL DEFAULT 0.7 CHECK (confidence >= 0.0 AND confidence <= 1.0),
    times_triggered  INT NOT NULL DEFAULT 0,   -- how many times this criterion matched a task result
    times_confirmed  INT NOT NULL DEFAULT 0,   -- how many times it was confirmed accurate
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_evaluator_memories_category ON evaluator_memories (category);
CREATE INDEX IF NOT EXISTS idx_evaluator_memories_confidence ON evaluator_memories (confidence DESC);

-- Seed with known patterns from Otto's operational history
INSERT INTO evaluator_memories (category, criterion, evidence, confidence) VALUES
(
    'failure_mode',
    'Tasks with timeout exit code 124 usually have prompts that are too broad or open-ended, requiring a scope reduction and clearer termination criteria.',
    'Eval gap push task repeatedly hit 900s timeout. Research sweep tasks with bounded paper counts succeeded. Broad "improve eval" prompts failed while specific "implement X from paper Y" prompts succeeded.',
    0.85
),
(
    'performance_pattern',
    'Paper trading signals where 100% of closed trades exit via time_exit_4h (not TP/SL) indicate the hold horizon is mismatched with the signal timeframe — the signal fires too early or the horizon is too long.',
    'All 11 closed paper trades lost, all exited via time_exit_4h with no TP/SL triggers. Root cause: whale_convergence signal parameters not calibrated for 4h hold horizon.',
    0.90
),
(
    'quality_check',
    'Research sweeps produce highest ROI when findings are immediately queued as implementation tasks in the same heartbeat cycle, not deferred to a future cycle.',
    'Research sweep #5 found AgeMem, A-Mem, SOFAI-LM. Only SOFAI-LM was immediately queued. A-Mem and AgeMem were deferred and had to be re-queued the next cycle, wasting one cycle.',
    0.80
),
(
    'quality_check',
    'Memory dedup threshold of 0.85 cosine similarity is effective for semantic memories — catches near-duplicates without over-suppressing genuinely distinct facts.',
    'AgeMem migration 023 implemented 0.85 threshold. Dedup events logged without false positives in subsequent cycles. Memory quality improved.',
    0.80
),
(
    'failure_mode',
    'Metadata corruption in task records (missing or malformed JSON) can cause tasks to appear failed or hidden even when the work was actually completed — always verify by checking the actual artifacts.',
    'Reflection 2026-02-22: 3 corrupted task records found. Tasks appeared errored but work was complete. Fixed via direct PostgreSQL UPDATE on metadata field.',
    0.85
),
(
    'failure_mode',
    'Gemini Flash metacognitive scoring failures are usually Gemini 429 quota exhaustion, not parse errors — graceful degradation (skip scoring) is the correct response, not a code fix.',
    'SOFAI-LM metacognition failures initially misdiagnosed as parse bug. Root cause was Gemini 429 errors at quota limit. Accepting graceful degradation resolved the false alarm.',
    0.80
),
(
    'performance_pattern',
    'Copy trading convergence signals from a single wallet buying the same token repeatedly are false positives — true convergence requires multiple distinct wallets buying the same token independently.',
    'Alpha scan 2026-02-21: 6 signals reported by Python but all were false positives from single wallets (SM_5, SM_20). Real deduplicated DB query returned 0 valid convergence signals.',
    0.90
),
(
    'quality_check',
    'Implementation tasks need max_turns >= 50. Tasks using the default 20 turns hit the limit despite completing the actual work — always set higher limits for build/code tasks.',
    'Alpha dashboard and context unification tasks completed work but hit the 20-turn default limit, causing reporting confusion. Fixed by setting max_turns=50+ on build tasks.',
    0.85
),
(
    'safety_flag',
    'When a task self-reports success but the output field is thin (< 100 chars), always verify by checking actual codebase artifacts before marking as reviewed.',
    'Multiple tasks reported completion with minimal output. Verification revealed some had partial completion. Principle: verify artifacts, not just task output text.',
    0.80
),
(
    'performance_pattern',
    'Context unification across Claude and Gemini brains is most effective when both read from the same context_builder.py function — divergent context injection paths cause identity drift.',
    'Multi-avatar architecture verified: both Claude (startup source) and Gemini (whatsapp source) use build_context_text(). Parity confirmed on purpose, priorities, working_memory, directives.',
    0.75
);
