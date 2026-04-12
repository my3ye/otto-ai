---
name: Dynamic Public Key System Architecture
description: Three-layer key system (Identity/Authority/Action) for zkPresence ecosystem. zkLogin-adapted, bio+pass derivation, epoch-based ephemeral key rotation, DynamicKeyRegistry contract. Argon2 Path B chosen. Two SP1 circuits (KeyBinding + Attendance). Phase 1-2 ~$11-16.
type: project
---

Dynamic Public Key System architecture completed (2026-04-12). Full spec at ~/otto/docs/dynamic-public-key-architecture-2026-04-12.md.

**Core Design:** Three-layer architecture:
- Layer 1 (Identity): stable `identity_commitment = SHA256(HKDF(FuzzyExtract(bio) || Argon2(pass)))` — never changes on-chain
- Layer 2 (Authority): ephemeral secp256k1 key pair, epoch-bounded, ZK-certified via KeyBinding circuit
- Layer 3 (Action): per-action ZK proofs (attendance, governance, credentials) bound to authority

**Key Decisions:**
1. Argon2 Path B — prove knowledge of output commitment, not computation (memory-hard = infeasible in ZK). Same pattern as zkLogin.
2. Epoch-based key expiry (not on-chain revocation) — stateless, gas-efficient, default 24h epochs
3. Two separate SP1 circuits: KeyBinding (identity→key binding) + Attendance (existing, extended) — composability across ecosystem
4. Fuzzy extractor stays device-side — raw biometrics never enter ZK circuit (GDPR Art. 9)
5. HKDF for key combination (RFC 5869) — domain-separated, uniform output
6. Groth16 for Phase 1-2, PLONK deferred to Phase 3 — avoid blocking on verifier deployment

**Why:** Current identity = SHA256(random_secret) — brittle, no recovery, no rotation. Ecosystem needs identity derived from who-you-are + what-you-know, with rotatable signing keys.

**How to apply:**
- Phase 1 (P0): Wire SHA-256 + ECDSA in circuit/main.rs — blocks everything
- Phase 2a: keys.rs module (HKDF, bio+pass combination)
- Phase 2b: KeyBinding SP1 circuit (new crate)
- Phase 2c: DynamicKeyRegistry.sol + ZkPresence.sol extension
- Phase 2d: TypeScript SDK (keys.ts)
- Phase 3: PLONK migration + recursive proofs + PQ
- DynamicKeyRegistry is shared primitive — all ecosystem contracts (ONEON, SOS, Koink) reference it
- Existing users backward-compatible: raw user_secret IS master_secret
