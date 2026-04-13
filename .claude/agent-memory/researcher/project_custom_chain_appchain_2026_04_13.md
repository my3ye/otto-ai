---
name: Custom Chain / L2 / L3 / Appchain Build Options 2026
description: Full research pipeline on build-your-own appchain options for MY3YE — ZK Stack / OP Stack / Orbit / Cosmos — validated 7.5/10 with 7 corrections applied
type: project
---

## Research Summary (2026-04-13)

**Pipeline: COMPLETE | Score: 7.5/10 | Memories: 10 | Note ID: 3064e558**

### Core Decisions
- **Base L2 = primary chain** for all MY3YE products. Arbitrum One is a secondary production target in zkPresence (chainId 42161 in chains.ts).
- **L3 RaaS = correct MVP entry** before any sovereign chain. Demand must be proven first. (MEDIUM — vendor-biased sources)
- **ZK Stack L3 = ONEON Q3 2026 target path** via Conduit/Caldera. Lens Chain = confirmed precedent. (MEDIUM — 2 independent signals)
- **OP Stack L3** = alternative ONEON path (2.5%/15% Superchain share)
- **Arbitrum Orbit** = best DA cost ($0.04/MB AnyTrust) + Rust/Stylus moat. Best for Otto Music.
- **Cosmos SDK = SOS Phase 2+ ONLY** (IBC v2 interop, sovereign governance). NOT Phase 1.
- **Avalanche** = NOT recommended (MEDIUM — weakest interop, single-source verdict)
- **Polkadot/JAM** = NOT recommended (too complex)
- **Appchain ROI threshold = 500K+ DAU** — do not build appchain before this

### Gap Verification (grep-confirmed)
- Zero Cosmos SDK Go, Substrate Rust, Orbit/OP Stack L3 config, ZK Stack hyperchain config in any repo
- Zero Conduit/Caldera RaaS deployment YAML
- zkPresence/chains.ts: Base + Arbitrum One + Ethereum only (no L3)

### Patches Applied (7)
1. Insight 1: "locked primary" → "primary" (Arbitrum One secondary target)
2. Insight 2: HIGH → MEDIUM (4/5 sources are RaaS vendors)
3. Insight 3: HIGH → MEDIUM (2 independent signals after dedup; Q3 2026 = target not validated)
4. Insight 7: HIGH → MEDIUM (Avalanche interop: single comparative source)
5. Insight 2: RaaS pricing date-qualified to March 2026
6. Action 3: Aztec non-sequitur qualifier removed
7. Base profitability claim softened to "most profitable per recent reporting"

### P0 Actions
1. ONEON: Deploy ZK Stack L3 via RaaS — Q3 2026 target
2. SOS: Stay Base Phase 1; draft Cosmos SDK Phase 2 spec post-PMF
3. Apply for ZK Stack native grants / Optimism retroPGF for ONEON

### Documentation Risk
- `invisible-web3-layer-architecture-2026-03-28.md` is memory-only, NOT git-tracked. This is the Decision 2 source for all chain decisions. Risk: architectural decisions without version control.

**Why:** ZK Stack grant window exists now; Cosmos Phase 2 needs spec before ONEON scales to require it.
**How to apply:** When evaluating any appchain work, verify DAU threshold first. For ONEON L3 planning, treat Q3 2026 as a target, not a commitment.
