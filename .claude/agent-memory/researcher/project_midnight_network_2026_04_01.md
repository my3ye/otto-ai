---
name: Midnight Network Research — Full Synthesis (2026-04-01)
description: Midnight blockchain by IOG — tech stack, mainnet status, roadmap, MY3YE relevance, strategic actions. VALIDATED 8.0/10.
type: project
---

## Midnight Network — VALIDATED SYNTHESIS (2026-04-01)

**Research Note DB ID:** 97be3f13-53cb-4384-8ed3-2876e2946269
**Episodic IDs:** bc629021 (I1), aac96e80 (I2), c6b5ad63 (I3), bbf67b61 (I4), 380517e8 (I5), 449d95a5 (I6), bd897221 (I7)
**Validation Score:** 8.0/10 — APPROVED

---

### STATE AS OF 2026-04-01 (mainnet +2 days)

**LIVE:** Kūkolu federated mainnet, $808M cap (CMC #63), NIGHT on Binance/Kraken/OKX.
Monument Bank £250M RWA partnership. Federated validators: Google Cloud, Blockdaemon,
MoneyGram, Worldpay, Telegram, eToro, Bullish, Pairpoint.

**TECH:**
- Substrate/Rust node. AURA 6s blocks + GRANDPA finality + BEEFY bridge (Cardano)
- ZK: Kachina → Halo2 (BLS12-381, recursive, no trusted setup)
- Dual-state ledger: public UTXO + private account-based
- Client-side proving — private data never leaves device
- Compact DSL (TypeScript-based, compiles to ZK circuits)
- NIGHT (governance) + DUST (non-transferable, auto-regenerates, pays fees)
- 24B NIGHT total supply, ~$0.044 at launch
- Glacier Drop: 4.5B+ to 8M+ wallets, 450-day thaw → **~Feb 2027** (PATCHED)

**ROADMAP:**
- Mōhalu Q2 2026: Cardano SPO validators, decentralization begins
- Hua Q3 2026: Ethereum/Solana bridges, cross-chain hybrid dApps
- Midnight OS 2026: browser-based node

---

### MY3YE CODEBASE GAPS (independently verified)

- **ONEON ZK: ZERO implementation** — grep confirmed (proof/circuit/witness/snark/stark/plonk in /mnt/media/projects/oneon-web → only content articles, no code)
- **No Midnight blockchain integration** in /mnt/media/projects/ — 26 "midnight" matches are all UI theme color references (theme-midnight.json)

---

### GRANTS

9.6B NIGHT ecosystem reserve (40% of 24B). Aliit Fellowship: 17 fellows, rolling admissions.
ONEON qualifies as identity/social infrastructure.
**CAUTION: Grant amounts and deadlines UNCONFIRMED — verify before acting.**

---

### RISKS

1. No public security audits (Trail of Bits, Certora, etc.) — pre-integration blocker
2. Federated validators (Google Cloud et al.) have no stated exit timeline — centralization paradox
3. Glacier Drop unlock pressure through **~Feb 2027** (450-day thaw from Dec 2025)
4. Mobile ZK proving speed: architecturally sound, benchmarks absent
5. Decentralization commitment undefined — Mōhalu "promises" SPO integration, not guarantees

---

### KEY CORRECTIONS (from validation)

- **PATCHED:** Glacier Drop thaw end date Dec 2026 → **~Feb 2027** (450 days from Dec 2025)
- **DOWNGRADED:** MCP server "29-tool" claim MEDIUM → MEDIUM-LOW (self-referential task log source, unverified)
- **CORRECTED:** Midnight is NOT the only viable compliance-native ZK chain — Mina Protocol and Aleo are also live, though Midnight is most compliance-native

---

### ACTIONS (ranked)

1. Apply for Aliit Fellowship for ONEON — confirm application window first (deadlines unconfirmed)
2. Build Compact DSL + selective disclosure PoC for ONEON identity layer (closes verified ZK gap)
3. Gate mainnet integration at Mōhalu Q2 2026 — wait for decentralization before committing

**Why:** How to apply:
- This research is the foundation for any Midnight integration or grant application
- Use research note 97be3f13 as source document for any proposal
- Do NOT commit to mainnet deployment before Mōhalu decentralization milestone
