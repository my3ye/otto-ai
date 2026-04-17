# Koink Protocol — Research Brief
**Date: 2026-03-23 | Status: Complete | Audience: Architect + Coder**

---

## TL;DR

Koink.fun is **our own platform** — not a third-party protocol to call. The "Koink protocol" IS the $KOINK Standard: a chain-agnostic tokenomics engine. This research documents what it specifies, what external APIs/protocols it depends on, and what integration points the OMS crypto engine needs to serve it.

---

## 1. The $KOINK Standard — What We're Building

The $KOINK Standard is an open-source tokenomics spec deployable on any chain that can run it. Every token launched via Koink.fun must implement:

| Mechanic | Spec | On-Chain Where |
|---|---|---|
| Fair launch | VRF-seeded randomness — no insider presales, no sniper bots | EVM: Chainlink VRF v2.5; Solana: Switchboard VRF |
| Anti-whale | Hard per-wallet caps at launch; enforced at contract level | ERC-20 transfer hook / Solana account constraint |
| Diamond Hands Multiplier (DHM) | On-chain hold accumulator; grows to 3x governance weight at 12 months | `DiamondHandsVault.sol` / Solana program |
| Graduated sell tax | Scales with sell velocity (not time); drops for long holders | EVM hook in transfer; Solana instruction handler |
| Community treasury | 20% auto-split every transaction | `KoinkTreasury.sol` / PDA treasury account |
| Contribution weighting | Hooks to attach ONEON / SOS Systems activity to governance weight | Off-chain oracle + on-chain attestation (EAS on EVM) |
| Fork specification | Full open-source — any project deploys a $KOINK Standard token | GitHub: ottomev/koink-fun |

**Chain targets (roadmap):**
- Phase 1: Base (genesis), Ethereum, Arbitrum, Optimism
- Phase 2: Solana, Cosmos, NEAR (requires custom OWS extension)

---

## 2. External Protocol Dependencies

### 2.1 EVM — Uniswap V4 (Base)

**Purpose:** Primary DEX integration for trading and liquidity after launch.

| Contract | Address (Base mainnet, chain ID 8453) |
|---|---|
| PoolManager | `0x498581ff718922c3f8e6a244956af099b2652b2b` |
| PositionManager | `0x7c5f5a4bbd8fd63184577525326123b519429bdc` |
| Quoter | `0x0d5e0f971ed27fbff6c2837bf31316121532048d` |
| StateView | `0xa3c0c9b65bad0b08107aa264b0f3db444b867a71` |
| Universal Router | `0x6ff5693b99212da76ad316178a184ab56d299b43` |
| Permit2 | `0x000000000022D473030F116dDEE9F6B43aC78BA3` |

**Anti-sniper hook pattern (V4 CCA — Commit-Confirm-Accumulate):**
- V4's hook system allows pre/post-swap logic
- Implement a `beforeSwap` hook for block-by-block anti-sniper enforcement
- Per prior research: use CCA (block-by-block) pattern — most effective EVM anti-sniper
- SDK: `@uniswap/v4-sdk` (npm) + `viem` for transaction construction

**⚠ WARNING:** `require(msg.sender == tx.origin)` anti-bot check is **broken on ETH mainnet post-Pectra (May 2025)** due to EIP-7702 account abstraction. Still valid on Base/L2s (they lag ETH opcode changes) — but verify at deployment time.

---

### 2.2 EVM — Chainlink VRF v2.5 (Base)

**Purpose:** Provably fair launch randomness — no one can predict the VRF seed pre-launch.

**Subscription model:**
1. Create subscription → get `subscriptionId`
2. Fund with LINK (Base LINK: `0x88Fb150BDc53A65fe94Dea0c9BA0a6dAf8C6e196`)
3. Add `KoinkLauncher.sol` as consumer
4. Call `requestRandomWords()` in launcher to seed the launch

**Key integration pattern (VRF Consumer):**
```solidity
import "@chainlink/contracts/src/v0.8/vrf/VRFConsumerBaseV2Plus.sol";

contract KoinkLauncher is VRFConsumerBaseV2Plus {
    bytes32 keyHash = 0x...; // Base keyHash from Chainlink docs
    uint256 subscriptionId;

    function requestLaunchSeed() external returns (uint256 requestId) {
        return s_vrfCoordinator.requestRandomWords(
            VRFV2PlusClient.RandomWordsRequest({
                keyHash: keyHash,
                subId: subscriptionId,
                requestConfirmations: 3,
                callbackGasLimit: 100000,
                numWords: 1,
                extraArgs: VRFV2PlusClient._argsToBytes(
                    VRFV2PlusClient.ExtraArgsV1({nativePayment: false})
                )
            })
        );
    }

    function fulfillRandomWords(uint256 requestId, uint256[] calldata randomWords)
        internal override {
        _launchWithSeed(randomWords[0]);
    }
}
```

**Base-specific parameters:** Check `https://docs.chain.link/vrf/v2-5/supported-networks` for current coordinator address and keyHash on Base.

---

### 2.3 EVM — Gnosis Safe (Treasury Multi-Sig)

**Purpose:** KoinkTreasury.sol requires DAO multi-sig for spending.

**Architecture:**
- Gnosis Safe = outer quorum (Mev + community signers + OWS-backed Otto = 1 signer)
- Otto's signing key held in OWS vault with policy: whitelist-only treasury address, max ETH value cap
- API: `https://safe-transaction-service.gnosis.io/` (REST API for Safe transaction management)
- SDK: `@safe-global/protocol-kit` (npm)

**Safe creation on Base:**
```bash
# Using Safe SDK
npx @safe-global/safe-deployments # gets Base contract addresses
```

---

### 2.4 EVM — Doppler (Fair Launch on Base, via Bankr Bot)

**Purpose:** The BANKR Bot integration uses "Doppler fair launch" for Base token launches.

**What Doppler is:** A Base-native fair launch protocol (pump.fun equivalent for Base). BANKR Bot accesses it via NL prompt to the Agent API (`POST api.bankr.bot/agent/prompt`).

**Integration pattern for Koink (Option A — via Bankr):**
```python
prompt = compose_launch_prompt(
    token_name="$KOINK",
    token_symbol="KOINK",
    supply="1000000000",
    platform="doppler",
    chain="base"
)
result = await bankr_client.execute(prompt)
```

**⚠ Caveat:** Doppler launches don't implement the $KOINK Standard natively (no DHM, no graduated tax). Doppler is a starting point only — Koink's custom mechanics need a bespoke contract, not Doppler's generic token.

**Recommendation:** Use Doppler only for pre-launch hype/early positioning. Koink's actual `$KOINK` token should deploy its own standard contracts.

---

### 2.5 Solana — Raydium LaunchLab

**Purpose:** Primary Solana launch mechanism with bonding curve.

**Mechanics:**
- Free to deploy a token with a bonding curve
- Early buyers get lower prices; price increases with supply purchased
- At graduation threshold: liquidity migrates automatically to a Raydium AMM pool; LP tokens burned (locked forever)
- 50% of trading fees returned to community
- **Platform PDA**: Third-party builders set their own fees via Platform PDA — Koink earns on every token launched through its interface

**Integration (SDK):**
```typescript
// @raydium-io/raydium-sdk-v2 (npm)
import { Raydium } from '@raydium-io/raydium-sdk-v2';
const raydium = await Raydium.load({ connection, owner });
// LaunchLab SDK methods TBD — consult docs.raydium.io/raydium/launchlab/for-developers
```

**Program addresses (mainnet):** Check `https://docs.raydium.io/raydium/launchlab/for-developers` for current program IDs.

**⚠ Anti-sniper on Solana:** Raydium standard launch = zero sniper protection. Per research:
- Use **Meteora Alpha Vault Pro-Rata** for pre-launch allowlist allocation
- Use **Switchboard VRF** (not Chainlink, no Solana support) for randomness
- Graduation detection: monitor Raydium program for `MigrateEvent`

---

### 2.6 OpenWallet Standard (OWS)

**Purpose:** Agent-side key management for Otto's deployment operations.

**What it does:**
- Local, policy-gated signing vault (keys never leave the signing path)
- CAIP-10 unified addresses across 9 chains (EVM, Solana, Cosmos, Bitcoin, TON, Tron, Sui, Spark, Filecoin)
- Pre-signing policies: chain allowlists, value caps, address whitelisting, expiry

**Koink-specific integration (per OWS-Koink assessment):**

| Action | OWS Policy |
|---|---|
| Deploy KoinkLauncher.sol on Base | `can_sign: ["deploy"], max_value_eth: 0.5, chain: "eip155:8453"` |
| Trigger fair launch | `can_sign: ["launch"], require_vrf_seed: true` |
| Treasury distribution signing | `can_sign: ["distributeToTreasury"], address_whitelist: [treasury_addr]` |
| Cross-chain adapter deployment | Derive wallets via CAIP-10 for each chain |

**CLI usage (agent key creation):**
```bash
ows keygen --name koink-deploy --chain eip155:8453,eip155:1,solana:5eykt4UsFv8P8NJdTREpY1vzqKqZKvdp
ows policy attach koink-deploy --can-sign deploy,launch --max-eth 0.5
```

**Language bindings:** Node.js + Python FFI to Rust core.

**Gap:** NEAR not in OWS's 9 chains — requires community extension (Ed25519, CAIP-2 `near`, `m/44'/397'/0'`).

---

## 3. Koink.fun — Current Platform State

| Item | Status |
|---|---|
| koink.fun domain | **LIVE** (200 OK) |
| Landing page | Live (Next.js, Vercel-deployed) |
| Public API | **NONE** — no `/api/*` endpoints |
| Smart contracts | **NOT DEPLOYED** — landing page only |
| GitHub | `github.com/ottomev/koink-fun` (landing page source) |
| Code repo | Exists at `/mnt/media/projects/koink-fun/` |

**Key insight:** Koink.fun is a landing page project. No backend, no on-chain contracts, no API. The OMS integration must build all of this from scratch.

---

## 4. OMS Crypto Engine — Integration Points

### What exists today (`/crypto/*` in otto/memory/routes/crypto.py):

| Endpoint | Status | Notes |
|---|---|---|
| `/crypto/launch` | Phase 3 — DB record only | Records intent, no execution |
| `/crypto/signals` | Active | DB-only signal tracking |
| `/crypto/price` | Active | CoinGecko + Birdeye |
| `/crypto/portfolio` | Active | Alchemy (EVM) |
| `/crypto/execute` | Phase 2 pending | 0x quote, not live |

### What Koink needs in OMS (NEW `/koink/*` routes):

| Endpoint | Priority | Description |
|---|---|---|
| `GET /koink/status` | P1 | Engine health, deployed contracts, wallet status |
| `POST /koink/deploy` | P1 | Deploy $KOINK Standard contracts to a target chain |
| `POST /koink/launch` | P1 | Execute fair launch (VRF seed → open trading) |
| `GET /koink/tokens` | P1 | List all $KOINK Standard tokens deployed via Otto |
| `GET /koink/tokens/{address}/dhm` | P2 | Diamond Hands Multiplier status for a wallet |
| `GET /koink/tokens/{address}/treasury` | P2 | Treasury balance + governance actions |
| `GET /koink/tokens/{address}/governance` | P2 | Contribution-weighted votes, multipliers |
| `POST /koink/fork` | P3 | Fork $KOINK Standard for a new project |

### What fits INTO existing `/crypto/launch`:
Extend `LaunchRequest` to accept KOINK Standard params:
```python
class LaunchRequest(BaseModel):
    # existing fields...
    koink_standard: bool = False          # Use $KOINK Standard mechanics
    vrf_seed: Optional[str] = None        # Chainlink/Switchboard VRF seed
    anti_whale_cap_pct: float = 1.0       # % of supply per wallet at launch
    treasury_pct: float = 20.0            # Community treasury auto-split
    dhm_months: int = 12                  # Months to reach max multiplier
    dhm_max_multiplier: float = 3.0       # Max governance multiplier
    sell_tax_initial_pct: float = 5.0     # Initial sell tax
```

---

## 5. Data Models (DB Schema Needed)

```sql
-- Token deployments via KOINK Standard
CREATE TABLE koink_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    symbol TEXT NOT NULL,
    chain TEXT NOT NULL,                    -- "base", "solana", etc.
    contract_address TEXT,                  -- NULL until deployed
    chain_id TEXT,                          -- CAIP-2 format
    status TEXT DEFAULT 'pending',          -- pending/deploying/deployed/launched
    vrf_request_id TEXT,                    -- Chainlink/Switchboard request ID
    launch_seed TEXT,                       -- VRF-fulfilled random seed
    total_supply NUMERIC,
    anti_whale_cap_pct FLOAT DEFAULT 1.0,
    treasury_pct FLOAT DEFAULT 20.0,
    dhm_months INT DEFAULT 12,
    sell_tax_initial_pct FLOAT DEFAULT 5.0,
    treasury_address TEXT,
    gnosis_safe_address TEXT,               -- For EVM treasury multi-sig
    ows_key_id TEXT,                        -- OWS key used for deployment
    metadata JSONB DEFAULT '{}',
    deployed_at TIMESTAMPTZ,
    launched_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- DHM tracking (off-chain index of on-chain state)
CREATE TABLE koink_dhm_positions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    token_id UUID REFERENCES koink_tokens(id),
    wallet_address TEXT NOT NULL,
    chain TEXT NOT NULL,
    hold_start_at TIMESTAMPTZ NOT NULL,
    current_multiplier FLOAT DEFAULT 1.0,  -- 1.0 → 3.0 over 12 months
    last_synced_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (token_id, wallet_address)
);

-- Treasury events
CREATE TABLE koink_treasury_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    token_id UUID REFERENCES koink_tokens(id),
    event_type TEXT NOT NULL,              -- "auto_split", "governance_spend"
    amount NUMERIC,
    tx_hash TEXT,
    chain TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

## 6. Integration Architecture (Summary)

```
koink.fun Web Platform (Next.js, no API)
├── User actions (connect wallet, launch token, vote)
│   └── EIP-1193 (MetaMask/WalletConnect) on EVM
│   └── @solana/wallet-adapter on Solana
│   └── On-chain: KoinkLauncher.sol / Solana program
│
└── Otto agent actions (deploy, distribute, automate)
    └── OWS vault (koink-deploy key, policy-gated)
        └── Chainlink VRF → fair launch seed
        └── Uniswap V4 Pool (post-launch liquidity)
        └── Gnosis Safe (treasury multi-sig, Otto = 1 signer)
        ↓
    Memory API /koink/* routes (NEW)
        └── Deploy coordinator (Phase 1)
        └── DHM tracker (Phase 2)
        └── Treasury monitor (Phase 2)
```

---

## 7. Rate Limits & Auth Requirements

| Service | Auth Required | Rate Limit | Cost |
|---|---|---|---|
| Chainlink VRF | LINK tokens + subscription | Per-request fee (~0.25 LINK/call on Base) | ~$0.50-2/launch |
| Uniswap V4 | None (public contracts) | Onchain gas only | Gas only |
| Raydium LaunchLab | Solana keypair (fee payer) | None | SOL gas only |
| Gnosis Safe API | None (read), tx signing (write) | 500 req/day free | Free |
| OWS | Local vault key file | N/A (local) | Free |
| Meteora Alpha Vault | Solana keypair | None | SOL gas only |
| Switchboard VRF | SOL fee payer | Per-request fee | ~$0.01-0.10/call |

---

## 8. Implementation Priority

### Immediate (Phase 0 — no contracts, just infrastructure):
1. **Create OWS wallet for koink-deploy agent** — Derive Base + Solana + Cosmos wallets. Store CAIP-10 descriptors.
2. **Add `/koink/status` to OMS Memory API** — Wire to existing crypto engine status pattern.
3. **Extend DB with `koink_tokens` table** — Migration file.
4. **Extend `/crypto/launch` to accept KOINK Standard params** — Backward compatible.

### Phase 1 (EVM launch — smart contracts needed):
1. Build `KoinkLauncher.sol` — VRF consumer + fair launch orchestrator
2. Build `KoinkToken.sol` (ERC-20 + graduated sell tax + anti-whale)
3. Build `DiamondHandsVault.sol` (hold duration accumulator)
4. Build `KoinkTreasury.sol` (20% auto-split + Gnosis Safe multi-sig)
5. Wire Uniswap V4 hooks (post-launch pool creation)
6. OMS: `POST /koink/deploy` → calls OWS → deploys contracts via Hardhat
7. OMS: `POST /koink/launch` → VRF request → seed fulfillment → launch execution

### Phase 2 (Solana + DHM + OMS frontend):
1. Solana Anchor program (Koink Standard port)
2. Switchboard VRF integration for Solana
3. Raydium LaunchLab Platform PDA integration
4. OMS: DHM tracker + treasury monitor endpoints
5. OMS frontend: Koink section on `/crypto` page

---

## 9. Key Unknowns / Risks

| Risk | Mitigation |
|---|---|
| OWS v1.0 stability (relatively new) | Pin to specific release; audit library pre-mainnet |
| Chainlink VRF request fulfillment time (3+ blocks, ~30-60s on Base) | Launch UI must show "VRF pending" state; don't let users trade until fulfilled |
| Uniswap V4 hook gas overhead | Benchmark hook gas costs; CCA anti-sniper adds ~30-50k gas per swap |
| Raydium LaunchLab SDK stability | Use official `@raydium-io/raydium-sdk-v2` only; pin version |
| EIP-7702 anti-bot bypass (ETH mainnet) | Deploy on Base/L2 first (not ETH mainnet); reverify at ETH deployment |
| Gnosis Safe quorum coordination | Define quorum (e.g., 2/3: Otto + Mev + community) before launch |
| NEAR OWS gap | Custom extension needed; defer NEAR to Phase 2+ |

---

## 10. OMS Crypto Engine Fit Assessment

**Verdict: YES, add Koink to the OMS crypto engine.**

The existing `/crypto/launch` is Phase 3 placeholder only. Koink is the actual use case it was designed for. The fit is natural:
- Existing signal board → $KOINK launch signals
- Existing trade history → Koink token trades
- Existing portfolio → $KOINK balance tracking
- Existing NL parser → "Launch a Koink on Base" intent
- **New**: `/koink/*` routes for deployment coordination, DHM, treasury

**What changes in OMS:**
1. Extend `LaunchRequest` with KOINK Standard params (backward compatible)
2. Add new `/koink/*` router (separate from `/crypto/*` to keep concerns clean)
3. Add `koink_tokens`, `koink_dhm_positions`, `koink_treasury_events` DB tables
4. Extend OMS frontend `/crypto` page with a Koink launch panel

---

*Document sources: koink-roadmap-2026-03-20.md, ows-koink-fit-2026-03-23.md, crypto.py, bankr/client.py, launch-filtering-antsniper research, Uniswap V4 deployments docs, Raydium LaunchLab docs, OWS GitHub, Chainlink VRF v2.5 docs.*
