# SOS Systems: Integrity Preservation Layer
## Architecture Specification — Blueprint v0.1

*Authored by Otto | 2026-03-17 | Status: Design Phase*

---

## Executive Summary

SOS Systems operates in adversarial environments where the four classic attack vectors are: **seizure** (government takes infrastructure), **shutdown** (network access cut), **corruption** (records altered to deny aid), and **capture** (single actor gains undue control).

The Integrity Preservation Layer (IPL) is the technical implementation of the promise: no ISP to seize, no plug to pull, no record to falsify, no board to bribe.

This document specifies four interlocking subsystems:

1. **Sovereign Identity Layer** — portable, self-sovereign identity that works offline
2. **Tamper-Proof Record Layer** — content-addressed, cryptographically verifiable records
3. **Auditable Aid Distribution Layer** — transparent, automated resource allocation with on-chain proof
4. **Offline-Capable Mesh Network Layer** — connectivity that survives infrastructure collapse

---

## 1. Sovereign Identity Layer

### 1.1 Problem

In crisis zones, people lose documents. Governments issue or revoke IDs politically. Central databases get captured. Traditional KYC fails exactly when it matters most — when the person needs it most.

### 1.2 Architecture

```
┌─────────────────────────────────────────────────────────┐
│                  IDENTITY LAYER                         │
│                                                         │
│  ┌────────────────┐      ┌───────────────────────────┐  │
│  │  Device Wallet │      │   Decentralized ID (DID)  │  │
│  │  (local keys)  │─────▶│   did:peer / did:key      │  │
│  └────────────────┘      └───────────┬───────────────┘  │
│                                      │                  │
│  ┌───────────────────────────────────▼──────────────┐   │
│  │         Verifiable Credential Store               │   │
│  │  - Aid eligibility VCs (issued by field workers)  │   │
│  │  - Skill credentials (issued by educators)        │   │
│  │  - Contribution records (issued by DPC system)    │   │
│  └───────────────────────────────────────────────────┘   │
│                                                         │
│  ┌────────────────────────────────────────────────────┐  │
│  │         Recovery Layer                             │  │
│  │  - Social recovery: 3-of-5 trusted contacts       │  │
│  │  - BIP-39 seed words on physical medium            │  │
│  │  - Biometric unlock (local only, no cloud)         │  │
│  └────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

### 1.3 Tech Stack

| Component | Choice | Rationale |
|-----------|--------|-----------|
| DID Method | `did:key` (offline) + `did:ethr` (on-chain anchor) | `did:key` works with zero connectivity; `did:ethr` anchors identity to Ethereum/L2 when connectivity returns |
| Key type | Ed25519 (signing) + X25519 (encryption) | Battle-tested, compact, fast on mobile |
| VC Format | W3C Verifiable Credentials 2.0 (JSON-LD + BBS+ signatures) | BBS+ enables selective disclosure — show "I am eligible for aid" without revealing name |
| Storage | Local: encrypted SQLite; Remote: IPFS (content-addressed) | IPFS CID = the record IS its own hash, unfalsifiable |
| Recovery | `Shamir Secret Sharing` (3-of-5, encoded in QR codes) | Printable, works without electronics |
| SDK | `@veramo/core` (TypeScript) | Most complete DID/VC toolkit, runs in React Native |

### 1.4 Identity Lifecycle

```
FIELD ENROLLMENT (offline capable):

  1. Field worker runs SOS app on Android device (no internet required)
  2. Generates did:key for beneficiary from device entropy
  3. Issues Verifiable Credential: "Aid eligible — Category: Displacement — Date: 2026-03-17"
  4. VC stored on beneficiary's device + paper backup (QR code printout)
  5. Field worker's device queues VC hash for on-chain anchoring

SYNC (when connectivity returns):

  6. Batch of VC hashes posted to L2 chain (Polygon zkEVM or Base)
  7. IPFS upload of encrypted full records
  8. DID Document updated with new capabilities

VERIFICATION (at aid distribution point):

  9. Beneficiary presents QR code or device NFC tap
  10. Verifier checks VC signature (cryptographic, no internet needed)
  11. Verifier's device checks nullifier: "Has this VC been used today?" (offline Bloom filter, syncs when connected)
  12. Aid dispensed, usage logged locally, synced to chain later
```

### 1.5 Privacy Model

- **Selective disclosure**: BBS+ signatures allow proving "Category = Displacement" without revealing name, age, or location
- **Zero-knowledge proofs**: ZK proof of eligibility can be generated without revealing underlying data to verifier
- **Data minimization**: Field workers record minimum viable data; extra details optional
- **Right to removal**: Beneficiary can revoke credentials from chain; VC becomes unverifiable (off-chain data remains on their device only)

---

## 2. Tamper-Proof Record Layer

### 2.1 Problem

Aid records get altered. Field reports get suppressed. A government or NGO operator can modify a database. Even honest mistakes compound. The integrity of what happened needs to be provable, permanently, without trusting any single operator.

### 2.2 Architecture

```
┌──────────────────────────────────────────────────────────────┐
│               TAMPER-PROOF RECORD LAYER                      │
│                                                              │
│  DATA CREATION                                               │
│  ┌──────────────┐   hash(content)   ┌──────────────────────┐ │
│  │  Field Input  │──────────────────▶│  Content-Addressed   │ │
│  │  (app form)   │                  │  Object (CAO)        │ │
│  └──────────────┘                  │  CID = sha256(data)  │ │
│                                    └──────────┬───────────┘ │
│                                               │             │
│  DUAL STORAGE                                 │             │
│  ┌────────────────────────────────────────────▼───────────┐  │
│  │  IPFS / Filecoin                                       │  │
│  │  - Content stored at CID (unfalsifiable by design)     │  │
│  │  - Pinned across SOS-operated + community nodes        │  │
│  │  - Encrypted with AES-256-GCM, key in smart contract   │  │
│  └────────────────────────────────────────────────────────┘  │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  On-Chain Anchor (Polygon zkEVM / Base L2)             │  │
│  │  - CID + timestamp + signer DID stored in contract     │  │
│  │  - Append-only: no record can be modified/deleted      │  │
│  │  - Gas: batched 500 records per tx (~$0.01 total)      │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                              │
│  MERKLE AUDIT TREE                                           │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  Daily Merkle roots published on-chain                 │  │
│  │  - Any record provably in or out of the set            │  │
│  │  - Sparse Merkle Trees for efficient non-membership    │  │
│  │    proof ("this person did NOT receive duplicate aid") │  │
│  └────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
```

### 2.3 Tech Stack

| Component | Choice | Rationale |
|-----------|--------|-----------|
| Content addressing | IPFS (go-ipfs, Kubo) | CID is the integrity check by design |
| Persistent storage | Filecoin (via web3.storage) | Economic incentives to keep data alive |
| On-chain anchor | Polygon zkEVM (or Base) | ~$0.001/tx, EVM-compatible, L2 security |
| Smart contract | Solidity `RecordAnchor.sol` | Append-only mapping: `(CID → signer → timestamp)` |
| Merkle tree | `@openzeppelin/merkle-tree` + custom Sparse MT | Standard, audited |
| Local DB | OrbitDB over IPFS | P2P database, syncs across nodes, works offline |
| Conflict resolution | CRDTs (Conflict-free Replicated Data Types) | Offline edits merge without loss when reconnected |

### 2.4 Record Schema

```json
{
  "schema_version": "1.0",
  "record_type": "aid_event | incident | enrollment | outcome",
  "id": "bafkreigh...",
  "timestamp_utc": "2026-03-17T08:42:00Z",
  "location": {
    "region": "Khartoum North",
    "geohash": "s4b8p",
    "precision_km": 5
  },
  "subject_did": "did:key:z6Mk...",
  "operator_did": "did:ethr:0x...",
  "payload_hash": "sha256:abc123...",
  "payload_cid": "bafkrei...",
  "signature": "z5jG9...",
  "previous_record_cid": "bafkrei...",
  "chain_anchor": {
    "tx_hash": "0xabc...",
    "block": 14523001,
    "chain_id": 137
  }
}
```

**Key properties:**
- `previous_record_cid` creates a hash-linked chain per subject (tamper reveals broken chain)
- `payload_hash` verifies content without downloading full payload
- `location` uses geohash at ~5km precision (balances utility vs. safety for sensitive populations)

### 2.5 Append-Only Guarantees

```solidity
// RecordAnchor.sol (simplified)
contract RecordAnchor {
    mapping(bytes32 => Record) public records;
    bytes32[] public recordIndex;

    event RecordAnchored(bytes32 indexed cid, address indexed signer, uint256 timestamp);

    function anchor(bytes32 cid, bytes calldata signerDID) external {
        require(records[cid].timestamp == 0, "Record already exists");  // NO UPDATES
        records[cid] = Record({
            cid: cid,
            signer: msg.sender,
            signerDID: signerDID,
            timestamp: block.timestamp
        });
        recordIndex.push(cid);
        emit RecordAnchored(cid, msg.sender, block.timestamp);
    }

    function batchAnchor(bytes32[] calldata cids, bytes[] calldata signerDIDs) external {
        for (uint i = 0; i < cids.length; i++) {
            anchor(cids[i], signerDIDs[i]);
        }
    }
}
```

---

## 3. Auditable Aid Distribution Layer

### 3.1 Problem

Aid distribution is one of the most corruption-prone systems on Earth. UN studies estimate 30-40% of aid in high-conflict zones is diverted. Centralized databases can be manipulated by operators. Double-dipping (same person receiving aid twice) happens at scale. Reporting to donors is opaque.

### 3.2 Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                  AID DISTRIBUTION LAYER                         │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  ELIGIBILITY ENGINE                                       │  │
│  │  - Smart contract holds eligibility rules (upgradeable)   │  │
│  │  - ZK proof of eligibility: prove VC is valid without     │  │
│  │    revealing identity to distributor                      │  │
│  │  - Rate limits: max 1 food kit per household per 7 days   │  │
│  └──────────────────────────┬────────────────────────────────┘  │
│                             │                                   │
│  ┌──────────────────────────▼────────────────────────────────┐  │
│  │  NULLIFIER REGISTRY (double-spend prevention)             │  │
│  │  - Sparse Merkle Tree of used nullifiers                  │  │
│  │  - Nullifier = hash(VC_id + distribution_event_id)       │  │
│  │  - Cannot be linked back to identity (one-way hash)       │  │
│  │  - Offline: device holds local Bloom filter               │  │
│  │  - Online: anchored to chain, globally verifiable         │  │
│  └──────────────────────────┬────────────────────────────────┘  │
│                             │                                   │
│  ┌──────────────────────────▼────────────────────────────────┐  │
│  │  DISTRIBUTION LEDGER                                      │  │
│  │  - Every distribution event: what, where, when, to whom  │  │
│  │  - "To whom" = nullifier only (not name/DID)              │  │
│  │  - Immutable on-chain, readable by anyone                 │  │
│  │  - Real-time donor dashboard: "Your donation fed X        │  │
│  │    families in Khartoum this week" (zero-knowledge)       │  │
│  └──────────────────────────┬────────────────────────────────┘  │
│                             │                                   │
│  ┌──────────────────────────▼────────────────────────────────┐  │
│  │  DPC INTEGRATION                                          │  │
│  │  - Field workers earn DPC contribution score for          │  │
│  │    verified distributions                                 │  │
│  │  - Distribution outcomes feed back to eligibility rules   │  │
│  │    (DAO proposes + votes on rule changes)                 │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### 3.3 Distribution Event Flow

```
PREPARATION (aid organization):
  1. DAO approves Distribution Event: "1000 food kits, Khartoum North, March 18-22"
  2. Smart contract locks allocation: event_id, resource_type, quantity, region, window
  3. Eligibility criteria set: any valid "Displacement" VC in target region

DISTRIBUTION (field, offline capable):
  4. Beneficiary presents device/QR
  5. Field worker app verifies VC signature (cryptographic, no internet)
  6. App generates nullifier locally: hash(VC_id + event_id)
  7. App checks local Bloom filter: "Has this nullifier been used?"
  8. If clear: aid dispensed, event logged locally
  9. Nullifier added to local Bloom filter (prevents same-device double-dip)

RECONCILIATION (on reconnection):
  10. Device uploads batch: nullifiers + distribution records (encrypted)
  11. Smart contract checks global nullifier registry
  12. Conflicts resolved by timestamp: first on-chain wins
  13. Merkle root updated, donors notified via event

AUDIT (ongoing, public):
  14. Anyone can query: total distributed vs. allocated
  15. Anyone can verify a specific distribution happened (with CID)
  16. Nobody can link nullifier back to individual (one-way hash)
  17. Weekly summary auto-published to IPFS + social (Otto-generated)
```

### 3.4 Tech Stack

| Component | Choice | Rationale |
|-----------|--------|-----------|
| Smart contracts | Solidity on Polygon zkEVM | Low cost, ZK-native for proof verification |
| ZK proofs | Circom + snarkjs (Groth16) | Mature, small proof size, fast mobile verify |
| Nullifier store | Sparse Merkle Tree (on-chain root + off-chain tree) | Efficient non-membership proofs |
| Offline filter | Bloom filter (serialized, device-local) | <1MB for 100k nullifiers, zero false negatives |
| Token | None required — record-keeping only | Avoid unnecessary tokenization of aid flows |
| Dashboard | The Graph Protocol indexer | Query chain events, build real-time donor UI |
| Audit reports | Otto AI generates weekly summaries | Automated, consistent, human-readable |

### 3.5 Anti-Corruption Properties

| Attack | Defense |
|--------|---------|
| Operator inflates distribution numbers | Records require valid VC signatures; can't fake beneficiaries |
| Double-dipping (same person twice) | Nullifier registry prevents reuse of same VC per event |
| Operator pocket allocations | Smart contract locks quantity before distribution begins |
| Corrupt DAO vote approves fake event | DPC-weighted governance: requires sustained contribution to influence |
| Retroactive record falsification | Append-only on-chain anchors + IPFS CIDs (mutation = different CID) |
| Selective reporting to donors | Public ledger; donors can query independently |

---

## 4. Offline-Capable Mesh Network Layer

### 4.1 Problem

In crisis zones, internet infrastructure is the first target. Cellular towers need power and backhaul. Satellite is expensive and blockable. The mesh layer must function when nothing else does — providing at minimum: identity verification, aid distribution, emergency beacon, and delayed message delivery.

### 4.2 Network Architecture

```
TIER 0: LOCAL MESH (0-5km, no infrastructure)
┌─────────────────────────────────────────────────────────────┐
│  Device ←──── WiFi Direct / BLE ────→ Device               │
│  Device ←──── LoRa (915MHz/868MHz) ───→ LoRa Node          │
│                                                             │
│  Use cases: identity verification, aid dispensing,         │
│  direct P2P messaging, emergency beacons                   │
│  Latency: <1 second | Range: 1-5km LoRa, 100m BLE         │
└─────────────────────────────────────────────────────────────┘
              │
              │ (when available)
              ▼
TIER 1: COMMUNITY NODES (5-50km, community infrastructure)
┌─────────────────────────────────────────────────────────────┐
│  Raspberry Pi 4 + LoRa hat + Solar + Battery                │
│  Runs: IPFS node, OrbitDB, SOS relay daemon                 │
│  Connectivity: LoRa mesh upward, WiFi/BLE downward          │
│                                                             │
│  Stores: local copy of aid records, identity cache,        │
│  message queue, Bloom filter for nullifiers                 │
│  Cost: ~$150/node | 5W power draw                          │
└─────────────────────────────────────────────────────────────┘
              │
              │ (when available)
              ▼
TIER 2: REGIONAL BACKBONE (satellite / long-haul)
┌─────────────────────────────────────────────────────────────┐
│  Starlink / Iridium / Outernet terminal                     │
│  OR long-range LoRa bridge to adjacent region              │
│  Syncs: pending records to IPFS, chain anchors, updates    │
│                                                             │
│  Cost: ~$300 hardware + $50/mo satellite (shared among     │
│  50+ community nodes it serves)                            │
└─────────────────────────────────────────────────────────────┘
              │
              │ (global)
              ▼
TIER 3: CHAIN / IPFS (global, eventually consistent)
┌─────────────────────────────────────────────────────────────┐
│  Polygon zkEVM / Base L2                                    │
│  IPFS + Filecoin                                            │
│  SOS Systems global node cluster                           │
└─────────────────────────────────────────────────────────────┘
```

### 4.3 Protocol Stack

```
Application layer:    SOS Protocol (custom, JSON over libp2p)
├── Message routing:  libp2p (gossipsub for broadcast, noise for encryption)
├── Storage:          IPFS / OrbitDB (CRDTs for conflict-free sync)
├── Identity:         DIDs + Verifiable Credentials
├── Transport (IP):   TCP / WebRTC / WiFi Direct
├── Transport (RF):   LoRa (Meshtastic protocol, ISM band 915/868MHz)
└── Physical:         BLE 5.0 (ultra-short range, device-to-device)
```

### 4.4 Tech Stack

| Component | Choice | Rationale |
|-----------|--------|-----------|
| LoRa hardware | Meshtastic devices (TTGO T-Beam, RAK4631) | Open firmware, active community, ~$30-40/device |
| Node hardware | Raspberry Pi 4 + RAK2287 LoRa hat + solar | Proven, repairable, sourceable in-region |
| P2P networking | libp2p (go-libp2p or rust-libp2p) | Foundation of IPFS, battle-tested |
| Offline DB | OrbitDB + IPFS | P2P, offline-first, CRDT conflict resolution |
| Message store-and-forward | Custom delay-tolerant networking (DTN) layer | Messages persist until delivery confirmed |
| Encryption | Noise Protocol Framework (via libp2p) | End-to-end, no certificate authorities needed |
| Mobile app | React Native (iOS + Android) | Single codebase, works offline, BLE + WiFi Direct |
| Node OS | Raspberry Pi OS Lite + Docker | Minimal, maintainable |

### 4.5 Delay-Tolerant Message Delivery

```
SCENARIO: Aid worker records 50 distributions in a village with zero connectivity.

1. All 50 records stored locally: encrypted SQLite + IPFS (local node)
2. Nullifiers added to local Bloom filter
3. "Pending sync" counter visible in app UI

SCENARIO: Worker walks near another node with satellite:

4. Meshtastic LoRa detects node
5. Protocol handshake: "I have 50 records newer than your last sync"
6. Records transferred (P2P, encrypted) to intermediate node
7. Intermediate node queues for satellite upload
8. When satellite connects: records upload to IPFS, hashes anchor to chain
9. Original worker's app notified via LoRa: "Records confirmed"
10. Bloom filter delta synced back (now knows global nullifier state)

LATENCY: Could be hours or days. That's acceptable — the records are integrity-preserved
the moment they're signed and stored locally.
```

### 4.6 Network Resilience Properties

| Threat | Defense |
|--------|---------|
| Internet cut entirely | Tier 0 + Tier 1 operate fully offline; only eventual sync lost |
| LoRa node seized | Network re-routes; no node is critical path |
| Node firmware tampered | Firmware hashes verified at boot; tampered node isolated |
| Sybil attack (fake nodes) | Nodes require signed DID; new nodes must be vouched by existing node |
| Man-in-the-middle | Noise Protocol end-to-end encryption; no certificate authority to compromise |
| Data withheld at border | Encrypted data meaningless without keys; keys held by beneficiary's device |

---

## 5. Cross-Layer Data Flow

### 5.1 End-to-End: Refugee Enrollment to Aid Receipt

```
DAY 0 — ENROLLMENT (offline, field camp, no internet)

  Refugee arrives → Field worker opens SOS app (offline mode)
    │
    ├─ Generate did:key from device entropy
    ├─ Issue Verifiable Credential: {type: "AidEligible", category: "Displacement", issued_by: "did:ethr:0x..."}
    ├─ Print QR code (paper backup)
    ├─ Store encrypted record locally → IPFS local node
    └─ Queue: [enrollment record CID, VC hash] for chain anchor

DAY 2 — SYNC (field worker reaches town with connectivity)

    └─ Batch upload to IPFS + anchor hashes to Polygon zkEVM
       └─ DID Document updated: new capability key registered

DAY 5 — AID DISTRIBUTION POINT (partial connectivity: LoRa mesh)

  Refugee presents QR → Distribution worker scans
    │
    ├─ Verify VC signature (cryptographic, offline)
    ├─ Check Bloom filter: nullifier not present
    ├─ ZK proof generated: "Eligibility valid" (no identity exposed)
    ├─ Aid dispensed
    ├─ Log: {event_id, nullifier, resource_type, timestamp, location_geohash}
    └─ Nullifier added to local Bloom filter

    │ (via LoRa mesh to nearby node)
    └─ Record propagates to regional node → queued for chain anchor

DAY 6 — CHAIN CONFIRMATION

    └─ Distribution record CID anchored to Polygon zkEVM
       ├─ Global nullifier registry updated (double-dip prevention live)
       ├─ Donor dashboard: "1 distribution confirmed, Khartoum North"
       └─ Field worker DPC score incremented (+1 verified distribution)
```

### 5.2 System State Diagram

```
               ┌──────────────────────────────┐
               │         OFFLINE STATE         │
               │   All operations function     │
               │   Records queue for sync      │
               └──────────────┬───────────────┘
                              │ (connectivity restored)
                              ▼
               ┌──────────────────────────────┐
               │          SYNC STATE           │
               │   IPFS upload: records        │
               │   Chain anchor: CID hashes    │
               │   Bloom filter: delta sync    │
               └──────────────┬───────────────┘
                              │ (confirmed)
                              ▼
               ┌──────────────────────────────┐
               │         VERIFIED STATE        │
               │   Records immutably anchored  │
               │   Nullifiers globally known   │
               │   DPC scores updated          │
               └──────────────────────────────┘
```

---

## 6. Integrated Tech Stack Summary

### 6.1 Recommended Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| **Identity** | `did:key` + `did:ethr` + W3C VCs 2.0 + BBS+ | Offline-capable, selective disclosure, ZK-friendly |
| **Storage** | IPFS (Kubo) + Filecoin (web3.storage) | Content-addressed, unfalsifiable, economically incentivized persistence |
| **Local DB** | OrbitDB + CRDTs | Offline-first, conflict-free sync, P2P native |
| **Chain** | Polygon zkEVM (primary) + Base (secondary) | Low cost, ZK-native, EVM-compatible, battle-tested |
| **Smart contracts** | Solidity + OpenZeppelin | Append-only records, eligibility rules, nullifier registry |
| **ZK proofs** | Circom + snarkjs | Mobile-verifiable proofs, mature tooling |
| **Mesh network** | Meshtastic (LoRa) + libp2p + WiFi Direct | Proven in crisis zones, open firmware, diverse hardware |
| **Node hardware** | Raspberry Pi 4 + RAK2287 + solar | Repairable, sourceable, community-maintainable |
| **Mobile app** | React Native + Expo | One codebase, offline-first, native BLE/WiFi |
| **Indexing** | The Graph Protocol | Query chain events without running full node |
| **Automation** | Otto AI | Generate audit reports, flag anomalies, DPC scoring |

### 6.2 What's NOT in This Stack (and Why)

| Rejected | Reason |
|---------|--------|
| Centralized database (even encrypted) | Single point of seizure |
| Ethereum L1 directly | Gas costs prohibitive for high-volume field ops |
| Solana | Node requirements too high for community hardware |
| Hyperledger / private chain | Defeats the purpose — permissioned = capturable |
| IPFS without Filecoin | Pinning incentive required for long-term persistence |
| Phone number / email as identity anchor | Requires telco cooperation — exactly what fails in crisis |
| Face recognition | Biometric data at rest creates targeting risk |

---

## 7. Tradeoff Analysis

### 7.1 Consistency vs. Availability (CAP Theorem)

SOS Systems chooses **AP (Availability + Partition Tolerance)** over consistency.

```
CHOICE: Eventual Consistency

WHY: In a crisis zone, "system unavailable" costs lives. A slightly
     stale nullifier list is better than no aid distribution at all.

MITIGATED BY:
  - Short distribution windows (5-day events, not open-ended)
  - Regional Bloom filter sync every few hours when connected
  - Double-dip is detectable post-hoc and correctable

TRADEOFF ACCEPTED:
  - In rare offline scenarios, same VC could be used twice at
    physically separate distribution points before sync
  - Detected after the fact; handled by correction record (not deletion)
  - Better outcome than blocking all distributions until connectivity restored
```

### 7.2 Privacy vs. Auditability

```
TENSION: Donors want to verify aid reached people. Beneficiaries
         need protection from targeting (governments, militias).

RESOLUTION: Zero-Knowledge Proof layer

  - Donors see: total distributions, region, date, resource type
  - Donors can verify: specific distribution events are real
  - Donors cannot see: who received what, individual identities
  - Compliance reports generated automatically by Otto (statistics only)

IMPLEMENTATION: ZK proofs of set membership
  "This distribution event is in the set of valid events, anchored to block X"
  — proven without revealing the individual record's content
```

### 7.3 Decentralization vs. Performance

```
TENSION: Fully decentralized systems are slower and harder to use.

RESOLUTION: Tiered architecture with progressive decentralization

  TIER 0 (device-local): Fast, fully offline, most operations
  TIER 1 (community node): Near-real-time, covers most needs
  TIER 2 (satellite/internet): Slow, expensive, but global

  Result: 90%+ of operations happen in Tier 0/1 where performance
  is acceptable. Only synchronization requires Tier 2.
```

### 7.4 Simplicity vs. Integrity Guarantees

```
TENSION: Simpler systems are easier to deploy in crisis zones
         (lower tech literacy, limited hardware). Stronger integrity
         guarantees require more complex cryptography.

RESOLUTION: Progressive complexity with sensible defaults

  MINIMUM: QR code + digital signature check
    → Works on any Android device
    → Any field worker can verify in 2 seconds
    → No blockchain knowledge required

  MAXIMUM: ZK proof + on-chain nullifier + Merkle audit
    → Requires connected device + smart contract call
    → For high-value distributions or audit functions
    → Field workers don't see this complexity

  The complexity lives in the backend. The UX stays simple.
```

### 7.5 On-Chain Cost Analysis

```
Operations per 1,000 distributions:
  - Batch anchor (500 records/tx × 2 txs): ~$0.02 on Polygon zkEVM
  - Nullifier updates (batched): ~$0.05
  - Total per 1,000: ~$0.07

Annual cost at scale (100,000 distributions/month):
  - Chain operations: ~$84/year
  - IPFS/Filecoin storage (1KB avg × 100k records × 12 months): ~$15/year
  - Total infrastructure: < $100/year at this scale

This is negligible. SOS Systems should never gate operations on gas costs.
```

---

## 8. Implementation Phases

### Phase 0 — Foundation (Weeks 1-6)
- [ ] `RecordAnchor.sol` deployed on Polygon zkEVM testnet
- [ ] IPFS node + OrbitDB setup on community node hardware
- [ ] DID key generation + basic VC issuance in React Native
- [ ] Manual QR-based verification flow working offline
- [ ] Field test: 5 field workers, 50 mock distributions

### Phase 1 — Mesh MVP (Weeks 7-14)
- [ ] Meshtastic integration: LoRa sync between field devices and community nodes
- [ ] Bloom filter implementation for offline nullifier checking
- [ ] ZK eligibility proofs (Circom circuit, mobile snarkjs verify)
- [ ] Donor dashboard (The Graph indexer + simple web UI)
- [ ] Field test: 1 community node, 20km radius, full distribution simulation

### Phase 2 — DAO Integration (Weeks 15-22)
- [ ] DPC scoring wired to distribution confirmations
- [ ] Governance: DAO approves distribution events on-chain
- [ ] Audit automation: Otto generates weekly reports
- [ ] Social recovery for lost keys
- [ ] Field test: actual SOS community, real distributions

### Phase 3 — Scale Hardening (Weeks 23-30)
- [ ] Multi-chain support (Base as secondary)
- [ ] Filecoin persistence for long-term records
- [ ] Interoperability: VCs compatible with major humanitarian standards (ICRC, UN OCHA)
- [ ] Hardware kit: documented, sourceable, community-maintainable node package
- [ ] Formal security audit

---

## 9. Integration with MY3YE Ecosystem

```
┌───────────────────────────────────────────────────────────────────┐
│                    MY3YE ECOSYSTEM INTEGRATION                    │
│                                                                   │
│  ONEON (Sovereign Identity Network)                               │
│    └─ Provides DID infrastructure; SOS identity is a            │
│       credential type within the ONEON identity layer            │
│                                                                   │
│  Otto AI (Intelligence Layer)                                     │
│    └─ Monitors distributions, flags anomalies, generates         │
│       audit reports, powers donor dashboard intelligence         │
│                                                                   │
│  Tusita (Physical Communities)                                    │
│    └─ Tusita nodes serve as trusted community infrastructure     │
│       nodes in the mesh, anchoring physical presence             │
│                                                                   │
│  Panik App (Emergency Response)                                   │
│    └─ Uses IPL for verified emergency beacons; integrates        │
│       identity layer for responder verification                  │
│                                                                   │
│  SOS DAO (DPC Governance)                                         │
│    └─ Approves distribution events, sets eligibility rules,      │
│       governs smart contract upgrades, validates field workers   │
└───────────────────────────────────────────────────────────────────┘
```

---

## 10. Open Questions for Pink Paper Integration

The following require DAO-level decisions before implementation begins:

1. **Minimum viable eligibility criteria**: Who decides what qualifies someone for "Displacement" VC? Field worker discretion vs. standardized criteria?

2. **Recovery window**: If a record turns out to be fraudulent (field worker error, not malice), what's the correction process? Append correction record? DAO vote required?

3. **Interoperability standard**: Should SOS VCs be compatible with the emerging W3C VCDM 2.0 standards from ICRC/UNHCR? Adds complexity but enables integration with existing humanitarian systems.

4. **Node economics**: Should community node operators earn DPC contribution credit for uptime? Creates incentive to maintain infrastructure.

5. **Satellite provider**: Starlink (performance but single-company dependency) vs. Iridium (slower but truly independent) vs. hybrid?

---

## Summary

The SOS Systems Integrity Preservation Layer is a four-subsystem architecture:

- **Identity**: Self-sovereign, offline-capable, ZK-selective-disclosure
- **Records**: Content-addressed, append-only, dual-stored (IPFS + chain)
- **Distribution**: Nullifier-protected, ZK-auditable, DAO-governed
- **Mesh**: LoRa/libp2p tiered network, delay-tolerant, community-operated

The design satisfies the core constraint: **no single point that can be seized, shut down, falsified, or bribed**. Each subsystem degrades gracefully under attack — losing connectivity doesn't stop operations, it only delays sync. Losing a node doesn't lose data, it just slows propagation.

This is not a MVP. This is the full blueprint. Implementation should start at Phase 0, field-tested at small scale, and expanded from there. The Pink Paper should incorporate this as the technical specification for the infrastructure promise SOS Systems makes.

---

*Architecture designed by Otto | Review by SOS Systems DAO before implementation | Next step: Pink Paper integration + Phase 0 kickoff*
