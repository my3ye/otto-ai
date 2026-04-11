---
name: ZK Ecosystem Fit, Grants, and Launchpad Synthesis 2026-04-11
description: ZK ecosystem grants/launchpad opportunities for MY3YE projects (zkPresence, ONEON, Panik). Circuit gaps verified, grant matrix ranked, 90-day action path.
type: project
---

## Key Insights (ranked by confidence × actionability)

1. **zkPresence circuit has 4 `todo!()` panics blocking all production use** — Confidence: HIGH | Sources: 3 (codebase grep, memory b3550ce9, memory e5672287)
   - SHA-256: `fn sha256(_data)` stub at line 26 → `todo!("Wire up SP1 SHA-256")`
   - ECDSA: 3 `todo!()` panics at lines 70, 104, 121 — all attestation modes (QR, geohash, organizer) broken
   - FIX: wire `sha2` crate + SP1 secp256k1 precompile. 1-2 days of work.
   - CORRECTION from prior synthesis: `ZkPresence.t.sol` EXISTS with MockSP1Verifier and contract-level tests. "Zero tests" claim is STALE. Gap = no prover integration tests (real proof generation), not total absence.

2. **EF PSE Semaphore + Succinct Residency = highest-fit grants once circuit is fixed** — Confidence: HIGH | Sources: 4 (web, memory b74831a1, memory b3550ce9, semantic hits)
   - EF PSE: identity/privacy ZK tools, Semaphore precedent. Est. $25-50K. OPEN.
   - Succinct Residency: rolling applications, SP1-native projects preferred. Deliverable = shipped integration + writeup. No public portal — direct outreach.
   - BOTH require functional circuit first.

3. **ETHGlobal NY (June 12–14, 2026) = nearest high-value ZK event, 2 months away** — Confidence: HIGH | Sources: 2 (ethglobal.com web, capital sequencing memory)
   - ZK Proofs + AI×Crypto tracks. Sponsor bounties. Direct grant-equivalent.
   - zkPresence circuit fix must be done before this deadline.

4. **Gitcoin GG25 (Q2 2026) = multi-project community launchpad, register NOW** — Confidence: HIGH | Sources: 3 (memory grant queue, web retrieval, capital sequencing memory)
   - Quadratic matching. SOS Systems, ONEON, Otto all eligible.
   - Action: register at builder.gitcoin.co immediately — no functional circuit required.

5. **ONEON has ZERO ZK implementation** — Confidence: HIGH | Sources: 2 (codebase grep verified: `find oneon-web/ -name "*.rs" -o -name "*.circom" -o -name "*.nr"` = empty, memory decision)
   - SP1 P0 path is weeks not months. $0.04/proof. No chain migration needed.
   - Aztec/Noir: BLOCKED until July 2026 (critical vuln, v5 fix July). Do not deploy.
   - ZK Stack L3 RaaS: Q3 2026 appchain path (Lens Chain precedent).

6. **Panik has ZERO Solidity contracts** — Confidence: HIGH | Sources: 2 (codebase grep: `find panik-app-web/ -name "*.sol"` = empty; memory panik synthesis)
   - $PNK token = confirmed gap (grep: no .sol, no PNK references in source)
   - Soulbound NFT = confirmed gap (grep: no .sol, no SoulBound references)
   - OP Retro Funding ($3B distributed) = best capital path. Build usage first, retroactive claim.
   - SP1 for ZK credentials: P0 after circuit fix.

7. **Optimism RetroPGF is retroactive — Panik must ship first** — Confidence: HIGH | Sources: 3 (retropgf.com, memory panik synthesis, capital sequencing)
   - Round 6 = 5M OP (governance focus). Round 7 TBD.
   - Strategy: ship Panik on Base, build active users, then apply retroactively.

8. **ZK proof market macro: $7.59B by 2033, 22.1% CAGR — 2026 is production inflection** — Confidence: MEDIUM | Sources: 2 (memory b3550ce9, ZK market research)
   - SP1 now secures $4B+ assets, 6M+ proofs across Optimism/Base/Polygon/Celestia.
   - FPGA 20x boost roadmap Q2 2026 (Succinct).

9. **Starknet Seed Grants ($25K STRK) and ZKsync Community Pilot (20M ZK tokens) = WRONG STACK** — Confidence: HIGH | Sources: 2 (web retrieval, architecture decision memories)
   - MY3YE uses SP1/Base/EVM stack. Cairo/Starknet and ZKsync are separate ecosystems.
   - Pursuing these would require full stack pivot. LOW priority.

## Contradictions / Uncertainties

- **"Zero tests" claim in prior synthesis vs. current codebase**: ZkPresence.t.sol with Foundry tests EXISTS now. Prior synthesis (zkpresence_competitive_synthesis_2026_04_11) said "no tests" — outdated. Tests added since. Gap = prover integration tests only.
- **EF ZK Grants $900K pool**: 2024 wave complete. 2025/2026 wave not yet announced. Timing uncertain. Do not block on this — pursue EF PSE (active) and Succinct (rolling) instead.
- **Succinct Residency amounts**: No public dollar amount confirmed. Listed as unknown. Direct outreach required to assess scope.
- **ETHGlobal sponsor bounty amounts**: Not specified. Treat as grant-equivalent (mindshare + demo credibility + direct bounty).
- **zkPad.AI relevance**: Exists as a ZK+AI launchpad. No traction data. $PNK launch relevance speculative — only if ZK identity angle is central to token mechanics.

## Recommended Actions (top 3, specific and implementable)

1. **Wire SP1 SHA-256 + ECDSA precompiles in zkPresence circuit** — Expected impact: Unblocks ALL downstream grant applications (EF PSE, Succinct Residency, ETHGlobal). Estimated 1-2 days. File: `crates/circuit/src/main.rs`. Steps: (a) replace sha256 stub with `sha2::Sha256::digest()` compiled for RISC-V; (b) replace 3 ECDSA `todo!()`s with SP1 secp256k1 precompile calls; (c) add prover integration test (prove + verify round-trip).

2. **Register for Gitcoin GG25 at builder.gitcoin.co** — Expected impact: Quadratic funding for SOS Systems, ONEON, Otto. No functional code required. Available NOW. Low effort, high leverage. Register all eligible projects.

3. **Prepare ETHGlobal NY submission plan for zkPresence (June 12–14)** — Expected impact: Bounty + developer mindshare + grant application credibility. Deliverable: circuit functional + demo attendee check-in flow. 7 weeks runway. This is the forcing function for the circuit fix.

## Evidence Quality Assessment

Coverage: **PARTIAL** — Web, memory, and codebase all represented; Graphiti offline (0 graph findings), no academic papers on grants specifically.
Source reliability: **HIGH** — Codebase grepping directly verified critical gap claims. Web sources from official grant pages (starknet.io/grants, ethglobal.com, esp.ethereum.foundation). Memory hits at 0.80-0.92 confidence.
Gaps: Missing confirmed dollar amounts for Succinct Residency and EF PSE 2026 rounds. Graphiti offline reduces relationship context. No confirmed ETHGlobal bounty amounts for 2026.

## Compressed Handoff (<=1000 tokens)

**Subject**: ZK ecosystem fit, grants, launchpads for MY3YE (zkPresence / ONEON / Panik)

**Verified codebase state**:
- zkPresence circuit: 4 `todo!()` panics (SHA-256 line 26, ECDSA lines 70/104/121). All 3 attestation modes broken. Contract tests exist (ZkPresence.t.sol, MockSP1Verifier). No prover integration tests.
- ONEON: zero ZK files (no .rs/.circom/.nr). Pure Next.js.
- Panik: zero .sol files. No $PNK token contract, no soulbound NFT.

**Grant matrix (ranked by fit × accessibility)**:
| Grant | Amount | Status | Fit | Gate |
|---|---|---|---|---|
| EF PSE Semaphore | ~$25-50K est | OPEN | zkPresence | Circuit fix first |
| Succinct Residency | Unknown | Rolling | zkPresence | OSS publish first |
| ETHGlobal NY (Jun 12-14) | Bounties | 2 months | zkPresence | Circuit fix |
| Gitcoin GG25 | Quadratic | Q2 2026 | SOS/ONEON/Otto | Register NOW |
| OP RetroPGF R7 | OP tokens | Retroactive | Panik | Ship usage first |
| ENS Public Goods | $12-50K | Ongoing | Protocol/identity | MEDIUM |
| EF ZK Grants $900K | $150K+/proj | 2024 done | zkPresence | 2025/26 wave TBD |
| Starknet Seed | $25K STRK | OPEN | WRONG STACK | Skip |

**Hard gates**:
- Aztec/Noir: do NOT deploy until July 2026 (critical vuln March 2026)
- Polygon zkEVM: SUNSETTING — avoid
- zkPresence grants: blocked until circuit functional

**90-day priority sequence**:
1. [Week 1-2] Wire SHA-256 (sha2 crate for RISC-V) + ECDSA (SP1 secp256k1 precompile) in crates/circuit/src/main.rs → add prover integration test
2. [Week 2] Register all projects at builder.gitcoin.co for GG25
3. [Week 3-4] OSS publish zkPresence → apply Succinct Residency + EF PSE
4. [Week 5-7] Build ETHGlobal NY demo (attendee check-in flow)
5. [Q3+] ZK Stack L3 RaaS for ONEON; $PNK + soulbound contracts for Panik

**memory_write_token**: b32e7565-06a5-401d-8a61-19550fc52ca2
