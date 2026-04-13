---
name: tusita_chain_fit_synthesis_2026_04_13
description: Tusita technical direction & chain fit synthesis — Base confirmed, 10 contracts mapped across 4 phases, CS Registry = keystone, zero contracts exist (Phase 0), legal entity = capital blocker
type: project
---

## Key Insights (ranked by confidence × actionability)

1. **Zero contracts exist — Phase 0 is the real starting point.** No `.sol`, `.rs`, `.circom`, or `.nr` files in tusita-web. No contract tooling (Hardhat/Foundry/Aragon) referenced anywhere. Product architecture fully defined in TypeScript data files, entirely unimplemented on-chain. — Confidence: HIGH | Sources: grep (empty ×4), 3 codebase data files

2. **Base is the correct primary chain, with implicit alignment already in codebase.** Otto-wide policy (Base = default). "Base governance voting" in tokenomics.ts Islander benefits = feature label (grep-confirmed), NOT a chain declaration. No competing chain named anywhere. — Confidence: HIGH | Sources: 2 memory (31b21b3a, 38fcf7aa), 1 codebase grep

3. **CS Registry is the architectural keystone — reuse oprlp LazyDecay pattern.** CS (Capital 30% + Resources 25% + Labour 45%) drives governance weight, NFT tier evolution, revenue distribution. Structurally isomorphic to SOS DPC. DPCRegistry + LazyDecay from oprlp-contracts = direct fork path. — Confidence: HIGH | Sources: 3 codebase files, 1 memory

4. **4-tier NFT with dynamic CS-driven metadata = Phase 0 product AND capital mechanism.** Caribbean CBI template ($270K entry, Grenada precedent). Phase 0 = Founding IslanderNFT ERC721 + $TUSITA ERC20 (35% vesting). — Confidence: HIGH | Sources: 3 codebase files, 1 memory

5. **Aragon OSx = proven DAO tooling (SOS-confirmed).** CS-weighted voting plugin + Council of Stewards (9 elected, quarterly). — Confidence: MEDIUM | Sources: 1 memory, 1 codebase

6. **Legal entity registration = hard prerequisite for capital + RWA deployment.** UNDP/ADB/SEZ all gated. Smart contracts buildable without this. — Confidence: HIGH | Sources: 3 memory

7. **Sybil risk: Capital 30% = plutocracy vector.** arXiv 2505.09313 (LightGBM, precision 0.9428) for labour verification. SP1 for ZK contribution proofs. — Confidence: MEDIUM | Sources: 1 paper, 1 codebase

8. **RWA land tokenization = Phase 4 (60+ months).** Plume Network viable then but irrelevant now. — Confidence: HIGH | Sources: 1 codebase, 1 web

## Contradictions / Uncertainties
- "Base governance voting" = feature label, not chain selection — requires explicit architecture doc
- Energy DAO P2P trading: no protocol referenced, may slip Phase 2
- Tusita↔SOS shared governance: no formal spec

## Recommended Actions
1. Write `on-chain-architecture.md` + declare Base explicitly
2. Build Phase 0: $TUSITA ERC20 + IslanderNFT ERC721
3. Fork oprlp DPCRegistry + LazyDecay → Tusita CS Registry

## Contract Stack (10 contracts, 4 phases)
- Phase 0: $TUSITA ERC20 (35% vesting), IslanderNFT ERC721
- Phase 1: 4-tier NFT, CSRegistry (LazyDecay), Aragon OSx DAO
- Phase 2: RevenueDistributor, EnergyDAO, EnergyCredits ERC20
- Phase 4: RWARegistry (Plume or Base RWA)

## Evidence Quality
Coverage: PARTIAL | Source reliability: HIGH | Gaps: energy protocol, shared governance spec, out-of-band Mev decisions

## Memory Write Token
b435a5d4-ad67-432c-9d10-f41d522156ba
