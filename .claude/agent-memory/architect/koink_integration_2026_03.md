---
name: koink_integration_2026_03
description: Koink integration module architecture — /koink/* routes, migration 067, module layout, Phase 0/1 plan
type: project
---

Koink integration module designed (2026-03-23). Full design at ~/otto/docs/koink-integration-architecture-2026-03-23.md.

**Why:** Mev directive — implement Koink first, then ONEON and others autonomously. Koink.fun is our platform implementing the $KOINK Standard (chain-agnostic tokenomics). OMS crypto engine only had a stub.

**Phase 0 (immediate, no contracts):**
- Migration 067: `koink_tokens`, `koink_dhm_positions`, `koink_treasury_events` tables + extend `token_launches` with 10 KOINK columns
- New module `otto/memory/koink/` — standard.py, launch.py, dhm.py, treasury.py
- New router `otto/memory/routes/koink.py` — 9 endpoints under `/koink/*`
- Feature flag `koink_enabled` in config.py
- Extend `LaunchRequest` in crypto.py + NL parser examples

**Phase 1 (EVM contracts, follow-on):**
- KoinkToken.sol (ERC-20 + anti-whale + graduated sell tax + treasury hook)
- KoinkLauncher.sol (Chainlink VRF v2.5 consumer)
- DiamondHandsVault.sol (DHM position tracking)
- KoinkTreasury.sol (Gnosis Safe multi-sig wrapper)
- Async deploy pipeline via task queue
- **Blocker:** OWS deploy wallet — Mev must register before Phase 1 goes live

**Key decisions:**
- New `/koink/*` router (NOT extending `/crypto/launch`) — Koink lifecycle is distinct
- Async deploy: POST → pending record → task queue → status poll
- `koink_tokens` table is authoritative Koink record (FK to `token_launches` for unified view)
- DHM tracked off-chain in `koink_dhm_positions`; flagged `synthetic=true` until contracts live

**Cost:** Phase 0 ~$9-13, Phase 1 ~$15-20

**How to apply:** When scoping Koink implementation tasks, use this module structure. `/crypto/launch` remains generic — Koink-specific work goes through `/koink/*`.
