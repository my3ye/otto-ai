# Solana Meme Token Launch Infrastructure
**Research Date:** 2026-02-21
**Status:** Research complete — actionable within 1 week
**Author:** Otto (task research)

---

## TL;DR

- **Easiest path:** pump.fun — zero cost to creator, live in minutes, auto-graduates to PumpSwap at ~$69k market cap
- **Best for control:** Raydium CPMM direct — ~1.5–6 SOL total, full customization
- **For Bobby specifically:** pump.fun launch + Jito bundle to protect creator allocation from bots
- **Copy trading:** Helius webhooks (already have key) + Birdeye PnL API for wallet discovery
- **Total launch cost estimate:** 0.02–2 SOL depending on platform + optional initial buy

---

## 1. Launch Platforms

### pump.fun (Recommended — Dominant Platform)

**How it works:**
- Creator deploys token at **zero cost** — the first buyer pays ~0.02 SOL ($2–3) for token creation
- 1B total supply: 800M on bonding curve for sale, 200M reserved for graduation LP
- Constant-product AMM with **virtual reserves** (30 SOL / 1.073B tokens at start)
- Initial price: ~0.0000000280 SOL/token (~$0.000004)
- Trades happen on the bonding curve until 800M tokens are sold
- **Graduation:** When bonding curve fills (~85 SOL total volume), token automatically migrates to **PumpSwap** (pump.fun's own DEX, launched March 2025)
- Creator earns **+0.5 SOL bonus** at graduation

**Fees (Project Ascend model):**
| Market Cap | Trading Fee |
|---|---|
| Under $300k | 0.95% |
| Scaling up | Sliding scale |
| Over $20M | 0.05% |
| PumpSwap post-graduation | 0.25% (0.2% LPs, 0.05% protocol) |

**Why it works for memes:**
- Zero friction, massive distribution (handles 80%+ of Solana new token launches)
- DEX Screener auto-lists immediately
- Community knows the pump.fun flow — any CT (Crypto Twitter) participant can buy instantly
- LP permanently locked at graduation — rug-proof after bonding curve fills

**Limitation:** You cannot pre-allocate tokens to yourself; pump.fun prohibits presales. All supply goes through the bonding curve. Bots will snipe the first blocks unless you use a Jito bundle.

---

### Moonshot / moon.it (DEX Screener Native)

- No-code launch built into DEX Screener's ecosystem
- **Graduation threshold: 500 SOL** — much higher than pump.fun
- Upon graduation, liquidity migrates to **Raydium** and LP tokens are burned
- Native visibility on DEX Screener platform
- Suitable if the token concept aligns with DEX Screener's community

**When to use:** When targeting traders who live on DEX Screener and want Raydium liquidity.

---

### Meteora Dynamic Bonding Curve

- Open-source bonding curve program — fully customizable
- **Anti-sniping fees:** Fee starts at 50% at launch, drops exponentially over 120 minutes to 0.25% permanently
- Creator earns fees on locked liquidity indefinitely (LP locked, fee revenue not locked)
- TVL: $1.1B+, growing rapidly
- **Alpha Vault:** Anti-sniping tool for fair distribution

**When to use:** Larger, more serious launches where you want fee customization and anti-bot protection baked in. Overkill for a first meme launch.

---

### Raydium CPMM (Direct Pool Creation)

- Create a liquidity pool directly without a launchpad
- Full control over initial price, liquidity, and supply allocation
- **Cost:** ~0.15–0.3 SOL pool creation + however much liquidity you seed
- Supports Token-2022 standard
- No OpenBook market ID required (vs older AMM V4 which needed ~1.5–2 SOL extra)

**When to use:** When you want creator allocation (buy tokens before opening pool) and full control. Requires Jito bundle to atomically seed LP + make initial buy.

---

### Jupiter LFG — NOT FOR MEMES

Jupiter LFG is a curated, DAO-voted launchpad for serious DeFi projects. Requires community forum post, discussion period, and JUP token holder vote. Not suitable for meme launches.

---

## 2. SPL Token Creation — Technical Steps

### What Gets Created On-Chain

| Account | Size | Cost (SOL) | Purpose |
|---|---|---|---|
| Mint Account | 82 bytes | ~0.00144 SOL | Stores supply, decimals, mint/freeze authority |
| Metadata Account (Metaplex PDA) | ~679 bytes | ~0.01–0.015 SOL | Name, symbol, URI pointer |
| Token Account (per holder) | 165 bytes | ~0.002 SOL | Holds token balance for each wallet |

**Total bare minimum:** ~0.015 SOL for the token to exist (no liquidity)

### Token Parameters for Meme Launches

```
decimals: 6           (pump.fun standard)
supply:   1,000,000,000,000,000  (1B * 10^6)
mint_authority: revoked after mint (builds trust)
freeze_authority: null (honeypot prevention)
update_authority: revoked for immutability (or keep to update metadata)
```

### Metadata JSON (Upload to IPFS First)

```json
{
  "name": "Based Bobby",
  "symbol": "BOBBY",
  "description": "Bitcoin Billionaire. Base Chain educator. Bringing a billion people on-chain.",
  "image": "https://ipfs.io/ipfs/QmXXX.../bobby_logo.png",
  "external_url": "https://basedbobby.xyz",
  "extensions": {
    "twitter": "https://x.com/basedbobby",
    "telegram": "https://t.me/basedbobbygroup",
    "discord": "https://discord.gg/basedbobby",
    "website": "https://basedbobby.xyz"
  }
}
```

### Programmatic Token Creation (TypeScript + Metaplex Umi)

```bash
npm install @metaplex-foundation/umi \
  @metaplex-foundation/mpl-token-metadata \
  @metaplex-foundation/umi-bundle-defaults \
  @solana/web3.js
```

```typescript
import { percentAmount, generateSigner, signerIdentity, createSignerFromKeypair } from '@metaplex-foundation/umi'
import { TokenStandard, createAndMint, mplTokenMetadata } from '@metaplex-foundation/mpl-token-metadata'
import { createUmi } from '@metaplex-foundation/umi-bundle-defaults'

const umi = createUmi('https://mainnet.helius-rpc.com/?api-key=YOUR_HELIUS_KEY');

const userWallet = umi.eddsa.createKeypairFromSecretKey(new Uint8Array(secretKeyArray));
const userWalletSigner = createSignerFromKeypair(umi, userWallet);
umi.use(signerIdentity(userWalletSigner));
umi.use(mplTokenMetadata());

const mint = generateSigner(umi);

await createAndMint(umi, {
  mint,
  authority: umi.identity,
  name: "Based Bobby",
  symbol: "BOBBY",
  uri: "https://ipfs.io/ipfs/QmXXX.../metadata.json",
  sellerFeeBasisPoints: percentAmount(0),
  decimals: 6,
  amount: 1_000_000_000_000_000n,  // 1B tokens
  tokenOwner: userWallet.publicKey,
  tokenStandard: TokenStandard.Fungible,
}).sendAndConfirm(umi);

// After mint: revoke mint authority to prevent inflation
// await setAuthority(umi, { mint, authority: umi.identity, authorityType: 'MintTokens', newAuthority: null })
```

### Revoking Mint Authority (Trust Signal)

After minting total supply, revoke mint authority so no more tokens can ever be created:
```typescript
import { setAuthority, AuthorityType } from '@solana/spl-token'
// authorityType: AuthorityType.MintTokens, newAuthority: null
```

---

## 3. Pump.fun Bonding Curve — Technical Detail

### Formula

```
k = virtual_sol_reserves * virtual_token_reserves
  = 30 * 1,073,000,191
  = 32,190,005,730 (constant)

Initial price = 30 SOL / 1,073,000,191 tokens ≈ 0.0000000280 SOL/token

Tokens received for x SOL:
  y = 1,073,000,191 - 32,190,005,730 / (30 + x)
```

### Supply Distribution

| Allocation | Amount | Notes |
|---|---|---|
| Bonding curve (for sale) | 800,000,000 | Public buys through this |
| Graduation LP | 200,000,000 | Locked in PumpSwap at graduation |
| Dev/creator allocation | 0 | Prohibited by pump.fun |

### Graduation

- Occurs when all 800M bonding curve tokens are purchased
- ~85 SOL of real SOL accumulated → ~79 SOL net after fees seeds PumpSwap pool
- Market cap at graduation: ~$69,000 (varies with SOL price)
- LP permanently locked — no rug possible post-graduation
- Creator earns **+0.5 SOL bonus** automatically

---

## 4. Cost Summary

### By Launch Method

| Method | Creator Cost | Min Initial Buy | Notes |
|---|---|---|---|
| pump.fun (fair launch) | **0 SOL** | 0 SOL (optional) | First buyer pays ~0.02 SOL |
| pump.fun + creator initial buy | ~0.02–1+ SOL | Creator's choice | Get tokens before bots |
| Moonshot / moon.it | ~0.02 SOL | ~0.02 SOL min | Higher graduation threshold (500 SOL) |
| Raydium CPMM (direct) | 0.15–0.3 SOL (pool) | 1–5 SOL liquidity | Full control, no launchpad |
| Jito bundle tip | +0.001–0.01 SOL | Per bundle | Atomically seed pool + buy |

### Full "Serious Launch" Budget

| Item | SOL | Notes |
|---|---|---|
| Token creation (metadata + mint) | 0.015 | Rent-exempt deposits |
| IPFS hosting (Pinata) | 0 | Free tier sufficient |
| pump.fun creation | 0 | Creator free |
| Initial creator buy (optional) | 0.1–1.0 | To get position before bots |
| Jito bundle tip | 0.005 | For bundled anti-bot launch |
| Twitter KOL (1–2 mid-tier) | External USD cost | ~$100–500 |
| **Total SOL** | **~0.12–1.02 SOL** | ~$20–170 at current prices |
| **Total USD** | **~$120–670** | Including KOL |

---

## 5. Copy Trading Infrastructure

### Current Stack (Already Operational)

Otto already has:
- **Helius API key** — can set up webhooks immediately
- **20 smart money wallets** tracked in `wallets.json`
- **Alpha live watcher** polling every 5 minutes via Helius

### Upgrading to Real-Time Copy Trading

**Step 1: Helius Enhanced Webhooks**

```typescript
// POST https://api.helius.xyz/v0/webhooks?api-key=YOUR_KEY
{
  "accountAddresses": ["wallet1", "wallet2", ...],  // up to 100k addresses
  "transactionTypes": ["SWAP"],
  "webhookURL": "http://your-server/webhook",
  "webhookType": "enhanced"
}
```

Webhook payload includes parsed swap data: `inputMint`, `outputMint`, `inputAmount`, `outputAmount`, `swap.innerSwaps`.

**Step 2: Birdeye PnL API for Wallet Discovery**

```bash
GET https://public-api.birdeye.so/wallet/v2/pnl?wallet=ADDRESS
Header: X-API-KEY: YOUR_BIRDEYE_KEY

# Returns: win_rate, total_trades, realized_pnl, roi_percentage
```

Filters to apply:
- `win_rate > 0.60`
- `trade_count > 50`
- `last_trade < 30 days ago`
- `roi > 100%`

**Step 3: Execution Pipeline**

```
Helius webhook received (SWAP event)
  → Extract: inputMint, outputMint, amount
  → Scale: our_amount = their_amount * (our_capital / their_capital)
  → GET Jupiter /quote?inputMint=...&outputMint=...&amount=...
  → POST Jupiter /swap (returns unsigned tx)
  → Sign with our keypair
  → Submit via Helius staked RPC (SWQoS) OR Jito bundle
  → Log to PostgreSQL
```

**Latency targets:**
- Helius confirmed webhook: ~400ms after tx confirmation
- Jito ShredStream: ~200–500ms before full propagation (requires separate access)
- Target: execute within same or next slot as target wallet

---

## 6. End-to-End Launch Flow: Bobby Example

### Pre-Launch (Week 0 — Do Now)

- [ ] Design Bobby logo (Laughing Buddha + Bob Marley aesthetic, brown skin, chain with ₿)
- [ ] Create Twitter/X account: `@BasedBobby` or similar
- [ ] Create Telegram group
- [ ] Write metadata JSON with description, social links
- [ ] Upload image + JSON to Pinata IPFS
- [ ] Write Character Bible (Hook: Bitcoin Billionaire turned Base educator → Lore: origin story → Voice: unique speech patterns)
- [ ] Queue 10 pre-launch tweets establishing lore/personality

### Launch Day

1. Deploy token via pump.fun UI (creator cost: 0 SOL)
   - OR: create SPL token programmatically → create Raydium CPMM pool → Jito bundle seed+buy
2. Make initial creator buy (0.1–0.5 SOL) to establish position and show commitment
3. Post CA (contract address) on Twitter with full branding
4. Open Telegram for community
5. Tag 2–3 mid-tier Solana KOLs

### Post-Launch (Hours 1–72)

- Monitor pump.fun bonding curve progress
- Post meme content every 2–4 hours
- Keep Telegram active with chart updates
- Watch for DEX Screener trending spike
- If graduation looks close: alert community, coordinate "graduation push"

### Otto's Automation Role

| Task | Otto Can Automate | Manual Required |
|---|---|---|
| Token contract deployment | Yes (TypeScript script) | Private key management |
| Metadata IPFS upload | Yes (Pinata API) | Image creation |
| Helius webhook monitoring | Yes (already built) | — |
| Copy trade execution | Yes (pipeline buildout) | Initial capital + risk params |
| Twitter post scheduling | Yes (Twitter API) | Content creation, voice |
| Telegram monitoring/alerts | Yes (Telegram bot) | Moderation |
| DEX Screener tracking | Yes (API polling) | — |
| KOL outreach | No | Manual negotiation |
| Community "raids" | No | Human coordination |

---

## 7. What We Can Build in 1 Week

### Week 1 Priority Build Order

**Day 1–2: Token Deployment Script**
- Python/TypeScript script that: uploads metadata to Pinata → creates SPL token → optionally creates Raydium CPMM pool
- Can launch Bobby or any future character in <5 minutes

**Day 2–3: pump.fun Monitor**
- Subscribe to PumpPortal WebSocket for new token events
- Apply rug filters: mint/freeze authority checks via Helius `getAsset`, holder concentration, creator wallet age
- Log qualified launches to PostgreSQL for copy-trade candidates

**Day 3–4: Copy Trade Execution Pipeline**
- Set up Helius enhanced webhooks for our 20+ smart money wallets
- Build swap execution: webhook → Jupiter quote → sign → submit
- Paper trade first (log decisions, no execution)

**Day 4–5: Bobby Launch Prep**
- Write launch script + deploy test token on devnet
- Prepare all social infrastructure
- Coordinate with Mev on timing + KOL budget

**Day 6–7: Go Live**
- Deploy Bobby on pump.fun (or Raydium if we want creator allocation)
- Activate copy trading with $50–100 initial capital
- Monitor both strategies simultaneously

---

## 8. Key Risks and Mitigations

| Risk | Severity | Mitigation |
|---|---|---|
| Bot sniping first blocks | High | Jito bundle: atomically deploy + buy in same block |
| Token gets no traction | High | Strong character lore pre-built, KOL coordination |
| Rug/honeypot in copy trading | High | Enforce rug filters before every copy trade |
| LP rug after launch | Medium | pump.fun LP auto-locked at graduation; Raydium: burn LP tokens |
| Overpaying gas during snipe | Medium | Set max tip on Jito bundles; use slippage limits |
| Smart money wallet goes cold | Low | Track 20 wallets; diversify |
| pump.fun fee changes | Low | Monitor platform announcements |

---

## Reference: Key Libraries and Tools

| Tool | Purpose | Install |
|---|---|---|
| `@metaplex-foundation/mpl-token-metadata` | Token + metadata creation | `npm install` |
| `@metaplex-foundation/umi-bundle-defaults` | Solana UMI framework | `npm install` |
| `@solana/web3.js` | Core Solana SDK | `npm install` |
| `@solana/spl-token` | SPL token authority ops | `npm install` |
| `helius-sdk` | Webhooks, RPC, asset queries | `npm install helius-sdk` |
| PumpPortal WebSocket | Real-time pump.fun launches | `wss://pumpportal.fun/api/data` |
| Jupiter V6 API | Swap quotes + execution | `https://quote-api.jup.ag/v6` |
| Jito bundles | Atomic tx bundles | `https://mainnet.block-engine.jito.wtf` |
| Pinata | IPFS metadata hosting | `https://pinata.cloud` |
| RugCheck.xyz | Automated rug scoring | `https://api.rugcheck.xyz` |
| Birdeye PnL API | Wallet discovery + scoring | `https://public-api.birdeye.so` |

---

## Reference: Key API Endpoints

```bash
# PumpPortal WebSocket — new token events
wss://pumpportal.fun/api/data
# Send: {"method": "subscribeNewToken"}
# Payload: {mint, name, symbol, creator, initialBuy, bondingCurveKey}

# Helius getAsset — authority checks
POST https://mainnet.helius-rpc.com/?api-key=KEY
{"jsonrpc":"2.0","id":1,"method":"getAsset","params":{"id":"MINT_ADDRESS"}}

# Jupiter V6 — quote
GET https://quote-api.jup.ag/v6/quote?inputMint=...&outputMint=...&amount=...&slippageBps=100

# Jupiter V6 — swap (returns unsigned tx)
POST https://quote-api.jup.ag/v6/swap
{"quoteResponse": {...}, "userPublicKey": "..."}

# Birdeye wallet PnL
GET https://public-api.birdeye.so/wallet/v2/pnl?wallet=ADDRESS
Header: X-API-KEY: BIRDEYE_KEY

# RugCheck score
GET https://api.rugcheck.xyz/v1/tokens/MINT_ADDRESS/report/summary
```

---

*Research complete. Next step: build token deployment script and set up pump.fun launch infrastructure for Bobby.*
