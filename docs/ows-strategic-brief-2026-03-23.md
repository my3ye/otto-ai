# OpenWallet Standard — Strategic Adoption Brief
**Date:** 2026-03-23
**For:** Mev
**Status:** Decision-ready

---

## The One-Line Answer

**Adopt OWS as signing infrastructure. Build identity, credentials, and UX above it. Never deep-couple.**

---

## What OWS Is (and Isn't)

OWS is an MIT-licensed, local-first, policy-gated signing vault. It handles keys, multi-chain accounts, and agent delegation.

It does **not** handle: DID documents, Verifiable Credentials, user wallet UX (MetaMask/Phantom), on-chain identity registries, or app-layer business logic.

The risk: OWS is early-stage (v1.0, small community). The mitigation: a thin adapter layer (`oneon.sign()`, `koink.sign()`) that wraps every OWS call. If OWS stalls or forks, we swap the adapter without touching anything above it.

---

## Build vs. Conform — Where Each Stands

| Layer | Decision | Rationale |
|---|---|---|
| Key vault + BIP-44 derivation | **Conform to OWS** | Solved, battle-tested, MIT. Rebuilding this is pure waste. |
| CAIP-2/CAIP-10 multi-chain addressing | **Conform to OWS** | 9 chains covered. NEAR is the only gap — addable as an Ed25519 community extension. |
| Agent signing delegation (Otto, SOS agents) | **Conform to OWS** | Scoped API keys + pre-signing policy engine is exactly what we need for bounded agent autonomy. |
| DID documents (`did:oneon`) | **Build above OWS** | Derived from OWS BIP-44 key material — one vault, two representations. No separate DID key needed. |
| Verifiable Credentials (ONEON Level 2) | **Build above OWS** | Use veramo.io as VC layer. OWS signs; veramo packages. |
| On-chain identity registry | **Build above OWS** | `ONEONIdentityRegistry.sol` on EVM L2. OWS signs the tx. |
| Memory Capsule (ONEON Level 3) | **Build above OWS** | IPFS content + OWS key for encryption. |
| User-facing wallet UX | **Don't use OWS at all** | Use EIP-1193 (MetaMask/Phantom) for users. OWS is agent-side only. |
| Koink fair launch agents | **Conform to OWS** | Replaces ~500 lines of custom vault/key management. Policy enforcement gates autonomous deployments. |
| Treasury multi-sig | **OWS + Gnosis Safe** | Otto is 1 OWS-backed signer. Mev + community hold quorum. |

**Rule of thumb:** Otto/agent-side = OWS. User-side = EIP-1193/Wallet Standard. Everything above keys = build.

---

## Sovereign / Non-Proprietary Alignment

OWS scores well against MY3YE's sovereignty principles:

- **MIT licensed** — no vendor lock-in, fork-safe
- **Local-first vault** — keys never leave the device/server; no custodial dependency
- **Policy at signing time** — agent autonomy is bounded, not unbounded (critical for SOS + fair launch integrity)
- **Open spec** — community can extend (e.g., NEAR namespace) without permission

**The one tension:** OWS is local-first but ONEON's Level 1 (custodial) users can't run local vaults. Mitigation: wrap OWS server-side for Level 1, with an explicit upgrade path to Level 2 self-custody. This is a design choice we make, not a constraint OWS imposes.

---

## Ecosystem Interoperability Wins

1. **Cross-chain with one key derivation path** — BIP-44 + CAIP-10 means one OWS vault signs on EVM, Solana, Cosmos, Bitcoin, TON, Tron, Sui, Spark, Filecoin. Koink's chain-agnostic architecture and ONEON's multi-chain identity both benefit without separate key management per chain.

2. **Agent delegation across the MY3YE stack** — Otto, SOS agents, and future autonomous components all get scoped signing tokens from one OWS vault. Policy rules (address whitelist, value limits, time windows) enforce what each agent can sign autonomously.

3. **`did:oneon` derived from OWS keys** — ONEON identity is cryptographically anchored to OWS key material. One user identity works across all MY3YE products without a separate identity keypair.

4. **Polkadot / W3F grant alignment** — The W3F Level 1 ONEON People Chain identity grant is strengthened by implementing OWS as the signing layer. It demonstrates interoperability standards adoption, which W3F explicitly favors.

5. **Koink treasury integrity** — Policy-gated treasury signing means fair launches and distribution operations run autonomously without Mev bottleneck, while governance still holds quorum for large moves.

---

## Phased Adoption Roadmap

### Phase 0 — Adapter First (no OWS yet, 1 week, $0)
Define the `sign()` adapter interface for both ONEON and Koink. Write it as an abstract contract. This is the insurance policy that makes everything else reversible.

```
interface WalletAdapter {
  sign(chain, payload, policy) → signature
  getAddress(chain, accountIndex) → address
  delegateAgent(agentId, policyRules) → scopedToken
}
```

**Why first:** Takes a week, costs nothing, and means every downstream task builds against the interface, not OWS directly.

### Phase 1 — OWS Core for Agents (3 weeks, ~$8K)
- Deploy OWS signing vault server-side (otto-machine + Koink infra)
- Implement the `WalletAdapter` against OWS
- ONEON: custodial Level 1 wrapping OWS
- ONEON: agent delegation tokens (Otto, SOS agents)
- Koink: fair launch deployment agent signs via OWS
- NEAR extension implementation (only gap in chain coverage)

**Milestone:** Otto can autonomously deploy Koink contracts on all 9 target chains. ONEON users can onboard at Level 1.

### Phase 2 — ONEON Identity Layer (4 weeks, ~$12K)
- `did:oneon` method derived from OWS BIP-44 keys
- `ONEONIdentityRegistry.sol` on EVM L2 (Optimism or Base)
- W3C Verifiable Credentials via veramo.io
- ONEON Level 2 self-custody (user controls their OWS vault)

**Milestone:** W3F Level 1 grant deliverables complete. ONEON identity is self-sovereign and interoperable.

### Phase 3 — Full Sovereignty (6 weeks, ~$20K)
- Memory Capsule (encrypted IPFS + OWS keys)
- Shamir social recovery
- ONEON Level 3 sovereign tier
- Koink treasury multi-sig (Otto + Mev + community quorum via OWS + Gnosis Safe)

**Milestone:** Full MY3YE sovereignty stack live. No proprietary signing dependency anywhere.

**Total: ~$40K, ~13 weeks, zero vendor lock-in.**

---

## Top 3 Prioritised Next Actions

**1. Write the WalletAdapter interface (this week, $0, autonomous)**
One file. Abstract the adapter before any OWS code is written. This is the single most leverage action — every downstream task builds against it, making OWS optional rather than baked in. Assign to coder agent, 2h, done.

**2. Implement OWS Phase 1 for Koink fair launch agent (before chain-agnostic launch, ~$3K)**
The Koink roadmap already has Phase 0 as "$KOINK Standard spec + chain-agnostic adapter." OWS is the answer to that adapter. Implement now — replaces ~500 lines of custom key management and adds policy enforcement for autonomous launches. Dependency: WalletAdapter interface (Action 1).

**3. Implement OWS Phase 1 ONEON custodial + agent delegation (before W3F grant PR, ~$5K)**
The W3F Level 1 grant for ONEON People Chain identity is ready to submit (from capital raise audit 2026-03-22). OWS Phase 1 strengthens the technical substance of that PR. Sequence: WalletAdapter → OWS ONEON Phase 1 → submit W3F PR. This is the cleanest path to $10K grant funding with a real technical deliverable behind it.

---

## Decision Required from Mev

No blocking decisions. The architecture above is consistent with all standing directives (chain-agnostic, sovereign, non-proprietary, MIT-only dependencies). Actions 1-3 are fully autonomous once Mev confirms this is the right direction.

The only open question is sequencing priority: **Koink first** (faster revenue path, simpler implementation) vs **ONEON first** (W3F grant money, stronger identity story). Recommendation: **Koink first** — shipping Koink fair launches is P9 revenue work; ONEON identity is P9 grant work. Both are P9, but Koink has a clearer near-term payoff.

---

*Full supporting docs: `~/otto/docs/ows-koink-fit-2026-03-23.md`, `~/otto/docs/oneon-ows-compatibility-2026-03-23.md`*
