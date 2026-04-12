---
name: zkPresence Dynamic Public Key System Review
description: Code review of commit 43e755c — three-layer dynamic public key implementation (KeyBinding circuit, DynamicKeyRegistry.sol, ZkPresence extension, TS SDK). NEEDS_CHANGES 7.5/10.
type: project
---

zkPresence dynamic public key system implementation (commit 43e755c, 2026-04-12, WF Step 2): NEEDS_CHANGES 7.5/10.

2 criticals:
1. `verifyAttendanceWithKey()` ephemeral signature check is broken (ZkPresence.sol:185) — `require(signer != address(0))` is security theater. Any valid ECDSA signature from any address passes. Doesn't verify the signer holds the ephemeral key identified by `ephPkHash`. Root cause: SHA256(compressed_pk) ≠ Ethereum address (keccak of uncompressed key). Fix: change registry to store Ethereum addresses, not SHA256 hashes, for ECDSA.recover compatibility.
2. `sign_with_ephemeral()` in Rust keys.rs double-hashes (crates/core/src/keys.rs:151) — `sk.sign(msg_hash)` via k256 Signer trait applies SHA-256 internally before signing. Since the function accepts a pre-hashed message, the output is `ecdsa_sign(SHA256(msg_hash))`. The TS SDK (noble-curves) signs prehash correctly. Cross-language incompatibility: Rust signatures cannot be verified by Solidity ECDSA.recover (keccak256-based). Fix: use `sign_prehash()` from k256.

3 warnings:
- `verifyAttendanceWithKey()` has zero test coverage — the new function is completely untested (no ZkPresence.t.sol tests for ephemeral path).
- ECDSA import in ZkPresence.sol imported from OZ but provides no real security due to critical #1 — should be removed or fixed.
- No event emitted for `setKeyRegistry()` — admin action is unauditable on-chain.

4 suggestions:
- KeyBinding circuit doesn't validate `eph_pk` is a valid secp256k1 point (crates/keybind/src/main.rs:43) — could bind garbage 33-byte strings as keys.
- ZkPresence.sol uses single-step ownership — no `transferOwnership` two-step pattern.
- `advanceEpoch()` is permissionless (intentional) — add comment documenting this is by design.
- `computeKeyNonce` is exported from SDK but not from core crate root (only KeyBindingPublicValues is re-exported).

What's good: Epoch system design is correct and clean (epochStart + EPOCH_DURATION arithmetic). Nullifier replay prevention is solid. HKDF domain separation correct. Backward compat with legacy user_secret handled cleanly. DynamicKeyRegistry tests are thorough (13 tests covering epoch, expiry boundary, nonce reuse, multi-key, rotation). Circuit ABI encoding consistent between Rust and Solidity. TS SDK input validation (length checks) is good discipline. Keys.rs unit tests (9 tests) comprehensive.

**Why:** sign/verify incompatibility is a cross-language integration blocker; broken sig check is a design invariant violation.
**How to apply:** When reviewing ZK+Solidity systems: always verify that off-chain signing libraries use prehash mode when on-chain verifier expects prehash; always verify that key identifiers use the same encoding as the on-chain recover function.
