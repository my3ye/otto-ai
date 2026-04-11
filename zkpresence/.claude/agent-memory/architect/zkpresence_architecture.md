---
name: zkPresence Architecture Decisions
description: Design decisions for the ZK proof-of-attendance system using SP1 zkVM on Base
type: project
---

zkPresence architecture designed 2026-04-11. Key decisions:

1. **SP1 v6.1.0** (Hypercube) — not v4.x. v4 is over a year old; v6 is latest stable with `ProverClient::from_env()`, `.groth16()` builder, `include_elf!` macro.

2. **SHA-256** for hashing (nullifier + identity commitment) — SP1 has native precompile, ~100x faster than software. Poseidon has no advantage in zkVM context.

3. **secp256k1 ECDSA** for attestation signatures — matches Ethereum's native scheme, SP1 precompile available.

4. **Groth16** for on-chain proofs — ~192B proof, ~230k gas, cheapest option. Uses pre-deployed SP1VerifierGateway at `0x397A5f7f3dBd538f23DE225B51f532c34448dA9B`.

5. **Single contract** with event registry — not factory pattern. Events are data entries, not separate contracts.

6. **Nullifier scheme**: `SHA-256(user_secret ‖ event_id)` — deterministic, unlinkable across events, collision-resistant.

7. **Three attestation modes**: QR code scan (rotating nonces), geohash proximity (5-char precision ~5km), organizer direct signature.

**Why:** Mev's directive to build ZK proof-of-attendance for Otto Music (concert attendance → exclusive content) and Tusita (community session verification).

**How to apply:** This is the foundation for any ZK credential work in the MY3YE ecosystem. Extension points: Semaphore-style group membership trees, multi-chain replay protection (add chainId to public values), mobile SDK wrapper.
