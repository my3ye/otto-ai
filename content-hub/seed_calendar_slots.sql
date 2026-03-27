-- Seed calendar_slots from the mev_start_here_schedule.csv audit data.
-- Run AFTER migration 077. Run ONCE.
--
-- This maps the 74-entry schedule into calendar_slots, setting:
-- - platform from the CSV platform column
-- - status from the content's current status (ready→ready, published→posted, else queued)
-- - pinned=TRUE for the 4 ready articles (immediate action items)
--
-- The CSV has columns: date, type, action, project, title, status, platform, content_length, id
-- We use content.id directly since the audit CSV provides it.

-- Step 1: Insert slots for all content items that have scheduled dates in content table
INSERT INTO calendar_slots (content_id, slot_date, slot_position, platform, action, status, pinned)
SELECT
    c.id,
    c.scheduled_at::date,
    ROW_NUMBER() OVER (PARTITION BY c.scheduled_at::date ORDER BY c.content_type DESC, c.title) - 1,
    CASE
        WHEN c.content_type = 'article' THEN 'paragraph'
        ELSE 'x'
    END,
    'publish',
    CASE
        WHEN c.status = 'ready' THEN 'ready'
        WHEN c.status = 'published' THEN 'posted'
        ELSE 'queued'
    END,
    FALSE
FROM content c
WHERE c.archived = FALSE
  AND c.scheduled_at IS NOT NULL
ON CONFLICT (content_id, slot_date, platform) DO NOTHING;

-- Step 2: Insert known ready articles that LACK scheduled_at
-- These are the "start here" items — schedule them starting tomorrow
INSERT INTO calendar_slots (content_id, slot_date, slot_position, platform, action, status, pinned)
SELECT
    c.id,
    CURRENT_DATE + (ROW_NUMBER() OVER (ORDER BY c.title))::int,
    0,
    'paragraph',
    'publish',
    'ready',
    TRUE  -- pinned = start here
FROM content c
WHERE c.archived = FALSE
  AND c.content_type = 'article'
  AND c.status = 'ready'
  AND c.scheduled_at IS NULL
  AND NOT EXISTS (
      SELECT 1 FROM calendar_slots cs WHERE cs.content_id = c.id
  )
ON CONFLICT (content_id, slot_date, platform) DO NOTHING;

-- Step 3: Pin the published articles too (if any exist as slots)
UPDATE calendar_slots
SET pinned = TRUE
WHERE content_id IN (
    SELECT id FROM content
    WHERE status IN ('ready', 'published')
      AND content_type = 'article'
      AND archived = FALSE
)
AND status IN ('ready', 'posted');

-- Verify
SELECT
    s.slot_date,
    s.platform,
    s.status,
    s.pinned,
    c.title,
    c.content_type,
    c.project_id
FROM calendar_slots s
JOIN content c ON c.id = s.content_id
ORDER BY s.slot_date, s.slot_position
LIMIT 20;
