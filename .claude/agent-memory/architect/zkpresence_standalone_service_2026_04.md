---
name: zkPresence Standalone Service Architecture
description: zkPresence expanded from MVP to standalone service + ecosystem base. Monorepo (crates/ + packages/), ChainAdapter trait (EVM/Solana/XMTP), Fastify+BullMQ service, 4 pricing tiers, 5 internal integrations (ONEON/Tusita/SOS/Koink/Music). 5 phases ~$32.
type: project
---

zkPresence standalone service architecture designed 2026-04-11. Full spec at ~/otto/docs/zkpresence-standalone-service-architecture-2026-04-11.md.

**Why:** Existing zkPresence is a self-contained MVP (SP1 circuits + ZkPresence.sol). To serve as shared privacy primitive for 5 internal projects AND a sellable managed service, it needs SDK boundaries, pluggable chain adapters, a service layer, and pricing.

**How to apply:**
- When any internal project (ONEON, Tusita, SOS, Koink, Otto Music) needs ZK presence/attendance proofs, point them to @zkpresence/sdk + adapter-evm
- Monorepo structure: crates/ (core, circuit, prover) + packages/ (sdk, adapter-evm, adapter-solana, adapter-xmtp, react-hooks, server)
- ChainAdapter trait is the extension point for new chains — implement the interface, register with service
- Service runs Fastify + BullMQ on existing VM, prover calls Succinct Network
- Pricing: Free (100/mo), Builder ($49, 2K/mo), Pro ($199, 20K/mo), Enterprise (custom)
- Internal projects use Pro-equivalent at $0 cost
- Phase 1 priority: fix SP1 precompile TODOs (sha256 + ecdsa_verify) before anything else
