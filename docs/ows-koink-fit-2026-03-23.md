# OpenWallet Standard — Koink Fit Assessment
**Date: 2026-03-23 | Status: Completed**

---

## TL;DR

OWS is a **strong fit for Otto's agent-side wallet operations** on Koink: fair launch automation, treasury signing, and cross-chain deployment coordination. It is **not a replacement** for user-facing wallet UX (MetaMask/Phantom/WalletConnect). Adoption model: OWS for the agent layer, standard browser wallet protocols for users, Gnosis Safe for the DAO treasury.

---

## Koink's Wallet Interaction Flows

Five core flows identified from the roadmap:

| Flow | What It Needs |
|---|---|
| **Fair Launch** | Sign deployment + launch txs; enforce no-sniper guarantees |
| **Treasury Distribution** | Sign 20% auto-split at every tx; enforced cap |
| **DHM Tracking** | On-chain hold duration accumulation; governance weight reads |
| **Adapter Deployment** | Deploy KoinkAdapter to new chains; manage cross-chain accounts |
| **User Wallet** | Connect MetaMask/Phantom; sign user-initiated governance/swap txs |

---

## OWS Fit Per Flow

### 1. Fair Launch Automation ✅ HIGH FIT

The Quantum Koinkulator is Otto-orchestrated. OWS's agent credential model maps perfectly:
- Otto gets `ows_key_<token>` with a policy: `"can_sign": ["deploy", "launch"], "max_value_eth": 0.1, "require_vrf_seed": true`
- Policy engine enforces these pre-signing — no raw key exposure to the orchestration layer
- CAIP-2 addressing unifies the `deploy()` call across EVM chains without custom address serializers

**What OWS replaces:** custom key management code for the deployment agent. Eliminates ~300-500 lines of bespoke vault/signing logic.

**What it doesn't replace:** Chainlink VRF subscription management, ABI encoding, constructor argument preparation. Hardhat/Anchor tooling still required for contract compilation and deployment.

---

### 2. Treasury Distribution Signing ✅ GOOD FIT (with caveat)

`distributeToTreasury()` = periodic policy-gated signing. OWS supports:
- Spending limits per signing session
- Address whitelisting (only sign to known treasury contract address)
- Rate limiting (N signs per hour)

**Caveat:** KoinkTreasury.sol requires multi-sig governance (DAO with N keyholders). OWS is single-wallet oriented. For the treasury multi-sig, use **Gnosis Safe** as the outer layer, with OWS-backed Otto as one signer. OWS handles Otto's key; Gnosis Safe handles the quorum.

---

### 3. DHM On-Chain Tracking ❌ OWS NOT APPLICABLE

The Diamond Hands Multiplier lives in `DiamondHandsVault.sol` — on-chain state, not a signing concern. OWS is a local signing layer. No overlap here. DHM tracking is purely smart contract logic + subgraph indexing.

---

### 4. Cross-Chain Adapter Deployment ✅ STRONG FIT

This is where OWS delivers the most architectural value for Koink. The chain-agnostic adapter pattern needs:
- One wallet identity per supported chain
- Consistent address derivation (no custom HD paths per chain)
- CAIP-10 account descriptors for the adapter registry

OWS's `WalletDescriptor` with CAIP-10 accounts is exactly this. Koink's adapter registry can consume OWS wallet descriptors natively.

**Supported Koink chains via OWS (out of box):**

| Koink Target | OWS Support | Status |
|---|---|---|
| Ethereum + all EVM L2s | ✅ secp256k1, m/44'/60' | Direct |
| Solana | ✅ Ed25519, m/44'/501' | Direct |
| Cosmos | ✅ secp256k1, m/44'/118' | Direct |
| TON | ✅ Ed25519, m/44'/607' | Direct |
| Bitcoin (for Spark L2 treasury) | ✅ secp256k1, m/84'/0' | Direct |
| NEAR | ❌ Not in OWS 9 chains | Custom adapter required |
| Tron | ✅ secp256k1, m/44'/195' | Direct (bonus) |

**NEAR gap:** OWS has an extension mechanism (provide CAIP-2 namespace + derivation path + address encoding). NEAR uses Ed25519 with `m/44'/397'/0'`. This can be added as an OWS community extension — it's not a blocker.

---

### 5. User Wallet Connections ❌ WRONG TOOL

Koink.fun's web platform needs browser wallet connections: MetaMask, Phantom, WalletConnect, Coinbase Wallet. OWS is a **server-side / agent-side** local vault — it does not implement EIP-1193 (Ethereum provider) or the Solana Wallet Standard.

Use the correct standards for user wallets:
- **EVM:** EIP-1193 (MetaMask, WalletConnect v2, Coinbase SDK)
- **Solana:** @solana/wallet-adapter (Wallet Standard)
- **Cross-chain UX:** wagmi + viem for EVM, @solana/wallet-adapter for Solana

OWS should never appear in the Koink.fun frontend bundle.

---

## Interoperability Gains

1. **Unified CAIP-10 account model** — Otto's chain-agnostic deployment agent uses one discovery call to enumerate all its wallets across chains. The adapter registry can be seeded from `ows.discoverWallets({ chainType: "*" })` at startup.

2. **Policy-enforced agent autonomy** — Heartbeat-triggered deployments (e.g., spinning up a new Koink fork on Base) can run autonomously with pre-signed policies bounding Otto's signing authority. No need for Mev approval on routine deployments once the policy is set.

3. **Key revocation = file delete** — If the deployment agent key is ever compromised, `rm ~/.ows/keys/koink-deploy.key` revokes access instantly. No on-chain key rotation needed at the agent layer.

4. **Auditability** — OWS key metadata includes creation timestamp, usage count, policy attachments. Contributes to the integrity preservation requirement (SOS Systems alignment).

---

## Architecture Recommendation

```
Koink.fun Web Platform
├── User actions (vote, swap, launch)
│   └── EIP-1193 / Wallet Standard (MetaMask / Phantom)
│       └── On-chain contracts
│
└── Agent actions (deploy, distribute, automate)
    └── OWS vault (Otto's agent key, policy-gated)
        └── Signing → tx broadcast → on-chain
            ↓
    Gnosis Safe (treasury multi-sig)
    ├── OWS-backed Otto (1 signer)
    └── Mev + community signers (remaining quorum)
```

---

## Implementation Order

1. **Phase 0:** Create OWS wallet for deployment agent. Derive EVM + Solana + Cosmos wallets. Store `WalletDescriptor` outputs in adapter registry schema.
2. **Phase 1 (EVM launch):** Attach OWS signing to KoinkLauncher deployment flow. Set policy: whitelist-only addresses, max ETH value cap, VRF prerequisite flag.
3. **Phase 2 (non-EVM):** Add NEAR as OWS extension (Ed25519, CAIP-2 namespace `near`). Reuse same vault; new derivation path entry.
4. **Phase 3 (fork tooling):** Fork page generates a fresh OWS wallet for each fork deployer's agent. Unified UX regardless of target chain.

---

## Chain-Specific Edge Cases OWS Doesn't Cover

| Edge Case | Chain | Mitigation |
|---|---|---|
| Solana tx fee payer separation | Solana | Custom fee-payer account logic outside OWS |
| Cosmos IBC routing | Cosmos | IBC packet construction is chain-specific; OWS only signs the outer tx |
| TON cell serialization | TON | TON's BOC format needs custom serializer before OWS signs |
| NEAR implicit accounts | NEAR | NEAR account model (human-readable IDs) differs from address model; custom encoder needed |
| EVM L2 gas oracle variance | Arbitrum/Base/Optimism | Gas estimation per-L2 still custom; OWS doesn't abstract this |
| Bitcoin UTXO selection | Spark L2 | UTXO selection algorithm still custom; OWS signs the assembled tx |

---

## Summary Decision

**Adopt OWS as the agent-side key management layer for Koink's chain-agnostic infrastructure.**

- Replaces: custom vault + key management (~500 lines), custom CAIP-10 serialization, per-chain address encoders
- Does not replace: Hardhat/Anchor tooling, VRF integration, smart contract logic, user wallet UX
- Risk: OWS is v1.0 and relatively new — pin to a specific release, audit the library before mainnet use
