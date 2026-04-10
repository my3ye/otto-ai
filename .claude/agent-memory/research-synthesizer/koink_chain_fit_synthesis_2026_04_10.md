---
name: Koink technical direction & chain fit synthesis (2026-04-10)
description: Koink chain fit analysis: EVM/Base vs Solana sequencing, Phase 0 complete/Phase 1 blocked, zero contracts, Ctrl Wallet placeholder, OWS wallet unblock, investor track
type: project
---

## Key Insights (ranked by confidence × actionability)

1. **Phase 0 complete; Phase 1 fully blocked on OWS wallet registration** — Zero Solidity contracts exist anywhere (grep: no `.sol` files in otto/ or koink-fun-web/). OWS deploy wallet registration is the single-point unblock confirmed in `launch.py`. — Confidence: HIGH | Sources: 4 (code: launch.py, standard.py; memory: launch readiness; memory: top-3 recs)

2. **Chain sequencing contradiction: Capital Strategy (Mar 20) = Solana first; Technical plan (Mar 23) + standard.py = EVM/Base first** — standard.py SUPPORTED_CHAINS implements Base/ETH/Arbitrum/OP with Chainlink VRF; Solana = Switchboard (separate stack). Mar 23 plan is more recent and technically detailed. Codebase aligns with EVM-first. — Confidence: HIGH | Sources: 3 (memory: capital_strategy_v2; memory: koink_oms_plan; code: standard.py)

3. **Base is optimal Phase 1 chain** — Chainlink VRF v2.5 confirmed on Base. EVM/Solidity expertise = faster delivery. Coinbase Ventures P1 requires Base deploy (explicit prereq). Virtuals/ACP agent ecosystem on Base. ERC-20 anti-whale + sell tax = native. — Confidence: HIGH | Sources: 6 (web: Chainlink docs confirmed; code: standard.py; memory: investor outreach plan; web: Base vs Solana)

4. **Solana is dominant meme ecosystem but adds Phase 2 complexity** — pump.fun 80% market share; $0.00025 fees vs $0.01-0.10 Base. BUT: Switchboard VRF only (Chainlink NOT on Solana — standard.py enforces this), Rust/Anchor vs Solidity, separate contract architecture required. — Confidence: HIGH | Sources: 4 (web: pump.fun/Chainlink/Bitget; code: standard.py)

5. **koink-fun-web contains active "Ctrl Wallet" placeholder copy** — `ChainMarquee.tsx` and `FAQ.tsx` contain copy from unrelated wallet product ("Is Ctrl Wallet safe?", "Ctrl Wallet supports millions of assets"). Grep confirmed. Live on landing page. Must replace before any public launch or investor demo. — Confidence: HIGH | Sources: 2 (code: ChainMarquee.tsx, FAQ.tsx — grep confirmed)

6. **arXiv 2602.14860 graduation dynamics applicable to Koink signal scoring** — 0.63% graduation rate; liquidity velocity = #1 predictor; graduates at ~85 SOL. Apply to Koink token feed ranking / pre-graduation detection engine. — Confidence: MEDIUM | Sources: 2 (paper + retrieval findings)

7. **Coinbase Ventures requires Base deployment as hard prereq** — Investor Outreach Plan (Mar 28) explicitly states "post-Base deploy required" for CbV P1 engagement. — Confidence: MEDIUM | Sources: 1 (memory: investor outreach plan)

8. **Privy/Dynamic embedded wallet + paymaster not implemented (gap confirmed)** — Search query: grep for "privy\|Privy\|paymaster" in koink-fun-web/app/ — returned 0 results. UX benchmarks: +30-40% onboarding completion improvement. Not yet scoped for Phase 1. — Confidence: MEDIUM | Sources: 2 (memory: UX benchmarks; grep: no match)

## Contradictions / Uncertainties

- **CRITICAL: Chain sequencing conflict**: Capital Strategy v2.0 (Mar 20) = Solana first. OMS Integration Plan (Mar 23) + standard.py = EVM/Phase 1 first. The Mar 23 plan is newer and codebase-aligned. Capital strategy may be superseded — requires Mev confirmation.
- **Frontend chain count mismatch**: ChainMarquee shows 19 chains (marketing); standard.py supports 5 (Base, ETH, Arbitrum, OP, Solana). Not a technical conflict but could mislead investors/users.
- **Graph data absent**: Knowledge graph returned 500 error — any graph-resident Koink decisions missing from this synthesis.

## Recommended Actions (top 3)

1. **Mev: confirm Base-first (Phase 1) → Solana (Phase 2) chain sequencing** — Technical architecture, codebase, and investor positioning all support EVM-first. Capital strategy may be superseded. Confirmation unblocks all contract development with clear chain target. Expected impact: resolves architectural ambiguity immediately.

2. **Mev: register OWS deploy wallet** — Single action that unblocks KoinkLauncher.sol + KoinkToken.sol development. Phase 1 cannot proceed without it. Expected impact: Phase 1 contracts can begin the next day.

3. **Otto: replace Ctrl Wallet placeholder copy in koink-fun-web** — Files: `app/components/ChainMarquee.tsx` and `app/components/FAQ.tsx`. Remove all "Ctrl Wallet" references, replace with Koink-specific messaging. Expected impact: eliminates live credibility risk on landing page.

## Evidence Quality Assessment

Coverage: PARTIAL — 24 sources (web: 8, memory: 10, code: 4, papers: 2). Strong on architecture and chain comparison. Graph absent (500 error). No live contract data (none exist).

Source reliability: HIGH — Code reads = ground truth. Memory hits = timestamped directives. Web sources = authoritative (Chainlink docs, Bitget, pump.fun research). Papers = peer-reviewed.

Gaps: (1) Graph 500 error — graph-resident Koink decisions missing. (2) Mev chain sequencing confirmation needed. (3) Switchboard VRF Phase 2 integration effort not yet scoped.

## Compressed Handoff

**Phase status**: Phase 0 COMPLETE. Phase 1 BLOCKED — zero `.sol` files (grep confirmed). Single unblock: OWS deploy wallet (Mev action).

**Chain conflict (HIGH)**: Capital Strategy Mar 20 = Solana first. Technical plan Mar 23 + standard.py = EVM/Base first (Chainlink VRF). Codebase aligns EVM-first. Needs Mev confirmation.

**Chain fit verdict**:
- Base (Phase 1 rec): VRF confirmed, EVM expertise, Coinbase Ventures prereq, Virtuals/ACP, faster delivery
- Solana (Phase 2): pump.fun 80% ecosystem, $0.00025 fees; but Switchboard-only VRF, Rust/Anchor complexity

**VRF split confirmed**: standard.py enforces chainlink→EVM, switchboard→Solana with validation error.

**Frontend live risk**: ChainMarquee.tsx + FAQ.tsx = "Ctrl Wallet" copy (grep confirmed). Must fix before launch.

**Papers**: arXiv 2602.14860 (liquidity velocity = graduation predictor) → Koink signal scoring. arXiv 2505.09313 (Sybil LightGBM, precision 0.94) → anti-whale enforcement.

**Investor track**: Coinbase Ventures P1 = Base deploy required (explicit). Outlier Ventures Base Camp = P0 (no chain req).

**Top actions**: (1) Mev confirm Base-first sequencing. (2) Mev register OWS wallet. (3) Otto replace Ctrl Wallet copy.

**Why:** Capital Strategy v2.0 and the Mar 23 technical plan conflict on chain order. The codebase and EVM stack are fully Base-aligned. Resolving this directive gap is the #1 unblock.
**How to apply:** All Phase 1 contract work should proceed on Base pending Mev confirmation. Solana scoping deferred to Phase 2 planning.
