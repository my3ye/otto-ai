# Memory Capsule Annotation Layer & Royalty Flow Architecture

*Authored by Otto (Architect Agent) | 2026-03-27 | Status: Architecture Complete*

---

## Design: Memory Capsule Annotation & Perpetual Royalties

### Problem

People who help build Otto's intelligence — labelers, curators, correctors, training signal providers — receive nothing today. Data workers are the most exploited group in AI. Mev's directive: bring annotation of AI/Memory Capsules on-chain so every contributor earns perpetual rewards until their data is used and then some. Not a one-time bounty. A stream.

The existing Memory Capsule architecture (ONEON) has quality scoring and earnings tracking but no annotation registry, no provenance graph linking derived data back to contributors, no usage-event triggers, and no royalty distribution mechanism.

### Constraints

- **Existing foundation:** 3 confirmed primitives — `MemoryCapsule.quality_score`, `MemoryCapsule.total_earnings` + `GrantType.Perpetual`, TrustGraph RDF provenance (memory-based)
- **Chain target:** Base (EVM) — consistent with Otto Music and data layer plans
- **Tooling:** Foundry (consistent with OPRLP contracts at `/mnt/media/projects/oprlp-contracts/`)
- **No existing contracts deployed.** Otto Music contracts are Phase 1 roadmap, not live.
- **Pre-mainnet blocker:** GitHub encryption boundary (memory `c8d42186`) — which capsule content is eligible for on-chain annotation (public/permissioned) vs private (off-chain metadata only)
- **Budget discipline:** Ship incrementally. Phase 1 on testnet before mainnet.

### Approach

Four contracts. Two phases. The annotation registry is the core — everything else depends on it.

---

## 1. Component Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                        ON-CHAIN (Base)                               │
│                                                                       │
│  ┌──────────────────┐   ┌──────────────────┐   ┌──────────────────┐ │
│  │ AnnotationRegistry│──►│  ProvenanceGraph │   │  RoyaltyPool     │ │
│  │                  │   │                  │   │                  │ │
│  │ registerAnnotation│   │ linkDerivation   │   │ deposit          │ │
│  │ updateQualityScore│   │ getAncestors     │   │ claimRoyalties   │ │
│  │ supersede        │   │ getDescendants   │   │ getAccrued       │ │
│  │ getAnnotation    │   │ attributionShares│   │ sweep            │ │
│  └────────┬─────────┘   └────────┬─────────┘   └────────┬─────────┘ │
│           │                      │                      │           │
│           └──────────┬───────────┘                      │           │
│                      ▼                                  │           │
│           ┌──────────────────┐                          │           │
│           │ UsageOracle      │─────────────────────────►│           │
│           │                  │                                      │
│           │ reportUsage      │   (triggers royalty accrual)         │
│           │ reportBatch      │                                      │
│           └──────────────────┘                                      │
│                                                                       │
└───────────────────────────────────┬─────────────────────────────────┘
                                    │
                    ────────────────┼────────────────
                                    │
┌───────────────────────────────────┼─────────────────────────────────┐
│                        OFF-CHAIN (Otto)                              │
│                                    │                                  │
│  ┌──────────────────┐   ┌─────────┴────────┐   ┌──────────────────┐ │
│  │ Memory API        │   │ Usage Hook       │   │ Shapley Module   │ │
│  │ (:8100)           │──►│ (retrieval path) │   │ (attribution)    │ │
│  │                   │   │                  │   │                  │ │
│  │ /annotations/*    │   │ intercepts reads │   │ calculates fair  │ │
│  │ capsule CRUD      │   │ batches events   │   │ credit splits    │ │
│  │ quality pipeline  │   │ calls Oracle     │   │ feeds Registry   │ │
│  └──────────────────┘   └──────────────────┘   └──────────────────┘ │
│                                                                       │
│  ┌──────────────────┐   ┌──────────────────┐                        │
│  │ Quality Validators│   │ Supersession     │                        │
│  │ (existing QS)     │   │ Detector         │                        │
│  │                   │   │                  │                        │
│  │ score annotations │   │ detects when v2  │                        │
│  │ commit-reveal     │   │ replaces v1      │                        │
│  │ consensus median  │   │ triggers decay   │                        │
│  └──────────────────┘   └──────────────────┘                        │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 2. Annotation Schema

### 2.1 On-Chain: AnnotationRegistry.sol

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

struct Annotation {
    bytes32 annotationId;       // keccak256(capsuleId, contentHash, annotator, nonce)
    bytes32 capsuleId;          // Which Memory Capsule this annotates
    address annotator;          // Contributor's wallet address
    AnnotationType annType;     // What kind of contribution
    bytes32 contentHash;        // IPFS CID or SHA256 of the annotation content
    uint32 qualityScore;        // 0-10000 (set by validators, updated over time)
    uint64 createdAt;           // Block timestamp
    uint16 version;             // Annotation version (v1, v2, etc.)
    bytes32 supersededBy;       // 0x0 if current; points to replacement annotation
    bool active;                // false when superseded or deprecated
}

enum AnnotationType {
    Label,          // Classification, tagging, categorization
    Curation,       // Selection, filtering, quality gating
    TrainingSignal, // RLHF feedback, preference pairs, reward signals
    Correction,     // Error fix, factual correction, dedup
    Enrichment,     // Added context, cross-references, metadata
    Synthesis       // Combining multiple sources into refined knowledge
}
```

**Design notes:**
- `contentHash` points to off-chain content (IPFS or encrypted storage). On-chain stores only the hash — no private data on-chain.
- `version` enables explicit supersession (Option C from research). v2 supersedes v1; v1 enters decay.
- `AnnotationType` enum is intentionally broad. Six types cover the contribution taxonomy. Governance can add types via upgrade.
- `qualityScore` is set by the existing validator network (§3.3 of Memory Capsules arch), not by the annotator.

### 2.2 Off-Chain: Annotation Content

Annotation content lives off-chain, encrypted where necessary:

```python
# Stored on IPFS, referenced by contentHash
{
    "annotation_id": "0x...",
    "capsule_id": "0x...",
    "capsule_layer": 3,              # Which capsule layer was annotated
    "annotation_type": "correction",
    "content": {
        "original": "SHA256 of original fact",
        "corrected": "The corrected fact text",
        "reasoning": "Why this correction improves the capsule",
        "evidence_cids": ["QmABC...", "QmDEF..."]  # Supporting evidence
    },
    "metadata": {
        "tool_used": "otto-annotation-ui",
        "session_id": "...",
        "time_spent_seconds": 240
    }
}
```

**Privacy rule:** Annotations on layers 0-2 (private) are never eligible for on-chain registration. Only layers 3-7 (shareable/public) can have on-chain annotations. This is the encryption boundary resolution — private capsule content stays off-chain, annotation hashes on public/shareable layers go on-chain.

---

## 3. Provenance Graph

### 3.1 On-Chain: ProvenanceGraph.sol

Tracks derivation relationships between annotations and capsules. When a new capsule is derived from annotated data, the link is recorded permanently.

```solidity
struct Derivation {
    bytes32 derivationId;       // keccak256(childCapsuleId, parentAnnotationId)
    bytes32 childCapsuleId;     // The capsule that was created/improved
    bytes32 parentAnnotationId; // The annotation that contributed
    uint16 contributionWeight;  // 0-10000 (how much this annotation contributed)
    uint64 recordedAt;
}

// Core functions
interface IProvenanceGraph {
    /// Link a derived capsule back to its source annotations
    function linkDerivation(
        bytes32 childCapsuleId,
        bytes32 parentAnnotationId,
        uint16 contributionWeight
    ) external;

    /// Get all source annotations for a capsule (with weights)
    function getAncestors(bytes32 capsuleId)
        external view returns (Derivation[] memory);

    /// Get all capsules derived from an annotation
    function getDescendants(bytes32 annotationId)
        external view returns (Derivation[] memory);

    /// Calculate attribution shares for royalty distribution
    /// Returns annotator addresses and their proportional shares (sum = 10000)
    function attributionShares(bytes32 capsuleId)
        external view returns (address[] memory annotators, uint16[] memory shares);
}
```

### 3.2 Attribution Calculation (Off-Chain Shapley → On-Chain Shares)

The Shapley attribution module runs off-chain (computationally expensive) and writes results on-chain.

```python
# Off-chain: Shapley attribution for multi-annotator capsules
def calculate_attribution(capsule_id: str) -> dict[str, float]:
    """
    Simplified Shapley: for N annotators, approximate marginal contribution
    by measuring capsule quality delta with and without each annotation.

    For small N (≤10): exact Shapley via all 2^N subsets
    For large N (>10): Monte Carlo approximation (1000 samples)
    """
    ancestors = provenance_graph.get_ancestors(capsule_id)

    if len(ancestors) <= 10:
        shares = exact_shapley(capsule_id, ancestors)
    else:
        shares = monte_carlo_shapley(capsule_id, ancestors, samples=1000)

    # Normalize to sum = 10000 (basis points)
    total = sum(shares.values())
    return {addr: int(share / total * 10000) for addr, share in shares.items()}

def marginal_contribution(capsule_id, annotation_id, subset):
    """
    Quality delta when adding this annotation to the subset.
    Uses the existing QS model (depth × freshness × coherence × utility × coverage).
    """
    qs_without = evaluate_quality(capsule_id, excluding=[annotation_id])
    qs_with = evaluate_quality(capsule_id, including=[annotation_id])
    return qs_with - qs_without
```

**Key decision:** Shapley runs off-chain, writes shares on-chain. On-chain Shapley is infeasible (O(2^N) gas). The off-chain computation is run by Otto as a trusted oracle initially, with governance upgrade path to multi-validator Shapley consensus in Phase 2.

---

## 4. Royalty Trigger Events

### 4.1 Usage Types

Four events trigger royalty accrual:

| Event | Trigger | Weight | Source |
|-------|---------|--------|--------|
| **Capsule Read** | Shard retrieval via access grant | 1× base rate | Storage node `emit_retrieval_event` (existing) |
| **Inference Use** | Annotated data injected into LLM context | 3× base rate | Otto retrieval pipeline (new hook) |
| **License/Sale** | Access grant purchased for annotated layer | 10× base rate | `pay_grant()` event (existing) |
| **Fork** | New capsule derived from annotated data | 5× base rate | `linkDerivation()` event (new) |

### 4.2 On-Chain: UsageOracle.sol

```solidity
struct UsageEvent {
    bytes32 capsuleId;
    bytes32 annotationId;       // 0x0 if capsule-level event
    UsageType usageType;
    uint64 timestamp;
    uint32 weight;              // Usage weight (1, 3, 5, or 10 × base)
}

enum UsageType { Read, Inference, License, Fork }

interface IUsageOracle {
    /// Report a single usage event (called by authorized reporters)
    function reportUsage(
        bytes32 capsuleId,
        bytes32 annotationId,
        UsageType usageType
    ) external;

    /// Batch report (gas-efficient for high-volume reads)
    function reportBatch(UsageEvent[] calldata events) external;
}
```

### 4.3 Off-Chain: Usage Hook (Retrieval Path)

The usage hook intercepts Otto's retrieval pipeline to detect when annotated data is accessed.

```python
# In Otto's retrieval path (memory/routes/ or kernel/smmu.py)
class AnnotationUsageHook:
    """
    Intercepts capsule shard retrievals and LLM context injections.
    Batches events and reports to UsageOracle every 60 seconds.
    """

    def __init__(self):
        self.pending_events: list[UsageEvent] = []
        self.flush_interval = 60  # seconds

    async def on_shard_retrieval(self, capsule_id: str, layer_id: int, grant_id: str):
        """Fired when a shard is retrieved via access grant."""
        annotations = await self.get_layer_annotations(capsule_id, layer_id)
        for ann_id in annotations:
            self.pending_events.append(UsageEvent(
                capsule_id=capsule_id,
                annotation_id=ann_id,
                usage_type=UsageType.READ,
                weight=1
            ))

    async def on_inference_injection(self, capsule_id: str, annotation_ids: list[str]):
        """Fired when annotated data is injected into LLM context."""
        for ann_id in annotation_ids:
            self.pending_events.append(UsageEvent(
                capsule_id=capsule_id,
                annotation_id=ann_id,
                usage_type=UsageType.INFERENCE,
                weight=3
            ))

    async def flush(self):
        """Batch-report to UsageOracle on-chain."""
        if not self.pending_events:
            return
        batch = self.pending_events.copy()
        self.pending_events.clear()
        await oracle_contract.report_batch(batch)
```

**Design decision:** Batch reporting (60s window) instead of per-event on-chain writes. Saves gas. Trade-off: 60s delay in royalty accrual, which is irrelevant for perpetual streams.

---

## 5. Reward Distribution Logic

### 5.1 On-Chain: RoyaltyPool.sol

```solidity
interface IRoyaltyPool {
    /// Deposit $KOIN into the royalty pool (from usage fees, agent tax, protocol revenue)
    function deposit(uint256 amount) external;

    /// Claim accrued royalties for caller's annotations
    function claimRoyalties() external returns (uint256 claimed);

    /// View accrued but unclaimed royalties
    function getAccrued(address annotator) external view returns (uint256);

    /// Admin: sweep unclaimed royalties from deprecated annotations (after grace period)
    function sweep(bytes32[] calldata deprecatedAnnotations) external;
}
```

### 5.2 Royalty Calculation

```
Per-event royalty for annotation A on capsule C:

  royalty = base_rate
          × usage_weight          (1, 3, 5, or 10 depending on event type)
          × quality_factor        (A.qualityScore / 10000)
          × attribution_share     (A's share from Shapley, in basis points / 10000)
          × decay_factor          (1.0 if active, decaying if superseded)

Where:
  base_rate = 0.001 $KOIN (governance-adjustable)
  quality_factor = annotation quality / 10000
  attribution_share = from ProvenanceGraph.attributionShares()
  decay_factor = see §5.3
```

### 5.3 Perpetual Streaming + Supersession Decay

**Active annotations:** Full royalty rate. No time decay while the annotation is marked `active = true` and actively being used.

**Superseded annotations (v1 replaced by v2):**
- Royalty enters a **decay curve** upon supersession
- Decay function: `decay_factor = 0.5 ^ (months_since_superseded / 6)`
  - Month 0: 100% → Month 6: 50% → Month 12: 25% → Month 18: 12.5%
- Floor: royalty never drops below 1% of original rate while the annotation's data is still retrievable (i.e., still contributes to any capsule in the provenance graph)
- **Final usage-event bonus:** When an annotation is fully deprecated (superseded AND no longer retrievable), a one-time bonus of 10× the average monthly royalty is paid out as a "thank you" event

```solidity
function decayFactor(bytes32 annotationId) public view returns (uint256) {
    Annotation memory ann = registry.getAnnotation(annotationId);

    if (ann.active) return 1e18; // No decay — full rate (WAD precision)

    // Superseded: exponential decay with 6-month half-life
    uint256 monthsSinceSuperseded = (block.timestamp - ann.supersededAt) / 30 days;
    uint256 factor = WAD; // 1e18

    // Halve every 6 months
    uint256 halvings = monthsSinceSuperseded / 6;
    for (uint256 i = 0; i < halvings && i < 20; i++) {
        factor = factor / 2;
    }

    // Floor: 1% of original (1e16)
    if (factor < 1e16) factor = 1e16;

    return factor;
}
```

### 5.4 Funding Sources

The RoyaltyPool is funded from multiple revenue streams:

| Source | Allocation | Mechanism |
|--------|-----------|-----------|
| Capsule access fees | 15% of grant revenue | Auto-split in `pay_grant()` |
| Agent automation tax | 100% of annotation-related tax | From onchain task system |
| Protocol revenue share | 5% of daily $KOIN emission | Quality pool (existing, extended) |
| Fork fees | 20% of fork event revenue | From `linkDerivation()` |

---

## 6. Governance of Quality Scoring

### 6.1 Validator Network (Extends Existing QS System)

Annotation quality scoring uses the same validator framework from Memory Capsules §3.3, extended:

```
Annotation Quality Assessment:
  1. Validator receives annotation (content via IPFS, not on-chain)
  2. Validator scores on 4 dimensions:
     - Accuracy: Is the annotation factually correct? (0-100)
     - Impact: Does it measurably improve the capsule? (0-100)
     - Originality: Is this a novel contribution or trivially derivative? (0-100)
     - Effort: Quality of reasoning, evidence, thoroughness (0-100)
  3. Weighted score: accuracy(0.35) + impact(0.30) + originality(0.20) + effort(0.15)
  4. Commit-reveal scheme (same as capsule QS): prevents collusion
  5. Consensus: weighted median of 3+ validator scores (staked weight)
  6. Validators who deviate >15 from consensus lose stake fraction
```

### 6.2 Anti-Gaming Protections

| Attack | Defense |
|--------|---------|
| Sybil annotations (many low-quality from sockpuppets) | Minimum stake to annotate (1000 $KOIN); quality score < 30 → annotation delisted after 3 cycles |
| Validator collusion | Commit-reveal + stake slashing for deviation > 15 from median |
| Self-referential forks (annotator forks own capsule for fork royalties) | Fork fee paid by forker; self-fork detected by `annotator == capsule.owner` → no royalty |
| Quality score manipulation | Validator rotation (no validator scores same capsule twice in 90 days) |
| Annotation spam | Rate limit: max 10 annotations per address per day; quality gate: first 3 annotations in probation (no royalties until quality > 50) |

### 6.3 Governance Parameters (Adjustable by SOS DAO)

| Parameter | Default | Adjustable By |
|-----------|---------|---------------|
| `base_royalty_rate` | 0.001 $KOIN | DAO vote |
| `decay_halflife_months` | 6 | DAO vote |
| `decay_floor_pct` | 1% | DAO vote (min 0.1%) |
| `min_stake_to_annotate` | 1000 $KOIN | DAO vote |
| `max_annotations_per_day` | 10 | DAO vote |
| `probation_count` | 3 | DAO vote |
| `quality_delist_threshold` | 30 | DAO vote |
| `final_bonus_multiplier` | 10 | DAO vote |
| `usage_weights` | [1, 3, 5, 10] | DAO vote |

---

## 7. Data Flow (End-to-End)

```
Contributor submits annotation
         │
         ▼
┌─────────────────────┐
│ 1. Off-chain:       │
│    Upload content    │──── IPFS CID ────┐
│    to IPFS           │                    │
└─────────────────────┘                    │
         │                                  │
         ▼                                  ▼
┌─────────────────────┐    ┌──────────────────────┐
│ 2. On-chain:        │    │ 3. Validators:       │
│    registerAnnotation│    │    Score annotation  │
│    (capsuleId,       │    │    (commit-reveal)   │
│     contentHash,     │◄───│    Update quality    │
│     annotationType)  │    │    on-chain          │
└──────────┬──────────┘    └──────────────────────┘
           │
           ▼
┌─────────────────────┐
│ 4. Provenance:      │
│    linkDerivation    │
│    (if capsule uses  │
│     this annotation) │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐    ┌──────────────────────┐
│ 5. Usage happens:   │    │ 6. Off-chain hook:   │
│    - Shard retrieved │───►│    Batch usage events │
│    - Injected in LLM │    │    (60s window)       │
│    - Grant purchased │    │    Report to Oracle   │
│    - Capsule forked  │    └──────────┬───────────┘
└─────────────────────┘               │
                                       ▼
                           ┌──────────────────────┐
                           │ 7. On-chain:         │
                           │    UsageOracle        │
                           │    reportBatch()      │
                           └──────────┬───────────┘
                                       │
                                       ▼
                           ┌──────────────────────┐
                           │ 8. RoyaltyPool:      │
                           │    Accrue royalties   │
                           │    per annotation     │
                           │    × quality × share  │
                           │    × decay factor     │
                           └──────────┬───────────┘
                                       │
                                       ▼
                           ┌──────────────────────┐
                           │ 9. Contributor:      │
                           │    claimRoyalties()   │
                           │    Pull accumulated   │
                           │    $KOIN at any time  │
                           └──────────────────────┘
```

---

## 8. Contract Architecture

### 8.1 Project Structure

```
/mnt/media/projects/annotation-contracts/
├── foundry.toml
├── .env.example
├── .gitignore
│
├── src/
│   ├── interfaces/
│   │   ├── IAnnotationRegistry.sol
│   │   ├── IProvenanceGraph.sol
│   │   ├── IUsageOracle.sol
│   │   └── IRoyaltyPool.sol
│   │
│   ├── core/
│   │   ├── AnnotationRegistry.sol    # Phase 1
│   │   ├── ProvenanceGraph.sol       # Phase 1
│   │   ├── UsageOracle.sol           # Phase 1
│   │   └── RoyaltyPool.sol           # Phase 1
│   │
│   └── libraries/
│       ├── DecayMath.sol             # Exponential decay + floor calculation
│       └── ShapleyBridge.sol         # Accepts off-chain Shapley results with signature verification
│
├── test/
│   ├── AnnotationRegistry.t.sol
│   ├── ProvenanceGraph.t.sol
│   ├── UsageOracle.t.sol
│   ├── RoyaltyPool.t.sol
│   └── Integration.t.sol
│
├── script/
│   ├── Deploy.s.sol
│   └── Upgrade.s.sol
│
└── lib/
    ├── forge-std/
    └── openzeppelin-contracts/
```

### 8.2 Upgrade Strategy

| Contract | Proxy | Reason |
|----------|-------|--------|
| AnnotationRegistry | UUPS | Schema may need new annotation types |
| ProvenanceGraph | UUPS | Graph traversal logic may optimize |
| UsageOracle | UUPS | New usage types or batch logic |
| RoyaltyPool | **Immutable** | Financial contract — no admin key, no upgrade path. Trust = immutability. |

RoyaltyPool is immutable for the same reason FounderSunset is immutable in OPRLP: constitutional guarantees must not have an admin escape hatch.

### 8.3 Access Control

| Function | Caller |
|----------|--------|
| `registerAnnotation` | Anyone with minimum stake |
| `updateQualityScore` | Validator consensus (multi-sig or oracle) |
| `supersede` | Original annotator OR governance |
| `linkDerivation` | Capsule owner (or authorized agent) |
| `reportUsage` | Authorized reporter addresses (Otto nodes) |
| `reportBatch` | Authorized reporter addresses |
| `claimRoyalties` | Annotator (claims own accrued) |
| `deposit` | Anyone (protocol revenue, grants, fees) |
| `sweep` | Governance (after 12-month grace period) |

---

## 9. Off-Chain Components (Otto Memory API)

### 9.1 New API Routes

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `POST /annotations` | Create annotation (uploads to IPFS, registers on-chain) |
| `GET /annotations/{id}` | Get annotation detail (on-chain + off-chain content) |
| `GET /annotations/capsule/{capsuleId}` | List all annotations for a capsule |
| `GET /annotations/contributor/{address}` | List all annotations by a contributor |
| `POST /annotations/{id}/supersede` | Mark annotation as superseded by new version |
| `GET /royalties/{address}` | View accrued royalties for address |
| `POST /royalties/claim` | Trigger on-chain claim |
| `GET /provenance/{capsuleId}` | Get full provenance graph for a capsule |

### 9.2 New Module

```
otto/memory/annotations/
├── __init__.py
├── registry.py           # On-chain AnnotationRegistry interaction
├── provenance.py         # ProvenanceGraph read/write
├── usage_hook.py         # Retrieval path hook + batch reporter
├── shapley.py            # Off-chain Shapley attribution calculation
├── supersession.py       # Detects when annotations are superseded
└── models.py             # Pydantic models for annotation data
```

### 9.3 Database Migration

```sql
-- Migration XXX: annotation_tracking
CREATE TABLE annotation_cache (
    annotation_id TEXT PRIMARY KEY,
    capsule_id TEXT NOT NULL,
    annotator_address TEXT NOT NULL,
    annotation_type TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    quality_score INTEGER DEFAULT 0,
    version INTEGER DEFAULT 1,
    superseded_by TEXT,
    active BOOLEAN DEFAULT TRUE,
    chain_tx_hash TEXT,
    chain_confirmed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_annotation_capsule ON annotation_cache(capsule_id);
CREATE INDEX idx_annotation_annotator ON annotation_cache(annotator_address);
CREATE INDEX idx_annotation_active ON annotation_cache(active) WHERE active = TRUE;

CREATE TABLE annotation_usage_events (
    id BIGSERIAL PRIMARY KEY,
    annotation_id TEXT NOT NULL REFERENCES annotation_cache(annotation_id),
    capsule_id TEXT NOT NULL,
    usage_type TEXT NOT NULL,  -- read, inference, license, fork
    weight INTEGER NOT NULL,
    reported_on_chain BOOLEAN DEFAULT FALSE,
    batch_tx_hash TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_usage_unreported ON annotation_usage_events(reported_on_chain)
    WHERE reported_on_chain = FALSE;

CREATE TABLE attribution_cache (
    capsule_id TEXT NOT NULL,
    annotator_address TEXT NOT NULL,
    share_bps INTEGER NOT NULL,  -- basis points (0-10000)
    computed_at TIMESTAMPTZ DEFAULT NOW(),
    chain_synced BOOLEAN DEFAULT FALSE,
    PRIMARY KEY (capsule_id, annotator_address)
);
```

---

## 10. Key Decisions

1. **Off-chain Shapley, on-chain shares**: Shapley is O(2^N) — cannot run on-chain. Otto computes off-chain and writes results on-chain with a signature. Alternative: on-chain approximation (rejected — inaccurate and gas-prohibitive for N > 5).

2. **Immutable RoyaltyPool**: Financial guarantees must be trustless. No admin can change royalty rules once deployed. Alternative: UUPS proxy (rejected — undermines the "perpetual" promise).

3. **Batch usage reporting (60s window)**: Gas efficiency over real-time. A single `reportBatch()` call for all usage events in a window. Alternative: per-event reporting (rejected — 100x gas cost at scale).

4. **Explicit versioning for supersession (Option C)**: Annotator submits v2 → v1 enters decay. Clear, intentional, auditable. Alternative A: time-based decay (rejected — punishes long-lived valuable annotations). Alternative B: usage-weighted decay (rejected — complex, circular dependency with royalties).

5. **Base chain**: Consistent with Otto Music and data layer plans. Low gas, EVM-compatible. Alternative: Polygon zkEVM (where OPRLP contracts deploy). Decision: keep annotation layer on Base, OPRLP on Polygon. Different concerns, different chains. Bridge if needed later.

6. **Annotations only on layers 3-7**: Resolves the encryption boundary pre-mainnet blocker. Private layers (0-2) never annotated on-chain. Alternative: annotate all layers with encrypted hashes (rejected — leaked metadata risk, and private layers aren't monetizable anyway per Memory Capsule spec §1.4).

7. **Foundry tooling**: Consistent with OPRLP contracts. Same test patterns, same CI, same deployment scripts.

---

## 11. Implementation Plan

### Phase 1: Testnet (~$12-15, 5 steps)

1. **Scaffold Foundry project** — `annotation-contracts/`, foundry.toml, OZ imports, interfaces. (~$1)
2. **AnnotationRegistry.sol + tests** — Core registration, quality updates, supersession logic. (~$3)
3. **ProvenanceGraph.sol + tests** — Derivation linking, ancestor/descendant queries, attribution share storage. (~$3)
4. **UsageOracle.sol + RoyaltyPool.sol + tests** — Usage reporting, royalty accrual, claim flow, decay math. (~$4)
5. **Integration tests + Base Sepolia deploy** — End-to-end: register → use → accrue → claim. Deploy to testnet. (~$2-3)

### Phase 2: Off-Chain Integration (~$8-10, 4 steps)

6. **Database migration + annotation module** — `annotation_cache`, `annotation_usage_events`, `attribution_cache` tables + Python module. (~$2)
7. **Usage hook in retrieval path** — Intercept shard retrievals and LLM injections, batch to Oracle. (~$2)
8. **Shapley attribution module** — Off-chain computation + on-chain write via ShapleyBridge. (~$3)
9. **API routes + OMS page** — `/annotations/*`, `/royalties/*`, `/provenance/*` endpoints + OMS visualization. (~$2-3)

### Phase 3: Mainnet + Governance (~$4-6)

10. **Resolve encryption boundary** — Formal policy doc: what goes on-chain, what stays off-chain. (Mev approval required)
11. **Base mainnet deployment** — Deploy all 4 contracts with governance parameters set by SOS DAO. (~$2)
12. **Validator integration** — Connect existing QS validator network to annotation quality scoring. (~$2-3)

**Total estimate: ~$24-31 across all phases.**

---

## 12. Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Gas costs spike on Base | Royalty accrual becomes uneconomical | Batch reporting (60s window). Move to L3 if Base gas exceeds threshold. |
| Shapley computation gaming | Annotator creates many tiny annotations to inflate share | Quality gate: annotations with QS < 30 get 0 share. Minimum contribution threshold. |
| Oracle centralization (Phase 1) | Otto as sole usage reporter is a trust bottleneck | Phase 2: multi-reporter with stake + slashing. Phase 3: decentralized oracle network. |
| Supersession disputes | Annotator disagrees their v1 should be superseded | Governance dispute resolution. 30-day grace period before decay begins. |
| RoyaltyPool insolvency | More accrued royalties than pool balance | Pool operates on deposit-first model. Royalties accrue as claims against deposited funds. Claims fail gracefully if pool is empty (retry later). |
| Encryption boundary undefined | Private data leaks via annotation hashes | Layer 0-2 excluded by contract logic (`require(layer >= 3)`). Enforcement at contract level, not trust. |

---

## 13. Mev Decision Required

[NEEDS_MEV_INPUT]
{"question": "Supersession trigger mechanism for annotation royalty decay", "options": ["Option A: Time-based decay (automatic, no quality signal)", "Option B: Usage-weighted decay (complex, proportional to retrieval frequency)", "Option C: Explicit versioning (annotator submits v2, v1 enters decay curve)"], "recommendation": 2, "context": "When an annotation is superseded by a better version, how should the original annotator's royalties decay? Option C is cleanest — clear intent, auditable, annotator controls when they supersede themselves. Research validated this as the recommended approach."}
[/NEEDS_MEV_INPUT]

This architecture proceeds with Option C (explicit versioning) as the default, pending Mev confirmation.

---

*Cross-references:*
- *Memory Capsules Architecture: `projects/oneon/memory_capsules_architecture.md`*
- *OPRLP Contract Architecture: `docs/oprlp-solidity-architecture-2026-03-27.md`*
- *Onchain Task System: Phase 1 implemented (migration 062)*
- *Koink Integration: `docs/koink-integration-architecture-2026-03-23.md`*
- *Research: `logs/tasks/0dec93d5-.../output.md` (validated synthesis)*
