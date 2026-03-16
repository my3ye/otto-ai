---
name: webassist_supabase_schema_not_run
description: WebAssist wizard 500 error caused by Supabase configured but schema migrations not run
type: project
---

Root cause: Supabase env vars (NEXT_PUBLIC_SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY) were configured in Vercel, but the database schema migrations were never run. The wizard_completions table didn't exist. The code returned 500 instead of gracefully falling back.

**Why:** The supabase.co project was created and credentials were added to Vercel env vars, but the SQL schema (at `/mnt/media/projects/web-assist/supabase-full-schema.sql`) was never executed in the Supabase dashboard SQL editor.

**How to apply:** When WebAssist wizard submission returns 500 with "Could not find the table 'public.wizard_completions' in the schema cache" — run the full schema SQL at https://app.supabase.com/project/dxptgrftyvsxabukvdlw/sql/new using the file `/mnt/media/projects/web-assist/supabase-full-schema.sql`.

Fix applied (commit 9ec2022): Changed DB error from 500 → graceful fallback (200 + WhatsApp notify + Vercel log). Once Mev runs the schema SQL, leads will persist to DB automatically with no further code changes needed.
