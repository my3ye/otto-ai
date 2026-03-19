---
name: bankr_integration_2026_03
description: BANKR Bot features — now implementing natively in-house (no Bankr API). Full native crypto engine design. Supersedes previous bankr-integration-architecture.md.
type: project
---

**DIRECTION CHANGE (2026-03-19):** Mev directive — "Don't connect to Bankr. Implement the features in house in our system." The Bankr API integration approach is cancelled. All capabilities are now being built natively.

**Previous design** (cancelled): ~/otto/docs/bankr-integration-architecture.md — used api.bankr.bot external API, required BANKR_API_KEY from Mev.

**New design** (active): ~/otto/docs/crypto-native-architecture-2026-03-19.md — fully sovereign native implementation.

**Why:** Full sovereignty — no external API dependency, no API key blocking deployment. CDP AgentKit already integrated and authenticated.

**Native Architecture summary (5-layer stack):**
1. Native Crypto Engine (`otto/memory/crypto/` — nlparser.py, executor.py, price_feed.py, portfolio.py, monitors.py, signals.py, launch.py)
2. Memory API routes (`/crypto/*` — 13 endpoints: parse, execute, portfolio, price, monitors, signals, launch)
3. DB migration (059_crypto_native.sql — crypto_trades, price_monitors, crypto_signals, token_launches tables)
4. OMS Frontend (interfaces/web-next/src/app/crypto/page.tsx — NL terminal + portfolio + signal board + monitors)
5. Config (CRYPTO_ENABLED, CRYPTO_EXECUTION_ENABLED, ALCHEMY_API_KEY, ZEROX_API_KEY — no blocking keys)

**Key decisions:**
- CDP AgentKit (already integrated) replaces Privy — EVM wallet execution ready now
- Claude (ourselves) does NL parsing — no external NL API needed
- 0x Swap API for DEX aggregation — free for quotes, 1% fee on swaps
- CoinGecko for price data — free tier, no key required
- Price monitors table + heartbeat polling replaces Bankr's limit/DCA/SL scheduler
- Native signal board (/crypto/signals) replaces bankrsignals.com dependency
- bankr_* tables in DB remain (empty) — new crypto_* tables are the active system

**Phases:** Phase 1 (Foundation, $7–8) → Phase 2 (Execution, $9–10) → Phase 3 (Signals & UI, $9–10). Total ~$25–28 across 9 tasks.

**No blockers:** CDP keys already configured. CoinGecko needs no key. Implementation can start immediately.

**How to apply:** Use crypto-native-architecture-2026-03-19.md as the design doc. Implementation starts with Task 1 (DB + Config). `/crypto/*` namespace for all new routes. Do NOT create `/bankr/*` routes.
