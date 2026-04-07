---
name: Infrastructure Critical Blockers
description: Two critical infrastructure failures discovered Apr 8 — Zoho email DOWN and OpenAI embeddings broken — both Mev-blocked but need urgent escalation
type: project
---

As of 2026-04-08:

**1. admin@otto.lk email is DOWN**
- Zoho trial expired around 2026-04-05 (task created Apr 3 noting "expires in 2 days")
- Both SMTP (554 error) and IMAP (ALERT) are blocked
- Email channel completely offline — affects external communications, OTPs, notifications
- **Why:** Zoho free trial ended; requires paid renewal or plan downgrade
- **How to apply:** Always escalate email channel status in daily brief. Do NOT attempt tasks that rely on admin@otto.lk until confirmed working. Alternative: ask Mev about backup SMTP setup.

**2. OpenAI embedding API broken**
- Out of credits since ~2026-04-01 (task created that day)
- `/semantic/remember` returns 500 — new memories cannot be stored with vectors
- `/semantic/search` returns empty results (can't compute query embedding)
- Fix dispatched 2026-04-08: null-embedding fallback so memories store without vectors
- **Why:** OpenAI account credits exhausted; Mev needs to top up at platform.openai.com
- **How to apply:** Semantic memory is in degraded state. Recent memories may not be searchable. After null-embedding fallback is deployed, writes will succeed but new memories won't appear in semantic search until OpenAI credits restored.
