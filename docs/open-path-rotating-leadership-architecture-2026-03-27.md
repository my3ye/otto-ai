# Open-Path Rotating Leadership Protocol
## Architecture Design Document v1.0

**Author:** Otto (Architect Agent)
**Date:** 2026-03-27
**Status:** Design Phase
**Prerequisite Research:** 29 sources synthesized (web x9, memory x10, graph x6, code x3, papers x1)
**Directive:** "There will be no leaders — anyone has a clear path to become one." — Mev

---

## Design: Open-Path Rotating Leadership Protocol

### Problem

Traditional governance fails in two directions. Centralized leadership creates capture — the powerful stay powerful. Rotating leadership without qualification gates merely cycles the same elite actors. The 2026 DAO landscape ($28B across 12,000+ DAOs) proves that token-weighted voting produces plutocratic stagnation, and naive rotation produces governance theater.

Mev's directive demands a system where:
1. Anyone can see exactly how to reach a leadership position
2. Leadership is earned through verifiable work, not held through inertia
3. All rules are enforced by math on-chain — no room where the real decisions happen behind closed doors
4. The answer to "who watches the watchers?" is: nobody needs to, because the system is self-correcting

The existing 505 Systems DPC formula `P = f(Is, Ec, Rw)` already solves the hardest part — measuring who deserves governance weight. This protocol designs the **rotation mechanics** that sit on top of DPC: how leaders enter, serve, and exit.

### Approach

The protocol defines three governance tiers — **Operational Councils**, **Strategic Assembly**, and **Constitutional Guardians** — each with different rotation frequencies, selection mechanisms, and powers. All selection is gated by DPC score. No position is permanent. Every rule is an on-chain smart contract.

---

## 1. Roles & Tiers

### Tier 1: Operational Councils (Execute)

Specialized domain councils that make day-to-day decisions within their scope. This is where most governance happens.

| Council | Domain | Seats | Term | Min DPC | Min Level |
|---------|--------|-------|------|---------|-----------|
| Build Council | Code, infrastructure, shipping | 5 | 90 days | 500 | Builder (L2) |
| Community Council | Education, onboarding, culture | 5 | 90 days | 500 | Builder (L2) |
| Treasury Council | Budget allocation, grants, revenue | 5 | 90 days | 1000 | Builder (L2) |
| Safety Council | Emergency response, dispute resolution | 3 | 90 days | 2000 | Steward (L3) |

**Total: 18 council seats across 4 domains.**

**Powers:**
- Approve/reject proposals within their domain (simple majority)
- Allocate budgets up to their domain's quarterly cap
- Set operational priorities for their domain
- Cannot modify the constitution, DPC formula, or cross-domain rules

**Constraints:**
- Decisions are on-chain and transparent (every vote recorded)
- Any decision can be challenged by 10% of total DPC-weighted governance power (triggers Strategic Assembly review)
- Council members cannot serve consecutive terms on the same council
- Maximum 2 terms total across all councils within 365 days (anti-entrenchment)

### Tier 2: Strategic Assembly (Direct)

Cross-domain body that handles ecosystem-wide decisions too significant for any single council.

| Parameter | Value |
|-----------|-------|
| Seats | 7 |
| Term | 180 days |
| Min DPC | 2000 |
| Min Level | Steward (L3) |
| Selection | Weighted sortition from eligible pool (see Section 3) |
| Consecutive terms | Prohibited |

**Powers:**
- Approve cross-domain proposals (e.g., launching a new ecosystem project)
- Override council decisions on challenge (2/3 majority)
- Set ecosystem-wide budgetary parameters
- Approve emergency power grants (with 72h auto-expiry)
- Propose constitutional amendments (requires Tier 3 ratification)

**Cannot:**
- Unilaterally amend the constitution
- Extend their own terms
- Modify the DPC formula without full community ratification

### Tier 3: Constitutional Guardians (Protect)

Not a governing body. A verification layer that ensures Tiers 1 and 2 operate within constitutional bounds.

| Parameter | Value |
|-----------|-------|
| Seats | 5 |
| Term | 365 days |
| Min DPC | 5000 |
| Min Level | Architect (L4) |
| Selection | Weighted sortition from Architect pool |
| Role | Review, veto unconstitutional actions, ratify amendments |

**Powers:**
- Veto any Tier 1 or Tier 2 decision that violates the constitution (2/3 majority)
- Ratify or reject constitutional amendments proposed by Tier 2
- Trigger emergency re-election of any council if corruption is detected
- **Cannot** initiate proposals, allocate budgets, or set priorities — purely protective

**Design rationale:** Separating protection from execution prevents the common failure where a "supreme court" becomes the de facto government. Guardians can only say no, never direct.

---

## 2. The Path: How Anyone Becomes a Leader

This is the core innovation. The path is visible, concrete, and enforced on-chain.

```
THE VISIBLE PATH

Step 1: ARRIVE (DPC: 0)
  Create ONEON identity. Join the ecosystem.
  You can see every council seat, who holds it,
  their DPC score, and when their term ends.
  The dashboard shows exactly what DPC you need.

Step 2: CONTRIBUTE (DPC: 0 → 100+)
  Complete contributions. Earn DPC through:
  - Is (Structural Impact): ship code, build infra, solve problems
  - Ec (Consistent Energy): show up weekly, compound effort
  - Rw (Weighted Resonance): earn peer recognition from high-impact reviewers
  Your DPC is public. Your progress is visible to you and everyone.

Step 3: QUALIFY (DPC: 500+)
  At Builder level (L2), you are eligible for Tier 1 councils.
  The system notifies you: "You now qualify for 3 of 4 councils."
  You can declare candidacy for the next rotation window.

Step 4: STAND (DPC: 500+ and declared)
  Declare candidacy during the 14-day nomination window
  before a council rotation. Your profile, DPC breakdown,
  and contribution history are published automatically.
  No campaign needed. Your work speaks.

Step 5: SELECTED (DPC-weighted sortition)
  Selection combines your DPC score with randomness (see Section 3).
  Higher DPC = higher probability, but not certainty.
  This prevents the same top-5 scorers from always winning.

Step 6: SERVE (90-365 days depending on tier)
  You serve your term. Your decisions are on-chain.
  Your DPC continues to be tracked during service.
  Council service itself earns Ec (Consistent Energy) and
  Rw (peer feedback from the community on your decisions).

Step 7: ROTATE OUT (mandatory)
  Term ends. You cannot serve consecutive terms on the same body.
  Your governance weight returns to the general pool.
  You can serve on a DIFFERENT council after one rotation gap,
  or re-qualify for the same council after 2 rotation gaps.

Step 8: RETURN (if you earn it)
  DPC decays without activity. To serve again, you must still
  be actively contributing. Past leaders who stop contributing
  lose eligibility naturally — no formal removal needed.
```

**Key property:** At every step, the contributor can see exactly where they are, what they need, and how long it will take. There is no hidden committee, no unwritten rule, no informal network required. The path is math.

---

## 3. Selection Mechanics: DPC-Weighted Sortition

Pure election cycles elites. Pure random selection ignores merit. The protocol uses **DPC-weighted sortition** — a randomized selection where your probability of being chosen is proportional to your DPC score, but not deterministic.

### How It Works

```
SELECTION ALGORITHM (on-chain, verifiable)

Input:
  eligible_pool[] = all candidates meeting min DPC + min level + cooldown satisfied
  seats = number of seats to fill
  vrf_seed = Chainlink VRF (verifiable random, manipulation-proof)

For each seat:
  1. Calculate selection weight for each candidate:
     weight_i = dpc_i^0.7  (sub-linear — diminishing returns on high DPC)

  2. Normalize weights to probabilities:
     prob_i = weight_i / sum(all weights)

  3. Use VRF to select one candidate from the weighted distribution

  4. Remove selected candidate from pool (no double-seating)

Output:
  selected[] = the new council members
  proof = VRF proof (anyone can verify the randomness was fair)
```

### Why `dpc^0.7` (Sub-Linear Weighting)

| DPC Score | Raw Weight | Selection Probability (5-person pool) |
|-----------|-----------|--------------------------------------|
| 500 | 500^0.7 = 79.4 | ~13% |
| 1000 | 1000^0.7 = 125.9 | ~20% |
| 2000 | 2000^0.7 = 199.5 | ~32% |
| 5000 | 5000^0.7 = 380.2 | ~35% (in Architect pool) |

A contributor with 4x the DPC of another gets roughly 2.5x the selection probability, not 4x. This ensures high contributors are more likely to serve but cannot dominate selection. Fresh Builders with DPC 500 still have a meaningful ~13% chance per seat.

**Alternative considered:** Linear weighting (prob proportional to DPC). Rejected because it concentrates selection power too heavily in top scorers, recreating the elite cycling problem.

**Alternative considered:** Pure sortition (equal probability regardless of DPC). Rejected because it ignores merit entirely and could place someone with minimal contribution in a Treasury Council seat.

### Cooldown Enforcement

```
COOLDOWN RULES (smart contract enforced)

Same council:    must skip 2 rotation cycles (180 days)
Different council: must skip 1 rotation cycle (90 days)
Same tier:       no more than 2 terms per 365 days
Cross-tier:      serving Tier 2/3 does not prevent Tier 1 candidacy after cooldown

Cooldown state is on-chain. The selection algorithm automatically
excludes candidates in cooldown. No human enforcement needed.
```

---

## 4. Anti-Capture Safeguards

### 4.1 Reputational Cartel Detection (from Pink Paper)

The Intelligence Layer (LAM) continuously monitors for Reputational Cartels — cliques where members systematically upvote each other to inflate Rw scores.

```
CARTEL DETECTION

Trigger: Rw graph clustering coefficient exceeds threshold
         (small group's internal review weight > 3x their external review weight)

Action:
  1. Flag the cluster for Truth-Anomaly Audit
  2. Temporarily amplify Is (Structural Impact) weight for flagged members
     (verifiable on-chain contributions can't be faked by a cartel)
  3. Reduce Rw weight to 0.5x for flagged members for 30 days
  4. Publish the audit result on-chain (transparent — everyone sees it)
  5. If confirmed: DPC recalculated, affected members may lose eligibility

No human tribunal. Math detects it. Smart contract enforces it.
Community can review and override if false positive (governance challenge).
```

### 4.2 Sybil Resistance

- Maximum 1 ONEON identity per person (biometric on-device, never transmitted)
- Sybil detection via subgraph analysis (precision 0.94, arXiv 2505.09313)
- If Sybil detected: all linked identities' DPC zeroed, permanently barred from council candidacy
- On-chain nullifier registry prevents duplicate participation

### 4.3 Term Limits + Cooldowns (see Section 3)

- No consecutive terms on same body
- Max 2 terms per year across all councils
- Cooldown enforced by smart contract — cannot be waived

### 4.4 Decision Transparency

Every council decision includes:
- The vote record (who voted how, with what governance weight)
- The DPC breakdown of each voter at time of vote
- Whether any cartel flags are active
- The on-chain transaction hash

No private channels. No off-chain agreements. If it's not on-chain, it didn't happen.

### 4.5 Community Challenge Mechanism

```
CHALLENGE PROCESS

Who can challenge: Any contributor with DPC >= 100 (Contributor level)

Challenge threshold: 10% of total active DPC-weighted governance power
  (not 10% of people — 10% of governance weight, preventing whale veto
   while ensuring significant community concern is needed)

What happens:
  1. Challenge submitted on-chain with rationale
  2. 7-day deliberation period
  3. Strategic Assembly votes (2/3 majority to overturn)
  4. If Assembly is the challenged body: Constitutional Guardians adjudicate
  5. If overturned: decision reversed, council confidence score decremented

If a council receives 3 successful challenges in one term:
  Emergency re-election triggered for that council.
```

### 4.6 Whale Governance Weight Cap

From existing architecture: **max 5% of total GovernanceWeight per wallet.** This applies to council selection weighting — no single identity can have more than 5% selection probability regardless of DPC score.

### 4.7 Founding Phase Transition

```
FOUNDING VETO SUNSET

Phase 0 (now → governance live):
  Mev holds veto power over all decisions.
  Purpose: protect the mission during bootstrapping.

Phase 1 (governance live → 12 months):
  Mev veto limited to constitutional matters only.
  Operational decisions fully in council hands.

Phase 2 (12 → 24 months):
  Mev veto replaced by Constitutional Guardian tier.
  No individual holds veto power.

Sunset trigger: autonomous, on-chain timer.
Cannot be extended without community supermajority (75%) vote.
```

---

## 5. Emergency Powers

```
EMERGENCY POWER PROTOCOL

Who can invoke: Safety Council (3 members, unanimous) OR
               Strategic Assembly (7 members, 5/7 majority)

What they can do:
  - Pause a smart contract (max 72 hours)
  - Freeze a treasury allocation (max 72 hours)
  - Suspend a contributor's governance weight pending investigation (max 72 hours)
  - Fast-track a critical proposal (48h vote window instead of 7 days)

What they CANNOT do (even in emergency):
  - Modify the DPC formula
  - Extend emergency powers beyond 72 hours
  - Mint tokens
  - Amend the constitution
  - Override Constitutional Guardian vetoes

AUTO-EXPIRY: All emergency actions expire after 72 hours
             without explicit community ratification (20% quorum, 60% approval).

If emergency expires without ratification:
  All actions automatically reversed.
  Emergency invokers' confidence score decremented.
  Repeated false emergencies (3 in one term) trigger council re-election.
```

---

## 6. On-Chain Architecture

### Smart Contracts

```
CONTRACT ARCHITECTURE (Solidity, EVM L2 — chain TBD)

CouncilRegistry.sol
  - Stores council definitions (domain, seats, term length, min DPC)
  - Manages member records (address, start_block, end_block, cooldown_until)
  - Enforces cooldown rules on candidate registration
  - Public view: anyone can query any council state

DPCOracle.sol
  - Reads DPC scores from the DPC computation contract
  - Provides selection weights (dpc^0.7) to the selection contract
  - Updated by the Intelligence Layer with on-chain attestations

CouncilSelection.sol
  - Implements DPC-weighted sortition
  - Consumes Chainlink VRF for verifiable randomness
  - Inputs: eligible pool, VRF seed
  - Outputs: selected members + cryptographic proof of fair selection
  - Anyone can verify the selection was honest

GovernanceAction.sol
  - Records all council decisions on-chain
  - Implements multi-sig for council votes (domain-specific thresholds)
  - Enforces scope constraints (Build Council can't touch Treasury)
  - Emits events for every action (full audit trail)

EmergencyModule.sol
  - Implements 72h auto-expiry timer
  - Manages emergency action state (pause, freeze, suspend)
  - Auto-reversal if no ratification within window
  - Cannot be re-invoked for the same action within 30 days

ChallengeRegistry.sol
  - Accepts community challenges (DPC >= 100 to submit)
  - Tracks challenge weight accumulation (10% threshold)
  - Routes to appropriate adjudicator (Assembly or Guardians)
  - Records outcomes and council confidence scores

FounderSunset.sol
  - Time-locked veto power that automatically narrows
  - Phase transitions triggered by block timestamp
  - Cannot be extended without 75% community supermajority
  - Self-destructs after Phase 2 sunset
```

### Data Flow

```
                    ┌──────────────────────┐
                    │  ONEON Identity       │
                    │  (did:key, on-chain)  │
                    └──────────┬───────────┘
                               │
                    ┌──────────▼───────────┐
                    │  DPC Computation      │
                    │  P = f(Is, Ec, Rw)    │
                    │  On-chain attestations │
                    └──────────┬───────────┘
                               │
              ┌────────────────▼─────────────────┐
              │  DPCOracle.sol                    │
              │  Provides dpc^0.7 weights         │
              └────────────────┬─────────────────┘
                               │
              ┌────────────────▼─────────────────┐
              │  CouncilSelection.sol             │
              │  + Chainlink VRF                  │
              │  = Verifiable weighted sortition  │
              └────────────────┬─────────────────┘
                               │
         ┌─────────────────────┼─────────────────────┐
         │                     │                       │
   ┌─────▼──────┐      ┌──────▼───────┐       ┌──────▼───────┐
   │ Tier 1      │      │ Tier 2        │       │ Tier 3        │
   │ Councils    │      │ Assembly      │       │ Guardians     │
   │ (execute)   │      │ (direct)      │       │ (protect)     │
   └─────┬──────┘      └──────┬───────┘       └──────┬───────┘
         │                     │                       │
         └─────────────────────┼───────────────────────┘
                               │
              ┌────────────────▼─────────────────┐
              │  GovernanceAction.sol             │
              │  All decisions recorded on-chain  │
              │  Full audit trail, public         │
              └──────────────────────────────────┘
```

---

## 7. Key Decisions

### Decision 1: DPC-weighted sortition over pure election
**Chosen:** Weighted random selection where DPC increases probability but doesn't guarantee selection.
**Why:** Pure election cycles the top-5 DPC scorers indefinitely (the rotation-elite problem identified in research). Sortition injects enough randomness that fresh contributors with qualifying DPC still have meaningful odds.
**Alternative rejected:** Pure election by DPC-weighted vote. Simpler to understand, but research confirms it produces elite cycling within 3-4 rotation periods.
**Tradeoff:** Some randomness means occasionally a lower-DPC candidate serves over a higher-DPC candidate. This is a feature — it prevents meritocracy calcification.

### Decision 2: Three-tier structure over flat council
**Chosen:** Operational (execute) → Strategic (direct) → Constitutional (protect) separation.
**Why:** Flat structures either concentrate all power in one body or diffuse it to paralysis. The three-tier split follows separation of concerns: execution is frequent and domain-specific, strategy is cross-domain and less frequent, constitutional protection is rare and purely defensive.
**Alternative rejected:** Single rotating council with varying powers. Simpler, but concentrates execute + direct + protect powers in one body — the "room where it all happens" that Mev's directive explicitly forbids.

### Decision 3: `dpc^0.7` sub-linear weighting
**Chosen:** Sub-linear (0.7 exponent) maps DPC to selection probability.
**Why:** Linear weighting gives 4x DPC = 4x probability, which is too deterministic. Square root (0.5) is too flat — almost ignores contribution differences. 0.7 balances merit recognition with meaningful odds for newer qualifiers.
**Alternative rejected:** Linear (1.0 exponent). Simpler math, but recreates the problem — top contributors always selected.

### Decision 4: 72-hour emergency auto-expiry (kept from existing SOS architecture)
**Chosen:** All emergency powers automatically expire after 72 hours without community ratification.
**Why:** History shows emergency powers that don't auto-expire become permanent. The 72h window is long enough for genuine emergencies (smart contract bug, active attack) but short enough to prevent abuse.
**Alternative rejected:** 7-day emergency window. Too long — a week of unchecked emergency power is a coup.

### Decision 5: Cooldown over term-limit-only
**Chosen:** Mandatory cooldown gaps between terms (180 days same council, 90 days different council) plus max 2 terms/year.
**Why:** Term limits alone let you cycle: Council A → Council B → Council A → Council B forever. Cooldowns plus term caps prevent this.
**Alternative rejected:** Lifetime term limits (e.g., max 4 terms ever). Too restrictive — long-term active contributors should be able to serve again after meaningful cooldowns.

---

## 8. Implementation Plan

### Phase 1: Foundation (smallest deployable unit)
1. **CouncilRegistry.sol** — Define councils, seats, terms, DPC thresholds
2. **DPCOracle.sol** — Bridge existing DPC computation to on-chain readable format
3. **CouncilSelection.sol** — Weighted sortition with Chainlink VRF integration
4. **Basic UI** — Dashboard showing all councils, members, terms, eligibility calculator ("You need X more DPC to qualify for Y")

**Dependency:** DPC computation must be on-chain or have a trusted oracle. If DPC is initially off-chain (computed by Intelligence Layer), use a signed oracle with fraud proofs until full on-chain DPC is built.

### Phase 2: Governance Actions
5. **GovernanceAction.sol** — Multi-sig council voting, domain scope enforcement
6. **ChallengeRegistry.sol** — Community challenge mechanism
7. **OMS integration** — Governance dashboard in Otto Management System (proposal tracking, vote history, council activity)

### Phase 3: Safety & Sunset
8. **EmergencyModule.sol** — 72h auto-expiry emergency powers
9. **FounderSunset.sol** — Time-locked veto narrowing with autonomous phase transitions
10. **Cartel detection integration** — Wire Intelligence Layer's Truth-Anomaly Audit to on-chain DPC recalculation

### Phase 4: Constitutional Layer
11. **Constitutional Guardian selection** — Separate sortition from Architect-level pool
12. **Amendment protocol** — On-chain constitutional amendment lifecycle
13. **Full ratification** — Community ratification of the protocol itself through the 24-week governance finalization pipeline

---

## 9. Risks

| Risk | Severity | Mitigation |
|------|----------|-----------|
| **DPC gaming** — contributors optimize for score rather than real impact | HIGH | Non-linear DPC formula (diminishing returns on any single variable), cartel detection, peer review weighting by reviewer impact |
| **Low participation** — not enough qualified candidates for councils | MEDIUM | Skill Bounties (Pink Paper) actively recruit into contribution. Lower initial DPC thresholds if pool is <3x seats. Ecosystem Need Board surfaces high-impact opportunities. |
| **VRF manipulation** — oracle providing biased randomness | LOW | Chainlink VRF is cryptographically verifiable. Anyone can check the proof. Multiple VRF providers as fallback. |
| **Emergency power abuse** — Safety Council using emergencies as policy tool | MEDIUM | 72h auto-expiry is absolute (smart contract, not human-enforced). 3 false emergencies = automatic re-election. Community ratification required to extend. |
| **Founding phase capture** — Mev's veto power not actually sunsetting | LOW | FounderSunset.sol is autonomous — time-locked, self-destructing. Extension requires 75% community supermajority. The contract code IS the guarantee. |
| **Voter apathy on challenges** — challenges never reaching 10% threshold | MEDIUM | Delegate challenge weight (DPC holders can delegate challenge votes to watchdog contributors). Lower threshold to 5% if consistently unmet after 6 months. |
| **Council coordination failure** — 4 councils acting at cross purposes | MEDIUM | Strategic Assembly exists precisely for cross-domain coordination. Monthly sync proposals from any council. Clear domain boundaries in CouncilRegistry. |

---

## 10. Sortition Decision (Phase 2 — Requires Mev Input)

The research identified a gap: pure meritocratic selection, even with DPC gating, may converge to the same high-scorers over time (meritocracy calcification). Sortition — random selection from a qualified pool — is the academic answer.

This protocol uses DPC-weighted sortition as the default. However, a stronger form exists:

**Option A (current design):** DPC-weighted sortition — higher DPC = higher probability
**Option B (stronger anti-calcification):** Two-pool sortition — 60% of seats filled by DPC-weighted selection, 40% by equal-probability random selection from the entire eligible pool

Option B guarantees that even the lowest-qualifying contributors regularly serve, at the cost of occasionally placing less-experienced members in council seats. This is the explicit tradeoff between merit and anti-capture.

[NEEDS_MEV_INPUT]
{"question": "Should council selection use pure DPC-weighted sortition (Option A) or split 60/40 between DPC-weighted and equal-random (Option B)?", "options": ["Option A: DPC-weighted sortition only — higher contribution = higher selection probability", "Option B: 60/40 split — most seats DPC-weighted, some seats purely random from eligible pool"], "recommendation": 0, "context": "Option A balances merit with randomness via sub-linear weighting. Option B adds a stronger anti-calcification guarantee but may occasionally place less-experienced members in important seats. Both are defensible. The research slightly favors B for long-term health but A is simpler to explain and implement first."}
[/NEEDS_MEV_INPUT]

---

## Appendix A: Integration with Existing Architecture

| Existing System | Integration Point |
|----------------|-------------------|
| **DPC Formula** (P = f(Is, Ec, Rw)) | Selection weight input via DPCOracle |
| **Contributor Levels** (L0-L4) | Eligibility gates for each tier |
| **GovernanceWeight Formula** | Used for community challenges and ratification votes |
| **ONEON Identity** | Required for candidacy (1 person = 1 candidacy) |
| **24-Week Ratification Pipeline** | This protocol itself will be ratified through it |
| **Dormant Token Decay** | activity_factor decay prevents inactive members from blocking active ones |
| **Pink Paper Cartel Detection** | Truth-Anomaly Audit feeds into DPC recalculation |
| **505 DAO Snapshot Voting** | Community ratification votes use existing Snapshot infrastructure |
| **Emergency Auto-Expiry (72h)** | EmergencyModule.sol implements existing SOS architecture decision |
| **Founding Veto Sunset** | FounderSunset.sol implements existing phase transition plan |

## Appendix B: Summary Table

| Property | Tier 1 (Councils) | Tier 2 (Assembly) | Tier 3 (Guardians) |
|----------|-------------------|--------------------|--------------------|
| **Role** | Execute domain ops | Direct ecosystem strategy | Protect constitution |
| **Seats** | 18 (4 councils) | 7 | 5 |
| **Term** | 90 days | 180 days | 365 days |
| **Min DPC** | 500-2000 | 2000 | 5000 |
| **Min Level** | Builder/Steward | Steward | Architect |
| **Selection** | DPC-weighted sortition | DPC-weighted sortition | DPC-weighted sortition |
| **Consecutive terms** | No | No | No |
| **Max terms/year** | 2 | 1 | 1 |
| **Can propose?** | Within domain | Cross-domain | No |
| **Can veto?** | No | Override councils | Veto unconstitutional acts |
| **Emergency power?** | Safety Council only | Yes (5/7) | No |

---

*The path is visible. The math is public. The contracts are the law.*

*Architecture by Otto | 2026-03-27 | Prerequisite research: 29 sources, 8 validated insights*
