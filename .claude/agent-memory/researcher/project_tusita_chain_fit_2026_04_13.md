---
name: Tusita Technical Direction & Chain Fit (2026-04-13)
description: Research pipeline complete — chain selection, Phase 0 contract scope, CS Registry design requirement, capital blockers for Tusita sovereign island project
type: project
---

## Pipeline: COMPLETE — 8.0/10

**Date:** 2026-04-13
**Memory token:** b435a5d4-ad67-432c-9d10-f41d522156ba
**Research note ID:** 744f4cfb-f8f9-4996-8587-e3c2c7db7297
**DB memory IDs:** 2d45b9de, ab0ed5c5, baf853fb, 14b9cad0, c16ecd38, f95cee33, ee6a262a, db4f3556
**Validation:** MINOR_CHANGES 8.0/10 — 2 warnings + 1 suggestion applied

---

## Chain Decision

**Base L2 = CONFIRMED** — ecosystem consensus (zkPresence/SOS/ONEON/Otto Music all on Base). No competing chain in tusita-web codebase. tokenomics.ts "Base governance voting" is Islander tier feature label (governance access), not a chain declaration.

---

## Phase 0 Status: GREENFIELD

Zero on-chain implementation:
- 0 `.sol`, `.rs`, `.circom`, `.nr` files in tusita-web
- 0 contract tooling (Hardhat/Foundry/Aragon) referenced
- Full product architecture in TypeScript data files: `tokenomics.ts`, `governance.ts`, `technology.ts`, `roadmap.ts`

---

## Key Design Finding: CSRegistry ≠ DPCRegistry Fork

**CRITICAL:** DPCRegistry.sol stores a single composite score (`uint128 rawScore`). Tusita CS has 3 independently weighted dimensions:
- Capital: 30%
- Resources: 25%
- Labour: 45%

These require independent per-dimension tracking + weighted aggregation at read time. Forking DPCRegistry as-is collapses all 3 dimensions to one unweighted score — **breaks governance model**.

**Correct approach:** Use DPCMath LazyDecay as the decay component. Design new 3-dimension weighted CS storage schema first, then implement CSRegistry.sol.

---

## Prioritized Actions

1. **P0:** Write `on-chain-architecture.md` for tusita-web — declare Base, document Phase 0 contract scope, unblocks parallel development
2. **P1:** Build $TUSITA ERC20 (35% community + 25% treasury, vesting schedule) + Founding IslanderNFT ERC721 (CS-gated dynamic metadata) on Base Sepolia
3. **P2:** Design 3-dimension CS Registry storage schema (Capital/Resources/Labour, weighted aggregation at read time, LazyDecay component)
4. **Parallel (Mev action):** Register Tusita legal entity — gates all UNDP/ADB/SEZ capital channels

---

## Capital Blockers

- Legal entity registration: **hard gate** for UNDP Green Bond, ADB $100M sustainable tourism, Port City SEZ
- Contract dev: **not blocked** by entity — Base Sepolia deployment independent
- RWA tokenization (Plume Network): **deferred to Phase 4 (60+ months)**

---

## Patches Applied

1. **Insight 5 (Aragon source):** Removed fabricated "1 codebase" source — zero Aragon refs in tusita-web/src/. Source corrected to "SOS-confirmed, extrapolated."
2. **Insight 3 + Action 3 (DPCRegistry fork scope):** "Direct fork" → "fork DPCMath LazyDecay decay math; design new 3D CS storage schema first."
3. **Insight 7 (SP1 label):** SP1 now labeled "extrapolated from zkPresence, not in Tusita codebase."

**Why:** Validator grep-verified all claims against tusita-web and oprlp-contracts. Two fabrications corrected, one extrapolation properly labeled.
