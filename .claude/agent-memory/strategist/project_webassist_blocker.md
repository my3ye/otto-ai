---
name: WebAssist Payment Blocker
description: WebAssist is code-complete with full payment flow built and deployed; only Mev action needed is running Supabase SQL migration
type: project
---

WebAssist payment flow is FULLY BUILT and deployed at webassist.ink. Stripe keys set, webhook registered, PaymentBanner integrated. Zero revenue because Mev has not yet run `supabase-full-schema.sql` (or `supabase-payment-migration.sql`) in the Supabase SQL Editor.

**Why:** Mev needs to personally access the Supabase dashboard for the WebAssist project and run the SQL file at /mnt/media/projects/web-assist/supabase-full-schema.sql.

**How to apply:** Do NOT create Otto tasks for this work. The blocker is not code — it is Mev's manual action in Supabase. Flag to Mev in every brief until resolved. The 3a8e267b task in the queue documents this.
