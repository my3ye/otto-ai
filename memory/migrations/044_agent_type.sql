-- Add agent_type column to tasks table for specialist agent routing
-- Valid values: researcher, coder, reviewer, debugger, architect, memory-curator, or NULL (default)
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS agent_type TEXT DEFAULT NULL;
