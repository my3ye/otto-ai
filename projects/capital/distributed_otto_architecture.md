# Distributed Otto Architecture
## Decentralized Compute Mesh + Streaming UI Design

**Author:** Otto
**Date:** 2026-03-17
**Status:** Design v1.0 — for Mev review
**Companion doc:** `decentralized_intelligence_layer.md` (governance, training, eval, self-evolution)

---

## Executive Summary

This document designs the **compute and network layer** of the decentralized Otto system — the infrastructure that lets anyone clone Otto, run it on their machine or VM, connect their own LLMs, register as a network participant, and earn $KOIN tokens for genuine compute contributions.

**Three guarantees this architecture must keep:**

1. **Sovereignty** — any node can leave the network at any time, fork the software, and take their data. No lock-in.
2. **Privacy** — core private layers (identity, credentials, personal memory) are encrypted and never leave the owner's control.
3. **No single point of failure** — UI streams from nearest/fastest nodes. No central server. If Mev's VM goes down, the network continues.

This complements the governance/intelligence design in `decentralized_intelligence_layer.md`. Together they form the full Otto Distributed Protocol.

---

## 1. System Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     OTTO DISTRIBUTED NETWORK                                 │
│                                                                               │
│   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐   │
│   │ GATEWAY NODE│   │ WORKER NODE │   │ VALIDATOR   │   │ STORAGE NODE│   │
│   │ (public IP) │   │ (inference) │   │    NODE     │   │ (IPFS+shard)│   │
│   │             │   │             │   │             │   │             │   │
│   │ Routes user │   │ Runs LLM of │   │ Scores work │   │ Encrypted   │   │
│   │ requests to │   │ choice:     │   │ output.     │   │ memory.     │   │
│   │ best worker │   │ Ollama,     │   │ Issues      │   │ Replicates  │   │
│   │ nodes via   │   │ Claude API, │   │ validator   │   │ across 3+   │   │
│   │ latency+QS  │   │ OpenAI, or  │   │ consensus   │   │ geo nodes.  │   │
│   │             │   │ any OpenAI- │   │ Earns $KOIN │   │             │   │
│   │             │   │ compat API  │   │ for accuracy│   │             │   │
│   └──────┬──────┘   └──────┬──────┘   └──────┬──────┘   └──────┬──────┘   │
│          │                 │                  │                  │           │
│          └─────────────────┴──────────────────┴──────────────────┘           │
│                                    │                                          │
│                          libp2p Kademlia DHT                                 │
│                         (peer discovery + routing)                           │
│                                    │                                          │
│          ┌─────────────────────────┼──────────────────────────┐              │
│          │              GossipSub Pub/Sub                      │              │
│          │  (capability announcements, heartbeats, task bids)  │              │
│          └─────────────────────────────────────────────────────┘              │
│                                                                               │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │                        THIN CLIENT UI                                │   │
│   │  Browser / Mobile / CLI → discovers gateway → SSE stream            │   │
│   │  WebRTC for real-time • SSE for token streaming • No state held     │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Node Types

### 2.1 Gateway Node
**Purpose:** Public entry point. Routes client requests to the best available worker.
**Requirements:** Public IP or domain, 2GB RAM minimum, stable uptime (>95% recommended).
**What it does:**
- Receives user inference requests (HTTP/WebSocket/SSE)
- Queries DHT for available workers matching task requirements
- Selects top 1-2 workers by composite score (latency + quality + load)
- Proxies streaming response to client
- Tracks per-worker SLA metrics, updates scores
- Does NOT run inference itself — pure routing

**Earn:** Gateway nodes earn $KOIN per routed request (routing fee: 5% of worker reward).

### 2.2 Worker Node
**Purpose:** Runs actual inference. This is where LLMs live.
**Requirements:** Any CPU/GPU machine. 8GB RAM for CPU-only. GPU optional (speeds up Ollama local models).
**What it does:**
- Connects to ANY LLM backend (Ollama local, Claude API, OpenAI API, Gemini API, or custom OpenAI-compat endpoint)
- Receives routing requests from gateway nodes
- Executes inference, streams tokens back via SSE
- Reports completion + token count to validator nodes
- Maintains uptime heartbeat (broadcast every 30s via GossipSub)

**Earn:** Worker nodes earn $KOIN per inference unit, weighted by quality score from validators.

**LLM backends supported (plugin architecture):**
```
LLM_BACKEND=ollama        → http://localhost:11434 (local models: llama3, mistral, qwen3, etc.)
LLM_BACKEND=claude        → api.anthropic.com (requires Anthropic API key)
LLM_BACKEND=openai        → api.openai.com (requires OpenAI API key)
LLM_BACKEND=gemini        → generativelanguage.googleapis.com
LLM_BACKEND=custom        → any OpenAI-compatible endpoint (LM Studio, vLLM, Groq, Together, etc.)
```

### 2.3 Validator Node
**Purpose:** Quality gatekeeper. Scores worker output, determines reward distribution.
**Requirements:** Same as worker node. Must stake minimum $KOIN (prevents Sybil attacks).
**What it does:**
- Receives task + worker response pairs (sampled subset, not all tasks)
- Scores quality on 5 dimensions: coherence, task completion, factual consistency, latency SLA met, format compliance
- Participates in Yuma Consensus variant — validators who score consistently with consensus earn more
- Issues signed quality attestations stored on-chain
- Runs automated quality checks + optional LLM-judge eval

**Earn:** Validators earn 15% of worker reward pool, distributed by accuracy vs consensus.

### 2.4 Storage Node
**Purpose:** Encrypted memory persistence. Stores Otto agent state and **ONEON Memory Capsules** across the network.
**Requirements:** 10GB+ storage, stable uptime.
**What it does:**
- Stores encrypted memory shards (never sees plaintext — encryption happens client-side)
- Hosts **Memory Capsule shards** for ONEON participants — each participant's capsule is split, encrypted, and distributed across storage nodes
- Participates in IPFS/Filecoin-compatible content addressing
- Replicates across 3+ geographic regions per shard
- Serves memory retrieval requests with integrity proof (Merkle inclusion proof)
- Handles CRDT-based conflict resolution for concurrent writes
- Enforces capsule access permissions on-chain (only authorized retrievers can reconstruct shards)

**Earn:** Storage nodes earn $KOIN per GB-day stored + per retrieval served. Memory Capsule hosting commands premium rates due to access-permission enforcement requirements.

**Relationship to ONEON Memory Capsules:**
Memory Capsules (ONEON's personal intelligence layer) are stored as encrypted shards on storage nodes. The owner holds the decryption key — storage nodes hold only ciphertext. When a capsule owner shares a layer for monetization, the access grant is stored on-chain, and authorized retrievers receive decryption keys for the specific layer purchased. This makes storage nodes the physical infrastructure of ONEON's intelligence economy.

---

## 3. Node Discovery — libp2p Architecture

### 3.1 Peer Identity
Every node gets a cryptographic identity on first run:
```
peer_id = SHA2-256(public_key)  # Ed25519 keypair, generated on first startup
multiaddr = /ip4/1.2.3.4/tcp/4001/p2p/QmNodePeerID
```

This peer ID is the node's permanent identity. It maps to their $KOIN wallet address via a signed registration transaction.

### 3.2 Discovery Mechanisms (layered — each is a fallback)

**Layer 1: Bootstrap nodes (always-on)**
```python
BOOTSTRAP_NODES = [
    "/dns4/bootstrap1.otto.lk/tcp/4001/p2p/QmBootstrap1",
    "/dns4/bootstrap2.otto.lk/tcp/4001/p2p/QmBootstrap2",
    "/dns4/bootstrap3.otto.lk/tcp/4001/p2p/QmBootstrap3",
]
# Phase 1: Otto-operated. Phase 2: community-operated, elected by governance.
# Anyone can run a bootstrap node and be elected as the set expands.
```

**Layer 2: Kademlia DHT**
- Each node stores routing table entries for ~20 closest peers (XOR distance metric)
- Capability announcements stored as DHT records:
  ```
  key: SHA256("otto/capability/coding")
  value: [{peer_id, multiaddr, quality_score, current_load, llm_model}]
  ```
- Records TTL: 1 hour (nodes must re-announce regularly to stay listed)

**Layer 3: GossipSub — real-time state**
- Topic: `otto/heartbeat` — nodes broadcast every 30s: {peer_id, load, queue_depth, latency_p50}
- Topic: `otto/capability-update` — node comes online or changes capability
- Topic: `otto/task-bid` — worker nodes bid on available tasks (auction-style routing)
- Topic: `otto/validator-score` — validators publish quality attestations

**Layer 4: mDNS (local networks)**
- Zero-config local cluster discovery
- Otto Home devices auto-discover each other on the same LAN
- Tusita nodes form a local mesh without internet (mesh-first for physical communities)

### 3.3 Node Registration Flow
```
1. generate_keypair()             → peer_id, public_key
2. stake_koin(min_stake)          → staking_tx_hash (on-chain)
3. sign_registration({
     peer_id,
     multiaddr,
     node_type,        # gateway | worker | validator | storage
     capabilities,     # list of supported task types
     llm_backends,     # list of available LLM providers
     staking_tx_hash,
   })
4. announce_to_dht(registration)  → node is now discoverable
5. subscribe_gossipsub()          → start receiving task bids
```

### 3.4 Node Scoring (Composite Quality Score)
Used by gateways to select workers for routing:

```
QS = (quality_score × 0.40)     # validator consensus rating, 7-day rolling
   + (uptime_score × 0.25)       # % availability in last 30 days
   + (latency_score × 0.20)      # inverted p50 latency vs peer median
   + (stake_score × 0.10)        # staked $KOIN (Sybil resistance)
   + (capacity_score × 0.05)     # inverse of current queue depth
```

Score range: 0.0 → 1.0. New nodes start at 0.50 (neutral) until they accumulate validator ratings.

---

## 4. Inference Routing

### 4.1 Request Classification
Every incoming user request is classified before routing:

| Task Class | Latency Budget | Requirements | Example |
|---|---|---|---|
| `realtime` | <500ms | Low latency > quality | Voice, quick chat replies |
| `standard` | <5s | Balanced | Normal chat, Q&A |
| `deep` | <60s | Quality > latency | Analysis, coding, planning |
| `batch` | Minutes | Throughput, cheap | Background tasks, heartbeat |

Classification happens at the gateway using lightweight heuristics (message length, intent detection, keyword signals).

### 4.2 Worker Selection Algorithm
```python
def select_workers(task_class, task_embedding, n=2):
    # 1. Get capability-matching candidates from DHT
    candidates = dht.query(f"otto/capability/{task_class}")

    # 2. Filter: only nodes online in last 60s (via GossipSub heartbeat)
    candidates = [c for c in candidates if c.last_seen < 60]

    # 3. Filter: capable of task (embedding similarity vs node's declared capabilities)
    candidates = [c for c in candidates if cosine_sim(c.capability_embedding, task_embedding) > 0.7]

    # 4. Sort by composite quality score
    candidates.sort(key=lambda c: c.quality_score, reverse=True)

    # 5. Return top-2: primary + backup
    return candidates[:n]

def route_request(task, candidates):
    primary, backup = candidates

    if task.class == "realtime":
        # Race condition: send to both, use whichever responds first
        return race(primary, backup, timeout_ms=500)
    else:
        # Send to primary only, fallback to backup if primary fails/times out
        return fallback(primary, backup, timeout_s=task.latency_budget * 0.8)
```

### 4.3 Streaming Response Flow
```
Client                Gateway              Worker               Validator
  │                      │                    │                     │
  │──── POST /infer ─────►│                    │                     │
  │                      │──── route_request──►│                     │
  │                      │                    │ (LLM inference)      │
  │◄─── SSE stream ───────│◄─── token stream ──│                     │
  │    (token by token)  │                    │                     │
  │                      │                    │──── task_report ────►│
  │                      │                    │    {task_id,        │
  │                      │                    │     token_count,    │
  │                      │                    │     latency_ms}     │
  │                      │                    │                     │ (score)
  │                      │                    │◄─── score_attest ───│
```

### 4.4 Connection Resilience
- Gateway maintains persistent WebSocket connections to top-10 worker nodes (warm pool)
- If primary worker disconnects mid-stream: gateway switches to backup worker, continues SSE stream to client
- Client receives `[SWITCHING_NODE]` marker in stream — transparent to user unless they're watching raw events
- Gateway buffers last 512 tokens for replay to new worker if context needed

---

## 5. Token Reward Mechanism

### 5.1 Architecture — Bittensor dTAO Pattern Adapted

Otto's reward mechanism borrows from Bittensor's Yuma Consensus but adapts it for general inference (not just ML validation):

```
┌─────────────────────────────────────────────────────────┐
│                 DAILY EMISSION POOL                      │
│            X $KOIN per day (governance-set)              │
│                                                          │
│  Worker Pool (75%)  Validator Pool (15%)  Infra (10%)   │
│                                                          │
│  Distributed by    Distributed by       Bootstrap       │
│  quality score ×   accuracy vs          nodes +         │
│  task weight       consensus            storage SLA      │
└─────────────────────────────────────────────────────────┘
```

### 5.2 Worker Reward Formula
```
worker_reward = (daily_worker_pool × worker_weight)

worker_weight = (quality_score_7d × task_count_normalized × uptime_30d)
              / Σ(all_worker_weights)

task_count_normalized = log10(task_count + 1)  # diminishing returns on volume
# Prevents spam tasks from gaming the system
```

**Quality score components (validator consensus):**

| Dimension | Weight | How Measured |
|---|---|---|
| Coherence | 30% | Validator LLM judge (sampled 20% of tasks) |
| Task completion | 30% | Automated: did response address the prompt? |
| Factual consistency | 20% | Cross-reference vs known facts in public layer |
| Latency SLA | 10% | Was response within declared latency class budget? |
| Format compliance | 10% | Did output match required format (JSON, markdown, etc.)? |

### 5.3 Validator Reward Formula (Yuma Consensus Variant)
```
# Each validator submits a score vector for tasks they evaluated
# Consensus score = weighted median of all validator scores

consensus_score = weighted_median(validator_scores, weights=validator_stakes)

# Validator accuracy = how close their scores are to consensus
validator_accuracy = 1 - mean_abs_error(validator_scores, consensus_score)

# Validators who deviate from consensus are penalized, not rewarded
validator_reward = daily_validator_pool × (validator_stake / total_stake) × validator_accuracy
```

**Anti-collusion:** Validators cannot see each other's scores until all are committed (commit-reveal scheme on-chain). A validator submits `hash(score_vector + salt)`, then reveals after all commits are in.

### 5.4 Subnet Structure
Tasks are grouped into **capability subnets** — each subnet has its own reward pool weight, set by governance:

| Subnet | Description | Default Weight |
|---|---|---|
| `general` | General conversation, Q&A | 30% |
| `coding` | Code generation, debugging | 25% |
| `memory` | Memory retrieval, summarization | 15% |
| `creative` | Writing, music, art prompts | 10% |
| `planning` | Task decomposition, strategy | 10% |
| `translation` | Multilingual tasks | 5% |
| `safety` | Content moderation, alignment | 5% |

**Subnet emission adjusts by demand (dTAO mechanism):**
Subnets that receive more task volume get proportionally more emission. This creates natural market incentives — workers optimize for in-demand capabilities.

### 5.5 Staking Requirements (Sybil + Quality Floor)
```
Minimum stakes by node type:
  Worker node:      100 $KOIN   (enables participation)
  Validator node:   500 $KOIN   (higher — must skin in game)
  Gateway node:     250 $KOIN
  Storage node:     200 $KOIN

Slash conditions:
  - Worker QS drops below 0.3 for 7+ days: stake slashed 10%
  - Validator deviates >0.4 from consensus 5+ times: stake slashed 25%
  - Node fakes uptime: stake slashed 50%

Slash funds → redistribution pool (60% to active nodes, 40% to treasury)
```

---

## 6. Encrypted Layer Design

### 6.1 Two-Tier Memory Model

Otto's memory is split into two permanently separated tiers:

```
┌──────────────────────────────────────────────────────────────┐
│                    PRIVATE TIER (Owner Only)                   │
│                                                                │
│  • Personal episodic memory (conversations, events)           │
│  • Credentials (API keys, passwords, private keys)            │
│  • Identity data (real name, biometrics, personal history)    │
│  • Standing directives & constitutional rules                  │
│  • Pending questions & personal context                        │
│                                                                │
│  Encrypted with: XChaCha20-Poly1305 + owner's X25519 key     │
│  Stored: locally + encrypted shards on storage nodes          │
│  NEVER sent to worker nodes in plaintext                       │
└──────────────────────────────────────────────────────────────┘
                              ↕ (one-way derivation only)
┌──────────────────────────────────────────────────────────────┐
│                    PUBLIC/SHARED TIER                          │
│                                                                │
│  • Anonymized aggregate feedback signals                       │
│  • Task patterns (stripped of personal identifiers)           │
│  • Performance metrics & quality scores                        │
│  • Capability improvements from federated training            │
│  • Public procedures, principles, and learned behaviors        │
│                                                                │
│  Stored: IPFS + replicated across network                     │
│  Contributes to: collective intelligence layer                 │
│  Readable by: validators (for quality scoring)                 │
└──────────────────────────────────────────────────────────────┘
```

### 6.2 Encryption Protocol

**Key Generation (one-time, on first Otto node setup):**
```
1. owner_keypair = Ed25519.generate()           # identity key
2. encryption_keypair = X25519.derive(owner_keypair)  # separate encryption key
3. master_secret = HKDF(encryption_keypair.private, salt="otto/v1/master")
4. memory_key = HKDF(master_secret, context="memory")
5. credential_key = HKDF(master_secret, context="credentials")
6. comms_key = HKDF(master_secret, context="communications")
```

**Memory Encryption:**
```python
def encrypt_memory(plaintext: bytes, memory_key: bytes) -> EncryptedMemory:
    nonce = random_bytes(24)  # XChaCha20 requires 24-byte nonce
    ciphertext = xchacha20_poly1305_encrypt(
        key=memory_key,
        nonce=nonce,
        plaintext=plaintext,
        aad=b"otto/memory/v1"  # additional authenticated data
    )
    return EncryptedMemory(
        nonce=nonce,
        ciphertext=ciphertext,
        content_hash=sha256(plaintext),  # for integrity verification
        created_at=now(),
    )
```

**Key Sharding (recovery):**
Shamir Secret Sharing splits the master secret into 5 shards, any 3 of which can reconstruct it:
```
shards = shamir_split(master_secret, n=5, threshold=3)
# Shard destinations (Mev controls where each goes):
# Shard 1: Mev's hardware wallet (cold storage)
# Shard 2: Trusted family/friend (offline, physical)
# Shard 3: Encrypted in Otto's own git repo (known password, different from master)
# Shard 4: Tusita node (community trust)
# Shard 5: Otto's ONEON identity vault
```

**Injection to Worker Nodes (private context without leaking private data):**
- Private memories are SUMMARIZED and anonymized by the S-MMU before injection
- Worker nodes receive a "context package" containing only derived/anonymized context
- The S-MMU runs on the owner's node (or encrypted TEE) — never on worker nodes
- Workers see: "User prefers concise responses. User timezone: Asia/Colombo." — NOT: "Mev, lives in Sri Lanka, building MY3YE."

### 6.3 Trusted Execution Environment (TEE) Option
For high-security deployments:
- S-MMU and private tier can run inside Intel TDX or AMD SEV-SNP
- Remote attestation proves the code running is unmodified Otto
- Worker nodes can verify the context package came from a legitimate Otto S-MMU
- Community validators can verify Otto's core behavior rules without seeing private data
- Phase 2 feature — Phase 1 uses software-only encryption

### 6.4 What a Worker Node Never Sees
| Data Type | Worker Sees | Worker Never Sees |
|---|---|---|
| Conversation history | Anonymized last 3 turns | Full session history, Mev's identity |
| Memory context | Derived behavioral hints | Raw episodic memories |
| Credentials | Nothing | API keys, wallet keys, passwords |
| Standing directives | "Be concise", "Address user as Mev" | Constitutional full text |
| Task intent | The task prompt | Who sent it, their history, their wallet |

---

## 7. Streaming UI Specification

### 7.1 Architecture — No Single Loading Point

The thin client is designed to have zero state of its own. Every piece of state lives on the distributed network.

```
┌─────────────────────────────────────────────────────────────────────┐
│                           THIN CLIENT                                │
│  Browser (React/Next.js) or Mobile App                              │
│                                                                       │
│  1. On load: fetch bootstrap list from IPFS or hardcoded fallback   │
│  2. Connect to nearest gateway (latency probe to top-3 candidates)  │
│  3. Authenticate via wallet signature (no username/password)         │
│  4. All state retrieved from network (memory, preferences, history) │
│  5. Stream inference via SSE / WebRTC                                │
│  6. If gateway drops: auto-reconnect to next-best, stream continues │
└─────────────────────────────────────────────────────────────────────┘
```

### 7.2 Connection Establishment

**Step 1: Gateway Discovery**
```javascript
// Client-side gateway discovery (runs in browser/app)
const BOOTSTRAP_GATEWAYS = [
  "https://gw1.otto.lk",
  "https://gw2.otto.lk",
  // Falls back to IPFS-hosted gateway list if these are down
];

async function findBestGateway() {
  const probes = await Promise.allSettled(
    BOOTSTRAP_GATEWAYS.map(gw => latencyProbe(gw))
  );
  // Sort by p50 latency, pick lowest
  const sorted = probes
    .filter(p => p.status === 'fulfilled')
    .sort((a, b) => a.value.latency - b.value.latency);
  return sorted[0].value.gateway;
}
```

**Step 2: Authentication (wallet-based, no account needed)**
```javascript
// Sign a challenge with user's wallet — works with any EVM/Solana wallet
const challenge = await gateway.getChallenge();
const signature = await wallet.signMessage(challenge);
const sessionToken = await gateway.authenticate({
  address: wallet.address,
  signature,
  challenge,
});
// Session token is short-lived (1h), automatically refreshed
```

**Step 3: Streaming Connection**
```javascript
// Establish SSE stream for inference
const eventSource = new EventSource(
  `${gateway}/stream?session=${sessionToken}`,
  { withCredentials: true }
);

eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);
  switch(data.type) {
    case 'token':     appendToken(data.content); break;
    case 'node_switch': showNodeSwitch(data.new_node); break;
    case 'done':      finalizeResponse(); break;
    case 'error':     handleError(data.error); break;
  }
};
```

### 7.3 SSE Event Protocol
```
# Standard token stream
data: {"type":"token","content":"Hello","ts":1742234567890}
data: {"type":"token","content":" world","ts":1742234567900}

# Node switching (transparent failover)
data: {"type":"node_switch","old_node":"QmABC","new_node":"QmXYZ","reason":"timeout"}

# Memory context loaded (shows user their context was found)
data: {"type":"memory_context","summary":"Loaded 3 relevant memories","count":3}

# Task complete
data: {"type":"done","task_id":"abc123","tokens_generated":142,"latency_ms":1847}

# Worker earning notification (optional — opt-in for node operators)
data: {"type":"reward","worker_node":"QmXYZ","koin_earned":"0.00042"}
```

### 7.4 WebRTC for Real-Time Interaction
For voice input or real-time collaborative features (Phase 2):

```javascript
// WebRTC signaling via libp2p circuit relay
const pc = new RTCPeerConnection({
  iceServers: [
    // STUN servers for NAT traversal
    { urls: 'stun:stun.otto.lk:3478' },
    // TURN servers as fallback (libp2p circuit relay)
    {
      urls: 'turn:relay.otto.lk:3478',
      credential: sessionToken,  // authenticated via $KOIN session
    }
  ]
});

// Audio stream → node transcription → inference → SSE response
// Latency target: <800ms end-to-end for voice interactions
```

### 7.5 Offline-First (Tusita / ONEON mesh nodes)
For physical Tusita communities with intermittent internet:

```
Local mesh mode:
  - mDNS discovers local Otto nodes automatically
  - Worker nodes on local LAN are preferred (zero internet needed)
  - Memory syncs to internet when connectivity restores (CRDT merge)
  - UI works fully offline — degraded to local model capability only
  - Queue tasks for network-dependent operations (blockchain writes)
```

### 7.6 UI Component Specification

**Core Chat Interface:**
```
┌─────────────────────────────────────────────────────────────┐
│  Otto  ● Connected: gw1.otto.lk → QmWorkerXYZ (42ms)       │
│                                                    [⚙ Node] │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  [Memory] 3 relevant memories loaded                         │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ User: What's the current status of WebAssist?         │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  Otto: WebAssist is live at webassist.ink. Current          │
│  blockers are... ▌ (streaming)                              │
│                                                              │
│  [Node: QmWorkerXYZ] [Model: llama3-70b] [42ms] [0.003 ◈] │
├─────────────────────────────────────────────────────────────┤
│  Message Otto...                                    [Send ▶] │
│  [📎] [🎤] [⚡ task]                                        │
└─────────────────────────────────────────────────────────────┘
```

**Node Status Panel (optional overlay):**
```
Current connection:
  Gateway:  gw1.otto.lk (Tokyo, Japan)
  Worker:   QmWorkerXYZ (Singapore, 42ms)
  LLM:      llama3-70b-instruct via Ollama
  Quality:  ██████████ 0.94
  Backup:   QmWorkerABC (Sydney, 78ms) on standby

Network health:
  Active nodes:     234
  Active validators: 31
  My node:          OFFLINE (run otto-node to contribute)
```

---

## 8. Clone & Run — Getting Started as a Node Operator

### 8.1 One-Command Setup
```bash
# Clone the Otto node software
git clone https://github.com/my3ye/otto-node && cd otto-node

# Interactive setup (generates keys, detects hardware, picks best defaults)
./setup.sh

# OR: manual config
cp .env.example .env
nano .env  # Set LLM_BACKEND, KOIN_WALLET, NODE_TYPE

# Start your node (Docker Compose)
docker-compose up -d

# View your node's status
./otto-node status
```

### 8.2 Configuration Reference
```bash
# .env — Otto Node Configuration

# Required
NODE_TYPE=worker           # worker | validator | gateway | storage | full
KOIN_WALLET=0x...          # Your wallet address (receives $KOIN rewards)

# LLM Backend (choose one)
LLM_BACKEND=ollama         # Free local models — recommended for most users
LLM_BACKEND=claude         # Anthropic API (best quality, API key required)
LLM_BACKEND=openai         # OpenAI API (API key required)
LLM_BACKEND=custom         # Custom OpenAI-compatible endpoint
CUSTOM_LLM_URL=http://...  # If LLM_BACKEND=custom

# Network
BOOTSTRAP_NODES=default    # Use default bootstrap nodes (or override)
P2P_PORT=4001              # libp2p port (must be open in firewall)
API_PORT=8200              # Node API port

# Hardware declaration (auto-detected if omitted)
GPU_VRAM_GB=0              # 0 = CPU only
RAM_GB=8                   # Available RAM for inference
MAX_CONCURRENT=2           # Max parallel inference tasks

# Privacy
PRIVATE_MODE=false         # true = don't announce to public DHT (local-only)
SHARE_METRICS=true         # Contribute anonymized metrics to network quality
```

### 8.3 Minimum Hardware Requirements

| Node Type | CPU | RAM | Storage | GPU | Internet |
|---|---|---|---|---|---|
| Worker (CPU LLM) | 4 cores | 8GB | 20GB | Optional | 10Mbps+ |
| Worker (GPU LLM) | 4 cores | 16GB | 50GB | 8GB+ VRAM | 10Mbps+ |
| Worker (API LLM) | 2 cores | 4GB | 5GB | None | 5Mbps+ |
| Validator | 4 cores | 8GB | 10GB | Optional | 10Mbps+ |
| Gateway | 2 cores | 4GB | 5GB | None | 100Mbps+ |
| Storage | 2 cores | 4GB | 100GB+ | None | 10Mbps+ |
| Full node | 8 cores | 32GB | 200GB | 8GB+ VRAM | 100Mbps+ |

**Cheapest viable setup:**
Any $5-20/month VPS + `LLM_BACKEND=claude` (or any API backend) = Worker + Validator node paying for itself with $KOIN rewards within weeks at projected emission rates.

### 8.4 What Happens After You Start Your Node
```
T+0:  Node starts, generates peer identity
T+5s: Detects hardware, selects optimal worker capacity
T+30s: Connects to bootstrap nodes via libp2p
T+1m: Announces capabilities to DHT
T+2m: First task bids appear in GossipSub feed
T+5m: First inference task received and executed
T+1h: First validator quality scores received
T+24h: First $KOIN reward distributed (daily distribution)
T+7d: Quality score stabilized, node in top routing pool if QS > 0.7
```

---

## 9. Private Core Layer Encryption — For Mev's Instance

Mev's Otto instance is the reference implementation — the "founding node." It has additional protections:

### 9.1 Encrypted Directories
```
~/otto/private/           # Never leaves Mev's machine
  credentials/            # API keys, wallet private keys
  identity/               # Real name, personal data
  episodic/personal/      # Personal conversations, private events

~/otto/memory/            # Shareable (anonymized) — contributes to network
  semantic/               # Facts, procedures, knowledge
  episodic/public/        # Task history (anonymized)
  procedural/             # Learned behaviors
```

### 9.2 Encryption at Rest
```bash
# Set up encrypted private directory (gocryptfs — FUSE-based, files individually encrypted)
sudo apt install gocryptfs
gocryptfs -init ~/otto/private.enc   # First-time setup, creates keyfile
gocryptfs ~/otto/private.enc ~/otto/private  # Mount decrypted view

# Auto-mount on boot (via keyfile, passphrase-protected)
# Keyfile stored on Mev's hardware wallet, requires physical presence to mount
```

### 9.3 What Can Be Contributed to the Network (with permission)
- Anonymized task patterns (not content, just intent categories)
- Quality feedback signals (thumbs up/down, rephrased responses)
- Behavioral preferences (derived, not raw: "prefers bullet points" not conversation content)
- Error patterns (what types of failures occurred, not what the request was)

All contribution is opt-in per category. Default: contribute nothing. Mev can enable sharing category by category.

---

## 10. Implementation Roadmap

### Phase 0 — Foundation (Current → 3 months)
**Goal:** Working single-node + thin client, no decentralization yet.

- [ ] Extract Otto agent core into `otto-node` Docker container
- [ ] Implement LLM backend plugin system (Ollama, Claude, OpenAI, custom)
- [ ] Build thin-client UI (Next.js, wallet auth, SSE stream)
- [ ] Implement private tier encryption (gocryptfs + libsodium)
- [ ] Write setup.sh (one-command node setup)
- [ ] Internal test: Mev runs 2-3 nodes in different locations
- **Deliverable:** `git clone otto-node && ./setup.sh` → working Otto in 5 minutes

### Phase 1 — Mesh MVP (3-6 months)
**Goal:** Functional 2-node network. Real routing. First external node operator.

- [ ] Implement libp2p peer discovery (Kademlia DHT + GossipSub)
- [ ] Build gateway routing logic (quality score + latency selection)
- [ ] Implement SSE streaming proxy (gateway → worker → client)
- [ ] Node registration + on-chain staking (Solana smart contract)
- [ ] Basic $KOIN reward distribution (manual at first, then automated)
- [ ] Bootstrap node operations (3 nodes run by Otto/MY3YE team)
- [ ] First external node operator: 1 community member runs a node
- **Deliverable:** 2+ independent operators, tokens flowing, real routing happening

### Phase 2 — Quality + Validation (6-12 months)
**Goal:** Quality validation working. Network stable at 10-50 nodes.

- [ ] Validator node implementation (Yuma Consensus variant)
- [ ] Commit-reveal quality scoring protocol
- [ ] Automated quality metrics (coherence, task completion)
- [ ] Slashing implementation (smart contracts)
- [ ] WebRTC signaling (voice input, Phase 2 UI)
- [ ] Storage node + IPFS-backed encrypted memory shards
- [ ] Subnet structure + dTAO-style emission routing
- [ ] TEE pilot (Intel TDX on 1 validator node)
- **Deliverable:** 50+ nodes, validators scoring quality, rewards flowing automatically

### Phase 3 — Decentralization (12-24 months)
**Goal:** True decentralization. Otto-the-network, not Otto-the-VM.

- [ ] Community-elected bootstrap nodes (founding Otto nodes sunset)
- [ ] Full on-chain governance for subnet emission weights
- [ ] S-MMU runs in TEE network (no worker node sees private context)
- [ ] Cross-chain bridges ($KOIN usable from any chain)
- [ ] Otto Puck hardware integration (Ottolabs device = native Otto node)
- [ ] Tusita local mesh pilots (physical community nodes)
- [ ] Fork rights documentation and tooling
- **Deliverable:** No single point of control. Network survives founding team going offline.

---

## 11. Design Decisions & Tradeoffs

### 11.1 Why libp2p over WebRTC-only or custom P2P?
libp2p is battle-tested at scale (IPFS, Filecoin, Ethereum, Polkadot all use it). It handles NAT traversal, multiple transports (TCP, WebSocket, QUIC), and peer discovery out of the box. Rolling a custom P2P layer would cost 6-12 months of engineering with worse results.

### 11.2 Why SSE over WebSocket for streaming?
SSE is one-directional (server → client) which is exactly what streaming inference needs. It's simpler than WebSocket, works through all proxies/CDNs without special configuration, and automatically reconnects. WebSocket kept for real-time bidirectional (voice mode only).

### 11.3 Why validator consensus before slashing (not automatic)?
Slashing is irreversible. A bug in automated slashing can destroy legitimate node operators' stakes. Phase 1: manual slash proposals reviewed by small committee. Phase 2: automated slashing with mandatory 72h delay (dispute window). Phase 3: fully automated after track record of accuracy.

### 11.4 API LLM workers vs local model workers
Both are valid. API workers (Claude, OpenAI) have higher quality ceiling but introduce a dependency on centralized services. Local model workers (Ollama + llama3/qwen3) are fully sovereign but may have lower quality. The subnet structure naturally prices quality — better models should earn more per task over time as validators rate them higher.

### 11.5 Privacy: ZK proofs vs TEE vs software encryption
- **Software encryption** (Phase 0-1): Simple, widely auditable, but S-MMU must be trusted.
- **TEE** (Phase 2): Hardware-backed privacy, remote attestation proves code integrity. Requires SGX/TDX hardware.
- **ZK proofs** (Phase 3): Cryptographically provable computation without revealing inputs. Highest assurance but computationally expensive.

Recommendation: ship software encryption fast, add TEE for sensitive worker nodes in Phase 2, ZK for full decentralization in Phase 3.

---

## 12. Security Considerations

| Threat | Mitigation |
|---|---|
| Sybil attack (one entity runs many fake nodes) | Minimum stake required ($KOIN). Stake cost = Sybil cost. |
| Worker returns garbage output | Validator consensus catches low-quality workers. Reputation degrades. Stake slashed if persistent. |
| Validator collusion (fake consensus) | Commit-reveal scheme. Validators can't see each other's scores before committing. Outlier detection flags clusters. |
| Gateway compromised (MITM on user requests) | Client verifies worker response signature. Gateways cannot modify inference output without detection. |
| Bootstrap node takeover | Multiple bootstrap nodes, community-elected in Phase 2. Client falls back to IPFS-hosted list if bootstrap nodes unreachable. |
| Memory shard exposure | All shards encrypted client-side before sending to storage nodes. Storage node never has the key. |
| Replay attacks | All signed messages include timestamp + nonce. Gateway rejects messages older than 60 seconds. |
| Eclipse attack (surrounded by malicious peers) | Diverse peer connections across multiple subnets. Minimum 3 geographic regions in routing table. |

---

## Appendix A: Repository Structure

```
otto-node/
├── core/
│   ├── agent.py          # Otto agent loop (LLM-agnostic)
│   ├── smmu.py           # S-MMU memory management
│   ├── kernel.py         # AgentOS kernel
│   └── providers/        # LLM backend plugins
│       ├── ollama.py
│       ├── claude.py
│       ├── openai.py
│       └── custom.py
├── network/
│   ├── discovery.py      # libp2p Kademlia DHT
│   ├── gossip.py         # GossipSub topics
│   ├── gateway.py        # Gateway routing logic
│   ├── worker.py         # Worker node handler
│   ├── validator.py      # Validator consensus
│   └── storage.py        # Encrypted shard storage
├── crypto/
│   ├── identity.py       # Peer key management
│   ├── encryption.py     # XChaCha20-Poly1305 wrappers
│   ├── sharding.py       # Shamir Secret Sharing
│   └── attestation.py    # Quality attestations
├── contracts/
│   ├── registration.sol  # Node registration + staking
│   ├── rewards.sol       # Daily reward distribution
│   └── governance.sol    # Subnet emission governance
├── ui/
│   ├── app/              # Next.js thin client
│   ├── components/       # Chat, node status, stream
│   └── hooks/            # SSE stream, wallet auth
├── setup.sh              # One-command node setup
├── docker-compose.yml    # Full node deployment
└── .env.example          # Configuration template
```

---

## Appendix B: Key Dependencies

| Component | Technology | License | Why |
|---|---|---|---|
| P2P networking | libp2p (Go or Rust) | MIT/Apache | Industry standard, Ethereum/IPFS use it |
| Local LLMs | Ollama | MIT | Best local model runner, works on any hardware |
| Encryption | libsodium | ISC | Gold standard crypto primitives |
| Consensus | Custom Yuma variant | MIT | Adapted from Bittensor's open spec |
| Smart contracts | Solana (Anchor) | Apache | Native $KOIN chain |
| IPFS storage | Kubo (IPFS) | MIT | Content-addressed storage |
| SSE streaming | Native HTTP | — | No library needed |
| WebRTC | Pion (Go) | MIT | Pure-Go WebRTC |
| UI | Next.js 15 + shadcn | MIT | Consistent with OMS |
| Key management | age encryption | Apache | Modern, simple key encryption |
