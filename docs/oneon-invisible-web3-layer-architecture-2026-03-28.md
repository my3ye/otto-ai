# ONEON Invisible Web3 Infrastructure Layer — Architecture
*Architect assessment — 2026-03-28*

---

## Design: Invisible Web3 Infrastructure for ONEON

### Problem

Mev directive: "making it in a way that anyone can participate — not just technical people and people with Web3 knowledge."

Current Web3 identity solutions (ENS, XMTP, Lens, Farcaster, Polkadot People Chain, Solana fragments) all share the same fatal flaw: **they require you to already be in Web3 to use them**. Every one demands a wallet, seed phrase management, gas tokens, and chain-specific knowledge before you can even create an identity.

ONEON's job is to make the on-ramp invisible. A user signs up with a handle and email — like any app they already use. Under the hood, they get a sovereign identity, encrypted communications, governance participation, and an upgradeable path to full self-sovereignty. They never see a wallet address, gas fee, or chain name unless they choose to.

The existing Phase 0 infrastructure (DB schemas, API routes, identity CRUD, governance stubs) provides the backend foundation. This architecture defines the **invisible layer** — the abstraction stack that makes Web3 disappear for users while maintaining full sovereignty underneath.

### What Exists vs What's Missing

**Already built (Phase 0):**
- `oneon_identities` table with tier system (waitlist → custodial → self_sovereign → sovereign)
- 12 API endpoints (`/oneon/*`) for identity CRUD + governance
- DID stub generation (`did:oneon:<handle>:<chain>:<address>`)
- WalletAdapter abstract interface (NullWalletAdapter stub)
- Feature flags (`oneon_enabled`)
- ONEON waitlist landing page (Next.js, terminal UX)

**Missing — the invisible layer:**
1. Automatic wallet creation behind a simple signup
2. Gas abstraction (users never see or pay gas)
3. Invisible signing (actions are signed without user friction)
4. Progressive disclosure (complexity revealed only on demand)
5. Communication layer (encrypted messaging without wallet setup)
6. Credential engine (achievements/reputation without VC jargon)

---

### Approach: Three Abstraction Tiers

The invisible layer is a **progressive abstraction stack** with three tiers. Each tier maps to ONEON's existing identity tiers but defines what the *user experiences* vs what happens *under the hood*.

```
USER EXPERIENCE                  UNDER THE HOOD
═══════════════════════════════════════════════════════════════════

Tier 1: "IT JUST WORKS"         (custodial — user knows nothing about Web3)
  Sign up: handle + email        → Smart account created (ERC-4337)
  Login: magic link / passkey    → Session key activated
  Post / Vote / Message          → Signed UserOp, gas sponsored
  Earn badges                    → VCs issued to their DID
  Everything free                → Paymaster covers gas

Tier 2: "I WANT TO OWN THIS"    (self-sovereign — user opts into control)
  Export identity                → DID + keys revealed, guided flow
  Connect own wallet             → Smart account ownership transferred
  See on-chain activity          → Block explorer links, tx history
  Back up with guardians         → Shamir social recovery setup
  Still no gas burden            → Paymaster still active (optional)

Tier 3: "I AM THE NETWORK"      (sovereign — full autonomy)
  Run own node                   → ONEON mesh participant
  Local vault                    → OWS vault on user's device
  Issue credentials to others    → Become a trust anchor
  Memory Capsule                 → Encrypted personal data store
  Full chain visibility          → Direct RPC, own gas management
═══════════════════════════════════════════════════════════════════
```

---

### Architecture Stack

```
┌─────────────────────────────────────────────────────────────┐
│                    ONEON Frontend (Next.js)                  │
│  Handle signup → Magic link login → Dashboard → Messaging   │
│  User never sees: wallet, gas, chain, tx hash, seed phrase  │
└────────────────────────────┬────────────────────────────────┘
                             │ REST / WebSocket
┌────────────────────────────┴────────────────────────────────┐
│                 ONEON Gateway API (FastAPI)                  │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │ Identity      │  │ Comms        │  │ Credentials      │  │
│  │ Service       │  │ Service      │  │ Service          │  │
│  │               │  │              │  │                  │  │
│  │ register()    │  │ send()       │  │ issue()          │  │
│  │ authenticate()│  │ receive()    │  │ verify()         │  │
│  │ upgrade()     │  │ channels()   │  │ present()        │  │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────────┘  │
│         │                  │                  │              │
│  ┌──────┴──────────────────┴──────────────────┴───────────┐ │
│  │              Invisible Signing Layer                     │ │
│  │                                                         │ │
│  │  For custodial:  auto-sign (no user prompt)             │ │
│  │  For sovereign:  passkey confirm (WebAuthn)             │ │
│  │                                                         │ │
│  │  sign_action(identity, action) → signed_payload         │ │
│  └──────────────────────┬──────────────────────────────────┘ │
└─────────────────────────┼───────────────────────────────────┘
                          │
┌─────────────────────────┴───────────────────────────────────┐
│              Account Abstraction Layer (ERC-4337)            │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │ Smart Account │  │ Paymaster    │  │ Bundler          │  │
│  │ Factory       │  │              │  │                  │  │
│  │               │  │ Sponsors gas │  │ Aggregates       │  │
│  │ Creates       │  │ for Tier 1   │  │ UserOps          │  │
│  │ account on    │  │ users        │  │                  │  │
│  │ first action  │  │              │  │ Submits to       │  │
│  │ (lazy)        │  │ Budget caps  │  │ chain            │  │
│  └──────────────┘  └──────────────┘  └──────────────────┘  │
│                                                             │
│  Session Keys: pre-authorized action types (vote, post,     │
│  message) — no per-action confirmation for Tier 1           │
└─────────────────────────┬───────────────────────────────────┘
                          │
┌─────────────────────────┴───────────────────────────────────┐
│                    Chain Layer (Base L2)                     │
│                                                             │
│  ONEONRegistry.sol     — DID ↔ smart account binding        │
│  ONEONCredentials.sol  — VC issuance + revocation           │
│  ONEONPaymaster.sol    — gas sponsorship logic              │
│  (future) ONEONMesh    — mesh comm anchoring                │
└─────────────────────────────────────────────────────────────┘
```

---

### Key Decisions

**Decision 1: ERC-4337 Account Abstraction** vs Embedded Wallets (Privy/Dynamic) vs MPC
- **Chosen**: ERC-4337 smart accounts
- **Why**: Native, decentralized, upgradeable, no vendor dependency. Smart accounts support session keys (gasless UX), social recovery (guardian-based), and ownership transfer (Tier 1 → Tier 2 migration). The user's "account" is a contract they eventually own — not a key held by a third party.
- **Alternative rejected**: Privy/Dynamic embedded wallets — fast to implement but creates centralized dependency. ONEON's mission is sovereignty; can't build sovereignty on a vendor's key custody.
- **Alternative rejected**: MPC wallets — complex infrastructure, still requires trust in threshold participants.

**Decision 2: Base L2** as primary chain vs Optimism vs Polygon vs Own L3
- **Chosen**: Base L2
- **Why**: Cheapest gas on any production OP Stack chain (~$0.001/tx), Coinbase fiat on-ramp ecosystem for future Tier 2 users, growing developer tooling. OP Stack means we can launch an ONEON L3 later with minimal migration.
- **Alternative rejected**: Optimism mainnet — slightly higher gas, less fiat on-ramp integration.
- **Alternative rejected**: Own L3 immediately — requires sequencer infrastructure, premature for Phase 1.
- **Alternative rejected**: Polkadot People Chain — good long-term fit but requires Substrate expertise and different account model. Phase 2 consideration.

**Decision 3: Eager Account Deployment on Signup** (not lazy/counterfactual)
- **Chosen**: Smart account is deployed on-chain at signup time, not deferred until first action. Address is deterministic (CREATE2), and the account is deployed in the same paymaster-sponsored batch as the first session key setup.
- **Why**: Session keys (Decision 4) require a deployed contract to call `addSessionKey()` on. A counterfactual address has no on-chain code — you cannot configure it. Eager deployment on Base L2 costs ~$0.001 per account, which is negligible. The alternative (deferring session key setup until first action) would mean the first action requires two transactions (deploy + configure + execute), adding latency and complexity to the moment the UX must be most seamless.
- **Alternative rejected**: Lazy/counterfactual creation — incompatible with session keys. Cannot call `addSessionKey()` on an undeployed address. Would require bundling deploy+configure+action on first use, degrading Tier 1 UX.
- **Alternative rejected**: Defer session keys until first action — makes first action slower and more complex. The ~$0.001 deploy cost is worth paying upfront for instant session key availability.

**Decision 4: Session Keys for Tier 1** (pre-authorized action types)
- **Chosen**: On signup, after the smart account is deployed (see Decision 3), session keys are configured authorizing common actions (vote, post, message, claim credential) for 30 days. No per-action wallet confirmation.
- **Why**: The #1 UX killer in Web3 is "confirm this transaction" popups. Tier 1 users don't know what transactions are. Session keys let the backend sign actions automatically within pre-authorized scopes.
- **Session key custody model (Tier 1)**: The server generates an ephemeral ECDSA key pair per user. The **private key** is encrypted with the vault master key (AES-256-GCM, key from `ONEON_VAULT_MASTER_KEY` env var) and stored in `oneon_session_keys.encrypted_private_key`. The public key is registered on-chain via `addSessionKey()`. On each Tier 1 action, `invisible.py` decrypts the private key in memory, signs the UserOp, and discards the plaintext. This is custodial by design — Tier 1 users trade self-custody for zero-friction UX. Tier 2+ users bring their own keys.
- **Alternative rejected**: HKDF-derived keys from master root — simpler but master key compromise exposes all session keys simultaneously. Per-user encryption limits blast radius.
- **Alternative rejected**: Memory-only keys (no persistence) — lost on restart, requiring re-setup for all users. Unacceptable for production.
- **Alternative rejected**: Per-action confirmation — defeats "invisible" goal. Reserved for Tier 2+ users who want control.

**Decision 5: XMTP for messaging** vs Waku vs custom
- **Chosen**: XMTP (Phase 1), with Waku mesh fallback (Phase 3)
- **Why**: XMTP is production-ready, wallet-to-wallet E2EE, supports smart account addresses, and has React SDK for fast frontend integration. Users see "send message" — XMTP handles encryption keyed to their smart account.
- **Alternative rejected**: Waku — excellent for censorship resistance but early-stage; save for Phase 3 mesh layer.
- **Alternative rejected**: Custom — enormous effort for something XMTP does well.

**Decision 6: Credentials as "achievements"** — never show "Verifiable Credential" to users
- **Chosen**: W3C VCs under the hood, but surface them as badges/achievements/reputation in the UI. "You earned Community Builder" not "VC issued by did:oneon:... with claim type CommunityBuilder".
- **Why**: VC jargon is a wall. The credential engine issues proper W3C VCs (portable, verifiable, standards-compliant) but the UI shows game-like achievements. Tier 2+ users can export raw VCs.
- **Alternative rejected**: Skip VCs entirely — loses interoperability with the broader identity ecosystem.

---

### API / Interface Design

#### New Endpoints (added to existing `/oneon/*` router)

```
# --- Invisible Onboarding ---
POST   /oneon/signup
       Body: {handle, email, display_name?}
       Returns: {identity_id, session_token}
       Under the hood: creates identity (waitlist→custodial), derives
       counterfactual smart account address, stores in oneon_identities,
       sends magic link to email

POST   /oneon/auth/magic-link
       Body: {token}  (from email link)
       Returns: {session_token, identity}
       Under the hood: verifies token, activates session key

POST   /oneon/auth/passkey/register
       Body: {identity_id, credential}  (WebAuthn)
       Returns: {ok}
       Under the hood: stores passkey credential for Tier 2+ signing

POST   /oneon/auth/passkey/verify
       Body: {credential}
       Returns: {session_token, identity}

# --- Invisible Actions (auto-signed for Tier 1) ---
POST   /oneon/actions/vote
       Body: {proposal_id, vote, identity_id}
       Returns: {action_id, status}
       Under the hood: constructs UserOp, session key signs,
       paymaster sponsors gas, bundler submits

POST   /oneon/actions/post
       Body: {content, channel?, identity_id}
       Returns: {action_id, content_hash}
       Under the hood: hashes content, signs attestation,
       anchors to chain (optional, based on content type)

POST   /oneon/actions/message
       Body: {to_handle, content, identity_id}
       Returns: {message_id}
       Under the hood: resolves recipient smart account,
       sends via XMTP E2EE

# --- Progressive Disclosure (Tier 2+) ---
GET    /oneon/identities/{id}/chain-activity
       Returns: {transactions[], credentials[], account_address}
       Shows on-chain activity — hidden from Tier 1 UI

POST   /oneon/identities/{id}/export
       Returns: {did, public_key, smart_account_address,
                 credentials[], recovery_instructions}
       Guided identity export flow

POST   /oneon/identities/{id}/connect-wallet
       Body: {wallet_address, signature}
       Returns: {ok}
       Under the hood: transfers smart account ownership
       to user's external wallet

# --- Credentials (shown as achievements) ---
POST   /oneon/credentials/issue
       Body: {subject_id, credential_type, claims}
       Returns: {credential_id, badge_name, badge_image}
       Under the hood: issues W3C VC, stores hash on-chain

GET    /oneon/identities/{id}/achievements
       Returns: [{name, description, earned_at, verifiable}]
       User-friendly credential view

GET    /oneon/identities/{id}/credentials
       Returns: [{vc_jwt, type, issuer, issuance_date}]
       Raw VC export (Tier 2+ only)

# --- Messaging ---
GET    /oneon/messages/{identity_id}/conversations
       Returns: [{peer_handle, last_message, unread_count}]

GET    /oneon/messages/{identity_id}/thread/{peer_handle}
       Returns: [{content, from, to, timestamp}]

POST   /oneon/messages/send
       Body: {from_identity_id, to_handle, content}
       Returns: {message_id}
```

#### Data Flow: User Signs Up

```
User fills handle + email on ONEON frontend
  │
  ├─ POST /oneon/signup
  │   ├─ Validate handle (2-32 chars, alphanumeric + underscore only)
  │   ├─ Create oneon_identities row (tier=custodial)
  │   ├─ Derive deterministic smart account address (CREATE2)
  │   ├─ Deploy smart account on Base L2 (paymaster-sponsored, ~$0.001)
  │   │   └─ Store address in smart_account_address, set smart_account_deployed=TRUE
  │   ├─ Generate session key pair (ECDSA), encrypt private key with vault master key
  │   │   └─ Store in oneon_session_keys (encrypted_private_key + public_key)
  │   ├─ Register session key on-chain: addSessionKey(pubkey, [VOTE,POST,MSG,CRED], 30d)
  │   ├─ Store DID: did:oneon:<handle>:base:<address>
  │   ├─ Hash email (SHA-256) → store email_hash for lookup, discard plaintext
  │   ├─ Send magic link email (via admin@otto.lk)
  │   └─ Return {identity_id, session_token (limited until email verified)}
  │
  ├─ User clicks magic link
  │   ├─ POST /oneon/auth/magic-link
  │   │   ├─ Verify token (SHA-256 hash lookup, single-use via used_at)
  │   │   ├─ Set email_verified = TRUE
  │   │   ├─ Activate full session privileges
  │   │   └─ Return {session_token, identity}
  │   │
  │   └─ User is now "logged in" — has a handle, DID, deployed smart account
  │       No wallet popup. No seed phrase. No gas.
  │
  └─ User votes on a proposal
      ├─ POST /oneon/actions/vote
      │   ├─ CHECK: email_verified = TRUE → if not, return 403 "Verify email first"
      │   ├─ CHECK: gas_used_today_usd < gas_budget_daily_usd → if not, return 429
      │   ├─ Lookup identity → get smart account address
      │   ├─ Construct governance vote UserOp
      │   ├─ Decrypt session key private key from vault
      │   ├─ Sign with session key (automatic, no user prompt)
      │   ├─ Paymaster validates: is this user sponsored? → yes
      │   ├─ Bundler submits UserOp to Base L2
      │   ├─ Increment gas_used_today_usd with actual gas cost
      │   └─ Return {action_id, tx_hash (hidden from UI)}
      │
      └─ User sees: "Vote recorded ✓" — nothing else
```

> **IMPORTANT for Phase 1A coder**: All Tier 1 action endpoints (`/actions/vote`, `/actions/post`, `/actions/message`) MUST check `email_verified = TRUE` before executing. Return HTTP 403 with `{"detail": "Email verification required. Check your inbox."}` if not verified. This prevents gas budget drain from unverified signups.

---

### Smart Contracts (Base L2, Solidity, Foundry)

```
contracts/
├── ONEONAccountFactory.sol    — Creates smart accounts (ERC-4337)
│   Uses: SimpleAccountFactory pattern (eth-infinitism)
│   Key: deterministic CREATE2 addresses from (handle_hash, salt)
│
├── ONEONPaymaster.sol         — Sponsors gas for Tier 1 users
│   Uses: VerifyingPaymaster pattern
│   Logic: check if sender is registered ONEON identity,
│          check daily gas budget per user ($0.10/day default),
│          sign paymaster data
│
├── ONEONRegistry.sol          — DID ↔ smart account binding
│   Functions:
│     register(did, account)   — bind DID to smart account
│     resolve(did) → account   — lookup
│     rotate(did, newAccount)  — key rotation
│     revoke(did)              — identity revocation
│   Events: IdentityRegistered, IdentityRotated, IdentityRevoked
│
├── ONEONCredentials.sol       — On-chain credential anchoring
│   Functions:
│     anchor(credentialHash, subject, issuer) — store VC hash
│     verify(credentialHash) → (subject, issuer, timestamp)
│     revoke(credentialHash) — issuer revocation
│   Note: Full VC is off-chain (IPFS or API). Only hash is on-chain.
│
└── ONEONSessionKey.sol        — Session key validation module
    Functions:
      addSessionKey(key, permissions, expiry)
      validateSessionKey(key, action) → bool
      revokeSessionKey(key)
    Permissions: VOTE, POST, MESSAGE, CLAIM_CREDENTIAL
```

### Backend Modules (Python, in `~/otto/memory/oneon/`)

```
oneon/
├── __init__.py                — (exists) — add new exports
├── spec.py                    — (exists) — update for Phase 1
├── identity.py                — (exists) — add signup + auth flows
├── governance.py              — (exists) — wire to on-chain voting
├── did.py                     — (exists) — real DID resolution
│
├── invisible.py               — NEW: Core invisible layer
│   Classes:
│     InvisibleSigner          — auto-sign for Tier 1, passkey for Tier 2+
│     ActionExecutor           — construct + submit UserOps
│     CounterfactualAccount    — deterministic address derivation
│
├── paymaster.py               — NEW: Gas sponsorship logic
│   Functions:
│     is_sponsored(identity_id) → bool
│     get_daily_budget(identity_id) → float
│     sign_paymaster_data(user_op) → bytes
│
├── credentials.py             — NEW: VC engine (achievements UI)
│   Functions:
│     issue_credential(subject_id, cred_type, claims) → VC
│     verify_credential(vc_jwt) → bool
│     list_achievements(identity_id) → list[Achievement]
│     export_raw_credentials(identity_id) → list[VC]
│
├── messaging.py               — NEW: XMTP integration wrapper
│   Functions:
│     send_message(from_id, to_handle, content)
│     get_conversations(identity_id) → list
│     get_thread(identity_id, peer_handle) → list
│     init_xmtp_client(smart_account_key) → XMTPClient
│
├── auth.py                    — NEW: Magic link + passkey auth
│   Functions:
│     send_magic_link(email, identity_id)
│     verify_magic_link(token) → session_token
│     register_passkey(identity_id, webauthn_credential)
│     verify_passkey(webauthn_credential) → session_token
│     create_session_key(identity_id, permissions, ttl)
│
└── chain.py                   — NEW: Chain interaction (Base L2)
    Functions:
      deploy_account(identity_id) → tx_hash
      submit_user_op(user_op) → tx_hash
      get_account_address(identity_id) → address (counterfactual)
      get_chain_activity(identity_id) → list[tx]
```

### Database Changes (Migration 080)

```sql
-- Migration 080: Invisible Web3 infrastructure layer

-- Session keys for invisible signing
CREATE TABLE IF NOT EXISTS oneon_session_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    identity_id UUID NOT NULL REFERENCES oneon_identities(id) ON DELETE CASCADE,
    public_key TEXT NOT NULL,
    encrypted_private_key TEXT NOT NULL,  -- AES-256-GCM encrypted with ONEON_VAULT_MASTER_KEY (Tier 1 custodial only)
    permissions TEXT[] NOT NULL DEFAULT '{}',  -- VOTE, POST, MESSAGE, CLAIM_CREDENTIAL
    expires_at TIMESTAMPTZ NOT NULL,
    revoked_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_oneon_session_keys_identity ON oneon_session_keys(identity_id);
CREATE INDEX idx_oneon_session_keys_pubkey ON oneon_session_keys(public_key);

-- Actions log (invisible signed operations)
CREATE TABLE IF NOT EXISTS oneon_actions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    identity_id UUID NOT NULL REFERENCES oneon_identities(id) ON DELETE CASCADE,
    action_type TEXT NOT NULL,  -- vote, post, message, credential_claim
    payload JSONB NOT NULL DEFAULT '{}',
    tx_hash TEXT,              -- NULL until submitted to chain
    status TEXT NOT NULL DEFAULT 'pending',  -- pending, submitted, confirmed, failed
    gas_sponsored BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    confirmed_at TIMESTAMPTZ
);
CREATE INDEX idx_oneon_actions_identity ON oneon_actions(identity_id);
CREATE INDEX idx_oneon_actions_status ON oneon_actions(status);

-- Credentials (W3C VCs surfaced as achievements)
CREATE TABLE IF NOT EXISTS oneon_credentials (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    subject_id UUID NOT NULL REFERENCES oneon_identities(id) ON DELETE CASCADE,
    issuer_id UUID REFERENCES oneon_identities(id) ON DELETE SET NULL,
    credential_type TEXT NOT NULL,   -- community_builder, first_vote, mentor, etc.
    claims JSONB NOT NULL DEFAULT '{}',
    vc_jwt TEXT,                     -- full W3C VC JWT (off-chain)
    credential_hash TEXT,            -- on-chain anchor hash
    badge_name TEXT NOT NULL,        -- user-friendly name
    badge_description TEXT,
    badge_image_url TEXT,
    issued_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    revoked_at TIMESTAMPTZ,
    anchored_at TIMESTAMPTZ          -- when hash was written to chain
);
CREATE INDEX idx_oneon_credentials_subject ON oneon_credentials(subject_id);
CREATE INDEX idx_oneon_credentials_type ON oneon_credentials(credential_type);

-- Magic link tokens
CREATE TABLE IF NOT EXISTS oneon_auth_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    identity_id UUID NOT NULL REFERENCES oneon_identities(id) ON DELETE CASCADE,
    token_hash TEXT NOT NULL UNIQUE,  -- SHA-256 of token (never store raw)
    token_type TEXT NOT NULL DEFAULT 'magic_link',  -- magic_link, passkey_challenge
    expires_at TIMESTAMPTZ NOT NULL,
    used_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_oneon_auth_tokens_hash ON oneon_auth_tokens(token_hash);

-- Add smart account fields to existing identities table
ALTER TABLE oneon_identities
    ADD COLUMN IF NOT EXISTS smart_account_address TEXT,
    ADD COLUMN IF NOT EXISTS smart_account_deployed BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS smart_account_salt TEXT,
    ADD COLUMN IF NOT EXISTS passkey_credential_id TEXT,
    ADD COLUMN IF NOT EXISTS email TEXT,
    ADD COLUMN IF NOT EXISTS email_verified BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS gas_budget_daily_usd NUMERIC(10,4) NOT NULL DEFAULT 0.10;
```

---

### Implementation Plan

#### Phase 1A: Backend Foundation (~$4-5, 2-3 tasks)

1. **Migration 080** — new tables + identity columns (see SQL above)
2. **auth.py** — magic link flow (send via admin@otto.lk, verify, session token)
3. **invisible.py** — `CounterfactualAccount` (deterministic address from handle hash), `ActionExecutor` (construct UserOp payloads)
4. **Update identity.py** — `register_identity()` now derives smart account address on creation, stores email
5. **Update routes/oneon.py** — add `/signup`, `/auth/magic-link`, `/actions/vote`, `/actions/post` endpoints
6. **credentials.py** — `issue_credential()`, `list_achievements()`, off-chain VC storage

#### Phase 1B: Smart Contracts (~$6-8, 2-3 tasks)

7. **Foundry project** at `~/otto/contracts/oneon/` — `ONEONAccountFactory.sol`, `ONEONPaymaster.sol`, `ONEONRegistry.sol`
8. **Tests** — factory deployment, paymaster gas sponsorship, registry binding
9. **Deploy to Base Sepolia** (testnet) — factory + paymaster + registry
10. **chain.py** — Python module wrapping contract interactions (web3.py / viem via subprocess)

#### Phase 1C: Messaging + Frontend (~$5-7, 2-3 tasks)

11. **messaging.py** — XMTP SDK integration (Node.js subprocess or XMTP HTTP API)
12. **ONEON frontend** — update oneon-web: signup flow (handle + email), dashboard (achievements, messages, governance), identity export
13. **Passkey auth** — WebAuthn registration + verification for Tier 2 users

#### Phase 2: Progressive Disclosure + Polish (~$4-6, 2 tasks)

14. **Export flow** — guided identity export (DID, keys, smart account ownership transfer)
15. **Connect wallet** — transfer smart account ownership to external wallet
16. **Chain activity view** — hidden by default, visible for Tier 2+ users
17. **Raw credential export** — W3C VC JWTs for Tier 2+ users

#### Phase 3: Mesh + Memory Capsule (future, not costed)

18. Waku mesh communication layer
19. Memory Capsule (IPFS/Arweave encrypted store)
20. Social recovery (Shamir 3-of-5)
21. ONEON L3 (own OP Stack rollup)

---

### Affected Files

**Modify:**
- `~/otto/memory/oneon/__init__.py` — add new module exports
- `~/otto/memory/oneon/spec.py` — update phase info, add Phase 1 spec
- `~/otto/memory/oneon/identity.py` — add email, smart_account_address to registration
- `~/otto/memory/routes/oneon.py` — add ~10 new endpoints
- `~/otto/memory/config.py` — add `oneon_paymaster_address`, `oneon_factory_address`, `base_rpc_url`, `xmtp_api_key`
- `~/otto/memory/api.py` — ensure oneon router is included (already is, but verify)
- `/mnt/media/projects/oneon-web/app/page.tsx` — evolve from waitlist to signup + dashboard

**Create:**
- `~/otto/memory/migrations/080_oneon_invisible_layer.sql`
- `~/otto/memory/oneon/invisible.py`
- `~/otto/memory/oneon/auth.py`
- `~/otto/memory/oneon/credentials.py`
- `~/otto/memory/oneon/messaging.py`
- `~/otto/memory/oneon/paymaster.py`
- `~/otto/memory/oneon/chain.py`
- `~/otto/contracts/oneon/` — Foundry project (4 contracts)

---

### Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| **ERC-4337 complexity** — bundler/paymaster infrastructure is non-trivial | Medium | Use existing infrastructure: Pimlico or Alchemy's bundler + paymaster as a service. Self-host later. |
| **Gas budget drain** — malicious signups burn paymaster budget | High | Daily per-user gas cap ($0.10), rate limiting on `/signup`, require email verification before first action |
| **XMTP SDK compatibility** — XMTP expects browser wallet, not server-side keys | Medium | Use XMTP's REST API or Node.js SDK with programmatic key provision. Tier 1 keys are server-managed anyway. |
| **Magic link email deliverability** — admin@otto.lk may hit spam filters | Medium | Use Zoho transactional email with SPF/DKIM already configured. Monitor deliverability. Passkey is the long-term auth. |
| **Smart account migration** — transferring ownership (Tier 1 → Tier 2) may confuse users | Low | Guided flow with clear explanation. Ownership transfer is a single tx. Reversible within 24h grace period. |
| **Base L2 chain risk** — single chain dependency | Low | Smart contracts are standard Solidity. Deployable to any OP Stack chain. Registry is the only chain-specific anchor. |
| **Budget constraint** — full Phase 1 is ~$15-20 across 6-8 tasks | Medium | Phase 1A alone (~$4-5) delivers invisible signup + auth + actions. Contracts (1B) can follow. Frontend (1C) can be separate sprint. |

---

### What Makes This Different From Existing Solutions

| Feature | ENS | XMTP | Lens | Farcaster | ONEON |
|---|---|---|---|---|---|
| **No wallet required to start** | No | No | No | No | **Yes** |
| **No gas ever (Tier 1)** | No | Yes | No | Partial | **Yes** |
| **Identity + messaging + governance unified** | No | No | No | No | **Yes** |
| **Progressive sovereignty** | No | No | No | No | **Yes** |
| **Credential system built in** | No | No | No | No | **Yes** |
| **Works offline (future)** | No | No | No | No | **Yes** |
| **Non-technical UX** | No | No | No | Partial | **Yes** |

The invisible layer is what turns ONEON from "another Web3 identity protocol" into "the first identity system where Web3 is an implementation detail, not a prerequisite."

---

### Cost Estimate

| Phase | Tasks | Est. Cost | Deliverable |
|---|---|---|---|
| 1A: Backend | 2-3 | ~$4-5 | Signup, auth, actions, credentials (API) |
| 1B: Contracts | 2-3 | ~$6-8 | Smart accounts, paymaster, registry (Base testnet) |
| 1C: Frontend + Messaging | 2-3 | ~$5-7 | ONEON web app, XMTP integration |
| 2: Progressive Disclosure | 2 | ~$4-6 | Export, wallet connect, chain view |
| **Total Phase 1+2** | **8-11** | **~$19-26** | **Full invisible Web3 identity system** |

Phase 1A is the minimum deployable unit — invisible signup and actions work without smart contracts (deferred signing, actions queue until contracts deploy).

---

*Output stored at: ~/otto/docs/oneon-invisible-web3-layer-architecture-2026-03-28.md*
