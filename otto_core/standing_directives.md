# Standing Directives Reference
*Last updated: 2026-03-27 — Consolidated from session decisions, Mev directives, and research findings.*

This document is the ground truth for all standing directional decisions. Agents must adhere to these when relevant. Cross-reference with CONSTITUTION.md for identity/mission boundaries.

---

## 1. Sovereign Advertising Philosophy

**Decision**: Otto ecosystems embrace advertising — not avoid it. The framing is sovereign and privacy-first, not anti-ad.

**The model**:
- Users own their on-chain interest profiles. They **opt in** to sharing interests in exchange for relevant ads and direct compensation.
- Advertisers pay into **transparent on-chain promotion pools** (DAO-governed). No dark auctions, no hidden bidding.
- AI handles filtering and categorization **openly** — logic is auditable, not black-box.
- What we reject is **involuntary surveillance advertising** (tracking without consent, opaque data brokers). We do NOT reject advertising itself.

**Applies to**: otto-music, otto-market, oneon, otto-billboards, any new MY3YE product copy, marketing materials.

**Committed**: `3defc4b` (2026-03-17)

---

## 2. Otto Devices Lineup

**Current lineup** (Ottolabs, Phase 4):

| Device | Function | Target Price |
|---|---|---|
| Otto Band | Biometrics / wellness tracking | — |
| Otto Glasses | AR vision layer — in-field Otto agent display, spatial compute, environmental awareness, ONEON-linked | $199 |
| Otto Ring | Payments / identity / health anchor — tap to pay (ONEON-native), biometric presence confirmation, SpO2/HR monitoring | $69 |

**Applies to**: Ottolabs YAML, roadmap docs, OMS universe browser, any product/device copy.

**Committed**: `29b8ce5` (2026-03-17)

---

## 3. New-Environment Authentication Checklist

When Otto is restored to a new VM or after a system clone, the following services **must** be re-authenticated before Otto can operate normally. Run `otto-env-check.sh` to verify all at once.

| Service | Check command | Re-auth command |
|---|---|---|
| GitHub CLI | `gh auth status` | `gh auth login` |
| Vercel CLI | `vercel whoami` | `vercel login` |
| GCP / gcloud | `gcloud auth list` | `gcloud auth login` |
| npm registry | `npm whoami` | `npm login` |
| WhatsApp (Baileys) | Check `interfaces/whatsapp/auth_state/` exists | Run `node login.mjs` → scan QR |
| `.env` secrets | Verify `~/memory/.env` has all keys (OpenAI, Supabase, etc.) | Manually restore from backup or Mev |
| systemd timers | `systemctl list-timers \| grep otto` | `systemctl enable --now otto-heartbeat.timer otto-reflection.timer` |
| Docker containers | `docker ps` — all 3 healthy (postgres, neo4j, graphiti) | `cd ~/memory && docker compose up -d` |
| Memory API | `curl localhost:8100/health` | `systemctl restart otto-memory` |

**Script**: `~/otto/otto-env-check.sh` (outputs JSON + human-readable status for all checks)

**API endpoint**: `GET /backup/env-check` (OMS-accessible)

**Committed**: `1cc062d` (2026-03-17)

---

## 4. Backup / Restore System

**One-command backup**: `~/otto/otto-backup.sh [output_dir]`
- Saves: ~/otto, ~/memory (including .env), ~/interfaces, systemd units, Docker volume dumps
- Output: `/mnt/media/backups/otto-backup-YYYYMMDD-HHMMSS.tar.gz`
- Restore: `~/otto/otto-restore.sh <archive>` — auto-runs env-check after restore

**OMS panel**: `mev.otto.lk/backup`
- Shows last backup timestamp, archive list, trigger button
- Shows env-check results after a restore

**Committed**: `831c231`, `1cc062d`

---

## 5. Social / Project Calendar Responsiveness

**Decision**: Both the social calendar and project calendar pages in OMS must be fully responsive on mobile (375px+).

**Root cause fixed (social calendar)**: Stats bar was a single non-wrapping flex row — overflowed on mobile. Fixed with `flex-wrap`, `min-w-0`, responsive `px-4 md:px-6`.

**Committed**: `58b9426a` (2026-03-17)

**Status**: Social calendar — fixed. Project calendar — **still pending** (noted for next responsiveness pass).

---

## 6. Context Rot — Research Findings & Otto Implications

**Source**: https://research.trychroma.com/context-rot (Chroma Research, 2026)

**Key findings**:
1. LLMs degrade non-linearly as input length grows — even on trivial tasks — despite passing standard benchmarks.
2. Lower Q&A semantic similarity = steeper degradation with longer context.
3. Near-match distractors compound failure **multiplicatively**, not additively.
4. Incoherent/shuffled haystacks outperform structured logical text (structure doesn't help retrieval).
5. Combining retrieval + reasoning over 113k tokens collapses performance vs 300-token filtered context.

**Otto improvements implemented / queued**:
- S-MMU slice ordering: inject relevant slices at context **START**, not mid-context
- Retrieval-reasoning split: decouple into retrieval agent + clean-context reasoning agent
- Distractor pruning: drop near-but-not-exact S-MMU matches via similarity threshold
- Context budget enforcement: keep S-MMU under 50% capacity (target: 20k/200k)
- Memory format: factual bullet lists preferred over narrative paragraphs

**Stored in DB**: Semantic memory IDs `98dd07d8`, `9d5bab02`, `e9f44e27`; research note `e8229507`

---

## 7. RLM (Recurrent LM) — Research Findings & Otto Implications

**Source**: arXiv 2512.24601

**Key findings applicable to Otto**:
1. **Long document processing**: Instead of upfront full-doc ingestion, give Otto doc metadata + access functions — let it recursively query slices as needed. Directly addresses WhatsApp document handler limitations.
2. **S-MMU L1 strategy**: RLM pattern validates Otto's current approach (position-anchored, chunked access) — continue reinforcing.
3. **Lost-in-the-middle**: Confirmed independently — LLM performance degrades 30%+ for info placed in middle of long context. Otto S-MMU now implements position bias anchor at context end.

**Status**: Research complete. Implementation queued in backlog.

---

## 8. Codebase Anti-Whale → Meritocratic Fairness Reframe

**Decision**: All "anti-whale" language across WebAssist and universe docs has been reframed to meritocratic fairness / equal-access contribution language.

**New framing**: The system rewards contribution and aligned behavior, not financial position. Large holders have no structural advantage over contributors.

**Committed**: `ec01367`, `77414dc` (2026-03-17)

**QA status**: Approved.

---

## 9. WhatsApp Document Handler

**Fix**: Handler now downloads documents sent by Mev (PDF, DOCX, TXT) and extracts text for LLM analysis. Previously documents were acknowledged but content ignored.

**Committed**: `93ab4a4`

**QA status**: Pending as of 2026-03-17.

---

## 10. Memory Capsules — ONEON Personal Intelligence Layer

**Decision (from Mev, 2026-03-17):** Every ONEON participant will have Memory Capsule layers of personal memory. These are the core product mechanic of ONEON's intelligence layer.

**Specification:**
- **Private by default** — capsules are not visible unless the owner explicitly shares layers
- **Monetizable** — owners can share specific layers in exchange for $KOIN compensation
- **Quality-linked earnings** — higher-quality, more useful capsules earn more when shared
- **LLM output quality tied to capsule depth** — deeper capsules produce better AI outputs for the owner; this is the core value proposition for building your capsule
- **The chain is the neural network** — Memory Capsules live on-chain as encrypted records. The ONEON chain is the continually-evolving collective intelligence layer. Each capsule is a node in that evolving network.

**Architecture relationship:**
- Capsule storage = Otto Distributed Storage Nodes (encrypted shards, owner holds key)
- Capsule identity = ONEON Layer 1 (self-sovereign DID)
- Capsule privacy = ONEON Layer 4 (E2E encrypted)
- Capsule monetization = ONEON governance (pricing standards, quality validation)

**Cross-references:**
- Otto AI distributed architecture: proof-of-concept of how capsule storage works technically
- ONEON roadmap Phase 3: Memory Capsules launch milestone
- Distributed Otto Architecture: Storage Node section

**Applies to:** ONEON product copy, ONEON roadmap, Otto AI architecture docs, investor materials, any feature touching identity + memory + monetization.

---

## 10. Contributor Task Protocol

**Decision (Mev directive, 2026-03-27):** Any task or action item assigned to Mev or any other contributor MUST be placed on the OMS task board as a formal task. Never rely on memory, semantic facts, or chat reminders alone.

**The rule:**
- Use `POST /tasks` with `owner=mev` (for Mev) or `owner=<contributor_name>` (for others)
- Every human-assigned task must include: actionable title, full context in prompt (what + why + how long), correct priority, and `status=pending`
- Before sending a WhatsApp nudge about a pending action, check if the task already exists: `GET /tasks?owner=mev&status=pending`
- The OMS board at mev.otto.lk is the **canonical source of truth** for all contributor-facing work items

**Applies to:** heartbeat (blocker surfacing), task creation logic, any agent that identifies work for a human contributor.

**Committed:** `standing_directives.md` update (2026-03-27). Semantic memory ID: `84b236ea`.

---

## Notes on Adherence

- This document is updated when Mev gives a new directional decision via WhatsApp or in-session.
- The heartbeat agent should reference this document when context rot or direction drift is suspected.
- All agents should treat entries here as decided — no re-debating unless Mev explicitly revisits.
- File path: `~/otto/otto_core/standing_directives.md`
