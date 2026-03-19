---
name: bankr_integration_2026_03
description: BANKR Bot full integration architecture for Otto & OMS — trading automation, portfolio, signals, token launch, LLM gateway. Designed 2026-03-19.
type: project
---

Full architecture designed at ~/otto/docs/bankr-integration-architecture.md (2026-03-19).

BANKR Bot is an AI-powered NL crypto trading platform (api.bankr.bot, `bk_...` API key) with Agent API, cross-chain wallets (Privy), LLM Gateway (llm.bankr.bot), and BANKR Signals (on-chain verified signal publishing).

**Why:** Mev directive — integrate all BANKR features into Otto & OMS, no artificial scope constraints.

**Architecture summary (5-layer stack):**
1. BANKR Client Module (`otto/memory/bankr/` — client.py, signals.py, llm_gateway.py)
2. Memory API routes (`/bankr/*` — 11 endpoints covering trade, portfolio, history, signals, launch)
3. DB migration (058_bankr.sql — bankr_trades, bankr_signals, bankr_jobs tables)
4. OMS Frontend (interfaces/web-next/src/app/bankr/page.tsx — portfolio + trade terminal + signals board)
5. Config (BANKR_API_KEY, BANKR_ENABLED, BANKR_SIGNALS_ENABLED, BANKR_LLM_GATEWAY_ENABLED)

**Key decisions:**
- All execution feature-flagged behind BANKR_ENABLED=false until Mev provides API key
- Async job pattern: 30s inline poll, overflow to Otto task queue for slow operations
- NL prompt-composer layer generates safe prompts (prevents BANKR parser ambiguity)
- BANKR Signals is an active revenue path (publish Otto's whale-convergence alpha with TX hash proofs)
- Token launch via Doppler (Base) is preferred mechanism for $KOINK — fair launch, 57% creator fees, anti-sniper
- LLM Gateway routing is Phase 3 (requires cost/latency benchmarking first)

**Phases:** Phase 1 ($6–8) → Phase 2 ($3–4) → Phase 3 ($5–6). Total ~$14–18 across 5 tasks.

**Critical blocker:** BANKR_API_KEY (bk_...) is Mev-held. All phases complete architecturally; execution unblocks when Mev provides key.

**How to apply:** When creating implementation tasks from this architecture, use the phased breakdown in the docs file. Start with Phase 1 DB migration + client module + routes. Phase 2 is purely frontend.
