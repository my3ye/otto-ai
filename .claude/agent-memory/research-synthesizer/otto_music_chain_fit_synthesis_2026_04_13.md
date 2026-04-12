---
name: otto_music_chain_fit_synthesis_2026_04_13
description: Otto Music technical direction & chain fit synthesis — Base confirmed, contracts=zero (grep-verified), RevenueRouter/DemandOracle are docs not code, 5-contract build order, appchain Phase 3+
type: project
---

## Key Insights (ranked by confidence × actionability)

1. **Base is the optimal Phase 1 chain for Otto Music** — Confidence: HIGH | Sources: 5
   - Sound.xyz (closest competitor) already on Base with music NFT infrastructure
   - ONEON (required artist auth) is EVM-based → zero rewrite needed
   - Existing oprlp-contracts/annotation-contracts deploy without modification
   - ERC-2981 + ERC721Royalty already in OZ lib at oprlp-contracts/lib/
   - Coinbase retail distribution = fan acquisition built-in; USDC native
   - Gas ~$0.01-0.30/tx suitable for NFT minting and batch settlement

2. **RevenueRouter, DemandOracle, ContributionRegistry do NOT exist as Solidity contracts** — Confidence: HIGH | Sources: grep-verified
   - CORRECTION to raw findings: described as "existing EVM Solidity contracts" — false
   - Grep `find /mnt/media/projects/ -name "RevenueRouter.sol"` → 0 results
   - They exist as architecture docs only (~/otto/docs/) + security audit scope
   - Security audit already completed (4 Critical, 6 High findings documented)
   - Must be written before any live Otto Music royalty payments

3. **Otto Music has zero smart contracts written — pure concept phase** — Confidence: HIGH | Sources: grep-verified
   - `grep -r "OttoMusic\|OTTM" /mnt/media/projects/ --include="*.sol"` → 0 results
   - Only artifacts: web UI (logo, project page), blog content, projects.ts definition
   - No dedicated repo under /mnt/media/projects/

4. **ERC-2981 royalty standard is immediately adoptable** — Confidence: HIGH | Sources: 2 (codebase + EIP)
   - OZ ERC2981.sol confirmed at oprlp-contracts/lib/openzeppelin-contracts/
   - ERC721Royalty.sol also present
   - Enforcement caveat: royalties are marketplace-voluntary; ERC-721C adds enforcement layer

5. **Solana is not viable for Phase 1 (full contract rewrite required)** — Confidence: HIGH | Sources: 3
   - NOT EVM → abandons entire oprlp-contracts + annotation-contracts stack
   - Audius precedent = Solana-native from day 0; Otto Music is EVM-native from day 0
   - Phase 2+ only if Wormhole bridge or separate Solana streaming node warranted

6. **DemandOracle Merkle batch settlement design solves per-stream economics** — Confidence: MEDIUM | Sources: 2 (docs)
   - Architecture doc specifies Merkle batch settlement for "music" vertical
   - Estimated ~$0.10-0.15 per full lifecycle on Polygon zkEVM (single-source, may be stale)
   - Security audit flagged DemandOracle trusted reporter as Critical-2 (trusted oracle = centralization risk)
   - Batch settlement off-chain → settle Merkle root on-chain = correct approach

7. **Appchain is the correct long-term architecture at 500K+ DAU** — Confidence: MEDIUM | Sources: 2
   - $45K/month vs $7.5M/month at 500K DAU scale; per-tx target <$0.0001
   - OP Stack or ZK Stack both viable (Lens Chain ZK Stack precedent)
   - Requires scale first; Phase 3+ timeline

8. **Sound Protocol pattern (non-upgradeable song contracts + factory/minimal proxy) is the right architecture primitive** — Confidence: MEDIUM | Sources: 1 authoritative
   - Songs as atomic unit, not albums
   - Factory + minimal proxy = cheap deployment per track
   - Base-native = aligns with chain recommendation
   - Permissionless non-upgradeable = aligns with Otto Music sovereignty ethos

## Contradictions / Uncertainties

- **"Existing EVM Solidity contracts" claim in raw findings**: RevenueRouter, DemandOracle, ContributionRegistry are DESIGN DOCS, not deployed contracts. Critical correction — do not plan on these being available for integration without a contract implementation sprint first.
- **Polygon zkEVM $0.10-0.15 estimate**: Single internal source, Polygon zkEVM is sunsetting in favor of Polygon AggLayer — estimate may be stale. Base gas estimates from web sources (~$0.05-0.30) are more current.
- **DemandOracle trusted reporter model**: Security audit flagged as Critical finding C2. Trustless per-stream settlement at Spotify-scale remains an unsolved architecture problem. Batch Merkle approach mitigates but doesn't eliminate trust.
- **Neo4j unavailable during retrieval**: Knowledge graph returned 500 error. Ecosystem relationship mappings (ONEON, Tusita, DPC) may be incomplete.

## Recommended Actions (top 3)

1. **Formally decide Base as Phase 1 chain and write a chain decision record** — Expected impact: removes architectural ambiguity blocking all contract work; aligns Otto Music with Sound.xyz ecosystem and Coinbase distribution
2. **Write Otto Music contract spec**: MusicTrack.sol (ERC-1155 + ERC-2981), MusicFactory.sol (Sound Protocol minimal proxy pattern), stub RevenueRouter integration interface — Expected impact: enables first contract implementation sprint; ERC-2981 already in OZ lib, minimal bootstrap cost
3. **Implement RevenueRouter.sol + DemandOracle.sol** addressing Critical findings C1 (role concentration) and C2 (trusted reporter oracle) from ~/otto/docs/on-chain-security-audit-2026-03-28.md — Expected impact: unblocks live royalty payments across ALL EVM products (Otto Music, ONEON, 505 Systems)

## Evidence Quality Assessment

Coverage: PARTIAL — Product definition, chain comparison, competitive landscape, and existing lib verification are solid. AI Studio, discovery staking, and streaming oracle architecture have zero codebase coverage.
Source reliability: HIGH for chain fees (web, 2026), HIGH for codebase grep results, MEDIUM for internal architecture docs (pre-implementation specs, not deployed code).
Gaps: (1) Neo4j unavailable — ecosystem relationship graph missing. (2) No deployed contract addresses. (3) AI Studio architecture entirely undefined.

## Compressed Handoff (≤1000 tokens)

**Otto Music Phase 1 — Base (confirmed fit):**
- EVM-native from day 0 → oprlp-contracts/annotation-contracts deploy as-is
- ONEON artist identity = EVM requirement met
- Sound.xyz on Base = music NFT ecosystem already exists there
- ERC-2981 + ERC721Royalty in OZ lib at oprlp-contracts/lib/ (ready to inherit)
- ERC-721C for royalty enforcement (not yet in lib — needs addition)
- Solana = Phase 2+ only (full rewrite cost prohibitive now)

**CRITICAL CORRECTION — nothing is deployed yet:**
- RevenueRouter.sol, DemandOracle.sol, ContributionRegistry.sol: ZERO .sol files in /mnt/media/projects/ — grep-verified. Architecture docs + security audit exist; contracts do not.
- Otto Music contracts: ZERO .sol files — concept-phase only.
- Account Abstraction/paymaster: ZERO .sol files — not yet implemented.

**Contract architecture to build (priority order):**
1. MusicTrack.sol (ERC-1155 + ERC-2981) — track editions, royalty info
2. MusicFactory.sol (minimal proxy pattern, Sound Protocol model) — cheap per-track deploy
3. RevenueRouter.sol — atomic payment split (5% protocol, 3% governance, 92% contributors)
4. DemandOracle.sol — Merkle batch settlement, music vertical, address C2 trusted reporter risk
5. ContributionRegistry.sol — contributor pool management

**Standards to adopt:**
- ERC-2981 (royalty signal, OZ ready) ✓
- ERC-1155 (track editions) — needs addition
- Sound Protocol minimal proxy factory pattern
- EIP-712 structured signatures for off-chain stream attestations
- ERC-4337 (AA/paymaster for gasless fan UX) — needs implementation

**Gaps (all grep-verified):**
- Otto Music contracts: 0 .sol files (`grep -r "OttoMusic\|OTTM" /mnt/media/projects/ --include="*.sol"`)
- RevenueRouter/DemandOracle: 0 .sol files (`find /mnt/media/projects/ -name "RevenueRouter.sol"`)
- StreamOracle/off-chain indexer: 0 matches (`grep -r "StreamOracle\|stream.*oracle" --include="*.sol"`)
- AI Studio architecture: 0 matches (`grep -r "MusicStudio\|audio.model" --include="*.sol" --include="*.py"`)
- Discovery staking: 0 matches (`grep -r "discovery.*stak\|DiscoveryStaking" --include="*.sol"`)
- ERC-4337 paymaster: 0 non-lib matches (`grep -r "paymaster" --include="*.sol" | grep -v lib`)

**Competitor positioning gap Otto fills:**
- Audius: streaming speed (Solana) + 90% rev; weak: no physical/event layer, ETH governance lag
- Sound.xyz: NFT ownership + Base; weak: no per-play royalties, no AI studio
- Royal: royalty tokenization only, no platform
- Otto Music unique: all 4 layers (manage + play + create + live) + ONEON sovereign identity + MY3YE ecosystem compounding + $OTTM discovery incentive

**Long-term path:** OP Stack or ZK Stack appchain at 500K+ DAU ($45K vs $7.5M/month). Lens Chain ZK Stack = precedent. Phase 3+.

## Memory Write Token
memory_write_token: 2c461560-0ad6-4239-81c3-17c909af7b91
