---
name: SOS Post-Quantum Framework
description: SOS Systems dual-trust PQ architecture — behavioral (DPC, quantum-immune) + PQ crypto (ML-DSA/STARKs). 6 layers, 4 phases, ~$28-40. Inverts trust hierarchy.
type: project
---

SOS Systems Post-Quantum Framework architecture completed (2026-04-12). Core innovation: dual-trust model that inverts blockchain's standard hierarchy — behavioral trust (DPC contribution record) is primary, PQ cryptography is secondary reinforcement.

**Why:** Every other PQC project replaces one lock with a stronger lock. SOS replaces the premise: if lattice assumptions break, behavioral trust continues functioning independently. DPC governance weight cannot be quantum-computed because it requires genuine verified history, not a mathematical relationship.

**How to apply:**
- All future SOS/ONEON cryptographic design must go through the crypto-agility layer (SignatureProvider interface)
- Identity ops use ML-DSA-65, on-chain ops use FN-DSA-512, root keys use SLH-DSA-128s
- ZK proofs migrate from Groth16 to STARKs (SP1/RISC Zero) — no pairing dependencies
- Selective disclosure gap: STARK attribute proofs as interim until lattice BBS+ standardizes (~2028)
- Three-tier identity assurance: Tier 1 (crypto), Tier 2 (behavioral/DPC), Tier 3 (multi-party attestation)
- Higher-stakes operations require higher tiers
- 4-phase migration: immediate hygiene → hybrid dual-signing → full PQ primary → legacy sunset
- No custom L1 chain — deploy on existing EVM L2s with PQ signature libraries

Full spec at ~/otto/docs/sos-pq-framework-architecture-2026-04-12.md
