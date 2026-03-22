---
name: Sybil Resistance for Crypto Investment Platforms
description: Comprehensive research on Sybil-resistance methods — wallet clustering, scoring, zkProof identity, smart contract enforcement, and hybrid approaches. Goal: limit real persons to max 3 wallets on an investment platform.
type: project
---

# Sybil Resistance for Crypto Investment Platforms

**Research date:** 2026-03-16
**Goal:** Detect Sybil attackers registering many wallets to bypass a per-person 3-wallet cap.

---

## 1. On-Chain Clustering / CEX Withdrawal Fingerprinting

### How it works
Two primary heuristics for Ethereum:
- **Deposit address clustering**: When multiple wallets all deposit to the same CEX deposit address, they are controlled by the same entity. 17.9% of all active EOAs on Ethereum cluster via this heuristic (4-year study). Most effective single heuristic for Ethereum.
- **Common input ownership (Bitcoin-derived)**: Multiple addresses signing inputs in the same tx = same controller. Less applicable to Ethereum account model.
- **Token authorization clustering**: When the same address authorizes a token spend from multiple wallets, those wallets are co-owned.

For Sybil investment platform use: If wallets A, B, and C all withdrew from Binance to deposit address `0xabc`, they belong to the same person. Flag as one entity.

### Tools
| Tool | Approach | Cost | Notes |
|------|----------|------|-------|
| **Chainalysis Reactor/KYT** | ML-based clustering + entity labels | Enterprise ($50K+/yr) | Regulatory-grade, bank-used. Proprietary. |
| **TRM Labs** | Custom entity clustering, 74M+ cross-chain swaps tracked | Enterprise | "One-click cross-chain tracing." Signatures ML for pattern detection. |
| **Nansen** | 500M+ labeled addresses, AI clustering | $150/mo to enterprise | Used by LayerZero (found 60,995-wallet sybil cluster), Linea (removed 516K of 1.3M wallets) |
| **TrustScan (TrustaLabs)** | Asset Transfer Graph analysis, 4 pattern types | API available | Used by Gitcoin Passport. Sybil score 0-100. |
| **Merkle Science** | Advanced clustering for Bitcoin + EVM | Paid | Good for multi-chain |

### Accuracy
- Nansen's Linea work: flagged 39.85% of eligible wallets (516,960 of 1.3M) as Sybil. Prioritized precision over recall — deliberately conservative to minimize false positives. No public FP rate.
- Academic subgraph-LightGBM model: Precision 0.9428, Recall 0.9182, F1 0.9303, AUC 0.9806.
- Deposit address heuristic alone: high precision (mis-clustering requires adversarial behavior), low recall (many sybil wallets don't share deposit addresses).

### Implementation complexity: 3/5
- Can implement deposit-address clustering yourself via Etherscan/Helius APIs. Get withdrawal tx history for each wallet → check if deposit addresses overlap.
- Full ML-graph approach: 4/5 complexity.

### Privacy implications
Moderate. Requires reading transaction history (public). No PII involved. But clustering links pseudonymous wallets.

---

## 2. Wallet Age / Activity Scoring

### Key metrics and weights (industry consensus from Wormhole, Linea, Trusta, academic literature)

| Signal | Weight | Notes |
|--------|--------|-------|
| Wallet age | High | <30 days = likely Sybil; 90+ days preferred; >1 year = strong signal |
| Total tx count | High | <10 txs = suspicious; 30+ = baseline; 100+ = strong |
| Gas paid (lifetime) | Medium | Proxy for genuine cost-bearing activity |
| DeFi interactions | High | Lending, LP, swaps on reputable protocols |
| NFT history | Medium | Non-minting NFT history (receiving, trading) |
| Time of first gas receipt | High | Temporal clustering: all fresh wallets funded same day = coordinated |
| Cross-chain activity | Medium | Genuine users bridge; pure airdrop farmers often don't |
| POAP history | Medium | Gitcoin Passport counts these as stamps |
| ENS ownership | Medium | Cost barrier (>$5/yr) — genuine identity signal |
| Address abandonment rate | High | Sybil wallets are often abandoned after use |

### Scoring formula (Trusta MEDIA-style approach)
```
score = w1*(age_days/365) + w2*(log(tx_count)/5) + w3*(defi_protocols_used/10) + w4*(cross_chain_bool) + ...
normalized 0-100
Gate at: 20-30 for low-security, 50+ for high-security contexts
```

### Practical thresholds (from real protocols)
- Gitcoin Passport recommends score threshold of **20** (Unique Humanity Scorer) for access gating
- LayerZero required wallets to have "genuine historical usage" not just protocol-specific activity
- Wormhole weighted cumulative volume, usage timing, consistency of activity
- Academic finding: wallets with lifecycle <1 year + balance barely above airdrop minimum = Sybil indicator

### Implementation complexity: 2/5
- Fully implementable with free/cheap APIs: Etherscan (free), Alchemy, Helius (Solana), Dune Analytics
- Score computation is pure arithmetic once data is fetched

### Cost
- Etherscan API: free tier 5 calls/sec; $199/mo for 100K calls/day
- Alchemy: free tier available
- For Solana: Helius Enhanced TX API (free tier 100K credits/mo)

### False positive risk
- Legitimate new users with fresh wallets will score low → denied entry
- Mitigation: allow appeal + manual review; or accept 2 tiers (verified vs unverified)

---

## 3. Behavioral Graph Analysis

### How it works
Construct a directed graph where nodes = wallets, edges = fund transfers or shared interactions. Then apply community detection to find dense clusters (same owner).

**Four canonical Sybil graph patterns (TrustaLabs)**:
1. **Star-like divergence**: One source wallet funds many leaf wallets (fan-out from master)
2. **Star-like convergence**: Many wallets funnel funds to one sink wallet
3. **Chain-like**: Sequential fund hops (A→B→C→D→...) to obscure origin
4. **Tree-structured**: Hierarchical distribution from one root

**Advanced signals**:
- **Timing correlation**: All wallets execute same action within a short window (e.g., all approve the same contract within 5 minutes) → automation indicator
- **Nonce patterns**: Sequential nonces across wallets = automated batch deployment
- **Fee payer clustering**: Multiple "different" wallets share same fee payer address = provably one entity (relevant to Solana — from our own research)
- **Token approval correlation**: Wallets approving same contract at same time = coordinated

### Graph methods used in practice
- Community detection: Louvain algorithm (most common), Girvan-Newman
- Graph Neural Networks (GNN/GCN): EvAnGCN for temporal graphs
- LightGBM on subgraph features: Best accuracy per academic paper (F1 0.9303)
- Elliptic: "Automatic behavioral detection" — behavioral fingerprinting for fraud

### Implementation complexity: 4/5
- Requires graph database (Neo4j) or graph analytics library (NetworkX, GraphX)
- Need to ingest all transfer txs for registered wallets — API-intensive
- TrustaLabs offers this as a service via TrustScan API (outsource the complexity)

### Cost
- TrustScan API: pricing not public, but used by Gitcoin Passport at scale
- DIY: Neo4j (free community edition) + Python graph analysis

### Accuracy
- Combined graph mining + behavioral analysis (Trusta 2-phase): reduces false positives significantly vs graph mining alone
- Academic LightGBM subgraph model: Precision 0.9428, F1 0.9303

---

## 4. zkProof Identity Solutions

### 4a. World ID (Worldcoin)

**How it works**:
- Users scan iris at physical "Orb" device. Biometric hash stored (zero-knowledge). User receives World ID.
- Proof of uniqueness: no two irises produce same commitment. Nullifier system prevents double-registration.
- ZK proof: user generates proof that they're a verified human WITHOUT revealing which account.
- **Nullifier mechanism**: Each app+action combination produces a deterministic but unlinkable nullifier per user. Same person always generates same nullifier for same app/action → allows deduplication without exposing identity.
- **World ID 4.0** (2025): True one-time-use nullifiers enforced at protocol level.

**Smart contract integration**:
```solidity
IWorldID.verifyProof(
  root,           // current Merkle root
  groupId,        // 1 = Orb-verified only
  signalHash,     // keccak256(user's wallet address)
  nullifierHash,  // user's unique ID for this action
  externalNullifierHash, // keccak256(appId, actionId)
  proof           // ZK proof array [8]
)
```
Store nullifierHash after first verification. Reject if already used → enforces one-person-one-action.

**Supported chains**: Ethereum, World Chain, Optimism, Base, Polygon (with ~5-60 min delay via state bridge). Permissionless bridge for any EVM chain.

**Adoption**: 38+ million verified users (Feb 2026), 150+ mini apps, 120 countries. Developer program with $300K in incentives.

**Accuracy**: Near-perfect for preventing double-registration (cryptographic guarantee). False positive = zero (either your iris matches or it doesn't). False negative = people who can't/won't do iris scan (privacy concern, no Orb access).

**Implementation complexity: 2/5**
- Well-documented SDK (world-id-starter on GitHub, Foundry-based)
- One contract call + nullifier storage

**Cost**: Free for developers. No API fees. World ID verification is end-user action.

**Privacy tradeoffs**:
- Users must surrender iris scan to a centralized Orb device (Tools for Humanity operates it)
- Privacy concern: biometric data + iris hash stored centrally
- ZK ensures on-chain privacy (no one can link nullifiers across apps)
- Significant controversy around biometric surveillance, especially in Global South
- Regulatory issues: banned/restricted in UK (ICO), Germany, Kenya, France (data protection)

**Best for**: Maximum Sybil resistance with lowest friction post-enrollment. If your users are already World ID verified, this is the strongest 1-person-1-action guarantee.

---

### 4b. Human Passport (formerly Gitcoin Passport)

**How it works**:
- Users collect "Stamps" — verifiable credentials from web2 and web3 sources
- Each stamp has a weight; aggregate = Unique Humanity Score (0-100+)
- Stamps include: Google, GitHub, Discord, Twitter/X, ENS, Lens, Farcaster, BrightID, Proof of Humanity, NFT ownership, POAP, Coinbase, Binance, LinkedIn, etc.
- Score reflects "cost of forgery" — higher score = harder to fake across multiple platforms

**Key stamps and approximate weights**:
- ENS name ownership: ~7 points
- Google account: ~2.25 points
- GitHub (10+ repos or followers): ~2-3 points
- BrightID verification: ~0.5 points
- Coinbase verification: ~2.5 points
- Civic: ~3.7 points
- World ID (Orb): available as stamp

**API integration**:
```
GET https://api.passport.xyz/v2/stamps/{scorer_id}/score/{address}
Headers: X-API-KEY: <your_key>
Response: { score: 32.5, passing_score: true, ... }
```

**Recommended threshold**: 20 (for standard Sybil resistance). Customizable.

**Adoption**: 2M+ users with passports. Free API access.

**Implementation complexity: 1/5** — simplest integration of all methods listed.

**Cost**: Free API. Stamps themselves are free for users (some stamps have costs, e.g., ENS).

**Accuracy**: Moderate. Score of 20+ means user has verified identity across multiple platforms — hard to fake at scale. But determined attackers can buy aged accounts or use social engineering. Not cryptographically guaranteed like World ID.

**Privacy**: Good. Stamps are verified credentials; no biometric data. User controls which stamps to share.

**Real-world use**: Gitcoin Grants (original use case), 1inch, Snapshot governance, Base ecosystem apps.

---

### 4c. Proof of Humanity (PoH v2)

**How it works**:
- Users submit video selfie + ETH deposit as a registration request
- Community members vouch for authenticity; disputes resolved via Kleros arbitration
- On-chain registry of verified humans on Gnosis Chain (v2)
- Soulbound IDs: non-transferable on-chain identity

**Current state (2025)**:
- v2 deployed on Gnosis Chain (lower fees than mainnet)
- Multi-chain expansion in progress
- Circles V2 integration planned (May 2025)
- New Keeper Bot automates vouching/rewards
- Ongoing development: WalletConnect → Reown migration, privacy features

**Controversy**:
- v1 had governance split (POH DAO vs Kleros) → forked into two registries
- Manual vouching = human review bottleneck
- Video selfies can theoretically be deepfaked (AI-generated faces)
- Smaller registered user base vs World ID

**Implementation complexity: 3/5**
- Requires checking on-chain registry
- Cross-chain lookup if your contract isn't on Gnosis Chain

**Cost**: Users pay ~$10-50 in gas/deposit (varies). Free for developers to query.

**Accuracy**: High for genuine users (social vouching layer). Vulnerable to deepfake attacks with advancing AI. Registry can be queried for registered status.

**Best for**: Projects that want human verification without biometrics. More decentralized than World ID.

---

### 4d. BrightID

**How it works**:
- Social graph-based proof of uniqueness — no biometrics, no documents
- Users connect with real-world contacts in the BrightID mobile app
- Graph analysis algorithms (SybilRank, Aura) determine if a user is unique
- Verification levels: "Just Met," "Already Knows," "Recovery" — higher level = stronger signal

**Current state (2025)**:
- Active development through Dec 2025 (confirmed GitHub activity)
- Uses IDChain (Ethereum-based) for graph synchronization
- Open-source analysis tools available
- Integrated into Gitcoin Passport as a stamp

**Adoption**: Lower than World ID/Passport. More niche, popular in certain communities (Gitcoin grants, some DAOs).

**Implementation complexity: 3/5**
- Requires BrightID API calls to verify a user's status
- Users need to install mobile app + attend "connection parties"

**Cost**: Free API. Users pay sponsorship (small ETH amount per verification).

**Accuracy**: Dependent on network density. Sparse networks = easier to Sybil. Dense networks = strong resistance. Verification spoofable if attacker has real social connections.

**Privacy**: Strong — no biometrics, no documents. Purely social.

**Best for**: Privacy-maximal communities. Less scalable than World ID for global investment platforms.

---

### 4e. Self Protocol (zk Passport / formerly OpenPassport)

**How it works**:
- Users scan NFC chip in government-issued passport or ID card (or Aadhaar) using mobile app
- Generates ZK-SNARK proof from passport data — proves validity without revealing document contents
- Selective disclosure: prove "I am over 18" or "I am not from OFAC-sanctioned country" without revealing name/passport number

**Recent developments (2025)**:
- $9M seed round (Greenfield Capital, SoftBank)
- Google Cloud Testnet Faucet uses Self for Sybil resistance
- Aave and Velodrome integrations live
- Aadhaar support added (India — 99% of adult population covered)
- EU Biometric ID card support

**Implementation complexity: 2/5**
- SDK available (docs.self.xyz)
- On-chain verifier contract + nullifier pattern (similar to World ID)

**Cost**: Free for developers (as of 2025). Users need a supported government ID.

**Accuracy**: Cryptographic — if a passport is valid and not duplicated, proof is sound. One passport = one nullifier = one allowed registration. Highly accurate.

**Privacy**: Strong — ZK proofs, no raw document data on-chain. Selective disclosure.

**Best for**: Investment platforms that need KYC-adjacent verification without storing PII. Especially strong in India (Aadhaar) and EU (biometric ID cards). OFAC screening built in.

---

### 4f. Anon Aadhaar

**How it works**:
- ZK protocol proving Aadhaar ownership (India's national ID, 1.4B+ issued)
- Generates ZK proof from Aadhaar QR code without revealing name/ID number
- Nullifier: can prove "same person" without revealing who

**Real use cases**: ETHIndia 2024 judging (Sybil-resistant voting), various DeFi applications.

**Coverage**: India-only. 1.4B IDs = 99%+ of India's adult population.

**Implementation complexity: 2/5**
- Open source: github.com/anon-aadhaar/anon-aadhaar
- PSE (Privacy & Scaling Explorations) backed

**Best for**: India-focused platforms or platforms with large Indian user base.

---

## 5. Per-Wallet Investment Caps — Smart Contract Enforcement

### The fundamental problem
Any per-wallet cap is trivially bypassed by creating new wallets unless identity is verified externally. The cap must be per-person, not per-address.

### Implementation patterns

**Pattern 1: Allowlist + off-chain KYC**
```solidity
mapping(address => bool) public allowlisted;
mapping(address => uint256) public invested;
uint256 public constant MAX_PER_WALLET = <amount>;

function invest(uint256 amount) external {
    require(allowlisted[msg.sender], "Not allowlisted");
    require(invested[msg.sender] + amount <= MAX_PER_WALLET, "Cap exceeded");
    invested[msg.sender] += amount;
    // ... transfer logic
}
```
Admin (multisig) controls the allowlist. Off-chain Sybil detection gates allowlist entry.

**Pattern 2: World ID nullifier + cap**
```solidity
mapping(uint256 => bool) public nullifierUsed;
mapping(uint256 => uint256) public nullifierInvested;

function invest(
    uint256 root, uint256 nullifierHash, uint256[8] calldata proof,
    uint256 amount
) external {
    worldId.verifyProof(root, 1, abi.encodePacked(msg.sender), nullifierHash, externalNullifier, proof);
    require(nullifierInvested[nullifierHash] + amount <= MAX_PER_PERSON, "Cap exceeded");
    nullifierInvested[nullifierHash] += amount;
}
```
Now cap is enforced per biometric person, not per address. Multiple wallets = same nullifier → same cap bucket.

**Pattern 3: Multi-wallet allowance via verified identity**
Goal: allow person to register up to 3 wallets, all sharing one cap pool.
```solidity
mapping(uint256 => address[]) public nullifierToWallets; // person → their wallets
mapping(address => uint256) public walletToNullifier;   // wallet → person ID
uint256 public constant MAX_WALLETS_PER_PERSON = 3;

function registerWallet(uint256 nullifierHash, ...) external {
    // verify World ID proof for msg.sender
    require(nullifierToWallets[nullifierHash].length < MAX_WALLETS_PER_PERSON, "Max wallets reached");
    nullifierToWallets[nullifierHash].push(msg.sender);
    walletToNullifier[msg.sender] = nullifierHash;
}
```

**Pattern 4: Gnosis Safe / multisig allowlist contract**
- Use a Gnosis Safe as the allowlist admin
- Requires M-of-N signatures to add new wallets → human review layer
- Good for high-value investment platforms where friction is acceptable

### Adidas NFT drop lesson (cautionary)
Adidas limited to 2 NFTs/wallet. Attacker bought 330 in one transaction via contract. Lesson: also need `require(msg.sender == tx.origin)` to block contract-based batch minting, or use per-block rate limits.

### Implementation complexity: 2-3/5
- Pattern 1 (allowlist only): 1/5
- Pattern 2 (World ID integration): 3/5
- Pattern 3 (multi-wallet pool): 3/5

---

## 6. Hybrid Approach — Confidence Score Architecture

### Recommended architecture for "max 3 wallets per person" investment platform

**Phase 1: Passive on-chain scoring** (runs at registration)
```
score = 0
+ wallet_age_score (0-25 pts): age_days mapped to 0-25, capped at 365 days
+ activity_score (0-25 pts): log(tx_count) * defi_interactions
+ clustering_check (0 or -100): if deposit address matches another registered wallet → flag as same person
+ gas_paid_score (0-15 pts): log(lifetime_gas_eth)
+ cross_chain_score (0-10 pts): bridged at least once
+ ens_score (0-10 pts): owns ENS name
+ nft_score (0-5 pts): non-minting NFT history
```
Gate: score < 20 → auto-reject (likely bot or fresh wallet)
Score 20-50 → require Passport verification
Score 50+ → allow directly (low Sybil risk)

**Phase 2: Identity attestation** (for score 20-50 range)
- Gitcoin/Human Passport: score >= 20 → allow (free, 1/5 complexity)
- OR Self Protocol: valid passport proof → allow (2/5 complexity, much stronger)
- OR World ID: orb-verified → allow (2/5 complexity, strongest)

**Phase 3: Behavioral monitoring** (ongoing)
- Check if newly registered wallets share funding sources with existing registered wallets (deposit address clustering)
- If detected: merge their investment caps (they become the same person)
- If same nullifier detected: automatically link wallets

**Phase 4: Per-person cap enforcement**
- On-chain: use Pattern 3 smart contract with nullifier-based pooled caps
- If World ID or Self Protocol is used, the nullifier IS the person identifier
- If Passport is used, the address IS the identifier (passport is per-address, not biometric)

### Confidence score bands
| Score | Action |
|-------|--------|
| 0-20 | Reject — bot/fresh wallet |
| 20-40 | Require Passport ≥20 OR Self Protocol proof |
| 40-65 | Allow with monitoring, clustering check |
| 65+ | Full allowance |

### Hybrid approach accuracy
- Academic result: ML hybrid reduced Sybil attack attempts by 97.4%
- Nansen-style clustering + activity scoring = caught 39.85% of Linea wallets as Sybil
- World ID alone: cryptographically sound for 1-person-1-action (but only 38M users globally)

---

## 7. Real-World Protocol Examples

| Protocol | Method | Result |
|----------|--------|--------|
| **Linea airdrop** | Nansen AI clustering + activity analysis | 39.85% of 1.3M wallets removed as Sybil |
| **LayerZero airdrop** | Nansen + Chaos Labs, ML training on 100K wallets | 60,995-wallet cluster found; 10M ZRO reclaimed |
| **Gitcoin Grants** | Passport scores, quadratic funding protection | 2M+ users protected |
| **Wormhole airdrop** | Volume weighting + timing + consistency | Organic users rewarded |
| **Arbitrum airdrop** | Nansen multi-criteria scoring | Graduated reward tiers |
| **Google Cloud Faucet** | Self Protocol ZK passport | Bot drain eliminated |
| **ETHIndia 2024 judging** | Anon Aadhaar | Sybil-resistant voting |
| **Aave** | Self Protocol | OFAC screening + Sybil resistance |

---

## Implementation Recommendation for the Platform

### Minimum viable (2-3 weeks, low cost)
1. Wallet age gate: reject wallets < 30 days old
2. Activity score: require ≥ 10 txs lifetime
3. Deposit address clustering: flag shared CEX deposit addresses across registered wallets → merge caps
4. Gitcoin/Human Passport: score ≥ 20 required for borderline wallets
5. Smart contract: allowlist pattern + per-person cap tracking via address

### Strong (4-6 weeks, medium cost)
All of above plus:
6. Self Protocol or World ID integration for strong 1-person-1-action enforcement
7. Full activity score (7-10 signals)
8. TrustScan API integration for graph-based cluster detection
9. Nullifier-based smart contract for cap pooling across wallet registrations

### Maximum (8-12 weeks, enterprise)
All of above plus:
10. Full graph analysis pipeline (Neo4j + custom community detection)
11. Behavioral monitoring (timing correlation, nonce patterns)
12. ML model trained on platform's own data after 3-6 months of operation
13. Chainalysis or TRM Labs API for entity labels on high-value wallets

---

## Sources
- Nansen Linea Sybil Detection: https://research.nansen.ai/articles/linea-airdrop-sybil-detection
- World ID Docs: https://docs.world.org/world-id/reference/contracts
- Human Passport API: https://docs.passport.xyz/building-with-passport/passport-api/quick-start-guide
- TrustaLabs TrustScan: https://trustalabs.gitbook.io/trustscan
- Academic Sybil Detection (arXiv 2505.09313): https://arxiv.org/html/2505.09313v1
- Self Protocol: https://docs.self.xyz + https://self.xyz
- Anon Aadhaar: https://github.com/anon-aadhaar/anon-aadhaar
- Proof of Humanity v2: https://docs.kleros.io/products/proof-of-humanity
- BrightID: https://brightid.gitbook.io/brightid
- Address Clustering Heuristics for Ethereum: https://www.ifca.ai/fc20/preproceedings/31.pdf
- LayerZero Sybil addressing: https://medium.com/layerzero-official/addressing-sybil-activity-a2f92218ddd3
