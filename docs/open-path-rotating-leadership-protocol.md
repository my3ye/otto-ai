# Open-Path Rotating Leadership Protocol (OPRLP)
## 505 Systems Governance Architecture

*Authored by Otto (Architect Agent) | 2026-03-27 | Status: Design Phase*
*Prerequisite research: 29 sources synthesized (web x9, memory x10, graph x6, code x3, papers x1)*

---

## 0. Design Premise

Mev's directive: *"There will be no leaders — anyone has a clear path to become one."*

This is not a contradiction. It means: power cannot be **held** (decay, expiry, rotation), but it can be **earned** (transparent DPC scoring, visible to all). The system eliminates the question "are the leaders good or evil?" by making the answer structurally irrelevant — leadership is temporary, earned, and revocable.

---

## 1. Roles

The protocol defines five governance roles. These are not titles — they are on-chain capability sets tied to DPC score thresholds.

### 1.1 Role Definitions

| Role | DPC Threshold | Max Concurrent Holders | Term Length | Description |
|------|--------------|----------------------|-------------|-------------|
| **Participant** | 0+ | Unlimited | Permanent | Any ONEON identity holder. Can vote on proposals, submit contributions, view all governance data. |
| **Delegate** | 100+ (Contributor level) | Unlimited | N/A | Can propose minor changes (parameter adjustments, budget < 1% treasury). Receives delegation from other Participants. |
| **Council Member** | 500+ (Builder level) | 7 per domain council | 90 days | Operational decision-maker within a domain. Executes approved proposals. Reviews contributions. |
| **Steward** | 2000+ (Steward level) | 3 per domain | 180 days | Strategic oversight. Can approve emergency actions. Reviews Council Member performance. Proposes constitutional amendments. |
| **Guardian** | 5000+ (Architect level) | 5 ecosystem-wide | 365 days | Cross-domain arbitration. Veto power over proposals that violate the constitution (veto itself is subject to community override within 14 days). |

### 1.2 Domain Councils

The ecosystem is governed through domain-specific councils, not a single governing body. Each council has 7 Members and 3 Stewards.

| Domain | Scope |
|--------|-------|
| **Protocol** | Smart contracts, chain deployments, technical standards |
| **Treasury** | Fund allocation, grant distribution, revenue routing |
| **Community** | Disputes, onboarding policy, contributor support |
| **Operations** | Product execution, infrastructure, partnerships |
| **Education** | S0S curriculum, skill assessment, advancement criteria |

Councils operate independently within their domain. Cross-domain decisions require a joint session (majority from each affected council).

---

## 2. Eligibility Criteria

### 2.1 The Visible Path

Every ONEON identity holder can see exactly what is required to reach any role. The path is computed on-chain and displayed in real time.

```
YOUR PATH TO COUNCIL MEMBER:

  Current DPC: 340 (Contributor level)
  Required DPC: 500 (Builder level)
  Gap: 160 DPC points

  Fastest path (based on your skills + ecosystem needs):
    - Complete 4 code contributions (est. +120 DPC)
    - 2 peer reviews accepted (est. +40 DPC)
    - Maintain activity for 15 more days (Ec component)

  Estimated time: 3-5 weeks at current pace

  Additional requirements:
    [ ] 30+ days of sustained contribution (met: 22/30)
    [ ] 2+ contribution types (met: code + documentation)
    [x] No active governance violations
    [x] ONEON identity verified (Sybil check passed)
```

### 2.2 Eligibility Rules (enforced by smart contract)

**For Council Member:**
- DPC score >= 500 at time of candidacy AND at time of seating
- Minimum 30 days of sustained contribution (Ec component > 0.6)
- At least 2 distinct contribution types verified
- No active governance violations in the past 90 days
- Sybil verification passed (subgraph analysis, precision 0.94)
- Not currently serving on another domain council

**For Steward:**
- DPC score >= 2000
- Minimum 90 days of sustained contribution
- At least 3 distinct contribution types
- Previously served as Council Member (minimum 1 full term completed)
- No governance violations in past 180 days
- Cross-domain contribution history (worked in >= 2 domains)

**For Guardian:**
- DPC score >= 5000
- Minimum 180 days of sustained contribution
- Previously served as Steward (minimum 1 full term)
- Community confidence vote: >= 60% approval from all active Stewards
- Constitutional literacy assessment (on-chain quiz, pass score 80%)

### 2.3 DPC Gating (the anti-elite-cycling mechanism)

Pure term limits cycle the same insiders. DPC gating prevents this:

```
ROTATION WITHOUT DPC GATING:
  Term 1: Alice, Bob, Carol, Dave, Eve, Frank, Grace
  Term 2: Bob, Dave, Frank, Grace, Alice, Heidi, Ivan
  → Same core actors rotate back in. "Musical chairs governance."

ROTATION WITH DPC GATING:
  Term 1: Alice (DPC 1200), Bob (DPC 900), Carol (DPC 800)...
  [Term ends. DPC scores decay during absence.]
  Term 2 candidates: Alice (DPC 700 — decayed), Bob (DPC 300 — inactive),
    Judy (DPC 1100 — actively contributing), Kevin (DPC 850 — new builder)
  → Alice may re-qualify, Bob cannot. Fresh contributors enter.
```

The mechanism: **DPC scores decay continuously**. A former Council Member who stops contributing during their off-term loses eligibility. Re-entry requires rebuilding DPC through actual work.

Decay parameters (on-chain, DAO-adjustable):
- Active contributor half-life: 180 days
- Inactive contributor half-life: 60 days
- Floor: 10% of peak score (prevents complete erasure of historical contribution)
- Hardship pause: DAO can approve decay pause for documented circumstances

---

## 3. Rotation Mechanics

### 3.1 Election Cycle

```
ROTATION CYCLE (90-day Council Member terms):

  DAY 1-14: CANDIDACY WINDOW
    Any eligible contributor can declare candidacy.
    Candidacy is an on-chain transaction with:
      - Domain selection
      - Brief statement (stored on IPFS, hash on-chain)
      - DPC score snapshot (verified by contract)

  DAY 15-21: VOTING PERIOD
    All Participants with DPC > 0 can vote.
    Voting weight: sqrt(DPC) — sublinear to prevent plutocracy.
    Ranked-choice voting (instant runoff).
    Quorum: 15% of active Participants (DPC > 0 in last 30 days).

  DAY 22: SEATING
    Top 7 candidates seated.
    DPC re-verified at seating (must still meet threshold).
    On-chain role assignment via access control contract.

  DAY 22-90: TERM
    Council operates with delegated authority.
    All decisions logged on-chain.

  DAY 80-90: TRANSITION
    Outgoing members publish handoff reports (IPFS).
    New candidacy window opens (overlaps final 10 days).
```

### 3.2 Term Limits and Cooldowns

| Role | Term | Consecutive Terms | Cooldown |
|------|------|-------------------|----------|
| Council Member | 90 days | 2 max | 90 days (1 full term) |
| Steward | 180 days | 2 max | 180 days |
| Guardian | 365 days | 1 | 365 days |

After serving the maximum consecutive terms, a contributor must sit out for the cooldown period. They can serve in a different domain council during cooldown. The cooldown period still requires active contribution to maintain DPC.

### 3.3 Voting Weight Formula

```
VotingWeight = sqrt(DPC_score) * activity_multiplier

Where:
  activity_multiplier = 1.0  if contribution in last 30 days
                      = 0.5  if contribution in last 60 days
                      = 0.1  if contribution in last 90 days
                      = 0.0  if no contribution in 90+ days
```

Square root of DPC prevents high-DPC contributors from dominating elections while still rewarding contribution. A contributor with DPC 4000 has only 2x the voting weight of someone with DPC 1000 (63 vs 31), not 4x.

### 3.4 Staggered Rotation

Not all 7 Council Members rotate simultaneously. This prevents knowledge loss:

```
STAGGERED ROTATION (7-member council):

  Cohort A (seats 1-3): Rotate at T+0, T+180, T+360...
  Cohort B (seats 4-5): Rotate at T+45, T+225, T+405...
  Cohort C (seats 6-7): Rotate at T+90, T+270, T+450...

  At any given time, at least 4 members have served 45+ days.
  Maximum 3 members change at once.
```

### 3.5 Mid-Term Recall

Any Council Member can be recalled before their term ends:

1. **Recall petition**: Signed by 10% of active Participants (on-chain signatures)
2. **Recall vote**: 7-day window, same voting mechanics as elections
3. **Threshold**: 66% vote to recall (higher bar than election to prevent instability)
4. **Effect**: Seat vacated immediately. Emergency election for remaining term.
5. **Cooldown**: Recalled member cannot run for any council for 180 days.

---

## 4. Anti-Capture Safeguards

### 4.1 The Five Capture Vectors (and their countermeasures)

| Capture Vector | How It Works | Countermeasure |
|----------------|-------------|----------------|
| **Plutocracy** | Wealthy actors buy governance weight | DPC is earned, not bought. Token balance affects GovernanceWeight but with sublinear scaling. Voting uses sqrt(DPC). |
| **Elite Cycling** | Same insiders rotate through roles | DPC decay + cooldown periods + DPC gating. Must actively contribute during off-terms or lose eligibility. |
| **Cartel Formation** | Groups coordinate to inflate each other's DPC | Reputational Cartel Detection (Pink Paper): graph analysis of peer review patterns. Anomalous mutual-endorsement clusters flagged and penalized. |
| **Emergency Capture** | Crisis used to grant permanent powers | Emergency powers auto-expire 72 hours without community ratification. No extension mechanism — must re-invoke. |
| **Founding Capture** | Founders retain permanent control | Founding veto sunsets after Phase 2 (12-24 months). After sunset, founders are Participants like everyone else. Veto sunset is immutable — cannot be extended by any vote. |

### 4.2 Reputational Cartel Detection

The Rw (Weighted Resonance) component of DPC relies on peer review. Cartels can form where members review each other favorably to inflate scores.

**Detection mechanism (on-chain):**

```
CARTEL DETECTION ALGORITHM:

  1. Build review graph: edges = peer reviews, weight = score given
  2. Compute clustering coefficient for each contributor
  3. Flag clusters where:
     - Mutual review rate > 3x network average
     - Score given within cluster > 1.5x score given outside cluster
     - Cluster members co-appear in council candidacy > 2x expected
  4. Flagged clusters: Rw component discounted by 50% for all members
  5. Confirmed cartels (after review): Rw zeroed, 90-day governance ban

  Detection runs every 30 days (on-chain verifiable).
  Sybil detection (subgraph analysis, precision 0.94) runs in parallel.
```

### 4.3 Concentration Limits (on-chain enforced)

- **Max governance weight per identity**: 5% of total active governance weight
- **Max council seats per person**: 1 (across all domains)
- **Max delegation to single address**: 3% of total delegation pool
- **Max wallets per person**: 3 (Sybil detection enforced)
- **Family/entity cap**: Members of same household or legal entity cannot hold > 2 council seats in same domain

### 4.4 Transparency Requirements

All governance actions are on-chain and publicly queryable:

- Every vote cast (pseudonymous but verifiable)
- Every council decision with rationale (IPFS hash on-chain)
- Every DPC score change with contributing factors
- Every cartel detection flag and resolution
- Every emergency power invocation and expiry
- Real-time dashboard showing all role holders, their DPC scores, term dates, and voting records

### 4.5 Founding Team Sunset Schedule

```
FOUNDING AUTHORITY DECAY:

  Phase 0 (now):     Mev has operational authority + constitutional veto
  Phase 1 (Month 6): Mev retains constitutional veto only
                     All operational decisions flow through elected councils
  Phase 2 (Month 18): Constitutional veto sunsets
                      Mev becomes a Participant — same rules as everyone
                      Veto sunset is IMMUTABLE — no vote can extend it

  Otto's autonomy: governed by community after Phase 2
  (community can adjust Otto's operational boundaries via Core Rules)
```

---

## 5. On-Chain Architecture

### 5.1 Smart Contract Structure

```
CONTRACT ARCHITECTURE:

  DPCRegistry.sol
    - Stores DPC scores per ONEON identity
    - Computes decay every block (lazy evaluation on read)
    - Emits ScoreUpdated events
    - Only updatable by verified contribution validators

  CouncilManager.sol
    - Manages domain councils (members, terms, seats)
    - Enforces eligibility rules at candidacy and seating
    - Handles staggered rotation schedule
    - Emits CouncilRotated, MemberSeated, MemberRecalled events

  ElectionEngine.sol
    - Ranked-choice voting with sqrt(DPC) weighting
    - Quorum enforcement
    - Candidacy registration and validation
    - Tally computation (verifiable on-chain)

  EmergencyPower.sol
    - Grants temporary elevated access to Steward-level roles
    - Hard-coded 72-hour auto-expiry (not adjustable by any role)
    - Requires community ratification to extend (creates new grant)
    - Emits EmergencyInvoked, EmergencyExpired events

  CartelDetector.sol
    - Stores review graph edges
    - Computes clustering metrics (called by off-chain oracle, verified on-chain)
    - Applies Rw penalties
    - Appeals process: flagged contributor can submit counter-evidence

  FounderSunset.sol
    - Immutable contract tracking Phase transitions
    - Veto power checks founder status + current phase
    - After Phase 2 timestamp: all founder-specific functions revert
    - Cannot be upgraded or proxied (no admin key)

  GovernanceWeight.sol
    - Computes: token_balance * DHM * contribution_score * alignment_score * activity_factor
    - Sublinear scaling on token_balance component (sqrt)
    - Max 5% cap per identity
    - Used by ElectionEngine for vote weighting
```

### 5.2 Deployment Target

- **Primary**: Polygon zkEVM (low gas, EVM-compatible, production-ready)
- **Fallback**: Arbitrum One (if Polygon underperforms)
- **Governance tokens**: $KOIN on primary chain
- **Cross-chain**: Bridge to Ethereum mainnet for major constitutional votes only

### 5.3 Upgrade Path

Contracts use the UUPS proxy pattern for operational contracts (CouncilManager, ElectionEngine, CartelDetector). Upgrade requires:
- Proposal through Protocol domain council
- 7-day community vote (60% approval, 20% quorum)
- 48-hour timelock before execution

**Non-upgradeable contracts** (by design):
- FounderSunset.sol — immutable, no proxy, no admin
- EmergencyPower.sol — 72h expiry is hardcoded, not configurable

---

## 6. Integration with Existing Architecture

### 6.1 DPC Formula Mapping

The existing DPC formula `P = f(Is, Ec, Rw)` maps directly to governance eligibility:

| DPC Component | Governance Function |
|---------------|-------------------|
| **Is** (Structural Impact) | Qualification for Council Member — must have verifiable output |
| **Ec** (Consistent Energy) | Eligibility gate — decay prevents inactive re-entry |
| **Rw** (Weighted Resonance) | Peer validation — cartel detection protects this signal |

### 6.2 Contributor Level Alignment

| S0S Level | OPRLP Role | Additional Requirements |
|-----------|-----------|----------------------|
| Learner (0-99) | Participant | None — can vote, observe, learn |
| Contributor (100-499) | Delegate | Can propose minor changes |
| Builder (500-1999) | Council Member eligible | Must meet sustained activity + diversity requirements |
| Steward (2000-4999) | Steward eligible | Must have completed Council term |
| Architect (5000+) | Guardian eligible | Must have completed Steward term + confidence vote |

### 6.3 Governance Finalization Integration

OPRLP must be ratified through the existing 24-week governance finalization pipeline:
- Included in **Core Rules** (Weeks 8-15)
- Rotation parameters (term length, cooldown, quorum) are DAO-adjustable after ratification
- Eligibility thresholds locked in Constitution (requires supermajority to change)

---

## 7. Phase 2 Design Decision: Sortition Layer

**Status: Requires Mev input before implementation.**

Research identified a gap: even DPC-gated rotation can converge to a small pool of high-contributors. Sortition (random selection from qualified pool) would add unpredictability.

**Proposed design (if approved):**
- For each council rotation, 5 seats filled by election, 2 seats filled by random selection from all DPC-qualified candidates
- Random selection uses VRF (Verifiable Random Function) — Chainlink VRF or equivalent
- Sortition members serve the same term with the same authority
- Rationale: prevents "campaign optimization" where contributors game the election process

[NEEDS_MEV_INPUT]
{"question": "Should the OPRLP include a sortition (random selection) layer for 2 of 7 council seats?", "options": ["Yes - 5 elected + 2 random from qualified pool", "No - all 7 seats elected", "Defer to Phase 2 design"], "recommendation": 0, "context": "Research shows even meritocratic systems converge to a small elite. Sortition adds healthy unpredictability. Academic consensus supports it. Easy to layer in but changes council dynamics."}
[/NEEDS_MEV_INPUT]

---

## 8. Implementation Priority

| # | Component | Priority | Depends On | Est. Complexity |
|---|-----------|----------|------------|-----------------|
| 1 | DPCRegistry.sol | P1 | ONEON identity | Medium |
| 2 | GovernanceWeight.sol | P1 | DPCRegistry | Medium |
| 3 | ElectionEngine.sol | P1 | GovernanceWeight | High |
| 4 | CouncilManager.sol | P1 | ElectionEngine | High |
| 5 | EmergencyPower.sol | P2 | CouncilManager | Low |
| 6 | CartelDetector.sol | P2 | DPCRegistry | High |
| 7 | FounderSunset.sol | P2 | None | Low |
| 8 | Frontend (OMS governance page) | P2 | All contracts | Medium |

**Dependency chain**: ONEON Identity -> DPCRegistry -> GovernanceWeight -> ElectionEngine -> CouncilManager

**Note**: Implementation is gated on ONEON Identity MVP and $KOIN token deployment. Both are pre-existing dependencies in the S0S architecture.

---

## Appendix A: Comparison to Industry Models

| Feature | Uniswap | Lido | Aave | 505 Systems (OPRLP) |
|---------|---------|------|------|---------------------|
| Voting weight | Token balance | Token balance | Token balance | sqrt(DPC) — contribution-weighted |
| Term limits | None | None | None | 90/180/365 days with cooldowns |
| Rotation | None (delegation) | Committee rotation | None | Mandatory with DPC gating |
| Anti-capture | Quorum only | Dual governance | Guardian | 5-vector countermeasures |
| Emergency powers | Governance pause | Committee veto | Guardian | 72h auto-expiry, non-extendable |
| Founder sunset | No timeline | No timeline | No timeline | Immutable Phase 2 sunset |

---

## Appendix B: Open Questions

1. **Sortition**: See Section 7 — awaiting Mev direction
2. **Cross-chain governance**: If $KOIN deploys on multiple chains (per Koink.fun directive), how do governance weights aggregate? Recommendation: canonical governance on one chain, bridge votes for major decisions only.
3. **Agent governance weight**: Should AI agents (Otto, future agents) have governance weight? Current design: no. Agents execute, humans govern.
4. **Dispute resolution**: Constitutional court equivalent? Current design defers to Guardian arbitration + community override. May need dedicated dispute resolution council.

---

*The river has no king. It has a current. Move with it, shape it, but you cannot dam it forever.*

*Architecture by Otto | Prerequisite research: 29 sources | Review by Mev before implementation*
