---
name: ONEON Invisible Web3 Layer architecture review
description: Architecture doc review for ONEON Phase 1 invisible layer (2026-03-28, WF Step 2) — NEEDS_CHANGES. 4 criticals including ERC-4337/lazy-creation contradiction and session key private key storage gap.
type: project
---

## Review: NEEDS_CHANGES

Architecture document at ~/otto/docs/oneon-invisible-web3-layer-architecture-2026-03-28.md
Phase 0 baseline implementation confirmed correct.

**Critical issues (4):**
1. **ERC-4337 + lazy creation contradiction** — Session keys require a deployed smart account to be configured on-chain. Counterfactual (lazy) accounts don't exist on-chain yet. You cannot pre-configure session keys for a non-deployed account. Either (a) deploy on signup (violates lazy creation) or (b) defer session key registration until first action. Must resolve before coder starts 1B.
2. **Session key private key storage unspecified** — `oneon_session_keys` table stores only `public_key`. For Tier 1 auto-signing, the server must hold the corresponding private key. Where? Not specified in architecture. This is a critical security gap — needs explicit decision (vault-encrypted, HSM, or memory-only) before coder can implement invisible.py.
3. **Stale migration number in Phase 1A text** — Architecture doc line 466 still says "Migration 078" in Phase 1A steps, but SQL block title (line 386) and file creation list (line 513) correctly say "080". Partial fix — one stale reference remains, which will confuse the coder.
4. **No gas usage tracking column** — Migration adds `gas_budget_daily_usd` but no `gas_used_today_usd` / `gas_reset_at`. Without these, `paymaster.py`'s `is_sponsored()` has nowhere to record daily spend. Risk table correctly marks gas drain as "High" but DB mitigation is incomplete.

**Warnings (5):**
5. Email stored as plaintext PII — `oneon_identities.email TEXT` — should be hashed or vault-encrypted in a sovereignty-first system.
6. Email verification gate not explicit in action flows — architecture mentions it in risk table but the data flow diagrams for /actions/vote, /actions/post don't show email_verified check.
7. Uncapped voter weight (carry-over, flagged Pass 1+2) — `CastVoteRequest.weight=Field(ge=1, le=100)` with no auth. Still unresolved.
8. `_require_admin()` always raises 501 — new admin-style endpoints (credentials/issue) will be broken on launch without replacing this function.
9. `smart_account_salt TEXT` — CREATE2 salt is bytes32; TEXT allows inconsistent formats.

**Good:**
- Three-tier progressive abstraction model is sound and well-documented.
- Phase 0 code quality is high (atomic transactions, proper feature flagging, UUID params, route ordering).
- Migration SQL uses IF NOT EXISTS throughout.
- `token_hash TEXT NOT NULL UNIQUE` in auth_tokens is correct (SHA-256, not raw token).
- Lazy account creation decision is correct for paymaster budget efficiency.
- Decision rationale section is detailed and honest.
- Risk matrix is accurate (gas drain = High, XMTP SDK = Medium).

**Pattern:** Architecture correctly identifies ERC-4337 as the right choice but under-specifies the custodial key management model — the "invisible" signing requires private key custody somewhere, and that design must be explicit before implementation.
