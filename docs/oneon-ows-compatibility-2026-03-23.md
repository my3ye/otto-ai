# ONEON × OpenWallet Standard — Compatibility Analysis
*Architect assessment — 2026-03-23*

---

## Design: ONEON + OWS Integration

### Problem

ONEON's sovereign identity layer needs:
1. Cryptographic key management across EVM + future chains
2. Three-tier identity architecture (custodial → self-sovereign → sovereign)
3. DID + Verifiable Credentials (W3C standards)
4. A "Memory Capsule" — encrypted, on-chain identity record
5. AI agent participation in governance and task attribution

OWS provides some of this. The question is which pieces to adopt, which to build, and where the seams go.

---

## Compatibility Matrix

| ONEON Requirement | OWS Coverage | Verdict | Notes |
|---|---|---|---|
| **Key management (all levels)** | Vault passphrase + agent tokens + BIP-44 derivation | ✅ Full fit | Use OWS vault as signing core |
| **Multi-chain account management** | 9 chains, CAIP-2/CAIP-10 addressed | ✅ Full fit | EVM + Solana + Cosmos already covered |
| **AI agent scoped signing** | Policy engine + API token as cryptographic capability | ✅ Full fit | Otto/SOS agents = OWS agent tokens |
| **Custodial tier (Level 1)** | Agent API tokens with policies | ⚠️ Partial | No UX / account abstraction layer — must build |
| **Self-sovereign DID (Level 2)** | No DID support | ❌ Gap | Build `did:oneon` on OWS-derived key material |
| **Verifiable Credentials** | No VC stack | ❌ Gap | Implement W3C VC-DATA-MODEL above OWS |
| **On-chain identity registry** | Local-only vault, no on-chain binding | ❌ Gap | EVM L2 registry contract: DID → CAIP-10 |
| **Memory Capsule (on-chain record)** | No encrypted distributed store | ❌ Gap | IPFS/Arweave blob, keys from OWS vault |
| **Mesh communications** | Out of scope | ❌ Different layer | libp2p / Waku — separate stack entirely |
| **Social / guardian recovery** | BIP-39 mnemonic only | ⚠️ Partial | Extend with Shamir secret sharing |
| **Revocation registry** | Local key-file deletion | ⚠️ Partial | On-chain revocation contract needed |
| **Cross-ecosystem identity recognition** | No federation | ❌ Gap | DID resolver + federation protocol |

**Summary**: OWS covers the bottom of the stack cleanly — keys, signing, multi-chain, and agent delegation. Everything above that (DID, VC, on-chain registry, Memory Capsule) is ONEON's responsibility to build.

---

## Architecture: Where OWS Sits in ONEON's Stack

```
ONEON Identity Stack
══════════════════════════════════════════════════════════════
Level 3: SOVEREIGN
  - did:oneon DID + on-chain registry (EVM L2)
  - Memory Capsule (IPFS/Arweave, encrypted, OWS-keyed)
  - VC issuance + selective disclosure (W3C VC-DATA-MODEL)
  - Social recovery (Shamir, guardian rotation)
──────────────────────────────────────────────────────────────
Level 2: SELF-SOVEREIGN
  - did:key derived from OWS BIP-44 secp256k1/Ed25519 key
  - VC wallet (presentation proofs, ZK disclosure)
  - Key rotation via on-chain update tx (OWS signs)
──────────────────────────────────────────────────────────────
Level 1: CUSTODIAL
  - Platform-managed OWS vault (agent token issued to user)
  - Policy engine: spend limits, chain allowlists
  - Account abstraction UI layer (familiar login experience)
══════════════════════════════════════════════════════════════
Cross-cutting (all levels):
  ◆ OWS Vault — key storage + in-process signing
  ◆ OWS CAIP-2/10 — multi-chain address management
  ◆ OWS Policy Engine — delegation + spend control
  ◆ OWS Agent Tokens — Otto/SOS agent participation
══════════════════════════════════════════════════════════════
Separate layer (not OWS):
  ◇ Mesh comms — libp2p/Waku, routes around censorship
  ◇ Governance — 505 DAO contracts, voting weight from VC
```

---

## Key Decisions

**Decision 1: OWS as signing core, not identity core**
- **Chosen**: OWS handles keys + signing only. Identity (DID/VC) is built above it.
- **Why**: OWS has no DID or VC support. Trying to make it carry identity semantics would mean forking the spec or hacking around it. Thin adapter = clean seam.
- **Alternative rejected**: Build a custom signing layer. Rejected because OWS gives us 9 chains + policy engine + agent tokens for free — that's months of work.

**Decision 2: derive `did:oneon` from OWS key material directly**
- **Chosen**: `did:oneon:<CAIP-2-chain>:<base58-pub-key>` — derive from the OWS secp256k1 or Ed25519 key via BIP-44.
- **Why**: Key material is DID-compatible (secp256k1 = did:key compatible, Ed25519 = did:key compatible). No curve conversion. One vault, two representations.
- **Alternative rejected**: Separate key for DID vs. wallet. Rejected — key proliferation, harder UX, harder to bind identity to onchain activity.

**Decision 3: OWS vault location for ONEON levels**
- **Level 3 (sovereign)**: user runs OWS vault locally, holds passphrase. Full autonomy.
- **Level 2 (self-sovereign)**: user holds passphrase, vault can be cloud-backed (E2EE).
- **Level 1 (custodial)**: ONEON platform manages the vault, issues agent tokens to user.
- **Why**: OWS was designed local-first. Custodial layer wraps it server-side with standard web auth, issuing agent tokens. Self-sovereign/sovereign users eventually export their vault.

**Decision 4: Conform to OWS interfaces fully — don't fork**
- **Chosen**: Implement the OWS SDK as a dependency. Never modify OWS internals.
- **Why**: OWS is MIT-licensed and externally maintained. The extension surface (new chains via CAIP-2, new policy types) is well-defined. Staying on-spec means we get upstream improvements.
- **Risk**: OWS is early-stage. Mitigation: thin adapter module between OWS and ONEON's DID layer so we can swap the signing core if needed.

---

## Interfaces ONEON Should Implement

### From OWS (adopt directly)
```
ows.createVault(passphrase)              → Level 1 platform vault, Level 3 user vault
ows.issueAgentToken(walletId, policies)  → Level 1 user tokens, Otto/SOS agent tokens
ows.sign(agentToken, tx)                 → All signing (governance, task attribution, VC issuance)
ows.discoverWallets(chainId)             → Cross-chain account management
ows.revokeAgentToken(tokenId)            → Delegation revocation
```

### ONEON Extensions (build above OWS)

```
oneon.createDID(owsVault, chainId)       → derives did:oneon from OWS key
oneon.resolveDID(did)                    → on-chain registry lookup
oneon.issueVC(issuerVault, subject, claims) → sign VC with OWS vault
oneon.verifyVC(vc, trustedIssuers)       → verify VC signature
oneon.sealMemoryCapsule(vault, data)     → encrypt + pin to IPFS/Arweave
oneon.openMemoryCapsule(vault, cid)      → decrypt using OWS-derived key
oneon.registerIdentity(chainId, did, address) → on-chain registry tx (signed via OWS)
oneon.rotateKey(vault, newKey)           → on-chain update + new DID fragment
```

---

## Gaps Requiring Extensions

| Gap | Severity | Estimated Effort | Approach |
|---|---|---|---|
| DID namespace + registry | Critical | 2-3 weeks | EVM L2 contract + did:oneon resolver |
| W3C VC issuance + verification | Critical | 2-3 weeks | veramo.io or custom per W3C spec |
| Memory Capsule store | High | 3-4 weeks | IPFS/Arweave + OWS-keyed AES-256 |
| Custodial UX layer | High | 2-3 weeks | Platform wraps OWS vault, issues tokens |
| Social recovery (Shamir) | Medium | 1-2 weeks | Shamir lib + guardian rotation flow |
| On-chain revocation registry | Medium | 1 week | Simple EVM mapping (DID → revoked) |
| DID federation / resolution | Low (Phase 2) | 2 weeks | Universal resolver + did:web bridge |

---

## Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| OWS spec is unstable / breaking changes | Medium | Thin adapter module. Never call OWS directly from DID layer — always go through `oneon.sign()` wrapper. |
| Local-first vault incompatible with web users | High | Level 1 custodial wraps the vault server-side. Web users get agent tokens; node operators get full vault. |
| Key recovery failure = permanent identity loss | High | Social recovery mandatory for Level 2+. Shamir (3-of-5) before sovereign level is reachable. |
| Agent token leakage → compromised identity | Medium | OWS token shown once, SHA-256 hash stored. Add ONEON policy: token TTL + scope restriction. |
| DID-OWS key binding broken by key rotation | Low | Bind DID to on-chain registry (not just key material). Key rotation = on-chain tx, DID resolves to new key. |

---

## Implementation Plan

### Phase 1 — OWS as signing core (2-3 weeks, ~$8K)
1. Install OWS SDK (`@open-wallet-standard/core`) in ONEON backend
2. Implement `oneon.sign()` wrapper — thin adapter, all signing routes through here
3. Level 1 custodial: platform vault manager, issue agent tokens on registration
4. Otto + SOS agent tokens: issue scoped tokens for governance + task attribution signing

### Phase 2 — DID + VC layer (3-4 weeks, ~$12K)
5. Deploy `ONEONIdentityRegistry.sol` on EVM L2 (Optimism/Base)
6. Implement `did:oneon` resolver — derives from OWS secp256k1 key, registers on-chain
7. Integrate W3C VC-DATA-MODEL (veramo.io recommended — handles key management abstraction well)
8. Level 2 self-sovereign: user exports vault passphrase, claims DID ownership

### Phase 3 — Memory Capsule + sovereign level (4-6 weeks, ~$20K)
9. Memory Capsule: IPFS/Arweave storage + OWS-derived AES-256 encryption
10. Social recovery: Shamir 3-of-5 guardian rotation
11. On-chain revocation registry
12. Level 3 sovereign: user runs OWS vault locally, full autonomy
13. Selective disclosure (ZK or simple VC presentation proofs)

---

## Recommended Integration Path (Summary)

**Start with Phase 1. It's low risk, high payoff, and directly serves current needs (Otto agent signing, governance attribution, Level 1 custodial for early users).**

OWS handles the "boring but critical" substrate — encrypted keys, multi-chain signing, policy-gated delegation. ONEON's real innovation is above that: the three-level identity architecture, the Memory Capsule, and the mesh backbone. Use OWS as infrastructure, not identity. Build identity on top.

The `oneon.sign()` adapter is the key seam. If OWS ever becomes untenable (spec breaks, project abandoned), the adapter gets swapped out without touching the DID/VC layer above it.

---

*Output stored at: ~/otto/docs/oneon-ows-compatibility-2026-03-23.md*
