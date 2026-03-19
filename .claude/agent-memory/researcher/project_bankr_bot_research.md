---
name: BANKR Bot Comprehensive Research
description: Full feature set, API, integrations, wallet architecture, and capabilities of BANKR Bot (bankr.bot) for integration planning
type: project
---

# BANKR Bot — Full Research Summary (2026-03-19)

## What It Is

Bankr is an AI-powered crypto trading agent that enables users to buy, sell, swap, and manage digital assets through natural language commands on social platforms and private interfaces. Founded by @0xDeployer, launched ~2023 on Farcaster before expanding to X.

**Backing**: Coinbase Ventures (Base Ecosystem Fund, Q3 2024 announcement)
**Adoption**: 70K+ active wallets, 1M+ messages sent, 100K+ transactions, $2M+ trading volume (early metrics)

---

## Platforms / Access Points

1. **X (Twitter)** — tag @bankrbot in public posts or DMs. Was suspended Oct 2025, reinstated same day. Community rallied with #FreeBankr.
2. **Farcaster** — original launch platform, still active
3. **Base App** — integrated into Coinbase's Base App
4. **XMTP** — on-chain messaging protocol integration (some features limited here — e.g., limit orders unavailable on XMTP)
5. **Private Terminal** — web UI at bankr.bot for private interactions, PnL tracking, transaction history
6. **Telegram** — launched then suspended Oct 2025, still suspended as of research date
7. **Agent API** — REST API for programmatic integration (bk_... API key)
8. **Bankr CLI** — npm package (`@bankr/cli`) for terminal-based control
9. **OpenClaw/MoltBot Skill** — plug-and-play agent skill for AI agent frameworks
10. **Claude Code Plugin** — direct integration via claude-plugins repo

---

## Supported Blockchain Networks

| Chain | Native Currency | Notes |
|-------|----------------|-------|
| Base | ETH | Primary chain. Gas SPONSORED by Bankr. Doppler/Uniswap V4 token launches |
| Ethereum | ETH | Full support |
| Polygon | POL | Full support |
| Unichain | ETH | Full support |
| Solana | SOL | Added 2025. Raydium launches. Bonding curve + LP fee model |

**Token standard**: Wallets auto-provisioned per user — cross-chain (EVM + Solana). No manual wallet setup. Privy server wallets backend.

---

## Wallet Architecture

- **Provider**: Privy server wallets (embedded, secure, managed on behalf of users)
- **Account linking**: X/Twitter account authentication triggers wallet provisioning tied to that user's X credentials
- **Key abstraction**: Users never see seed phrases, browser extensions, or private keys. Fully abstracted.
- **Delegation**: Bankr can execute transactions on behalf of users via authorization key delegation
- **Gas sponsorship**: Bankr covers gas on Base (and supported EVM chains), enabling zero-cost trades for users
- **Separate balances**: Trading wallet (on-chain crypto) vs. LLM credits (USD, separate balance for LLM gateway)

---

## Trading Features (Complete List)

### Order Types
- **Spot swaps** — instant buy/sell ("Buy $200 of $BNKR", "Swap 0.1 ETH to USDC")
- **Limit orders** — price-triggered buy/sell, supports % change, absolute USD price, or relative to another asset
  - Buy on dip: "buy 100 BNKR if it drops 10%"
  - Take profit: "sell my BNKR when it rises 20%"
  - Absolute: "sell when ETH hits $3,500"
  - Relative: "sell DEGEN when BTC reaches $50,000"
  - Manage: "show my limit orders", "cancel all my limit orders"
  - Note: EVM chains only (Base, ETH, Polygon, Unichain). NOT available on Solana or via XMTP.
- **Stop-loss** — "Stop loss for all holdings at -20%"
- **Take-profit** — combined with positions
- **DCA (Dollar Cost Averaging)** — "DCA $100 into ETH every week"
- **TWAP (Time-Weighted Average Price)** — spread large orders over time to minimize market impact
- **Conditional orders** — "Sell ETH if BTC drops 5%" (cross-asset triggers)
- **Leveraged trading** — available (specific platforms/chains not documented in detail)
- **Bridging** — cross-chain asset moves in one message ("bridge ETH from Base to Solana")

### DEX / Routing
- **0x Swap API** (v2) — primary order routing for best-in-class pricing across 9M+ tokens
- Aggregates liquidity across DEXes on all supported chains
- **Doppler Protocol** (Uniswap V4 hooks) — token launches on Base specifically
- **Raydium** — token launches and liquidity on Solana

---

## Portfolio & Tracking

- `bankr balances` — wallet balances across all chains (hides sub-$1 tokens by default)
- `bankr balances --low-value` — include tiny positions
- `bankr balances --chain <chain>` — filter by chain
- Private terminal: full PnL per trade, transaction history, real-time prices
- Natural language: "What is my ETH balance on Base?", "Show my portfolio"
- AI-driven analytics: real-time price and sentiment insights

---

## Automation / Alerts System

- Price-triggered orders (limit/stop) function as de facto alerts + execution
- DCA scheduling ("every week", "monthly")
- TWAP automation for large order execution
- No explicit "price alert without execution" documented — alerts are always tied to order execution

---

## Token Launch Features

### On Base (via Doppler Protocol / Uniswap V4):
- Fair launch mechanics — bonding curve protection limits whale accumulation and sniping
- Fee structure: **1.2% swap fee split** — Creator 57%, Bankr 36.1%, Ecosystem 1.9%, Protocol/Doppler 5%
- Agent receives **60% of trading fees** on Base
- Deploy API + Partner Deploy API available
- Fee claiming: `bankr fees` CLI command
- Launch command: `bankr launch`
- Doppler powers 40,000+ daily asset creations on Base, $1.5B+ aggregate value

### On Solana (via Raydium):
- Token deploy on Raydium
- During bonding curve: creators earn **0.5% per trade**
- Post-migration to LP: agent earns LP trading fees from **50% pool position**
- Bankr AI itself deployed $BNKR through Farcaster social feed (Feb 2025)

### Clanker Integration:
- Token creation handled by Clanker protocol on Base
- Automates token deployment, LP setup, fee mechanics
- Bankr described as "DeFAI terminal of the Clanker ecosystem"

### Notable Incident (March 2025):
- Grok (xAI) was responding to @bankrbot interactions and accidentally created 17 tokens, largest hitting $40M market cap
- Bankr disabled Grok interaction: "Grok was not built to responsibly manage its own wallet and safeguard its funds"

---

## DeFi Integrations

- **Polymarket** — prediction market betting via natural language ("bet $50 on X")
- **NFT** — buy, sell, manage collections across supported chains
- **Hydrex** — liquidity pool participation (lock HYDX for voting, deposit single-sided liquidity, claim oHYDX rewards)
- **Endaoment** — crypto donations to 501(c)(3) organizations, donor-advised fund deployment
- **Veil Cash** — privacy tools, shielded pools, zero-knowledge withdrawals
- **ENS** — domain name management across blockchain layers

---

## API Documentation

### Base URL
- Agent API: `https://api.bankr.bot`
- LLM Gateway: `https://llm.bankr.bot`

### Authentication
- Header: `X-API-Key: bk_YOUR_KEY`
- Key types: read-write (full), read-only (blocks write endpoints), LLM-only
- Security options: IP whitelisting (`allowedIps` on API key), 403 for non-whitelisted IPs

### Rate Limits
- Standard: 100 messages/day
- Bankr Club: 1,000/day
- Custom per key
- LLM Gateway: 60 requests/minute
- Rolling 24h window from first message

### REST Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/agent/prompt` | POST | Submit prompt (async) — returns jobId |
| `/agent/job/{jobId}` | GET | Poll job status |
| `/agent/job/{jobId}/cancel` | POST | Cancel running job |
| `/agent/balances` | GET | Wallet balances (sync, optional ?chains= filter) |
| `/agent/sign` | POST | Sign messages/transactions (sync) — 403 if read-only key |
| `/agent/submit` | POST | Submit raw transactions (sync) — 403 if read-only key |
| `/agent/me` | GET | User/wallet info |

### Async Job Workflow
1. POST to `/agent/prompt` → receive `jobId`
2. Poll `GET /agent/job/{jobId}` every 2s (up to 60 attempts)
3. Terminal states: `completed`, `failed`, `cancelled`
4. Response includes `threadId` for multi-turn conversation continuity

### SDK
- npm: `@bankr/sdk`
- Provides `BankrClient` with `promptAndWait()` method (auto-polls to completion)

### Environment Variables
```
BANKR_API_KEY   — API key
BANKR_API_URL   — Custom endpoint (default: https://api.bankr.bot)
BANKR_LLM_KEY   — LLM gateway key
BANKR_LLM_URL   — Custom LLM endpoint
BANKR_CONFIG    — Custom config path
```

### Config File: `~/.bankr/config.json`
Valid keys: `apiKey`, `apiUrl`, `llmKey`, `llmUrl`

---

## LLM Gateway

OpenAI-compatible proxy routing to multiple LLM providers through a single endpoint.

### Supported Models (as of research date)
- Anthropic: Claude Opus, Sonnet, Haiku (including claude-opus-4.6, claude-sonnet-4.6)
- Google: Gemini Pro, Flash (including gemini-3-flash)
- OpenAI: GPT-5.2, Codex, Mini, Nano
- Moonshot AI: Kimi K2.5
- Alibaba: Qwen3 Coder

### Credits System
- Credits are USD-denominated, separate from crypto wallet
- Top-up via USDC, ETH, BNKR, or other ERC-20 tokens on Base
- Auto top-up configurable: `bankr llm credits auto --enable`
- New accounts start at $0 — must top up before first LLM call (else 402 error)
- Usage visible at bankr.bot/llm

### IDE Integrations
- OpenClaw: `bankr llm setup openclaw --install`
- OpenCode: `bankr llm setup opencode --install`
- Claude Code: `bankr llm setup claude` (env vars)
- Cursor: `bankr llm setup cursor`

---

## OpenClaw / Skills Ecosystem

The skills repo (github.com/BankrBot/skills, 1K stars, 368 forks) has 16 plug-and-play tools:

| Skill | What It Does |
|-------|-------------|
| bankr | Core crypto trading, portfolio, DeFi, token launching |
| siwa | Sign-In With Agent (SIWA) auth for ERC-8004 agents |
| bankr-signals | On-chain verified trading signals on Base (by Axiom) |
| botchan | On-chain agent messaging on Base (permanent storage) |
| endaoment | Crypto donations to 501(c)(3) nonprofits |
| ens-primary-name | ENS domain management across layers |
| erc-8004 | Agent identity NFTs (ERC-721 with metadata + trust scores) |
| onchainkit | Coinbase React components for wallet/tx UI |
| qrcoin | QR-based URL bidding auction on Base |
| veil | Privacy: shielded pools, ZK withdrawals |
| yoink | Social token-grabbing game |
| neynar | Full Farcaster API: post, like, recast, follow, search |
| quicknode | RPC access: Base, ETH, Polygon, Solana, Unichain |
| hydrex | LP participation: lock, vote, deposit, claim rewards |
| clanker | (Listed, no description) |
| zapper | (Listed, no description) |

---

## BANKR Signals (bankrsignals.com)

On-chain verified trading signal platform for autonomous agents on Base.

- Every signal requires a Base blockchain TX hash — no fake screenshots
- Agents register on-chain as Ethereum addresses
- Leaderboard with verified PnL, win rates, trade counts
- Signal data includes: entry price, leverage, reasoning, confidence score, exit confirmation
- Stats: 12 active agents, 312 verified trades, 34% avg win rate, +81.3% aggregate PnL
- Top performer: ClawdFred_HL — 238 consecutive verified trades, 99% win rate
- Free weekly digest email
- Provider onboarding: `curl -s bankrsignals.com/api/onboard | bash`
- Created by Axiom (clawbots.org), MIT license, open-source

---

## Security System (Sentinel)

All transactions pass through Bankr's "Sentinel" system:
- Checks for malicious contracts
- Phishing detection
- Unusual pattern flagging
- Prompt injection attack protection
- Hallucination guards built into skills

---

## BNKR Token

- **Network**: Base blockchain
- **Type**: ERC-20 utility token
- **Total supply**: 100 billion
- **Launch**: February 2025 (deployed by Bankr AI agent itself through Farcaster)
- **No ICO** — organic launch
- **Utility**: Transaction fees, staking rewards, governance, ecosystem funding
- **Trading**: Uniswap V3, Aerodrome, Uniswap V4 on Base
- **ACP Integration**: January 2026 — integrated with Virtuals Protocol's Agent Commerce Protocol, enabling other virtual agents to access Bankr's swap execution via standardized onchain protocols

---

## ERC-8004 (Agent Identity Standard)

- Went live on Ethereum mainnet January 29, 2026
- ERC-721 NFTs representing agent identities with metadata, capabilities, trust scores
- Bankr supports SIWA (Sign-In With Agent) for ERC-8004 registered agents
- Enables agents to discover each other, build verifiable reputations, and collaborate securely
- Bankr wallet address used as agent's on-chain identity

---

## Self-Sustaining Agent Model

The core value proposition for builders:
1. Agent gets Bankr wallet (auto-provisioned, gas sponsored)
2. Launch token via Bankr API → earn 57% of 1.2% swap fees on every trade
3. Fee revenue flows to agent treasury automatically
4. Treasury funds LLM compute costs (via LLM Gateway credits)
5. No per-request API costs + no gas fees = breakeven at low volume

---

## Authentication / Account Linking

- **X/Twitter**: Tag @bankrbot, wallet created tied to X account
- **Email OTP**: `bankr login email <address>` then verify with `--code <otp>`
- **API key**: `bankr login --api-key <key>` for programmatic access
- **Read-Only mode**: `--read-write` flag required to enable write operations
- **LLM mode**: `--llm` flag enables LLM gateway access separately

---

## Known Limitations / Gotchas

- Limit orders: EVM chains only, NOT on Solana or XMTP
- LLM credits and crypto wallet are completely separate — having crypto ≠ having LLM credits
- New accounts start with $0 LLM credits (402 error if you call LLM before topping up)
- Standard rate limit: 100 messages/day (1,000 for Bankr Club)
- Telegram suspension (Oct 2025) — still suspended as of research date
- Grok disabled from interacting after accidental token creation spree (March 2025)
- Price targets on limit orders are approximate — depend on DEX liquidity at execution
- Orders expire if balance becomes insufficient

---

## Integration with Otto

Otto can integrate with BANKR as:
1. **Agent API consumer** — use `POST /agent/prompt` to execute trades, check balances, launch tokens
2. **LLM Gateway user** — route LLM calls through Bankr's proxy (access Claude, GPT, Gemini)
3. **Skill user** — install bankr-signals, neynar, quicknode skills for expanded capabilities
4. **Token launcher** — deploy $KOINK or other tokens via Bankr's Doppler integration
5. **Signal provider** — register on bankrsignals.com, publish verified trades as proof-of-performance

**Key API pattern for Otto**:
```python
# Submit
resp = requests.post("https://api.bankr.bot/agent/prompt",
    headers={"X-API-Key": "bk_...", "Content-Type": "application/json"},
    json={"prompt": "Buy $50 of ETH on Base", "threadId": thread_id})
job_id = resp.json()["jobId"]

# Poll
while True:
    status = requests.get(f"https://api.bankr.bot/agent/job/{job_id}",
        headers={"X-API-Key": "bk_..."}).json()
    if status["status"] in ("completed", "failed", "cancelled"):
        break
    time.sleep(2)
```

---

## Sources

- https://docs.bankr.bot/ (official docs)
- https://docs.bankr.bot/getting-started/overview/
- https://docs.bankr.bot/features/trading/limit-orders/
- https://docs.bankr.bot/llm-gateway/overview/
- https://docs.bankr.bot/llm-gateway/openclaw/
- https://docs.bankr.bot/guides/self-sustaining-agent/
- https://docs.bankr.bot/openclaw/available-skills/
- https://github.com/BankrBot/openclaw-skills/blob/main/bankr/SKILL.md
- https://github.com/BankrBot/skills
- https://bankrsignals.com/
- https://0x.org/case-studies/bankr
- https://privy.io/blog/bankrbot-case-study
- https://phemex.com/academy/what-is-bankrcoin-bnkr-ai-trading-web3
- https://thedefiant.io/news/defi/trading-bot-bankr-adds-solana-support
- https://theblock.co/post/374119/bankr-back-live-x
- https://theblock.co/post/346027/bankrbot-ends-groks-unintentional-token-creation-spree-by-disabling-interactions-on-x
- https://www.ainvest.com/news/coinbase-ventures-backs-ai-platform-bankr-boost-blockchain-integration-autonomous-financial-systems-2507/
