-- Migration 092: Backfill relationship types on existing note_links
--
-- IMPL-07 follow-up: All 1514 existing links have relationship_type = 'related'
-- because the heuristic classification only applies to NEW link creation.
-- Original thresholds (0.95/0.85) were too high for actual data distribution
-- (max link_strength = 0.85, p90 = 0.825). Recalibrated to 0.83/0.78.
--
-- Thresholds match recalibrated _classify_relationship() in semantic.py:
--   sim >= 0.83 → 'extends'  (same topic, adding detail)
--   sim >= 0.78 → 'refines'  (same domain, different angle)
--   sim <  0.78 → 'related'  (keep default)
--
-- Note: contradiction detection requires content keyword analysis,
-- cannot be done in pure SQL. Those stay as 'related' and will be
-- classified correctly on any future link updates.

-- High-similarity links → extends
UPDATE note_links
SET relationship_type = 'extends'
WHERE link_strength >= 0.83
  AND relationship_type = 'related';

-- Medium-high similarity → refines
UPDATE note_links
SET relationship_type = 'refines'
WHERE link_strength >= 0.78
  AND link_strength < 0.83
  AND relationship_type = 'related';
