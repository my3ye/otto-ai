# ONEON Memory Capsules — Detailed Technical Architecture

**Author:** Otto
**Date:** 2026-03-18
**Status:** Design v1.0 — ONEON Phase 3 Pre-work
**Cross-references:**
- `otto_core/standing_directives.md` § 10 (Memory Capsules directive)
- `projects/capital/distributed_otto_architecture.md` § 2.4, § 6 (Storage Nodes, Encrypted Layer)
- `projects/memory_upgrade/ARCHITECTURE.md` § 8 (ONEON application of Otto's memory system)

---

## Overview

Every ONEON participant has a **Memory Capsule** — a sovereign, layered, on-chain personal intelligence store. Memory Capsules are the core product mechanic of ONEON's intelligence layer.

**The three guarantees:**
1. **Private by default** — no layer is visible unless the owner explicitly grants access
2. **Monetizable** — owners share specific layers in exchange for $KOIN
3. **Quality compounds** — deeper, richer capsules produce better LLM outputs for the owner and earn more when shared

**Architecture relationship:**
```
Memory Capsule
├── Identity anchor:   ONEON Layer 1 (self-sovereign DID)
├── Privacy layer:     ONEON Layer 4 (E2E encryption, XChaCha20-Poly1305)
├── Storage:           Otto Distributed Storage Nodes (encrypted shards)
└── Monetization:      ONEON governance ($KOIN quality-linked earnings)
```

Otto's 3-tier memory system (working → episodic → semantic/graph) is the **reference implementation** of Memory Capsules internally. Everything here mirrors that architecture — wrapped in client-side encryption and on-chain access control.

---

## 1. On-Chain Encrypted Storage Schema

### 1.1 Capsule Identity Record (on-chain)

Each capsule has a minimal on-chain anchor. The content stays off-chain (encrypted shards on storage nodes). The chain holds only the access manifest — pointers, hashes, and permissions.

```solidity
// Solana Anchor account (or EVM equivalent)
struct MemoryCapsule {
    owner: Pubkey,               // Owner's wallet address (= DID controller)
    did: String,                 // ONEON DID: did:oneon:QmOwnerPubkeyHash
    capsule_id: [u8; 32],        // SHA256(owner_pubkey || salt) — deterministic per owner
    version: u64,                // Incremented on each capsule mutation
    created_at: i64,             // Unix timestamp
    last_updated: i64,

    // Shard manifest (encrypted, only owner can read)
    shard_manifest_cid: String,  // IPFS CID of encrypted shard manifest
    manifest_hash: [u8; 32],     // SHA256 of plaintext manifest (integrity check)

    // Layer index (plaintext — access control is public, content is not)
    layer_count: u8,             // Current number of layers (max 8)
    layers: [LayerHeader; 8],    // Public metadata per layer

    // Quality + earnings state
    quality_score: u32,          // 0-10000 (scaled by 100 for precision)
    total_earnings: u64,         // Lifetime $KOIN earned (in lamports/smallest unit)
    last_validated: i64,         // When quality was last assessed

    // Access grants (monetization)
    active_grants: u16,          // Count of live access grants
}

struct LayerHeader {
    layer_id: u8,                // 0-7 (matches ONEON layer model)
    label: String,               // Short public label, e.g. "Professional Skills"
    visibility: Visibility,      // Private | Shared | Public
    shard_count: u8,             // How many shards this layer is split into
    root_cid: String,            // IPFS CID of this layer's encrypted shard root
    content_type: ContentType,   // Episodic | Semantic | Procedural | Graph
    freshness_ts: i64,           // Timestamp of last update (freshness signal)
    quality_contribution: u16,   // This layer's contribution to capsule QS (0-10000)
}

enum Visibility { Private, Shared, Public }
enum ContentType { Episodic, Semantic, Procedural, Graph, Mixed }
```

### 1.2 Shard Schema (off-chain, encrypted)

Each capsule layer is split into shards stored on Otto Distributed Storage Nodes. The content is never visible to storage nodes — encryption is client-side.

```
CapsuleShard {
    // Shard identity
    shard_id:           SHA256(capsule_id || layer_id || shard_index)
    capsule_id:         [u8; 32]
    layer_id:           u8              // 0-7
    shard_index:        u16             // index within this layer
    total_shards:       u16             // total shards for this layer

    // Encrypted payload
    nonce:              [u8; 24]        // XChaCha20 nonce (unique per shard)
    ciphertext:         bytes           // XChaCha20-Poly1305 encrypted content
    aad:                bytes           // "oneon/capsule/v1/{capsule_id}/{layer_id}"

    // Integrity
    content_hash:       [u8; 32]        // SHA256(plaintext) — owner verifies on decrypt
    merkle_path:        [[u8; 32]]      // Merkle proof path for inclusion verification
    layer_root:         [u8; 32]        // Merkle root of all shards in this layer

    // Metadata (plaintext — needed by storage nodes for routing/expiry)
    owner_did:          String          // Owner's DID (for routing, not content access)
    created_at:         i64
    expires_at:         i64             // Optional TTL (null = permanent)
    replication_target: u8              // Minimum replicas (default: 3)
    geo_requirements:   [String]        // Optional: ["Asia", "Europe"] for latency
}
```

### 1.3 Shard Manifest (encrypted, IPFS-stored)

The shard manifest is the owner's private index of all their shards. It's stored as a single encrypted blob on IPFS, with its CID anchored on-chain.

```python
# Decrypted manifest structure (JSON, encrypted before storing)
{
  "capsule_id": "...",
  "version": 42,
  "layers": {
    "0": {  # Layer 0 = active working context
      "layer_id": 0,
      "content_type": "Semantic",
      "shards": [
        {"shard_id": "...", "cid": "QmABC...", "storage_nodes": ["peer_id_1", "peer_id_2", "peer_id_3"]},
        {"shard_id": "...", "cid": "QmDEF...", "storage_nodes": ["peer_id_2", "peer_id_4", "peer_id_5"]}
      ],
      "layer_key_encrypted": "..."  # Layer key encrypted with owner's public key
    },
    "1": { ... },  # Layer 1 = episodic history
    ...
  },
  "access_grants": [...],  # List of active grants per layer
  "recovery_shards": [...]  # Shamir shards for master key recovery
}
```

### 1.4 Capsule Layers — ONEON Layer Model Mapping

Memory Capsules mirror ONEON's five-layer identity model:

| Capsule Layer | ONEON Layer | Content | Default Visibility |
|---|---|---|---|
| 0 — Active Context | Working (Tier 1) | Current goals, session state, active tasks | Private |
| 1 — Episodic Memory | Encrypted Private (Layer 4) | Conversations, events, decisions | Private |
| 2 — Semantic Memory | Encrypted Private (Layer 4) | Long-term facts, beliefs, knowledge | Private |
| 3 — Skills & Procedures | Community (Layer 2) | Learned behaviors, workflows, capabilities | Shareable |
| 4 — Professional Profile | Community (Layer 2) | Skills, expertise, work history (abstract) | Shareable |
| 5 — Social Graph | Community (Layer 2) | Relationships, community ties | Shareable |
| 6 — Governance Record | Governance (Layer 3) | Voting history, contribution record | Public |
| 7 — Public Presence | Public Presence (Layer 1) | Name, interests, opt-in public context | Public |

Layers 0-2 are never eligible for monetization sharing. Layers 3-7 can be granted per-layer access.

---

## 2. Layer Access Control Protocol

### 2.1 Access Grant Model

Access grants are on-chain records. An owner creates a grant that authorizes a specific entity (wallet address, DID, or role) to retrieve and decrypt a specific layer.

```solidity
struct AccessGrant {
    grant_id:       [u8; 32],         // SHA256(capsule_id || grantee || layer_id || nonce)
    capsule_id:     [u8; 32],
    grantor:        Pubkey,            // Capsule owner
    grantee:        Pubkey,            // Who receives access (wallet or service DID)
    layer_id:       u8,                // Which layer is being shared

    // Encrypted layer key (only grantee can decrypt)
    layer_key_enc:  [u8; 96],          // Layer key encrypted with grantee's X25519 pubkey

    // Grant terms
    grant_type:     GrantType,         // OneTime | Subscription | Perpetual
    valid_from:     i64,
    valid_until:    i64,               // -1 = perpetual
    max_retrievals: u32,               // -1 = unlimited
    retrievals_used: u32,

    // Monetization
    price_per_period: u64,             // $KOIN lamports, 0 = free
    payment_interval: u32,            // seconds, 0 = one-time
    last_paid:        i64,
    total_paid:       u64,

    // Status
    active:         bool,
    revoked_at:     i64,               // 0 = not revoked
}

enum GrantType { OneTime, Subscription, Perpetual }
```

### 2.2 Grant Creation Flow (Owner → Monetize a Layer)

```
Owner Client                     ONEON Chain              Grantee Client
     │                                │                         │
     │  1. Owner selects layer 4      │                         │
     │     (Professional Profile)     │                         │
     │     and sets price/terms       │                         │
     │                                │                         │
     │  2. Fetch grantee's X25519 pubkey (from their on-chain DID)
     │                                │                         │
     │  3. Encrypt layer_key with grantee's pubkey             │
     │     layer_key_enc = X25519_encrypt(grantee_pubkey, layer_key)
     │                                │                         │
     │──── create_access_grant() ────►│                         │
     │  {grant_id, capsule_id,        │                         │
     │   layer_id=4, grantee,         │                         │
     │   layer_key_enc, terms}        │                         │
     │                                │◄─── pay_grant() ────────│
     │                                │  {grant_id, payment}    │
     │◄─── grant_activated event ─────│                         │
     │                                │──── grant_confirmed ───►│
     │                                │                         │
     │                                │   Grantee can now:      │
     │                                │   - Decrypt layer_key   │
     │                                │     using their key     │
     │                                │   - Fetch shards from   │
     │                                │     storage nodes       │
     │                                │   - Reconstruct layer   │
```

### 2.3 Shard Retrieval with Access Verification

Storage nodes enforce access control on-chain — they won't serve shards to unauthorized retrievers.

```python
# Storage node retrieval endpoint
async def retrieve_shard(request: ShardRequest) -> Shard:
    # 1. Verify requester has a valid on-chain grant
    grant = await chain.get_active_grant(
        capsule_id=request.capsule_id,
        layer_id=request.layer_id,
        grantee=request.requester_pubkey
    )

    if not grant or not grant.active:
        raise Unauthorized("No active grant for this layer")

    if grant.valid_until > 0 and grant.valid_until < now():
        raise Unauthorized("Grant expired")

    if grant.max_retrievals > 0 and grant.retrievals_used >= grant.max_retrievals:
        raise Unauthorized("Retrieval limit reached")

    # 2. Verify requester signature (they signed the shard_id with their wallet key)
    if not verify_signature(request.shard_id, request.signature, request.requester_pubkey):
        raise Unauthorized("Invalid signature")

    # 3. Fetch encrypted shard (storage node never decrypts)
    shard = await storage.get(request.shard_id)

    # 4. Include Merkle proof for integrity verification
    proof = merkle_tree.get_proof(request.shard_id)

    # 5. Increment retrieval counter on-chain (atomic)
    await chain.increment_retrievals(grant.grant_id)

    # 6. Emit retrieval event (for earnings calculation)
    await chain.emit_retrieval_event(grant.grant_id, request.shard_id)

    return ShardResponse(
        shard=shard,
        merkle_proof=proof,
        layer_root=grant.layer_root
    )
```

### 2.4 Access Revocation

Revocation is immediate — the on-chain grant is marked revoked, and all storage nodes refuse further retrievals.

```python
async def revoke_grant(owner: Pubkey, grant_id: bytes):
    # Only owner can revoke
    grant = await chain.get_grant(grant_id)
    assert grant.grantor == owner

    await chain.update_grant(grant_id, {
        "active": False,
        "revoked_at": now()
    })

    # Propagate revocation to storage nodes via GossipSub
    await gossipsub.publish("oneon/grant-revocation", {
        "grant_id": grant_id,
        "capsule_id": grant.capsule_id,
        "layer_id": grant.layer_id,
    })
    # Storage nodes subscribe to this topic and update their local cache
```

### 2.5 Key Rotation

If a capsule layer is re-encrypted (e.g. owner suspects key compromise), all active grants for that layer must have their `layer_key_enc` updated:

1. Owner generates a new layer key
2. Re-encrypts all shards with new key (client-side, can be batched)
3. Updates shard manifest on IPFS (new CID anchored on-chain)
4. For each active grant: re-encrypts new layer key with grantee's pubkey, updates grant on-chain
5. Old shard CIDs are de-pinned from storage nodes after 24h grace period

---

## 3. Quality Scoring Mechanism

### 3.1 Quality Score Model

A capsule's quality score (QS) reflects how useful and well-structured its content is as an intelligence layer. Quality drives both LLM output improvements for the owner and earnings when shared.

**Score range:** 0–100 (stored as 0–10000 on-chain for precision)

**Score composition:**
```
Capsule QS = (Depth Score     × 0.30)   # Volume and richness of content
           + (Freshness Score × 0.25)   # How recently layers were updated
           + (Coherence Score × 0.25)   # Structural quality, no bloat/noise
           + (Utility Score   × 0.15)   # How much the capsule improves LLM outputs
           + (Coverage Score  × 0.05)   # Distribution of content across layer types
```

### 3.2 Score Dimensions

**Depth Score (0–100)**
Measures the density of real information across layers:
```python
depth_score = min(100, sum(
    layer_depth_contribution(layer)
    for layer in capsule.layers
    if layer.visibility != Visibility.Private  # only shareable layers are scored
))

def layer_depth_contribution(layer):
    # Approximate content richness
    raw = layer.semantic_fact_count * 1.0     # each fact = 1 point
         + layer.episodic_event_count * 0.3   # events count less (more noise)
         + layer.procedure_count * 2.0        # procedures are high-value
         + layer.graph_edge_count * 0.5       # relationships add context

    # Diminishing returns above 50 facts per layer
    return raw / (1 + raw / 100) * 100
```

**Freshness Score (0–100)**
Stale capsules earn less. Fresh capsules reflect active minds.
```python
def freshness_score(layer: LayerHeader) -> float:
    days_since_update = (now() - layer.freshness_ts) / 86400
    # Half-life: 30 days → score drops to 50
    return 100 * exp(-0.693 * days_since_update / 30)

# Capsule freshness = weighted average across layers
capsule_freshness = weighted_avg(
    [freshness_score(l) for l in capsule.layers],
    weights=[l.quality_contribution for l in capsule.layers]
)
```

**Coherence Score (0–100)**
Assessed by validators. Measures structural quality:
- No duplicate facts (deduplication ratio)
- Semantic consistency (no contradictions)
- Appropriate granularity (not too coarse, not noisy)
- Memory categorization accuracy (right content in right layer)

```python
# Validator assigns coherence dimensions:
coherence = {
    "dedup_ratio":      1 - (duplicate_count / total_facts),  # 1.0 = no dupes
    "consistency":      semantic_consistency_score,             # LLM judge: 0-1
    "granularity":      granularity_fitness_score,             # LLM judge: 0-1
    "categorization":   category_accuracy_score,               # LLM judge: 0-1
}
coherence_score = (
    coherence["dedup_ratio"] * 0.35
  + coherence["consistency"] * 0.30
  + coherence["granularity"] * 0.20
  + coherence["categorization"] * 0.15
) * 100
```

**Utility Score (0–100)**
The only score measured empirically. When a grantee uses a layer to enhance their LLM interactions, they can rate the utility:
```python
# After each access, grantee rates utility (opt-in, defaults to neutral 50)
# Running EMA (same pattern as Otto's semantic memory utility scoring)
utility_score = prev_utility + 0.1 * (grantee_rating - prev_utility)
```

For the capsule owner's own usage: utility is measured by comparing LLM response quality with vs without the capsule injected (A/B sampling, 5% of interactions).

**Coverage Score (0–100)**
Rewards balanced capsules that use multiple content types:
```python
content_types_present = len(set(l.content_type for l in capsule.layers))
coverage_score = min(100, content_types_present * 25)  # 4 types = 100
```

### 3.3 Validator Assessment Flow

Quality assessment happens in two modes:

**Automated Assessment (continuous)**
Runs on every capsule update. Calculates Depth, Freshness, and Coverage scores locally using metadata — no access to content needed.

**Validator Assessment (sampling)**
Every 30 days, or when a capsule's QS has been stale for 7+ days, a validator node performs deep assessment:

1. Validator receives a **read grant** from the owner (auto-created for assessment, non-transferable)
2. Validator decrypts the shareable layers (3-7 only — personal layers 0-2 are never assessed)
3. Validator runs coherence assessment:
   - Duplicate detection (embedding similarity > 0.92 = dupe)
   - Consistency check (LLM judge on random 5% sample)
   - Granularity and categorization review
4. Validator submits scores using commit-reveal scheme (prevents collusion)
5. Consensus score = weighted median of 3+ validator assessments
6. QS updated on-chain with new coherence component

```python
# Validator consensus (same Yuma variant as compute node validation)
consensus_coherence = weighted_median(
    [v.coherence_score for v in validators],
    weights=[v.stake for v in validators]
)

# Validators who deviate >15 from consensus are flagged
validator_accuracy = 1 - abs(v.score - consensus_coherence) / 100
```

### 3.4 Quality Score Effects

| QS Range | Effect on Owner | Effect on Monetization |
|---|---|---|
| 0–30 (Poor) | Baseline LLM outputs | Not eligible for monetization |
| 31–50 (Basic) | 10% better responses | Can share, base rate |
| 51–70 (Good) | 25% better responses | 1.5× earnings multiplier |
| 71–85 (High) | 50% better responses | 2.5× earnings multiplier |
| 86–100 (Elite) | 75%+ better responses | 4× earnings multiplier, featured in discovery |

"Better responses" = empirically measured improvement in relevance and personalization when capsule context is injected vs not injected (A/B sampling).

---

## 4. $KOIN Earnings Formula

### 4.1 Earnings Model Overview

Capsule owners earn $KOIN when:
1. **Access grants are purchased** — upfront or subscription payment
2. **Retrievals are served** — per-retrieval micro-earnings
3. **Quality bonuses** — periodic rewards to high-QS capsules from the quality pool

```
Owner earnings = Grant Revenue + Retrieval Revenue + Quality Pool Share
```

### 4.2 Grant Revenue

Direct payment from grantee to owner when a grant is created:

```
Grant payment = price_per_period × (QS_multiplier)

where QS_multiplier:
  QS 0-30:   1.0× (base)
  QS 31-50:  1.0× (base, no penalty)
  QS 51-70:  1.2× (markets price in quality)
  QS 71-85:  1.5×
  QS 86-100: 2.0×

# Subscription renewals: grantee pays per interval while grant is active
# One-time grants: single payment
# Perpetual grants: negotiated flat fee
```

Market forces set the `price_per_period`. The QS_multiplier is advisory — owners can set any base price, the multiplier is applied on top as a signal to buyers.

### 4.3 Retrieval Revenue

Each shard retrieval earns a micro-payment:

```python
# Per-retrieval earnings (paid by grantee on each access)
retrieval_fee = base_retrieval_rate × layer_complexity_factor × QS_factor

base_retrieval_rate = 0.001 $KOIN  # Base rate, governance-adjustable

layer_complexity_factor = {
    ContentType.Semantic:   1.0,
    ContentType.Procedural: 1.5,   # Procedures are more valuable
    ContentType.Graph:      1.3,   # Graph relationships add context
    ContentType.Episodic:   0.8,   # Raw events less curated
    ContentType.Mixed:      1.2,
}[layer.content_type]

QS_factor = 0.5 + (capsule.quality_score / 100)  # range 0.5x-1.5x
# QS 0 → 0.5×, QS 50 → 1.0×, QS 100 → 1.5×
```

### 4.4 Quality Pool Share (Protocol Incentive)

The protocol reserves a **Quality Pool** from the daily $KOIN emission to reward top-quality capsules, independent of direct monetization activity. This ensures high-quality capsules are rewarded even when the market is thin.

```
Daily Quality Pool = 5% of total daily $KOIN emission

Each capsule's quality pool share:
  pool_share = QS² / Σ(QS²)  # Quadratic to heavily favor top-quality capsules

# Example: 1000 capsules in network
# Capsule A: QS=90 → 90²=8100 contribution
# Capsule B: QS=50 → 50²=2500 contribution
# Capsule C: QS=20 → 20²=400  contribution
# Σ = 11000 (simplified for 3 capsules)
# A earns 8100/11000 = 73.6% of pool
# B earns 2500/11000 = 22.7%
# C earns 400/11000  = 3.6%
```

Eligibility for quality pool: QS ≥ 50, at least 1 active grant, not revoked.

### 4.5 Full Earnings Formula

```python
def capsule_daily_earnings(capsule: MemoryCapsule, day_data: DayData) -> int:
    # 1. Grant revenue (direct)
    grant_revenue = sum(
        grant.price_per_period * qs_multiplier(capsule.quality_score)
        for grant in day_data.new_grants
        if grant.capsule_id == capsule.capsule_id
    )

    # 2. Retrieval revenue
    retrieval_revenue = sum(
        base_retrieval_rate
        * layer_complexity_factor(layer)
        * qs_factor(capsule.quality_score)
        for retrieval in day_data.retrievals
        if retrieval.capsule_id == capsule.capsule_id
        for layer in [get_layer(retrieval.layer_id)]
    )

    # 3. Quality pool share
    if capsule.quality_score >= 50 and capsule.has_active_grant:
        qs_sq = capsule.quality_score ** 2
        total_qs_sq = sum(c.quality_score ** 2 for c in eligible_capsules())
        quality_share = day_data.quality_pool * (qs_sq / total_qs_sq)
    else:
        quality_share = 0

    return grant_revenue + retrieval_revenue + quality_share
```

### 4.6 Anti-Gaming Mechanisms

**Rate limiting:** Max retrieval revenue per capsule per day = 10× the base grant revenue for that capsule (prevents artificial inflation via self-retrieval).

**Stake requirement for monetization:** Owners must stake 50 $KOIN to activate monetization for a capsule (prevents throwaway capsules flooding the quality pool).

**Decay on inactivity:** Capsules with QS ≥ 50 but no grants or retrievals for 30+ days have their quality pool eligibility reduced by 10%/month until they reach 0% (must become active to restore).

---

## 5. Integration with Otto Distributed Storage Nodes

### 5.1 Storage Node Role for Memory Capsules

Storage Nodes (defined in `distributed_otto_architecture.md` § 2.4) are the physical infrastructure of the memory economy. Capsule shards are distributed across them.

**Key properties:**
- Storage nodes hold **only ciphertext** — encryption is always client-side
- Each layer's shards are replicated across **3+ geographically distributed** nodes
- Storage nodes earn $KOIN per GB-day stored + per retrieval served (premium rate for capsule hosting)
- Access permission enforcement is **on-chain** — storage nodes verify the grant before serving

### 5.2 Shard Write Flow (Capsule Update)

```
Owner Client          Storage Nodes              ONEON Chain
     │                      │                         │
     │  1. Owner updates capsule (new memory added)   │
     │                      │                         │
     │  2. Client-side processing:
     │     a. Serialize new layer content
     │     b. Encrypt with layer key (XChaCha20-Poly1305)
     │     c. Split into shards (Reed-Solomon erasure coding)
     │     d. Build Merkle tree, get layer_root hash
     │     e. Select 3+ storage nodes via DHT (prefer geographic spread)
     │                      │                         │
     │──── store_shard(1) ──►│ (node 1, Asia)          │
     │──── store_shard(1) ──►│ (node 2, Europe)        │
     │──── store_shard(1) ──►│ (node 3, Americas)      │
     │◄─── CID + receipt ────│                         │
     │                      │                         │
     │  3. Update shard manifest (local, encrypted)    │
     │  4. Push manifest to IPFS (new CID)             │
     │──── update_capsule_record({new CID, hash}) ───►│
     │◄─── tx confirmed ───────────────────────────────│
```

### 5.3 Reed-Solomon Erasure Coding

Shards use erasure coding for fault tolerance. A layer's content can be reconstructed from any k-of-n shards:

```python
# Reed-Solomon parameters
DATA_SHARDS = 4       # k — minimum shards needed to reconstruct
PARITY_SHARDS = 2     # extra shards for redundancy
TOTAL_SHARDS = 6      # n — total shards created per layer

# This means the layer survives loss of any 2 storage nodes
# Replication target is still 3 geographic nodes, but each node
# holds a different subset of the 6 shards

from pyfinite import ffield, genericmatrix
from reed_solomon import ReedSolomon

rs = ReedSolomon(DATA_SHARDS, PARITY_SHARDS)

def shard_layer(layer_plaintext: bytes) -> list[Shard]:
    chunks = split_into_chunks(layer_plaintext, DATA_SHARDS)
    encoded = rs.encode(chunks)  # returns DATA_SHARDS + PARITY_SHARDS chunks

    nonce = random_bytes(24)
    layer_key = get_layer_key(layer_id)

    shards = []
    for i, chunk in enumerate(encoded):
        ciphertext = xchacha20_poly1305_encrypt(
            key=layer_key,
            nonce=derive_shard_nonce(nonce, i),  # unique per shard
            plaintext=chunk,
            aad=f"oneon/capsule/v1/{capsule_id}/{layer_id}/{i}".encode()
        )
        shards.append(CapsuleShard(
            shard_index=i,
            total_shards=TOTAL_SHARDS,
            nonce=nonce,
            ciphertext=ciphertext,
            content_hash=sha256(chunk),
            ...
        ))
    return shards

def reconstruct_layer(shards: list[Shard], layer_key: bytes) -> bytes:
    # Need any DATA_SHARDS of the total
    assert len(shards) >= DATA_SHARDS
    chunks = []
    for shard in shards[:DATA_SHARDS]:
        plaintext_chunk = xchacha20_poly1305_decrypt(
            key=layer_key,
            nonce=derive_shard_nonce(shard.nonce, shard.shard_index),
            ciphertext=shard.ciphertext,
            aad=f"oneon/capsule/v1/{capsule_id}/{layer_id}/{shard.shard_index}".encode()
        )
        chunks.append(plaintext_chunk)
    return rs.decode(chunks)
```

### 5.4 Storage Node Selection

Owner clients select storage nodes via the DHT using a quality + diversity score:

```python
def select_storage_nodes(layer_size_bytes: int, geo_preferences: list[str] = None) -> list[PeerID]:
    # 1. Query DHT for available storage nodes
    candidates = dht.query("otto/capability/storage")

    # 2. Filter: sufficient capacity
    candidates = [c for c in candidates if c.free_storage_bytes > layer_size_bytes * 2]

    # 3. Filter: recent heartbeat (online in last 60s)
    candidates = [c for c in candidates if c.last_seen_s < 60]

    # 4. Filter: geographic diversity (prefer different regions)
    if geo_preferences:
        preferred = [c for c in candidates if c.region in geo_preferences]
        candidates = preferred if len(preferred) >= 3 else candidates

    # 5. Score by composite quality (same QS model as compute nodes)
    candidates.sort(key=lambda c: storage_quality_score(c), reverse=True)

    # 6. Select 3+ from top candidates, ensuring geographic spread
    selected = []
    seen_regions = set()
    for c in candidates:
        if c.region not in seen_regions or len(selected) < 3:
            selected.append(c)
            seen_regions.add(c.region)
        if len(selected) >= max(3, TOTAL_SHARDS):
            break

    return selected
```

### 5.5 Replication Health Monitoring

Each capsule owner's client periodically verifies shard replication health:

```python
async def check_capsule_health(capsule_id: bytes):
    manifest = await fetch_and_decrypt_manifest(capsule_id)

    for layer in manifest.layers.values():
        for shard in layer.shards:
            alive_nodes = 0
            for node_id in shard.storage_nodes:
                try:
                    # Ping storage node, verify they still hold the shard
                    proof = await storage_node.verify_shard(node_id, shard.shard_id)
                    if verify_merkle_proof(proof, shard.layer_root):
                        alive_nodes += 1
                except (Timeout, NodeOffline):
                    pass

            if alive_nodes < DATA_SHARDS:
                # Emergency: below minimum for reconstruction
                await trigger_emergency_replication(shard, needed=TOTAL_SHARDS - alive_nodes)
            elif alive_nodes < TOTAL_SHARDS:
                # Sub-optimal: queue background re-replication
                await queue_replication(shard, needed=TOTAL_SHARDS - alive_nodes)
```

Health checks run hourly. Results feed into the owner's capsule dashboard.

### 5.6 Storage Node Earnings for Capsule Hosting

Storage nodes earn premium rates for capsule hosting because they must enforce access permissions:

```python
# Storage node daily earnings (capsule segment)
capsule_storage_earnings = (
    stored_capsule_GB * daily_rate_per_GB_capsule      # GB-day storage
  + capsule_retrievals_served * retrieval_fee           # per-retrieval
  + permission_verifications * verification_fee         # on-chain verification overhead
)

# Rates (governance-set, approximate initial values)
daily_rate_per_GB_capsule = 0.05 $KOIN  # vs 0.03 $KOIN for non-capsule storage
retrieval_fee_capsule = 0.0005 $KOIN    # vs 0.0003 $KOIN for public content
verification_fee = 0.00001 $KOIN        # per on-chain access check
```

Storage nodes that store capsules for highly-active (many-retrieval) accounts earn significantly more than average storage nodes — aligning incentives toward quality capsule hosting.

---

## 6. LLM Output Quality Enhancement

### 6.1 How Capsule Depth Improves Outputs

When a ONEON user interacts with an Otto-powered interface, their Memory Capsule layers are injected into the LLM context via the S-MMU. Deeper, higher-quality capsules produce more personalized, accurate outputs:

```
Request: "What should I work on today?"

Without capsule injection:
  → Generic productivity advice (no context)

With QS 40 capsule (shallow):
  → "Based on your goals in tech, consider..."
  → Knows role but not priorities or context

With QS 80 capsule (deep):
  → "You mentioned yesterday you're stuck on the WebAssist payment flow.
     Given your pattern of working best on focused problems in the morning,
     and your context that Stripe setup needs Mev's credentials first,
     I'd suggest: (1) Document what you need from Mev so it's ready when
     they're available. (2) Use the morning block for the next OMS feature..."
```

### 6.2 Context Injection Protocol

S-MMU injects capsule layers into context using the same priority-tiered approach as Otto's internal system:

```python
# Context injection order (memory pressure: highest priority first)
INJECTION_ORDER = [
    (0, "active_context"),     # Layer 0: always injected (owner's session state)
    (2, "semantic_memory"),    # Layer 2: relevant facts (vector search)
    (3, "skills"),             # Layer 3: relevant procedures
    (4, "professional"),       # Layer 4: relevant background
    (1, "episodic"),           # Layer 1: relevant recent events
    (5, "social"),             # Layer 5: relevant relationships
]

def inject_capsule_context(query: str, capsule: DecryptedCapsule, budget_tokens: int) -> str:
    context_parts = []
    remaining_budget = budget_tokens

    for layer_id, layer_name in INJECTION_ORDER:
        layer = capsule.layers.get(layer_id)
        if not layer or not layer.content:
            continue

        # Retrieve relevant content from layer using vector similarity
        relevant = layer.semantic_search(query, top_k=5)
        layer_context = format_layer_context(layer_name, relevant)

        if token_count(layer_context) <= remaining_budget:
            context_parts.append(layer_context)
            remaining_budget -= token_count(layer_context)

    return "\n\n".join(context_parts)
```

### 6.3 Quality → Output Quality Causal Chain

```
High QS capsule → more facts, less noise, fresh context
                → S-MMU retrieves more relevant slices
                → LLM receives higher-quality context
                → LLM produces more personalized, accurate responses
                → User rates response higher
                → Utility score increases
                → QS increases
                → Earnings increase
                [Virtuous cycle]
```

---

## 7. Privacy Boundaries

| Data Type | Who Can See | Who Can Never See |
|---|---|---|
| Capsule existence | Anyone (public on-chain) | Layer content |
| Layer headers (labels, types) | Anyone | Layer content |
| Layer content (QS 0-2) | Owner only | Anyone else, ever |
| Layer content (QS 3-7) | Owner + active grantees | Storage nodes (hold ciphertext only) |
| Shard ciphertext | Storage nodes | Grantees without grant |
| Owner's wallet address | Anyone (public) | Real identity (DID ≠ real name) |
| Quality score | Anyone (public) | How it was earned |
| Earnings | Owner + governance | Amount per grantee |

**Zero-knowledge path (Phase 3):** Capsule quality can be proven using ZK proofs without revealing content. A validator can attest "this capsule has QS ≥ 70" without seeing what's in it. ZK-SNARK proof generation from capsule Merkle tree. Enables anonymous high-QS certification.

---

## 8. Implementation Phases

### Phase 1 (ONEON Launch Prerequisites)
- On-chain account schema (Solana Anchor)
- Basic shard schema + client-side encryption
- Grant creation and revocation
- Manual quality scoring (owner self-assessment, no validators yet)
- Storage node capsule hosting (single replica first)
- Basic earnings: grants only (no retrieval revenue, no quality pool)

### Phase 2 (ONEON Phase 3 — Memory Capsules Launch)
- Full shard storage + Reed-Solomon erasure coding
- 3-node replication with geographic diversity
- Validator quality assessment (3-of-5 consensus)
- Full earnings formula (grants + retrieval + quality pool)
- S-MMU capsule injection in Otto ONEON client
- Health monitoring dashboard
- Access grant marketplace (discovery + subscription management)

### Phase 3 (Decentralized Intelligence Layer)
- ZK quality proofs (anonymous capsule quality certification)
- TEE-based S-MMU (private context processing without owner device)
- Cross-chain capsule portability ($KOIN on any chain)
- Federated capsule quality training (validators improve assessment models from feedback)
- Capsule composites (owner can create derived capsules combining multiple layers with different access policies)

---

## Appendix: Key Constants (Governance-Adjustable)

| Constant | Initial Value | Governance Path |
|---|---|---|
| Min QS for monetization | 30 | DAO vote |
| Min stake for monetization | 50 $KOIN | DAO vote |
| Quality pool share of emission | 5% | DAO vote |
| Base retrieval rate | 0.001 $KOIN | DAO vote |
| Freshness half-life | 30 days | DAO vote |
| Reed-Solomon k/n | 4/6 | Core protocol (hard fork) |
| Min replication target | 3 nodes | Core protocol |
| Max validator deviation | 15 points | DAO vote |
| Quality pool quadratic exponent | 2 | DAO vote |
