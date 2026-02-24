-- Migration 038: Consolidate memory categories from 24 → 12 canonical categories
-- Canonical set: identity, mission, decision, infrastructure, project, learning,
--                relationship, system, research, capability, directive, observation
-- Run: 2026-02-25

-- market_research → research (same domain, just a sub-label)
UPDATE semantic_memories SET category = 'research' WHERE category = 'market_research';

-- self_improvement → capability (Otto's capability/learning improvements)
UPDATE semantic_memories SET category = 'capability' WHERE category = 'self_improvement';

-- alpha → project (crypto trading project)
UPDATE semantic_memories SET category = 'project' WHERE category = 'alpha';

-- characters → project (Bobby, PiPi etc. are brand/product projects)
UPDATE semantic_memories SET category = 'project' WHERE category = 'characters';

-- pipeline_status → system (status of internal systems/pipelines)
UPDATE semantic_memories SET category = 'system' WHERE category = 'pipeline_status';

-- brand → project (brand is a type of project)
UPDATE semantic_memories SET category = 'project' WHERE category = 'brand';

-- procedure → capability (procedures are capabilities/skills)
UPDATE semantic_memories SET category = 'capability' WHERE category = 'procedure';

-- working_memory → system (internal memory system state)
UPDATE semantic_memories SET category = 'system' WHERE category = 'working_memory';

-- reasoning_chain → system (internal reasoning/orchestration artifacts)
UPDATE semantic_memories SET category = 'system' WHERE category = 'reasoning_chain';

-- architecture → infrastructure (system design is infrastructure knowledge)
UPDATE semantic_memories SET category = 'infrastructure' WHERE category = 'architecture';

-- product → project (products are projects)
UPDATE semantic_memories SET category = 'project' WHERE category = 'product';

-- project_context → project
UPDATE semantic_memories SET category = 'project' WHERE category = 'project_context';

-- narrative → observation (narrative summaries are observations)
UPDATE semantic_memories SET category = 'observation' WHERE category = 'narrative';

-- implementation → capability (implementations are capabilities)
UPDATE semantic_memories SET category = 'capability' WHERE category = 'implementation';

-- goal → mission (goals are sub-missions)
UPDATE semantic_memories SET category = 'mission' WHERE category = 'goal';

-- own_model → project (building Otto's own model is a project)
UPDATE semantic_memories SET category = 'project' WHERE category = 'own_model';

-- webassist → project (WebAssist is a product/project)
UPDATE semantic_memories SET category = 'project' WHERE category = 'webassist';

-- general → observation (general facts/observations)
UPDATE semantic_memories SET category = 'observation' WHERE category = 'general';

-- Verify result
SELECT category, COUNT(*) FROM semantic_memories GROUP BY category ORDER BY count DESC;
